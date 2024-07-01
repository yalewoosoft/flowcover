import json
import subprocess
import argparse
import sys
import time
from pprint import pprint

import networkx as nx
from ipmininet.cli import IPCLI
from mininet.log import setLogLevel
from mininet.topo import Topo
from ipmininet.iptopo import IPTopo
from itertools import product
from random import random
from timeit import default_timer as timer
import ipmininet.clean as ipm_clean
import mininet.clean as m_clean
from ipmininet.ipnet import IPNet
from mininet.node import OVSSwitch, RemoteController
from ipmininet.host import IPHost
import pickle
from random import sample
from math import floor, sqrt
from typing import Optional, TextIO
import os
import signal


from utils import HostIdIPConverter
from utils.GraphGenerator import *

network: Optional[IPNet] = None
NUM_BYTES_PER_FLOW = 1000
BITRATE = '1MB'
trafgen_flag = False
exit_timeout = 1800 # in seconds
def port_id_generator():
    current_id = 1
    while True:
        yield current_id
        current_id += 1

class SimulatedNetworkTopology(IPTopo):
    my_switches: [str]
    lossy_switches: [str]
    switch_switch_port: dict[(int, int), int]
    switch_host_port: dict[(int, int), int]
    graph: nx.Graph
    """
        This class represents a simulated mininet network.
        Supports generating a random topology using Erdos-Renyi or Waxman.
    """

    def build(self, n, random_type='linear', prob=0.5, waxman_alpha=0.5, waxman_beta=0.5, loss_switch_ratio=0, packet_loss_ratio=0, **_kwargs):
        """
        Initializes a Mininet topology using given parameters.
        :param n: number of switches
        :param random_type: linear/erdos-renyi/waxman
        :param prob: probability for erdos-renyi and waxman random graph generation
        :param loss_switch_ratio: percent of lossy switches, in float
        :param packet_loss_ratio: percent of packet loss on a lossy switch, in float
        :return: None
        """
        ipm_clean.cleanup()
        m_clean.cleanup()
        assert 0 <= prob <= 1
        assert 0 <= waxman_alpha <= 1
        assert 0 <= waxman_beta <= 1
        assert 0 <= loss_switch_ratio <= 1
        assert 0 <= packet_loss_ratio <= 1
        self.my_switches = [None] # switch index starts from 1, 0 is None due to Ryu bug
        self.lossy_switches = []
        self.switch_switch_port = {}
        self.switch_host_port = {}
        self.graph = nx.Graph()
        id_generator = port_id_generator()
        if random_type == 'linear':
            self.graph = linear_generator(n)
        elif random_type == 'erdos-renyi':
            self.graph = erdos_renyi_generator(n, prob)
        elif random_type == 'waxman':
            self.graph = waxman_generator_1(n, waxman_alpha, waxman_beta)
        else:
            raise NotImplementedError()
        print(self.graph)
        # note that s is always an int in the following code, not the switch object.
        for s in self.graph.nodes:
            self.my_switches.append(self.addSwitch('s%s' % s))
            self.graph.add_node(s)
        # pick lossy switches out using loss_switch_ratio
        num_lossy_switches = floor(n * loss_switch_ratio)
        self.lossy_switches = sample(self.my_switches[1:], num_lossy_switches)
        # Mininet only allows configuring loss on links, not switches.
        # Workaround: if packet_loss_rate=p, apply sqrt(p) loss rate to every link it connects (including host link)
        # Then every packet would have the same loss rate p since it always passes 2 edges
        # If two loss switches are connected: add sqrt(a) and sqrt(b).
        for s in self.graph.nodes:
            # add a host for every switch, ip generated using Converter class
            h = self.addHost('h%s' % s, ip=f"{HostIdIPConverter.id_to_ip(s)}/32", mac=HostIdIPConverter.id_to_mac(s))
            # add an edge to host and switch
            id_1 = next(id_generator)
            # calculate loss rate if switch lossy:
            loss_rate = 0
            if f's{s}' in self.lossy_switches:
                loss_rate = 1-sqrt(1-packet_loss_ratio)
            self.addLink(self.my_switches[s], h, port1=id_1, loss=loss_rate*100)
            self.switch_host_port[(s, s)] = id_1
        # for the switch graph, calculate the loss rate together
        loss_rate_graph: dict[(int, int),float] = {}
        for s1, s2 in self.graph.edges:
            if f's{s1}' in self.lossy_switches and f's{s2}' in self.lossy_switches:
                loss_rate_graph[(s1, s2)] = packet_loss_ratio
            if f's{s1}' not in self.lossy_switches and f's{s2}' not in self.lossy_switches:
                loss_rate_graph[(s2, s1)] = 0
            loss_rate_graph[(s1, s2)] = 1-sqrt(1-packet_loss_ratio)
        # add an edge in three steps: generate ids -> add a switch link -> record its port id
        for s1, s2 in self.graph.edges:
            id_1 = next(id_generator)
            id_2 = next(id_generator)
            self.addLink(self.my_switches[s1], self.my_switches[s2], port1=id_1, port2=id_2, loss=loss_rate_graph[(s1, s2)]*100)
            self.switch_switch_port[(s1, s2)] = id_1
            self.switch_switch_port[(s2, s1)] = id_2
        self.write_initial_topology(random_type)
        super().build()

    def write_initial_topology(self, random_type: str):
        nx.write_adjlist(self.graph, 'topology.bin')
        with open('random_type.txt', 'w') as f:
            f.write(random_type)
        with open('switch_switch_port_id.bin', 'wb') as f:
            pickle.dump(self.switch_switch_port, f)
        with open('switch_host_port_id.bin', 'wb') as f:
            pickle.dump(self.switch_host_port, f)




