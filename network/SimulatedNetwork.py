from mininet.topo import Topo
from itertools import product
from random import random
from mininet.net import Mininet
from mininet.node import OVSSwitch

class SimulatedNetworkTopology(Topo):
    """
        This class represents a simulated mininet network.
        Supports generating a random topology using Erdos-Renyi or Waxman.
    """

    def __init__(self, *args, **params):
        super().__init__(args, params)
        self.switches: [OVSSwitch] = []

    def build(self, n=200, random_type='linear', prob=0.5):
        """
        Initializes a Mininet topology using given parameters.
        :param n: number of switches
        :param random_type: linear/erdos-renyi/waxman
        :param prob: probability for erdos-renyi and waxman random graph generation
        :return: None
        """
        for s in range(0, n):
            self.switches.append(self.addSwitch('s%s' % s))
        if random_type == 'linear':
            for s in range(0, n-1):
                self.addLink(self.switches[s], self.switches[s+1])
        elif random_type == 'erdos-renyi':
            for s1, s2 in product(self.switches, self.switches):
                if s1 == s2:
                    continue
                x = random()
                if x <= prob:
                    self.addLink(s1, s2)
        else:
            raise NotImplementedError()