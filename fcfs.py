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

log_filename = f"scheduler_log.txt"
log_file = None
log_lock = threading.Lock()

def log_message(message):
    global log_file
    with log_lock:
        log_entry = f"{message}\n"
        log_file.write(log_entry)
        log_file.flush()  

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
                log_message("[SCHEDULER] Received END signal, shutting down...")
                print("\n[SCHEDULER] Received END signal, shutting down...")
                shutdown_flag.set()
                break
            
            try:
                pid, wait = current.strip().split()

                # Update running state with lock
                with queue_lock:
                    running = f"{pid} : with burst time {wait}"

                log_message(f"[RUNNING] Process {pid} started with burst time {wait}")

                # Sleep for the full duration - don't check pause during execution
                time.sleep(int(wait))

                log_message(f"[COMPLETED] Process {pid} finished after {wait} seconds")

                # Clear running state with lock
                with queue_lock:
                    running = ""
                
            except (ValueError, IndexError) as e:
                print(f"\n[ERROR] Invalid process format: {current} - {e}")
                error_msg = f"[ERROR] Invalid process format: {current} - {e}"
                log_message(error_msg)
        else:
            # No tasks in queue, sleep briefly to avoid busy-waiting
            time.sleep(0.1)

def shell():
    global process_queue
    global queue_lock
    global running
    global shutdown_flag
    
    print("\nCommands: 'list' (show queue), 'pause', 'continue', 'exit' (quit)")
    
    while True:
        try:
            s = input("> ")
            
            if s == "exit":
                shutdown_flag.set()
                print("Shutting down...")
                log_message("[SHELL] Shutdown intitiated by user.")
                break
            elif s == "list":
                with queue_lock:
                    print(f"\nQueue ({len(process_queue)} tasks): {process_queue}")
                    print(f"Currently running: {running if running else 'None'}")
            elif s == "pause":
                if pause_flag.is_set():
                    pause_flag.clear()
                    print("Scheduler PAUSED")
                    log_message("[SHELL] Scheduler paused by user.")
                else:
                    print("Scheduler is already paused")                   
            elif s == "continue":
                if not pause_flag.is_set():
                    pause_flag.set()
                    print("Scheduler RESUMED")
                    log_message("[SHELL] Scheduler resumed by user.")
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

def receiver(client_socket):
    """Continuously receive messages from the server."""
    global shutdown_flag
    
    while not shutdown_flag.is_set():
        try:
            message = client_socket.recv(1024).decode('utf-8')
            
            if not message:
                log_message("[RECEIVER] Server closed the connection")
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
                            log_message("[RECEIVER] Received END message from server")
                            print("\n[RECEIVER] Received END message")
                        else:
                            log_message(f"[RECEIVER] Received process: {msg}")
            
        except ConnectionResetError:
            print("\n[RECEIVER] Connection was reset by the server.")
            log_message(f"[RECEIVER] Connection was reset by the server.")
            shutdown_flag.set()
            break
        except Exception as e:
            if not shutdown_flag.is_set():
                error_msg = f"[RECEIVER] Error: {e}"
                log_message(error_msg)
            break
        
        time.sleep(0.1)

def main():
    # Log implementation
    global log_file
    try:
        log_file = open(log_filename, 'w')
        log_message(f"[SYSTEM] Scheduler started - Log file: {log_filename}")
        print(f"Logging to: {log_filename}")
    except Exception as e:
        print(f"Error creating log file: {e}")
        exit(1)   

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect((SERVER_IP, SERVER_PORT))
        log_message(f"[SYSTEM] Connected to server at {SERVER_IP}:{SERVER_PORT}")
    except socket.error as e:
        error_msg = f"Connection failed: {e}"
        log_message(f"[SYSTEM] {error_msg}")
        print("Connection failed:", e)
        log_file.close()
        exit(1)

    print("Connected to the server")
    receiver_thread = threading.Thread(target=receiver, args=(client_socket,), daemon=True)
    receiver_thread.start()

    scheduler_thread = threading.Thread(target=scheduler)
    shell_thread = threading.Thread(target=shell)
    scheduler_thread.start()
    shell_thread.start()

    # Wait for threads to complete
    shell_thread.join()
    scheduler_thread.join()
    
    # Cleanup
    client_socket.close()
    log_message("[SYSTEM] Scheduler shutdown complete")
    log_file.close()
    print(f"\nLog saved to: {log_filename}")

if __name__ == "__main__":
    main()