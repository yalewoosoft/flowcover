import networkx as nx
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.topo import Topo
from itertools import product
from random import random
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
import pickle

from utils import HostIdIPConverter
from utils.GraphGenerator import *

def port_id_generator():
    current_id = 1
    while True:
        yield current_id
        current_id += 1

class SimulatedNetworkTopology(Topo):
    my_switches: [OVSSwitch]
    switch_switch_port: dict[(int, int), int]
    switch_host_port: dict[(int, int), int]
    graph: nx.Graph
    """
        This class represents a simulated mininet network.
        Supports generating a random topology using Erdos-Renyi or Waxman.
    """

    def build(self, n, random_type='linear', prob=0.5, **_kwargs):
        """
        Initializes a Mininet topology using given parameters.
        :param n: number of switches
        :param random_type: linear/erdos-renyi/waxman
        :param prob: probability for erdos-renyi and waxman random graph generation
        :return: None
        """
        self.my_switches = [None] # switch index starts from 1, 0 is None due to Ryu bug
        self.switch_switch_port = {}
        self.switch_host_port = {}
        self.graph = nx.Graph()
        id_generator = port_id_generator()
        if random_type == 'linear':
            self.graph = linear_generator(n)
        elif random_type == 'erdos-renyi':
            self.graph = erdos_renyi_generator(n, prob)
        else:
            raise NotImplementedError()
        print(self.graph)
        # note that s is always an int in the following code, not the switch object.
        for s in self.graph.nodes:
            self.my_switches.append(self.addSwitch('s%s' % s))
            self.graph.add_node(s)
            # add a host for every switch, ip generated using Converter class
            h = self.addHost('h%s' % s, ip=f"{HostIdIPConverter.id_to_ip(s)}/32")
            # add an edge to host and switch
            id_1 = next(id_generator)
            self.addLink(self.my_switches[s], h, port1=id_1)
            self.switch_host_port[(s, s)] = id_1
        # add an edge in three steps: generate ids -> add a switch link -> record its port id
        for s1, s2 in self.graph.edges:
            id_1 = next(id_generator)
            id_2 = next(id_generator)
            self.addLink(self.my_switches[s1], self.my_switches[s2], port1=id_1, port2=id_2)
            self.switch_switch_port[(s1, s2)] = id_1
            self.switch_switch_port[(s2, s1)] = id_2
        self.write_initial_topology()

    def write_initial_topology(self):
        nx.write_adjlist(self.graph, 'topology.bin')
        with open('switch_switch_port_id.bin', 'wb') as f:
            pickle.dump(self.switch_switch_port, f)
        with open('switch_host_port_id.bin', 'wb') as f:
            pickle.dump(self.switch_host_port, f)

def main():
    setLogLevel('debug')
    network = Mininet(
        topo=SimulatedNetworkTopology(n=7, random_type='erdos-renyi', prob=0.5),
        controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6633, protocols="OpenFlow13")
    )
    network.start()
    return network

if __name__ == '__main__':
    net = main()
    CLI(net)
    net.stop()
