from mininet.net import Mininet
from mininet.log import setLogLevel
from network.SimulatedNetwork import SimulatedNetworkTopology
from controller.Controller import Controller

if __name__ == '__main__':
    setLogLevel('debug')
    net = Mininet(
        topo=SimulatedNetworkTopology(n=5, random_type='linear'),
        controller=Controller()
    )
    net.start()
    input()
    net.stop()