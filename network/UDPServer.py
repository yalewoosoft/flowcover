import signal
import socket
import sys
# CLI Param: flow_id port

num_bytes = 0
server_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
flow_id = int(sys.argv[1])
server_socket.bind(('::', int(sys.argv[2])))
while True:
    message = server_socket.recv(1024)
    message_str = message.decode('utf-8')
    if message_str.find('B') != -1:
        # end of data; exit server
        filename = f'/tmp/trafgen_{flow_id}.log'
        print(f'Flow {flow_id}: {num_bytes} received.')
        with open(filename, 'w') as f:
            f.write(str(num_bytes // 38 * 100))
        sys.exit()
    else:
        num_bytes += len(message)