import signal
import socket
import sys
# CLI Param: flow_id port

num_bytes = 0
def handle_signal(sig, frame):
    filename = f'/tmp/trafgen_{flow_id}.log'
    print(f'Flow {flow_id}: {num_bytes} received.')
    with open(filename, 'w') as f:
        f.write(str(num_bytes))
    sys.exit()
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
flow_id = int(sys.argv[1])
server_socket.bind(('', int(sys.argv[2])))
while True:
    message, address = server_socket.recv(1024)
    num_bytes += len(message)