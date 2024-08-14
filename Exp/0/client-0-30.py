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

def udp_listener(udp_socket, stop_event, ticket_db, user_balance, tcp_socket, transaction_complete):
    """ Listens for messages on the UDP socket and handles scalping requests. """
    last_message_time = time.time()
    try:
        while not stop_event.is_set():
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
                # Check if 3 minutes have passed since the last message
                if time.time() - last_message_time > 180:
                    logging.debug("No activity on UDP for 3 minutes, considering transactions complete.")
                    break
            except Exception as e:
                logging.error(f"Error processing UDP data: {e}")
    finally:
        udp_socket.close()
        logging.info("UDP connection closed.")


def handle_udp_message(message, udp_socket, ticket_db, user_balance, addr, tcp_socket, transaction_complete):
    """ Processes received messages via UDP and performs actions based on the message type. """
    parts = message.split()
    command = parts[0]

    if command == "SCALP":
        # This client is the scalper and should respond to a scalping request
        buyer_balance = int(parts[1])
        if ticket_db:
            ticket_number, ticket_price = min(ticket_db.items(), key=lambda x: x[1])
            doubled_price = 2 * ticket_price
            if buyer_balance >= doubled_price:
                # Buyer can afford the scalped ticket, proceed with transaction
                response = f"{ticket_number} {doubled_price}"
                udp_socket.sendto(response.encode(), addr)
                # Update scalper's database and balance
                del ticket_db[ticket_number]
                user_balance[0] += doubled_price
                logging.debug(f"Scalped ticket {ticket_number} sold for {doubled_price}")
            else:
                # Buyer cannot afford, send NOMONEY
                udp_socket.sendto(b"NOMONEY", addr)
                logging.debug("Sent NOMONEY to buyer due to insufficient funds")
        else:
            udp_socket.sendto(b"Scalper is sold-out", addr)
            logging.debug("No tickets available to scalp")

    elif parts[0].isdigit() and len(parts) == 2:
        # This client is the buyer and needs to update their ticket database and balance
        ticket_number, ticket_price = parts
        ticket_price = int(ticket_price)
        # Update buyer's ticket database and balance
        ticket_db[ticket_number] = ticket_price
        user_balance[0] -= ticket_price
        logging.debug(f"Bought scalped ticket {ticket_number} for {ticket_price}")
        transaction_complete.set()  # Complete the transaction after updating database and balance

    elif message == "NOMONEY":
        # Buyer received NOMONEY, must sell a ticket to acquire funds
        if ticket_db:
            sell_ticket(tcp_socket, ticket_db, user_balance)
        transaction_complete.set()  # After selling a ticket, transaction is complete

    else:
        # Log any other unexpected messages
        logging.debug(f"Received unexpected message: {message}")


def send_requests_to_server(tcp_socket, udp_socket, ticket_db, user_balance, transaction_complete):
    """ Handles automated buy/sell requests to the server """
    for _ in range(15):
        transaction_complete.wait()  # Wait here if the previous loop iteration set it to wait
        transaction_complete.clear()  # Clear it to handle next message
        message = f"BUY {user_balance[0]}"
        tcp_socket.sendall(message.encode())
        response = tcp_socket.recv(1024).decode()
        logging.debug(f"Received from server: {response}")

        if "NOFUNDS" in response:
            sell_ticket(tcp_socket, ticket_db, user_balance)
            transaction_complete.set()  # Transaction complete, move to next
        elif "SOLDOUT" in response:
            become_scalper(user_balance, udp_socket)
            # Do not set the transaction_complete here; wait for UDP transaction to complete
        else:
            ticket_number, price = response.split()
            ticket_db[ticket_number] = int(price)
            user_balance[0] -= int(price)
            transaction_complete.set()  # Transaction complete, move to next

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
    logging.info(f"Client initiated scalping transaction due to SOLDOUT. {message}")

def main():
    user_balance = [4000]  # Using a list to maintain reference
    ticket_db = {}
    stop_event = threading.Event()
    transaction_complete = threading.Event()
    transaction_complete.set()  # Initially set

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

    udp_thread = threading.Thread(target=udp_listener, args=(udp_socket, stop_event, ticket_db, user_balance, tcp_socket, transaction_complete))
    udp_thread.start()

    send_requests_to_server(tcp_socket, udp_socket, ticket_db, user_balance, transaction_complete)

    # Ensure UDP connection is closed first
    stop_event.set()
    udp_thread.join()
    logging.info("UDP connection properly closed.")

    # Close TCP connection afterwards
    tcp_socket.close()
    logging.info("TCP connection closed.")

if __name__ == "__main__":
    main()
