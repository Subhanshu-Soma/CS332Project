import threading
import socket
import time
import sys
from datetime import datetime

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12345

pause_flag = threading.Event()
pause_flag.set()  # Set means NOT paused (running)

process_queue = []
running = ""
queue_lock = threading.Lock()
shutdown_flag = threading.Event()

def scheduler():
    global running
    global process_queue
    global queue_lock
    
    while not shutdown_flag.is_set():
        pause_flag.wait()
        

        current = None
        
        # Get next process from queue (release lock quickly)
        with queue_lock:
            if len(process_queue) > 0:
                current = process_queue.pop(0)
        
        # Process outside the lock so receiver can continue adding tasks
        if current:
            if current == "END":
                print("\n[SCHEDULER] Received END signal, shutting down...")
                shutdown_flag.set()
                break
            
            try:
                pid, wait = current.strip().split()
                running = f"{pid} : with burst time {wait}"
                #print(f"\n[RUNNING] Beginning Process {pid} with burst time {wait}")
                
                # Sleep outside the lock
                time.sleep(int(wait))
                
                #print(f"[COMPLETED] Process {pid} finished")
                running = ""
                
            except (ValueError, IndexError) as e:
                print(f"\n[ERROR] Invalid process format: {current} - {e}")
        else:
            # No tasks in queue, sleep briefly to avoid busy-waiting
            time.sleep(0.1)
            
        

def shell():
    global process_queue
    global queue_lock
    global running
    global shutdown_flag
    
    print("\nCommands: 'top' (show queue), 'exit' (quit)")
    
    while True:
        try:
            s = input("> ")
            
            if s == "exit":
                shutdown_flag.set()
                print("Shutting down...")
                break
            elif s == "list":
                with queue_lock:
                    print(f"\nQueue ({len(process_queue)} tasks): {process_queue}")
                    print(f"Currently running: {running if running else 'None'}")
            elif s == "pause":
                if pause_flag.is_set():
                    pause_flag.clear()
                    print("Scheduler PAUSED")
                else:
                    print("Scheduler is already paused")
            elif s == "continue":
                if not pause_flag.is_set():
                    pause_flag.set()
                    print("Scheduler RESUMED")
                else:
                    print("Scheduler is already running")
            elif s == "":
                pass  # Ignore empty input
            else:
                print(f"Unknown command: {s}")
                
        except EOFError:
            # Handle Ctrl+D or input stream closing
            shutdown_flag.set()
            break
# ...

def receiver(client_socket):
    """Continuously receive messages from the server."""
    global shutdown_flag
    
    while not shutdown_flag.is_set():
        try:
            message = client_socket.recv(1024).decode('utf-8')
            
            if not message:
                print("\n[RECEIVER] Server closed the connection.")
                shutdown_flag.set()
                break
            
            # Handle multiple messages in one packet
            messages = message.strip().split('\n') if '\n' in message else [message]
            
            with queue_lock:
                for msg in messages:
                    if msg:  # Skip empty messages
                        process_queue.append(msg)
                        if msg == "END":
                            print("\n[RECEIVER] Received END message")
                        else:
                            #print(f"\n[RECEIVED] Added to queue: {msg}")
                            pass
            
        except ConnectionResetError:
            print("\n[RECEIVER] Connection was reset by the server.")
            shutdown_flag.set()
            break
        except Exception as e:
            if not shutdown_flag.is_set():
                print(f"\n[RECEIVER] Error: {e}")
            break
        
        time.sleep(0.1)
def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect((SERVER_IP, SERVER_PORT))
    except socket.error as e:
        print("Connection failed:", e)
        exit(1)

    print("Connected to the server")
    receiver_thread = threading.Thread(target=receiver, args=(client_socket,), daemon=True)
    receiver_thread.start()


    scheduler_thread = threading.Thread(target=scheduler)
    shell_thread = threading.Thread(target=shell)
    scheduler_thread.start()
    shell_thread.start()

    # ...

    shell_thread.join()
    scheduler_thread.join()
    client_socket.close()
    #log_file.close()

if __name__ == "__main__":
    main()