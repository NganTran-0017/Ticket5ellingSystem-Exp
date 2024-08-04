import socket
import threading
import random
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

# Initialize client variables
user_balance = 4000
ticket_db = {}  # Local ticket database
hostname = 'localhost'
tcp_port = 12345
udp_port = tcp_port + 1  # UDP port is one more than the TCP port

def udp_listener():
    """ Listens for messages on the UDP socket """
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind((hostname, udp_port))

    while True:
        try:
            data, addr = udp_sock.recvfrom(1024)
            message = data.decode()
            logging.info(f"Received SCALP request: {message} from {addr}")
            # Process SCALP request here (not implemented in this snippet)
        except Exception as e:
            logging.error(f"UDP Listener error: {e}")
            break

    udp_sock.close()

def send_requests_to_server(tcp_socket):
    """ Sends automated BUY requests to the server and handles responses """
    global user_balance

    for _ in range(15):  # Simulate 15 transactions
        try:
            request = f"BUY {user_balance}"
            tcp_socket.sendall(request.encode())
            logging.info(f"Sent to server: {request}")

            response = tcp_socket.recv(1024).decode()
            logging.info(f"Received from server: {response}")

            if response.startswith('NOFUNDS'):
                # Select a ticket to sell (simplified: select the first one)
                if ticket_db:
                    ticket_number, ticket_price = next(iter(ticket_db.items()))
                    sell_request = f"SELL {ticket_number}"
                    tcp_socket.sendall(sell_request.encode())
                    user_balance += ticket_price
                    del ticket_db[ticket_number]
                    logging.info(f"Sold ticket {ticket_number} back to server, updated balance: {user_balance}")
            elif response.startswith('SOLDOUT'):
                # Process buying tickets from scalper here (not implemented)
                pass
            else:
                ticket_number, price = response.split()
                ticket_db[ticket_number] = int(price)
                user_balance -= int(price)
                logging.info(f"Bought ticket {ticket_number} for ${price}, updated balance: {user_balance}")

        except Exception as e:
            logging.error(f"Error during transaction: {e}")
            break

    tcp_socket.close()
    logging.info("Client TCP connection closed.")

def start_client():
    # Connect to the server
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.connect((hostname, tcp_port))

    # Set up UDP listener in a separate thread
    udp_thread = threading.Thread(target=udp_listener)
    udp_thread.start()

    # Send requests to the server
    send_requests_to_server(tcp_socket)

    logging.info("Waiting for UDP listener to finish...")
    udp_thread.join()
    logging.info("Client operations completed. Client ticket database: %s", ticket_db)

if __name__ == "__main__":
    start_client()
