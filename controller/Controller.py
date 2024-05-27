import sys
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.controller import Datapath
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
import ryu.ofproto.ofproto_v1_3_parser as parser
import ryu.ofproto.ofproto_v1_3 as ofproto
from ryu.lib import hub
from ryu.lib.packet import packet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet, arp, ipv4, ipv6
from netaddr import IPAddress, IPNetwork
from ryu.cmd import manager
import networkx as nx
import pickle
from .ControllerTemplate import ControllerTemplate





class Controller(ControllerTemplate):
    topology: nx.Graph
    link_port: dict[(int, int), int]

    def __init__(self, *args, **kwargs):
        super(ControllerTemplate, self).__init__(*args, **kwargs)
        self.info('Controller started')
        self.ready = False
        self.online_switches: dict[int, Datapath] = {}
        self.get_initial_topology()
        self.flows = self.generate_random_flows()
        self.switch_flows = self.generate_switch_flow_list()
        self.polling = self.set_cover()
        self.flow_stats: [[int]] = []
        # TODO:
        self.monitor_thread = hub.spawn(self._monitor)

    def get_initial_topology(self) -> None:
        self.topology = nx.read_adjlist('topology.bin')
        with open('port_id.bin', 'rb') as f:
            self.link_port = pickle.load(f)

    def generate_random_flows(self) -> [[int]]:
        """
        TODO: select random paths from topology and generate random flows
        Use self.topology and networkx.
        return value should be a list of lists of switch ids
        """
        return []

    def generate_switch_flow_list(self) -> [[int]]:
        """
        TODO: Converts the list of flows to the list of switches where the flow passes through
        Use self.flows
        :return:
        """
        pass

    def set_cover(self) -> dict[int, [int]]:
        """
        TODO: transform the flow/switch_flow structure into set cover input and solve it
        Use self.flows and self.switch_flows
        :return: a dict: switch id -> flows to poll
        """
        return {}

    def request_stats(self, datapath: Datapath) -> None:
        """
        TODO: Request statistics according to the result of set cover algorithm.
        Use self.polling.
        To poll all stats on a switch: OFPFlowStatsRequest
        """
        pass

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev) -> None:
        """
        TODO: Callback of received statistics. Record the data from individual flow.
        Write results to self.flow_stats.
        """
        body = ev.msg.body
        pass

    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        """
        Register online routers
        """
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.online_switches:
                self.logger.debug('register switch: %016x', datapath.id)
                self.online_switches[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.online_switches:
                self.logger.debug('unregister switch: %016x', datapath.id)
                del self.online_switches[datapath.id]

    def _monitor(self):
        while True:
            if self.ready:
                for dp in self.online_switches.values():
                    self.request_stats(dp)
                hub.sleep(10)


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """Packet-In Callback."""
        msg = ev.msg
        datapath = msg.datapath
        data = msg.data
        in_port = msg.match["in_port"]
        pkt = packet.Packet(data)
        eth = pkt.get_protocol(ethernet.ethernet)
        # Handle ARP
        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            self.handle_arp(datapath, in_port, eth, data)
            return
        if eth.ethertype == ether_types.ETH_TYPE_IP:
            pass

    # This decorator makes sure that the function below is invoked
    # every time a new switch is connected to our controller.
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """SwitchConnect Callback."""
        print(f"Switch {ev.msg.datapath.id} connected.")

def main():
    sys.argv.append('controller.Controller')
    sys.argv.append('--verbose')
    sys.argv.append('--enable-debugger')
    manager.main()

if __name__ == '__main__':
    main()
