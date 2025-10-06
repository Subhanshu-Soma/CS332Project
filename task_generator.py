import random
import time
import socket
from datetime import datetime

SERVER_IP = '127.0.0.1'
SERVER_PORT = 12345
END_MESSAGE = "END"

def send_process_info(client_socket, pid, burst_time):
    process_info = f"{pid} {burst_time} "
    client_socket.sendall(process_info.encode())
    print(f"Sent process info: {process_info}")

def main():
    average_tasks_per_minute = float(input("Enter average tasks per minute: "))
    average_burst_time = float(input("Enter average burst time: "))

    average_interval = 60.0 / average_tasks_per_minute

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"generator_log_{timestamp}.txt"
    log_file = open(log_filename, "w")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_IP, SERVER_PORT))
    server_socket.listen(5)

    print(f"Waiting for incoming connections on {SERVER_IP}:{SERVER_PORT}...")

    client_socket, client_address = server_socket.accept()
    print(f"Accepted connection from {client_address}")

    start_time = time.time()
    pid = 1
    while time.time() - start_time < 60:  # Run for 60 seconds
        burst_time = max(1, int(random.expovariate(1.0 / average_burst_time)))
        send_process_info(client_socket, pid, burst_time)
        log_message = f"Sent process info: PID={pid} Burst Time={burst_time}\n"
        log_file.write(log_message)
        log_file.flush()
        pid += 1
        interval = max(0.1, random.expovariate(1.0 / average_interval))
        time.sleep(interval)

    # Send "END" message when finished
    client_socket.sendall(END_MESSAGE.encode())
    client_socket.close()
    server_socket.close()
    log_file.close()

if __name__ == "__main__":
    main()