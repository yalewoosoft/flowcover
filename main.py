from mininet.cli import CLI
from network import SimulatedNetwork
from controller import Controller

if __name__ == '__main__':
    net = SimulatedNetwork.main()
    Controller.main() # start controller
    CLI(net) # drop to mininet console for debugging
    net.stop()