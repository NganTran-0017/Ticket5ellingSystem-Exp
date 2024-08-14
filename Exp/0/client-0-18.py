import socket
import threading
import logging
import time

server_prog = input('Enter the server program name: ')
client_prog = input('Enter the client program name: ')

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    handlers=[
                        logging.FileHandler("{}-{}.log".format(client_prog, server_prog)),  # Log file name
                        logging.StreamHandler()  # Log to stdout
                    ])

hostname = 'localhost'
tcp_port = 12345  # Example TCP port for server connection
udp_port = tcp_port + 1  # UDP port is one more than the TCP port
other_client_address = (hostname, udp_port)  # Assuming both clients know each other's address

def udp_listener(udp_socket, stop_event, ticket_db, user_balance):
    """ Listens for messages on the UDP socket and handles scalping requests. """
    last_message_time = time.time()
    try:
        while not stop_event.is_set():
            if time.time() - last_message_time > 180:  # 3 minutes timeout
                break
            try:
                data, addr = udp_socket.recvfrom(1024)
                if data:
                    message = data.decode()
                    logging.debug(f"Received via UDP from {addr}: {message}")
                    last_message_time = time.time()
                    handle_udp_message(message, udp_socket, ticket_db, user_balance)
            except socket.timeout:
                continue
    except Exception as e:
        logging.error(f"UDP Listener error: {e}")
    finally:
        udp_socket.close()
        logging.info("UDP connection closed.")
        stop_event.set()

def handle_udp_message(message, udp_socket, ticket_db, user_balance):
    """ Handles incoming messages from the other client. """
    parts = message.split()
    if parts[0] == "SCALP":
        buyer_balance = int(parts[1])
        if ticket_db:
            ticket_number, ticket_price = next(iter(ticket_db.items()))
            if buyer_balance >= 2 * ticket_price:
                response = f"{ticket_number} {2 * ticket_price}"
                udp_socket.sendto(response.encode(), other_client_address)
                logging.debug(f"Sent SCALP response: {response}")
            else:
                udp_socket.sendto(b"NOMONEY", other_client_address)
                logging.debug("Sent SCALP response: NOMONEY")
        else:
            udp_socket.sendto(b"NOMONEY", other_client_address)
            logging.debug("Sent SCALP response: NOMONEY")

def send_requests_to_server(tcp_socket, ticket_db, user_balance):
    """ Function to handle automated buy/sell requests to the server """
    for _ in range(15):  # Simulate 15 transactions
        try:
            message = f"BUY {user_balance[0]}"
            tcp_socket.sendall(message.encode())
            logging.debug(f"Sent to server: {message}")

            response = tcp_socket.recv(1024).decode()
            logging.debug(f"Received from server: {response}")

            if "NOFUNDS" in response:
                sell_ticket(tcp_socket, ticket_db, user_balance)
            elif "SOLDOUT" in response:
                become_scalper(user_balance)
            elif response:
                ticket_number, price = response.split()
                ticket_db[ticket_number] = int(price)
                user_balance[0] -= int(price)

        except Exception as e:
            logging.error(f"Error during BUY/SELL transactions: {e}")
            break

    logging.info(f"Final user balance: {user_balance[0]}")
    logging.info("Final ticket database:")
    for ticket, price in ticket_db.items():
        logging.info(f"Ticket #{ticket}: Price {price}")

def become_scalper(user_balance):
    logging.info("Client has become a scalper due to SOLDOUT.")
    message = f"SCALP {user_balance[0]}"
    udp_socket.sendto(message.encode(), other_client_address)
    logging.debug(f"Sent to other client: {message}")

def main():
    user_balance = [4000]  # Using a list to maintain reference
    ticket_db = {}
    stop_event = threading.Event()

    # Initialize UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.bind((hostname, udp_port))
    udp_socket.settimeout(1.0)  # Set a short timeout for responsiveness
    logging.debug(f"Client bound UDP socket to port {udp_port}")

    udp_thread = threading.Thread(target=udp_listener, args=(udp_socket, stop_event, ticket_db, user_balance))
    udp_thread.start()

    # Initialize TCP connection and handle buy/sell requests
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.connect((hostname, tcp_port))
    logging.debug("TCP connection established with server.")

    send_requests_to_server(tcp_socket, ticket_db, user_balance)

    # Clean up connections
    tcp_socket.close()
    logging.info("TCP connection closed.")
    stop_event.set()
    udp_thread.join()

if __name__ == "__main__":
    main()
