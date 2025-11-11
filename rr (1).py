import threading
import socket
import time
import sys
from datetime import datetime

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12345

pause_flag = threading.Event()
pause_flag.set()

process_queue = []
running = ""
queue_lock = threading.Lock()
shutdown_flag = threading.Event()

log_file = None
log_lock = threading.Lock()

TIME_QUANTUM = 2  

def log_message(message):
    global log_file
    with log_lock:
        log_entry = f"{message}\n"
        log_file.write(log_entry)
        log_file.flush()


def _sleep_exact(seconds):
    time.sleep(seconds)


def scheduler():
    global running
    global process_queue
    global queue_lock

    while not shutdown_flag.is_set():
        pause_flag.wait()

        current = None

        with queue_lock:
            if len(process_queue) > 0:
                current = process_queue.pop(0)

        if current:
            if current == "END":
                # Only shut down if queue is empty, otherwise re-queue END and continue processing
                with queue_lock:
                    if len(process_queue) == 0:
                        log_message("[SCHEDULER] Received END signal, shutting down...")
                        print("\n[SCHEDULER] Received END signal, shutting down... \n>", end="")
                        shutdown_flag.set()
                        break
                    else:
                        # END received but queue not empty, put END back at end and continue processing
                        process_queue.append("END")
                        continue

            try:
                parts = current.strip().split()
                if len(parts) != 2:
                    raise ValueError("Expected 'pid burst'")
                pid, remaining = parts[0], int(parts[1])
                slice_time = min(TIME_QUANTUM, remaining)
                with queue_lock:
                    running = f"{pid} : with burst time {remaining}"

                log_message(f"Process {pid} started with remaining time: {remaining}s")

                _sleep_exact(slice_time)

                remaining_after = remaining - slice_time

                if remaining_after > 0:
                    log_message(
                        f"Process {pid} exceeded time quantum (2s) and will be requeued with remaining time: {remaining_after}s"
                    )
                    with queue_lock:
                        process_queue.append(f"{pid} {remaining_after}")
                else:
                    # Calculate total burst time (original remaining was the last slice)
                    total_burst = remaining
                    log_message(
                        f"Process {pid} completed in burst time: {total_burst}s"
                    )

                with queue_lock:
                    running = ""

            except (ValueError, IndexError) as e:
                print(f"\n[ERROR] Invalid process format: {current} - {e}")
                error_msg = f"[ERROR] Invalid process format: {current} - {e}"
                log_message(error_msg)
        else:
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
                pass
            else:
                print(f"Unknown command: {s}")

        except EOFError:
            shutdown_flag.set()
            break


def main():
    global log_file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"scheduler_log_{timestamp}.txt"
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

    scheduler_thread = threading.Thread(target=scheduler)
    shell_thread = threading.Thread(target=shell)
    scheduler_thread.start()
    shell_thread.start()

    global shutdown_flag

    while not shutdown_flag.is_set():
        try:
            message = client_socket.recv(1024).decode('utf-8')

            if not message:
                log_message("[RECEIVER] Server closed the connection")
                print("\n[RECEIVER] Server closed the connection.")
                shutdown_flag.set()
                break
            with queue_lock:
                process_queue.append(message)
                if message == "END":
                    log_message("[RECEIVER] Received END message")
                    break
                else:
                    # Log in the format: "Received process info: PID=<ID>, Burst Time=<time>s"
                    try:
                        parts = message.strip().split()
                        if len(parts) == 2:
                            pid = parts[0]
                            burst_time = parts[1]
                            log_message(f"Received process info: PID={pid}, Burst Time={burst_time}s")
                    except:
                        log_message(f"[RECEIVER] Recieved Process Info: {message}")

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

    shell_thread.join()
    scheduler_thread.join()

    client_socket.close()
    log_message("[SYSTEM] Scheduler shutdown complete")
    log_file.close()
    print(f"\nLog saved to: {log_filename}")


if __name__ == "__main__":
    main()
