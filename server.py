import socket
import time
import threading

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12345

def handle_client(client_socket, client_address):
    """Handle communication with a connected client."""
    print(f"[SERVER] Client connected from {client_address}")
    
    try:
        # Example: Send some process data to the client
        processes = [
            "P1 3",
            "P2 5",
            "P3 2",
            "P4 4",
            "P5 1"
        ]
        
        # Send processes one by one
        for process in processes:
            print(f"[SERVER] Sending: {process}")
            client_socket.send(f"{process}\n".encode('utf-8'))
            time.sleep(1)  # Simulate delay between arrivals
        
        # Send END signal
        time.sleep(1)
        print("[SERVER] Sending END signal")
        client_socket.send("END\n".encode('utf-8'))
        
        # Keep connection alive until client disconnects
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            time.sleep(0.1)
                
    except Exception as e:
        print(f"[SERVER] Error with client {client_address}: {e}")
    finally:
        client_socket.close()
        print(f"[SERVER] Client {client_address} disconnected")

def main():
    # Create server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((SERVER_IP, SERVER_PORT))
        server_socket.listen(5)
        print(f"[SERVER] Listening on {SERVER_IP}:{SERVER_PORT}")
        print("[SERVER] Waiting for connections...")
        
        while True:
            # Accept client connection
            client_socket, client_address = server_socket.accept()
            
            # Handle client in a separate thread
            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket, client_address)
            )
            client_thread.start()
            
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
    except Exception as e:
        print(f"[SERVER] Error: {e}")
    finally:
        server_socket.close()
        print("[SERVER] Server stopped")

if __name__ == "__main__":
    main()