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
                        logging.FileHandler("{}-{}.log".format(server_prog, client_prog)),
                        logging.StreamHandler()
                    ])

hostname = 'localhost'
tcp_port = 12345  # TCP port for server connection
udp_port = tcp_port + 1  # UDP port is one more than the TCP port
other_client_address = (hostname, udp_port)  # Address of the other client

def udp_listener(udp_socket, stop_event, ticket_db, user_balance, tcp_socket):
    """ Listens for messages on the UDP socket and handles scalping requests. """
    last_message_time = time.time()
    try:
        while not stop_event.is_set():
            if time.time() - last_message_time > 180:  # 3 minutes timeout
                logging.debug("No activity on UDP for 3 minutes, closing listener.")
                break
            try:
                data, addr = udp_socket.recvfrom(1024)
                if data:
                    message = data.decode()
                    print(f"Received via UDP from {addr} to {udp_socket.getsockname()}: {message}")
                    if addr != udp_socket.getsockname():  # Ensure not processing own messages
                        logging.debug(f"Received via UDP from {addr}: {message}")
                        handle_udp_message(message, udp_socket, ticket_db, user_balance, addr, tcp_socket)
                        last_message_time = time.time()
            except socket.timeout:
                continue
    except Exception as e:
        logging.error(f"UDP Listener error: {e}")
    finally:
        udp_socket.close()
        logging.info("UDP connection closed.")

def handle_udp_message(message, udp_socket, ticket_db, user_balance, addr, tcp_socket):
    """ Handles incoming messages from the other client. """
    parts = message.split()
    if parts[0] == "SCALP":
        buyer_balance = int(parts[1])
        # Find the minimum priced ticket to offer
        if ticket_db:
            ticket_number, ticket_price = min(ticket_db.items(), key=lambda x: x[1])
            if buyer_balance >= 2 * ticket_price:
                response = f"{ticket_number} {2 * ticket_price}"
                udp_socket.sendto(response.encode(), addr)
                user_balance[0] += 2 * ticket_price  # Update scalper's balance
                del ticket_db[ticket_number]  # Remove the sold ticket
                logging.debug(f"Sent SCALP response: {response} to {addr}")
            else:
                udp_socket.sendto(b"NOMONEY", addr)
                logging.debug(f"Sent NOMONEY to {addr}")
        else:
            udp_socket.sendto(b"Scalper is sold-out", addr)
            logging.debug(f"Sent Scalper is sold-out to {addr}")
    elif parts[0].isdigit() and len(parts) == 2:  # Buyer received a ticket offer
        ticket_number, price = parts
        price = int(price)
        if user_balance[0] >= price:
            ticket_db[ticket_number] = price
            user_balance[0] -= price
            logging.info(f"Bought ticket #{ticket_number} for {price}, remaining balance: {user_balance[0]}")
        else:
            logging.debug("Not enough funds to buy scalped ticket, sending back NOMONEY")
            udp_socket.sendto(b"NOMONEY", other_client_address)
            if ticket_db:
                sell_ticket(tcp_socket, ticket_db, user_balance)  # Try selling a ticket to get funds

def send_requests_to_server(tcp_socket, udp_socket, ticket_db, user_balance):
    """ Handles automated buy/sell requests to the server """
    for _ in range(15):
        message = f"BUY {user_balance[0]}"
        tcp_socket.sendall(message.encode())
        logging.debug(f"Sent to server: {message}")

        response = tcp_socket.recv(1024).decode()
        logging.debug(f"Received from server: {response}")

        if "NOFUNDS" in response:
            sell_ticket(tcp_socket, ticket_db, user_balance)
        elif "SOLDOUT" in response:
            become_scalper(user_balance, udp_socket)
        elif response:
            ticket_number, price = response.split()
            ticket_db[ticket_number] = int(price)
            user_balance[0] -= int(price)

def sell_ticket(tcp_socket, ticket_db, user_balance):
    """ Sells a ticket back to the server. """
    if ticket_db:
        ticket_number, ticket_price = next(iter(ticket_db.items()))
        sell_message = f"SELL {ticket_number}"
        tcp_socket.sendall(sell_message.encode())
        received_message = tcp_socket.recv(1024).decode()
        user_balance[0] += ticket_price
        del ticket_db[ticket_number]
        logging.debug(f"Sent SELL to server: {sell_message}, received: {received_message}")

def become_scalper(user_balance, udp_socket):
    """ Initiates scalping transaction due to SOLDOUT. """
    message = f"SCALP {user_balance[0]}"
    udp_socket.sendto(message.encode(), other_client_address)
    logging.info("Client initiated scalping transaction due to SOLDOUT.")

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

    # Initialize TCP connection and handle buy/sell requests
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.connect((hostname, tcp_port))
    logging.debug("TCP connection established with server.")

    udp_thread = threading.Thread(target=udp_listener, args=(udp_socket, stop_event, ticket_db, user_balance, tcp_socket))
    udp_thread.start()

    send_requests_to_server(tcp_socket, udp_socket, ticket_db, user_balance)

    # Ensure UDP connection is closed first
    stop_event.set()
    udp_thread.join()
    logging.info("UDP connection properly closed.")

    # Close TCP connection afterwards
    tcp_socket.close()
    logging.info("TCP connection closed.")

if __name__ == "__main__":
    main()
