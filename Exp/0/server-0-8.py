import socket
import threading
import random
import logging

server_prog = input('Enter the server program name: ')
client_prog = input('Enter the client program name: ')

# Set up logging
logging.basicConfig(level=logging.DEBUG,  # Set logging to debug level
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    handlers=[
                        logging.FileHandler("{}-{}.log".format(server_prog, client_prog)),
                        logging.StreamHandler()
                    ])

# Lock for thread safety in modifying shared resources
lock = threading.Lock()

# Initialize ticket database
tickets = {f"{10000 + i}": {"price": random.randint(200, 400), "sold": False} for i in range(25)}

# List to track client threads
client_threads = []

def handle_client(client_socket, address):
    global tickets
    logging.debug(f"Client connected: {address}")

    try:
        while True:
            data = client_socket.recv(1024).decode('utf-8').strip()
            if not data:
                break

            logging.debug(f"Received from {address}: {data}")
            cmd, *args = data.split()

            response = "UNKNOWN COMMAND"
            with lock:
                if cmd == "BUY":
                    user_balance = int(args[0])
                    for ticket, details in tickets.items():
                        if not details['sold'] and user_balance >= details['price']:
                            details['sold'] = True
                            response = f"{ticket} {details['price']}"
                            break
                    else:
                        response = "SOLDOUT" if all(t['sold'] for t in tickets.values()) else "NOFUNDS"
                elif cmd == "SELL":
                    ticket_number = args[0]
                    if tickets.get(ticket_number, {}).get('sold', False):
                        tickets[ticket_number]['sold'] = False
                        response = f"{ticket_number} {tickets[ticket_number]['price']}"

            client_socket.sendall(response.encode())
            logging.debug(f"Sent to {address}: {response}")

    except Exception as e:
        logging.error(f"Error handling client {address}: {e}")

    finally:
        client_socket.close()
        logging.debug(f"Client disconnected: {address}")

def start_server(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', port))
    server_socket.listen(2)  # Expecting only 2 clients
    logging.info("Server started and waiting for clients.")

    try:
        while len(client_threads) < 2:
            client_socket, addr = server_socket.accept()
            thread = threading.Thread(target=handle_client, args=(client_socket, addr))
            thread.start()
            client_threads.append(thread)

        # Wait for all client threads to finish
        for thread in client_threads:
            thread.join()

    finally:
        logging.info("All clients have disconnected. Final ticket status:")
        for ticket, details in tickets.items():
            logging.info(f"Ticket #{ticket}: Price ${details['price']}, Sold {details['sold']}")

        server_socket.close()
        logging.info("Server shutdown.")

if __name__ == "__main__":
    start_server(12345)
