# network/server.py
import socket
import threading
import random
import json

class GameServer:
    def __init__(self, host='0.0.0.0', port=0):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = []
        self.client_lock = threading.Lock()
        self.is_running = False
        self.access_code = self.generate_access_code()
        self.on_receive = None # Callback for received data
        self.on_client_connect = None
        self.on_client_disconnect = None


    def generate_access_code(self):
        """Generates a random 4-digit access code."""
        return str(random.randint(1000, 9999))

    def start(self):
        """Starts the server and listens for connections."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        if self.port == 0:
            self.port = self.server_socket.getsockname()[1]
        
        self.server_socket.listen(2) # Listen for up to 2 clients
        self.is_running = True
        print(f"Server started on {self.host}:{self.port}, Access Code: {self.access_code}")

        thread = threading.Thread(target=self.accept_clients)
        thread.daemon = True
        thread.start()

    def accept_clients(self):
        """Accepts incoming client connections."""
        while self.is_running:
            try:
                client_socket, addr = self.server_socket.accept()
                print(f"Connection from {addr}")
                thread = threading.Thread(target=self.handle_client, args=(client_socket, addr))
                thread.daemon = True
                thread.start()
            except OSError:
                # Server socket has been closed
                break

    def handle_client(self, client_socket, addr):
        """Handles a single client connection."""
        try:
            # 1. Access Code Verification
            message = client_socket.recv(1024).decode('utf-8')
            data = json.loads(message)

            if data.get('code') != self.access_code:
                print(f"Authentication failed for {addr}.")
                client_socket.send(json.dumps({"status": "denied", "message": "Invalid access code"}).encode('utf-8'))
                client_socket.close()
                return

            client_socket.send(json.dumps({"status": "accepted"}).encode('utf-8'))
            
            with self.client_lock:
                self.clients.append(client_socket)
            
            if self.on_client_connect:
                self.on_client_connect(client_socket)


            # 2. Listen for messages
            while self.is_running:
                message = client_socket.recv(1024).decode('utf-8')
                if not message:
                    break
                
                if self.on_receive:
                    self.on_receive(message, client_socket)

        except (ConnectionResetError, json.JSONDecodeError):
            print(f"Connection lost with {addr}")
        finally:
            with self.client_lock:
                self.clients.remove(client_socket)
            
            if self.on_client_disconnect:
                self.on_client_disconnect(client_socket)

            client_socket.close()

    def broadcast(self, message: str, sender_socket=None):
        """Broadcasts a message to all clients, optionally excluding the sender."""
        with self.client_lock:
            for client in self.clients:
                if client is not sender_socket:
                    try:
                        client.send(message.encode('utf-8'))
                    except:
                        # Handle broken pipe
                        self.clients.remove(client)

    def stop(self):
        """Stops the server."""
        self.is_running = False
        with self.client_lock:
            for client in self.clients:
                client.close()
        self.server_socket.close()
        print("Server stopped.")

if __name__ == '__main__':
    # Test
    server = GameServer()
    server.start()

    def receive_callback(msg, sender):
        print(f"Received from client: {msg}")
        server.broadcast(msg, sender)
    
    server.on_receive = receive_callback

    try:
        while True:
            pass
    except KeyboardInterrupt:
        server.stop()

