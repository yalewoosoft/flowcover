import sys
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
import ryu.ofproto.ofproto_v1_3_parser as parser
import ryu.ofproto.ofproto_v1_3 as ofproto
from ryu.lib.packet import packet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet, arp, ipv4, ipv6
from netaddr import IPAddress, IPNetwork
from ryu.cmd import manager
from ControllerTemplate import ControllerTemplate


class Controller(ControllerTemplate):

    def __init__(self, *args, **kwargs):
        super(ControllerTemplate, self).__init__(*args, **kwargs)
        self.info('Controller started')

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
