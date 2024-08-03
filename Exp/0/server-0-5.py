import socket
import threading
import random
import logging

server_prog = 'server-0-4-1'
client_prog = 'na'

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d',
                    handlers=[
                        logging.FileHandler("{}-{}.log".format(server_prog, client_prog)),  # Log file name
                        logging.StreamHandler()  # Log to stdout
                    ])

# Global lock for thread safety
lock = threading.Lock()

# Initialize ticket database
tickets = {f"{10000 + i}": {"price": random.randint(200, 400), "sold": False} for i in range(25)}


def handle_client(client_socket, address):
    global tickets
    transaction_log = []

    while True:
        try:
            data = client_socket.recv(1024).decode('utf-8').strip()
            if not data:
                break

            logging.info(f"Received from {address}: {data}")  # Log received data
            cmd, *args = data.split()

            # Process BUY request
            if cmd == "BUY":
                user_balance = int(args[0])
                response = "SOLDOUT"
                with lock:
                    for ticket, details in tickets.items():
                        if not details['sold'] and user_balance >= details['price']:
                            details['sold'] = True
                            response = f"{ticket} {details['price']}"
                            transaction_log.append((ticket, 'BUY'))
                            break
                        elif not details['sold']:
                            response = "NOFUNDS"
                            break
                client_socket.sendall(response.encode())
                logging.info(f"Sent to {address}: {response}")  # Log sent data

            # Process SELL request
            elif cmd == "SELL":
                ticket_number = args[0]
                with lock:
                    if ticket_number in tickets and tickets[ticket_number]['sold']:
                        tickets[ticket_number]['sold'] = False
                        response = f"{ticket_number} {tickets[ticket_number]['price']}"
                        transaction_log.append((ticket_number, 'SELL'))
                        client_socket.sendall(response.encode())
                        logging.info(f"Sent to {address}: {response}")  # Log sent data
                    else:
                        error_msg = "ERROR"
                        client_socket.sendall(error_msg.encode())
                        logging.info(f"Sent to {address}: {error_msg}")  # Log error sent

        except Exception as e:
            logging.error(f"Error with client {address}: {e}")
            break

    client_socket.close()
    logging.info(f"Transaction log for {address}: {transaction_log}")


def start_server(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', port))
    server_socket.listen(2)

    logging.info("Server started, waiting for clients.")
    logging.info("Initial Tickets:")
    for ticket, details in tickets.items():
        logging.info(f"Ticket #{ticket}, Price: ${details['price']}, Sold: {details['sold']}")

    clients = []
    try:
        while len(clients) < 2:
            client_socket, addr = server_socket.accept()
            logging.info(f"Connected with {addr}")
            client_thread = threading.Thread(target=handle_client, args=(client_socket, addr))
            client_thread.start()
            clients.append(client_thread)
    except KeyboardInterrupt:
        logging.info("Server shutdown initiated by KeyboardInterrupt.")

    for thread in clients:
        thread.join()

    logging.info("Final Tickets:")
    for ticket, details in tickets.items():
        logging.info(f"Ticket #{ticket}, Price: ${details['price']}, Sold: {details['sold']}")

    server_socket.close()
    logging.info("Server has been shutdown.")


if __name__ == "__main__":
    random.seed(10)
    start_server(12345)
