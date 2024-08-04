import socket
import threading
import random
import logging

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

# Global lock for thread safety
lock = threading.Lock()

# Global ticket database
tickets = {f"{10000 + i}": {"price": random.randint(200, 400), "sold": False} for i in range(25)}

# Connection barrier to wait for both clients
connection_barrier = threading.Barrier(2)  # Set to 2, for two clients


def handle_client(client_socket, address):
    global tickets
    transaction_log = []

    # Wait for all clients to connect
    try:
        connection_barrier.wait()
    except threading.BrokenBarrierError:
        logging.error("Barrier is broken due to some client disconnection!")
        return

    while True:
        try:
            data = client_socket.recv(1024).decode('utf-8').strip()
            if not data:
                break

            logging.info(f"Received from {address}: {data}")
            cmd, *args = data.split()

            # Process BUY request
            if cmd == "BUY":
                user_balance = int(args[0])
                response = "SOLDOUT"
                with lock:
                    for ticket, details in tickets.items():
                        if not details['sold'] and user_balance >= details['price']:
                            if user_balance >= details['price']:
                                details['sold'] = True
                                response = f"{ticket} {details['price']}"
                                transaction_log.append((ticket, 'BUY'))
                                break
                            else:
                                response = "NOFUNDS"
                                break
                client_socket.sendall(response.encode())
                logging.info(f"Sent to {address}: {response}")

            # Process SELL request
            elif cmd == "SELL":
                ticket_number = args[0]
                with lock:
                    if ticket_number in tickets and tickets[ticket_number]['sold']:
                        tickets[ticket_number]['sold'] = False
                        response = f"{ticket_number} {tickets[ticket_number]['price']}"
                        transaction_log.append((ticket_number, 'SELL'))
                        client_socket.sendall(response.encode())
                        logging.info(f"Sent to {address}: {response}")
                    else:
                        client_socket.sendall("ERROR".encode())
                        logging.error(f"Sent to {address}: ERROR: Invalid ticket!")

        except Exception as e:
            logging.error(f"Error with client {address}: {e}")
            break

    client_socket.close()
    logging.info(f"Transaction log for {address}: {transaction_log}")


def start_server(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', port))
    server_socket.listen(2)  # Expecting exactly 2 clients

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
        logging.info("Server is shutting down...")

    # Wait for all threads to complete
    for thread in clients:
        thread.join()

    logging.info("Final Tickets:")
    for ticket, details in tickets.items():
        logging.info(f"Ticket #{ticket}, Price: ${details['price']}, Sold: {details['sold']}")

    server_socket.close()


if __name__ == "__main__":
    random.seed(10)
    start_server(12345)
