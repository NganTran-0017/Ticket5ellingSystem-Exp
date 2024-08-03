import socket
import threading
import random
from collections import defaultdict

# Global lock for thread safety
lock = threading.Lock()

# Global ticket database
tickets = {f"{10000 + i}": {"price": random.randint(200, 400), "sold": False} for i in range(25)}


def handle_client(client_socket, address):
    global tickets
    transaction_log = []

    while True:
        try:
            data = client_socket.recv(1024).decode('utf-8').strip()
            if not data:
                break

            print(f"Received from {address}: {data}")
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

            # Process SELL request
            elif cmd == "SELL":
                ticket_number = args[0]
                with lock:
                    if ticket_number in tickets and tickets[ticket_number]['sold']:
                        tickets[ticket_number]['sold'] = False
                        response = f"{ticket_number} {tickets[ticket_number]['price']}"
                        transaction_log.append((ticket_number, 'SELL'))
                        client_socket.sendall(response.encode())
                    else:
                        client_socket.sendall("ERROR".encode())

        except Exception as e:
            print(f"Error with client {address}: {e}")
            break

    client_socket.close()
    print(f"Transaction log for {address}: {transaction_log}")


def start_server(port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', port))
    server_socket.listen(2)

    print("Initial Tickets:")
    for ticket, details in tickets.items():
        print(f"Ticket #{ticket}, Price: ${details['price']}, Sold: {details['sold']}")

    clients = []
    try:
        while len(clients) < 2:
            client_socket, addr = server_socket.accept()
            print(f"Connected with {addr}")
            client_thread = threading.Thread(target=handle_client, args=(client_socket, addr))
            client_thread.start()
            clients.append(client_thread)
    except KeyboardInterrupt:
        print("Server is shutting down...")

    for thread in clients:
        thread.join()

    print("Final Tickets:")
    for ticket, details in tickets.items():
        print(f"Ticket #{ticket}, Price: ${details['price']}, Sold: {details['sold']}")

    server_socket.close()


if __name__ == "__main__":
    random.seed(10)
    start_server(12345)