def handle_signal_emulate_traffic(sig, frame):
    assert network is not None
    global trafgen_flag
    if trafgen_flag:
        print('Trafgen already started; not starting again')
        return
    trafgen_flag = True
    global NUM_BYTES_PER_FLOW, BITRATE, trafgen_INTERVAL
    print('Signal USR1 received, start sending traffic')
    print('Killing all existing trafgen')
    for i in network.keys():
        if i.startswith('h'):
            host: IPHost = network.get(i)
            host.popen(['killall', 'trafgen'], cwd="/tmp/", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            break
    print('Starting trafgen')
    # read random flows from file
    with open('random_flows.bin', 'rb') as f:
        flows: dict[int, [int]] = pickle.load(f)
        # prepare trafgen template
        with open('utils/trafgen.conf', 'r') as f:
            trafgen_conf_template = f.read()
        with open('utils/trafgen_close_server.conf', 'r') as f:
            trafgen_close_template = f.read()
        # assign a port for every flow
        flow_port: dict[int, int] = {}
        flow_dst = set(map(lambda flow: flow[-1], flows.values()))
        host_next_port: dict[int, int] = {}
        server_processes: dict[int, subprocess.Popen] = {}
        server_logs: dict[int, TextIO] = {}
        for dst in flow_dst:
            host_next_port[dst] = 1
        for flow_id, flow in flows.items():
            dst = flow[-1]
            flow_port[flow_id] = host_next_port[dst]
            host_next_port[dst] += 1
            # start server on corresponding port
            # prepare log file
            log_filename = f"logs/server_{flow_id}.log"
            os.makedirs(os.path.dirname(log_filename), exist_ok=True)
            server_logs[flow_id] = open(log_filename, 'w')
            dst_host: IPHost = network.get(f'h{dst}')
            dst_popen = dst_host.popen(['python3',
                                        'network/UDPServer.py',
                                        str(flow_id),
                                        str(flow_port[flow_id])
                                        ],
                                       cwd=".", stdout=server_logs[flow_id],
                                       stderr=subprocess.STDOUT)
            server_processes[flow_id] = dst_popen
            time.sleep(1)
        client_processes: dict[int, subprocess.Popen] = {}
        client_logs: dict[int, TextIO] = {}
        print(f'Sending per flow {NUM_BYTES_PER_FLOW} bytes')
        for flow_id, flow in flows.items():

            # prepare log file
            log_filename = f"logs/trafgen_{flow_id}.log"
            os.makedirs(os.path.dirname(log_filename), exist_ok=True)
            client_logs[flow_id] = open(log_filename, 'w')

            src = flow[0]
            dst = flow[-1]
            src_host: IPHost = network.get(f'h{src}')
            dst_host: IPHost = network.get(f'h{dst}')
            src_ip = HostIdIPConverter.id_to_ip(src)
            dst_ip = HostIdIPConverter.id_to_ip(dst)
            trafgen_conf = trafgen_conf_template.format(
                eth_dst=HostIdIPConverter.id_to_mac(dst),
                flow_id=flow_id,
                ipv6_src=src_ip,
                ipv6_dst=dst_ip,
                port=flow_port[flow_id],
            )
            print(trafgen_conf)
            if NUM_BYTES_PER_FLOW > 0:
                src_popen = src_host.popen(['trafgen',
                                            '--dev',f'h{src}-eth0',
                                            '-b', BITRATE,
                                            '-n', str(NUM_BYTES_PER_FLOW // 100),
                                            f' \'{{ {trafgen_conf} }}\''
                                            ], cwd="/tmp/",
                                           stdout=client_logs[flow_id], stderr=subprocess.STDOUT)
            else:
                src_popen = src_host.popen(['trafgen',
                                            '--dev', f'h{src}-eth0',
                                            '-b', BITRATE,
                                            f' \'{{ {trafgen_conf} }}\''
                                            ], cwd="/tmp/",
                                           stdout=client_logs[flow_id], stderr=subprocess.STDOUT)
            client_processes[flow_id] = src_popen
        # wait for all trafgens to finish
        for flow_id, p in client_processes.items():
            p.wait()
            print(f'Flow {flow_id} send complete')
            client_logs[flow_id].flush()
            client_logs[flow_id].close()
        print('All flows sent. Sending close packet.')
        for flow_id, flow in flows.items():

            # prepare log file
            log_filename = f"logs/trafgen_close_{flow_id}.log"
            os.makedirs(os.path.dirname(log_filename), exist_ok=True)
            client_logs[flow_id] = open(log_filename, 'w')

            src = flow[0]
            dst = flow[-1]
            src_host: IPHost = network.get(f'h{src}')
            dst_host: IPHost = network.get(f'h{dst}')
            src_ip = HostIdIPConverter.id_to_ip(src)
            dst_ip = HostIdIPConverter.id_to_ip(dst)
            trafgen_conf = trafgen_close_template.format(
                eth_dst=HostIdIPConverter.id_to_mac(dst),
                ipv6_src=src_ip,
                ipv6_dst=dst_ip,
                port=flow_port[flow_id],
            )
            src_popen = src_host.popen(['trafgen',
                                        '--dev',f'h{src}-eth0',
                                        '-b', BITRATE,
                                        '-n', str(NUM_BYTES_PER_FLOW // 100),
                                        f' \'{{ {trafgen_conf} }}\''
                                        ], cwd="/tmp/",
                                       stdout=client_logs[flow_id], stderr=subprocess.STDOUT)
            client_processes[flow_id] = src_popen
        for flow_id, p in client_processes.items():
            p.wait()
            print(f'Flow {flow_id} close send complete')
            client_logs[flow_id].flush()
            client_logs[flow_id].close()

def parse_flow_trafgen(flow_ids: [int]) -> dict[int, int]:
    """
    This function accepts a list of flow ids, parses the corresponding trafgen log files, and output the number of bytes actually received for every flow.
    Together with controller data this could be used to calculate flow statistics accuracy.
    :param flow_ids: list of flow ids to count
    :return: a dict: flow id -> number of bytes
    """
    global exit_timeout
    wait_time_start = timer()
    flow_bytes: dict[int, int] = {}
    for flow_id in flow_ids:
        log_filename = f"/tmp/trafgen_{flow_id}.log"
        done = False
        while not done:
            if os.path.exists(log_filename):
                with open(log_filename, 'r') as f:
                    flow_bytes[flow_id] = int(f.read())
                done = True
            time.sleep(0.2)
            time_now = timer()
            wait_time = wait_time_start - time_now
            if wait_time >= exit_timeout:
                print(f'Server exit timed out. Setting traffic of flow {flow_id} to zero.')
                flow_bytes[flow_id] = 0

    return flow_bytes

def handle_signal_exit(sig, frame):
    print('Receiving signal from controller. Will exit after stats saved.')
    with open('random_flows.bin', 'rb') as f:
        flows: dict[int, [int]] = pickle.load(f)
        trafgen_stats = parse_flow_trafgen(flows.keys())
        pprint(trafgen_stats)
        filename = f"stats/trafgen_stats.json"
        print('Saving stats')
        with open(filename, 'w') as f1:
            json.dump(trafgen_stats, f1)
        print('Stats saved. Mininet will exit.')
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description='Simulated Mininet network')
    parser.add_argument('--num-switches', default=20, type=int)
    parser.add_argument('--random-type', default='linear')
    parser.add_argument('--erdos-renyi-prob', default=0.5, type=float)
    parser.add_argument('--waxman-alpha', default=0.5, type=float)
    parser.add_argument('--waxman-beta', default=0.5, type=float)
    parser.add_argument('--loss-switch-ratio', default=0, type=float)
    parser.add_argument('--packet-loss-ratio', default=0, type=float)
    parser.add_argument('--num-bytes-sent', default=1000, type=int)
    parser.add_argument('--bitrate', default='1MB', type=str)
    parser.add_argument('--timeout', default=1800, type=int)

    args = parser.parse_args()
    setLogLevel('debug')
    global network
    global NUM_BYTES_PER_FLOW, BITRATE, exit_timeout
    NUM_BYTES_PER_FLOW = args.num_bytes_sent
    BITRATE = args.bitrate
    exit_timeout = args.timeout
    network = IPNet(
        topo=SimulatedNetworkTopology(
            n=args.num_switches,
            random_type=args.random_type,
            prob=args.erdos_renyi_prob,
            waxman_alpha=args.waxman_alpha,
            waxman_beta=args.waxman_beta,
            loss_switch_ratio=args.loss_switch_ratio,
            packet_loss_ratio=args.packet_loss_ratio,
        ),
        allocate_IPs=False,
        switch=OVSSwitch,
        controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6653, protocols="OpenFlow13")
    )

    #controller = RemoteController('c1', ip='127.0.0.1', port=6633, protocols="OpenFlow13")
    network.staticArp()
    #network.addController(controller)
    with open('pid.txt', 'w', encoding='utf-8') as f:
        # write mininet pid to file; Ryu uses this to notify mininet to start sending traffic
        f.write(str(os.getpid()))
    network.start()
    with open(f'/tmp/mininet_started.flag', 'w', encoding='utf-8') as f:
        f.write('0')
    print('mininet started')
    return network

if __name__ == '__main__':
    signal.signal(signal.SIGUSR1, handle_signal_emulate_traffic)
    signal.signal(signal.SIGUSR2, handle_signal_exit)
    net = main()
    IPCLI(net)
    net.stop()
