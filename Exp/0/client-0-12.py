import socket
import threading
import logging

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

def main():
    # Initialize UDP socket
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.bind((hostname, udp_port))
    logging.debug(f"Client bound UDP socket to port {udp_port}")

    udp_thread = threading.Thread(target=udp_listener, args=(udp_socket,))
    udp_thread.start()

    # Example TCP client setup (simplified)
    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.connect((hostname, tcp_port))
    # Assume some communication to determine role, etc.

    tcp_socket.close()
    udp_thread.join()
    udp_socket.close()

if __name__ == "__main__":
    main()
