# network/client.py
import socket
import threading
import json

class GameClient:
    def __init__(self):
        self.client_socket = None
        self.is_connected = False
        self.on_receive = None # Callback for received data
        self.on_disconnect = None

    def connect(self, host, port, access_code):
        """Connects to the server and authenticates."""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, port))
            
            # Send access code for authentication
            auth_message = json.dumps({"code": access_code})
            self.client_socket.send(auth_message.encode('utf-8'))
            
            # Wait for authentication response
            response = self.client_socket.recv(1024).decode('utf-8')
            response_data = json.loads(response)

            if response_data.get("status") == "accepted":
                self.is_connected = True
                thread = threading.Thread(target=self.receive_messages)
                thread.daemon = True
                thread.start()
                print("Connection successful and authenticated.")
                return True, "Connection successful"
            else:
                self.client_socket.close()
                error_message = response_data.get("message", "Authentication failed")
                print(error_message)
                return False, error_message
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False, str(e)

    def receive_messages(self):
        """Listens for incoming messages from the server."""
        while self.is_connected:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if not message:
                    break
                if self.on_receive:
                    self.on_receive(message)
            except (ConnectionResetError, ConnectionAbortedError):
                print("Connection to server lost.")
                break
        
        self.is_connected = False
        if self.on_disconnect:
            self.on_disconnect()


    def send_message(self, message: dict):
        """Sends a JSON message to the server."""
        if self.is_connected:
            try:
                self.client_socket.send(json.dumps(message).encode('utf-8'))
            except:
                print("Failed to send message.")

    def disconnect(self):
        """Disconnects from the server."""
        if self.is_connected:
            self.is_connected = False
            self.client_socket.close()
            print("Disconnected from server.")

if __name__ == '__main__':
    # You would typically run the server script first.
    # This is a simple test case for the client.
    
    # This test requires a server running on localhost:8080 with a known access code.
    # Replace '1234' with the actual code from the running server.
    
    host = '127.0.0.1'
    port = 8080 # The port your server is running on
    code = '1234' # The access code from the server console
    
    client = GameClient()

    def receive_callback(msg):
        print(f"\nReceived from server: {msg}")
    
    def disconnect_callback():
        print("Server has closed the connection.")

    client.on_receive = receive_callback
    client.on_disconnect = disconnect_callback

    success, message = client.connect(host, port, code)
    
    if success:
        print("Enter message to send (or 'quit' to exit):")
        while True:
            msg_to_send = input("> ")
            if msg_to_send.lower() == 'quit':
                break
            client.send_message({"text": msg_to_send})
        
        client.disconnect()
    else:
        print(f"Could not connect: {message}")

