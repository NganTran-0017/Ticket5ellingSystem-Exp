import socket
import threading
import logging
import sys

server_prog = input('Enter the server program name: ')
client_prog = input('Enter the client program name: ')

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("{}-{}.log".format(client_prog, server_prog)),  # Log file name
                        logging.StreamHandler()
                    ])

hostname = 'localhost'
tcp_port = 12345  # Example TCP port for server connection
udp_port = tcp_port + 1  # UDP port is one more than the TCP port


def udp_listener(udp_socket):
    """ Listens for messages on the UDP socket. Both clients will use this method. """
    try:
        while True:
            data, addr = udp_socket.recvfrom(1024)
            message = data.decode()
            logging.debug(f"Received via UDP from {addr}: {message}")
            # Handle incoming messages based on protocol logic here
    except Exception as e:
        logging.error(f"UDP Listener error: {e}")


def send_requests_to_server(tcp_socket):
    """ Function to handle automated buy/sell requests to the server """
    user_balance = 4000
    ticket_db = {}

    for _ in range(15):  # Simulate 15 transactions
        try:
            message = f"BUY {user_balance}"
            tcp_socket.sendall(message.encode())
            logging.debug(f"Sent to server: {message}")

            response = tcp_socket.recv(1024).decode()
            logging.debug(f"Received from server: {response}")

            if "NOFUNDS" in response:
                # Assuming the client chooses to sell the first ticket for simplicity
                if ticket_db:
                    ticket_number, ticket_price = next(iter(ticket_db.items()))
                    sell_message = f"SELL {ticket_number}"
                    tcp_socket.sendall(sell_message.encode())
                    received_message = tcp_socket.recv(1024).decode()
                    logging.debug(f"Sent SELL to server: {sell_message}, received: {received_message}")
                    user_balance += ticket_price  # Update balance assuming server buys it back at price
                    del ticket_db[ticket_number]
            elif "SOLDOUT" not in response:
                ticket_number, price = response.split()
                ticket_db[ticket_number] = int(price)
                user_balance -= int(price)

        except Exception as e:
            logging.error(f"Error during BUY/SELL transactions: {e}")
            break


def main():
    # Initialize UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.bind((hostname, udp_port))
    logging.debug(f"Client bound UDP socket to port {udp_port}")

    udp_thread = threading.Thread(target=udp_listener, args=(udp_socket,))
    udp_thread.start()

    # Initialize TCP connection and handle buy/sell requests
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.connect((hostname, tcp_port))
    logging.debug("TCP connection established with server.")

    send_requests_to_server(tcp_socket)

    tcp_socket.close()

    logging.info("Waiting for UDP listener to finish...")
    udp_thread.join()
    udp_socket.close()


if __name__ == "__main__":
    main()
