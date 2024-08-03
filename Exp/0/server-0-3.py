
import logging.config
import  os
path = os.getcwd()
parent_dir = os.path.dirname(path)
print('Parent Dir:', parent_dir, ' \temp.conf')
program_name = 'server-0-3'
client_program_name = 'na'

log_filename = '{}-{}.log'.format(program_name, client_program_name)
# Full path to log file
full_log_path = os.path.join(path, log_filename)

# Set up basic configuration with dynamic filename
logging.basicConfig(
    filename=full_log_path,
    filemode='a',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d',
    level=logging.DEBUG  # Set to DEBUG to capture all levels of logs
)
# create logger
logger = logging.getLogger(program_name)
logger.info('Start execution')

import socket
import threading
import random

def handle_client(client_socket, address):
    while True:
        try:
            # Example: Receive data from client (actual implementation will vary)
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                logger.warning('No data received from client')
                break
            # Process data here (buy/sell logic)
            print(f"Received from {address}: {data}")
        except Exception as e:
            print(f"Error with client {address}: {e}")
            logger.error(f"Error with client {address}: {e}")
            break
    client_socket.close()
    logger.info(f"Client {address} disconnected")

def start_server(port):
    # Step 1: Initialize the server
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', port))
    server_socket.listen(2)  # Expecting only 2 clients
    logger.info(f"Server started on port {port}")

    # Step 2: Generate and manage tickets
    random.seed(10)  # Fixed seed for reproducibility
    tickets = {f"{10000 + i}": {"price": random.randint(200, 400), "sold": False} for i in range(25)}
    print("Initial Tickets:")
    logger.info("Initial Tickets: ")
    for ticket, details in tickets.items():
        print(f"Ticket #{ticket}, Price: ${details['price']}, Sold: {details['sold']}")
        logger.info(f"Ticket #{ticket}, Price: ${details['price']}, Sold: {details['sold']}")
    # Step 3: Handling client connections
    clients = []
    print('Waiting for clients to connect...')
    logger.info('Waiting for clients to connect...')
    try:
        while len(clients) < 2:
            client_socket, addr = server_socket.accept()
            print(f"Connected with {addr}")
            logger.info(f"Connected with Client {addr}")
            client_thread = threading.Thread(target=handle_client, args=(client_socket, addr))
            client_thread.start()
            clients.append(client_thread)
    except KeyboardInterrupt as ve:
        print("Server is shutting down...")
        logger.exception("Exception occurred: %s. Server is shutting down...", str(ve))

    # Join threads to wait for all to complete
    for thread in clients:
        thread.join()
    logger.info('All clients finished transactions.')

    # After all clients are handled
    print("Final Tickets:")
    logger.info("Final Tickets:")
    for ticket, details in tickets.items():
        print(f"Ticket #{ticket}, Price: ${details['price']}, Sold: {details['sold']}")
        logger.info(f"Ticket #{ticket}, Price: ${details['price']}, Sold: {details['sold']}")

    server_socket.close()
    print('Server closed!')
    logger.info('Server closed.')

if __name__ == "__main__":
    start_server(12345)  # Specify the port number
