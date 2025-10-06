#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <arpa/inet.h>
#include <signal.h>
#include <termios.h>
#include <time.h>

#define SERVER_IP "127.0.0.1"
#define SERVER_PORT 12345
#define MAX_BUFFER_SIZE 1024

typedef struct {
    int pid;
    int arrival_time; 
    int burst_time;
} Process;

typedef struct Node {
    Process process;
    struct Node* next;
} Node;

volatile int pause_flag = 0;
volatile int running = 1;

Node* head = NULL;
pthread_mutex_t lock;

FILE* log_file = NULL;

/* ... */

void* scheduler(void* arg) {
/* ... */
}

void* shell(void* arg) {
    char command[100];
    while (running) {
        printf("Shell Command (pause/continue/list): ");
        scanf("%s", command);

        if (strcmp(command, "pause") == 0) {
            pause_flag = 1;
            printf("Scheduler paused.\n");
        } else if (strcmp(command, "continue") == 0) {
            pause_flag = 0;
            printf("Scheduler continued.\n");
        } else if (strcmp(command, "list") == 0) {
            /* ... */
        } else {
            printf("Unknown command.\n");
        }
    }
    return NULL;
}

int main() {
    pthread_t scheduler_thread, shell_thread;
    pthread_mutex_init(&lock, NULL);

    int client_socket;
    struct sockaddr_in server_addr;
    char buffer[MAX_BUFFER_SIZE];

    if ((client_socket = socket(AF_INET, SOCK_STREAM, 0)) == -1) {
        perror("Socket creation failed");
        exit(1);
    }

    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(SERVER_PORT);

    if (inet_pton(AF_INET, SERVER_IP, &server_addr.sin_addr) <= 0) {
        exit(1);
    }

    if (connect(client_socket, (struct sockaddr*)&server_addr, sizeof(server_addr)) == -1) {
        exit(1);
    }

    printf("Connected to the server\n");

    pthread_create(&scheduler_thread, NULL, scheduler, NULL);
    pthread_create(&shell_thread, NULL, shell, NULL);

    /* ... */

    pthread_join(shell_thread, NULL);
    pthread_join(scheduler_thread, NULL);

    close(client_socket);
    fclose(log_file);
    pthread_mutex_destroy(&lock);

    return 0;
}