import networkx as nx
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.topo import Topo
from itertools import product
from random import random
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
import pickle

def port_id_generator():
    current_id = 1
    while True:
        yield current_id
        current_id += 1

class SimulatedNetworkTopology(Topo):
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
        self.my_switches: [OVSSwitch] = []
        self.link_port: dict[(int, int), int] = {}
        self.graph: nx.Graph = nx.Graph()
        id_generator = port_id_generator()
        for s in range(1, n+1):
            self.my_switches.append(self.addSwitch('s%s' % s))
            self.graph.add_node(s)
        # add an edge in four steps: generate ids -> add a switch link -> record its port id -> add to networkx graph
        if random_type == 'linear':
            for s in range(1, n+1):
                id_1 = next(id_generator)
                id_2 = next(id_generator)
                self.addLink(self.my_switches[s], self.my_switches[s + 1], port1=id_1, port2=id_2)
                self.link_port[(s, s+1)] = id_1
                self.link_port[(s+1, s)] = id_2
                self.graph.add_edge(s, s+1)
        elif random_type == 'erdos-renyi':
            for s1, s2 in product(range(0, n), range(0, n)):
                if s1 == s2:
                    continue
                x = random()
                if x <= prob:
                    id_1 = next(id_generator)
                    id_2 = next(id_generator)
                    self.addLink(self.my_switches[s1], self.my_switches[s2], port1=id_1, port2=id_2)
                    self.link_port[(s1, s2)] = id_1
                    self.link_port[(s2, s1)] = id_2
                    self.graph.add_edge(s1, s2)
        else:
            raise NotImplementedError()
        self.write_initial_topology()

    def write_initial_topology(self):
        nx.write_adjlist(self.graph, 'topology.bin')
        with open('port_id.bin', 'wb') as f:
            pickle.dump(self.link_port, f)

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
