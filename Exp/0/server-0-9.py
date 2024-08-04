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

# Initialize ticket database
tickets = {f"{10000 + i}": {"price": random.randint(200, 400), "sold": False} for i in range(25)}

# Connection barrier to ensure both clients are connected before processing starts
connection_barrier = threading.Barrier(2)  # Waiting for 2 clients


def handle_client(client_socket, address):
    global tickets
    # Wait for both clients to connect
    connection_barrier.wait()

    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            data = data.decode('utf-8').strip()

            logging.debug(f"Received from {address}: {data}")
            cmd, *args = data.split()

            with lock:
                if cmd == "BUY":
                    user_balance = int(args[0])
                    response = "SOLDOUT"
                    for ticket, details in tickets.items():
                        if not details['sold'] and user_balance >= details['price']:
                            details['sold'] = True
                            response = f"{ticket} {details['price']}"
                            break
                    client_socket.sendall(response.encode())
                    logging.debug(f"Sent to {address}: {response}")

                elif cmd == "SELL":
                    ticket_number = args[0]
                    if tickets[ticket_number]['sold']:
                        tickets[ticket_number]['sold'] = False
                        response = f"{ticket_number} {tickets[ticket_number]['price']}"
                        client_socket.sendall(response.encode())
                        logging.debug(f"Sent to {address}: {response}")

    except Exception as e:
        logging.error(f"Error with client {address}: {e}")
    finally:
        logging.info(f"Client {address} disconnected.")
        #client_socket.close()


def start_server(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', port))
    server_socket.listen(2)  # Expecting only 2 clients
    logging.info("Server is ready and waiting for clients.")

    threads = []
    try:
        for _ in range(2):  # We expect exactly 2 clients
            client_socket, addr = server_socket.accept()
            logging.info(f"Client {addr} connected.")
            thread = threading.Thread(target=handle_client, args=(client_socket, addr))
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            client_socket.close()

    finally:
        logging.info("All clients have disconnected. Final ticket database:")
        for ticket, details in tickets.items():
            logging.info(f"Ticket #{ticket}: Price ${details['price']}, Sold {details['sold']}")

        server_socket.close()
        logging.info("Server has shut down.")


if __name__ == "__main__":
    start_server(12345)
