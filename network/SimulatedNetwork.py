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

    def build(self, n, random_type='linear', prob=0.5, **_kwargs):
        """
        Initializes a Mininet topology using given parameters.
        :param n: number of switches
        :param random_type: linear/erdos-renyi/waxman
        :param prob: probability for erdos-renyi and waxman random graph generation
        :return: None
        """
        self.my_switches: [OVSSwitch] = []
        for s in range(0, n):
            self.my_switches.append(self.addSwitch('s%s' % s))
        if random_type == 'linear':
            for s in range(0, n - 1):
                self.addLink(self.my_switches[s], self.my_switches[s + 1])
        elif random_type == 'erdos-renyi':
            for s1, s2 in product(self.my_switches, self.my_switches):
                if s1 == s2:
                    continue
                x = random()
                if x <= prob:
                    self.addLink(s1, s2)
        else:
            raise NotImplementedError()
