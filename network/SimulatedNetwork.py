import subprocess

import networkx as nx
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.topo import Topo
from itertools import product
from random import random
from mininet.clean import cleanup
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController, Host
import pickle
from random import sample
from math import floor, sqrt
from typing import Optional
import os
import signal

from utils import HostIdIPConverter
from utils.GraphGenerator import *

network: Optional[Mininet] = None
NUM_BYTES_PER_FLOW = 10000
def port_id_generator():
    current_id = 1
    while True:
        yield current_id
        current_id += 1

class SimulatedNetworkTopology(Topo):
    my_switches: [str]
    lossy_switches: [str]
    switch_switch_port: dict[(int, int), int]
    switch_host_port: dict[(int, int), int]
    graph: nx.Graph
    """
        This class represents a simulated mininet network.
        Supports generating a random topology using Erdos-Renyi or Waxman.
    """

    def build(self, n, random_type='linear', prob=0.5, loss_switch_ratio=0, packet_loss_ratio=0, **_kwargs):
        """
        Initializes a Mininet topology using given parameters.
        :param n: number of switches
        :param random_type: linear/erdos-renyi/waxman
        :param prob: probability for erdos-renyi and waxman random graph generation
        :param loss_switch_ratio: percent of lossy switches, in integer [0, 100]
        :param packet_loss_ratio: percent of packet loss on a lossy switch, in integer [0, 100]
        :return: None
        """
        cleanup()
        assert 0 <= prob <= 1
        assert 0 <= loss_switch_ratio <= 100
        assert 0 <= packet_loss_ratio <= 100
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
            self.graph = waxman_generator_1(n, 0.5, 0.5)
        else:
            raise NotImplementedError()
        print(self.graph)
        # note that s is always an int in the following code, not the switch object.
        for s in self.graph.nodes:
            self.my_switches.append(self.addSwitch('s%s' % s))
            self.graph.add_node(s)
        # pick lossy switches out using loss_switch_ratio
        num_lossy_switches = floor(n * loss_switch_ratio / 100)
        self.lossy_switches = sample(self.my_switches[1:], num_lossy_switches)
        # Mininet only allows configuring loss on links, not switches.
        # Workaround: if packet_loss_rate=p, apply sqrt(p) loss rate to every link it connects (including host link)
        # Then every packet would have the same loss rate p since it always passes 2 edges
        # If two loss switches are connected: add sqrt(a) and sqrt(b).
        for s in self.graph.nodes:
            # add a host for every switch, ip generated using Converter class
            h = self.addHost('h%s' % s, ip=f"{HostIdIPConverter.id_to_ip(s)}/32")
            # add an edge to host and switch
            id_1 = next(id_generator)
            # calculate loss rate if switch lossy:
            loss_rate = 0
            if s in self.lossy_switches:
                loss_rate = sqrt(1-packet_loss_ratio)+1
            self.addLink(self.my_switches[s], h, port1=id_1, loss=loss_rate)
            self.switch_host_port[(s, s)] = id_1
        # for the switch graph, calculate the loss rate together
        loss_rate_graph: dict[(int, int),float] = {}
        for s1, s2 in self.graph.edges:
            if s1 in self.lossy_switches and s2 in self.lossy_switches:
                loss_rate_graph[(s1, s2)] = packet_loss_ratio
            if s1 not in self.lossy_switches and s2 not in self.lossy_switches:
                loss_rate_graph[(s2, s1)] = 0
            loss_rate_graph[(s1, s2)] = sqrt(1-packet_loss_ratio)+1
        # add an edge in three steps: generate ids -> add a switch link -> record its port id
        for s1, s2 in self.graph.edges:
            id_1 = next(id_generator)
            id_2 = next(id_generator)
            self.addLink(self.my_switches[s1], self.my_switches[s2], port1=id_1, port2=id_2, loss=loss_rate_graph[(s1, s2)])
            self.switch_switch_port[(s1, s2)] = id_1
            self.switch_switch_port[(s2, s1)] = id_2
        self.write_initial_topology()

    def write_initial_topology(self):
        nx.write_adjlist(self.graph, 'topology.bin')
        with open('switch_switch_port_id.bin', 'wb') as f:
            pickle.dump(self.switch_switch_port, f)
        with open('switch_host_port_id.bin', 'wb') as f:
            pickle.dump(self.switch_host_port, f)


def send_traffic(src: int, dst: int, num_bytes: int) -> None:
    assert network is not None
    src_host: Host = network.get(f'h{src}')
    dst_host: Host = network.get(f'h{dst}')
    dst_ip = HostIdIPConverter.id_to_ip(dst)
    dst_host.popen(['iperf3', '-s'], cwd="/tmp/", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    src_host.popen(['iperf3', '-c', dst_ip, '-n', num_bytes], cwd="/tmp/", stderr=subprocess.DEVNULL)

def handle_signal_emulate_traffic(sig, frame):
    print('Signal USR1 received, start sending traffic')
    # read random flows from file
    with open('random_flows.bin', 'rb') as f:
        flows: dict[int, [int]] = pickle.load(f)
        for flow in flows.values():
            src = flow[0]
            dst = flow[-1]
            send_traffic(src, dst, NUM_BYTES_PER_FLOW)


def main():
    setLogLevel('debug')
    global network
    network = Mininet(
        topo=SimulatedNetworkTopology(n=7, random_type='erdos-renyi', prob=0.5, loss_switch_ratio=50, packet_loss_ratio=1),
        controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6633, protocols="OpenFlow13")
    )
    with open('pid.txt', 'w', encoding='utf-8') as f:
        # write mininet pid to file; Ryu uses this to notify mininet to start sending traffic
        f.write(str(os.getpid()))
    network.start()
    return network

if __name__ == '__main__':
    signal.signal(signal.SIGUSR1, handle_signal_emulate_traffic)
    net = main()
    CLI(net)
    net.stop()
