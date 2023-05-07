import telnetlib
import sys
import select
import msvcrt
import os

def print_server_data(connection):
    output_buffer = bytearray()

    while True:
        try:
            data = connection.read_eager()
            if not data:
                break

            output_buffer.extend(data)
        except EOFError:
            return False

    if output_buffer:
        print(output_buffer.decode(errors='ignore').strip())

    return True

def main():
    # Replace with the desired Telnet server and port
    server = "localhost"
    port = 23
    timeout = 0.5
    svrtimeout = 5
    login = 'moo'
    # Connect to the Telnet server
    try:
        connection = telnetlib.Telnet(server, port, svrtimeout)
    except Exception as e:
        print(f"Error connecting to the Telnet server: {e}")
        sys.exit(1)

    while True:
        if not print_server_data(connection):
            print("Connection closed by the server.")
            break

        # Check if the connection is closed before requesting input
        if connection.eof:
            break

        # Get input from the user and send it to the server
        try:
            while True:
                # Check for data from the server
                ready_to_read, _, _ = select.select([connection], [], [], timeout)

                # If there's data from the server, print it
                if ready_to_read:
                    if not print_server_data(connection):
                        print("Connection closed by the server.")
                        break

                # If there's data from the user, send it to the server
                if msvcrt.kbhit():
                    user_input = input()
                    connection.write(user_input.encode() + b'\n')
                    break

        except EOFError:
           # print("Connection closed by the server.")
            break

if __name__ == "__main__":
    main()
