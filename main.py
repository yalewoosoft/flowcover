from mininet.net import Mininet
from mininet.log import setLogLevel
from network.SimulatedNetwork import SimulatedNetworkTopology
from mininet.node import RemoteController

if __name__ == '__main__':
    setLogLevel('debug')
    net = Mininet(
        topo=SimulatedNetworkTopology(n=5, random_type='linear'),
        controller=lambda name: RemoteController(name, ip='127.0.0.1', port=6633)
    )
    net.start()
    input()
    net.stop()