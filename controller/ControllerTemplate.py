from ryu.base import app_manager
import ryu.ofproto.ofproto_v1_3_parser as parser
import ryu.ofproto.ofproto_v1_3 as ofproto
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls, CONFIG_DISPATCHER
from ryu.lib.packet import ether_types


class ControllerTemplate(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ControllerTemplate, self).__init__(*args, **kwargs)

    def info(self, text):
        print("*" * (len(text) + 4))
        print(f"* {text} *")
        print("*" * (len(text) + 4))

    def clear_screen(self):
        print('$SDNC_CLEAR_SCREEN$')

    def program_flow(
            self, datapath, match, actions, cookie, priority=0,
            hard_timeout=0, idle_timeout=0, table_id=0):
        """
        Programs a flow to the switch identified by the given datapath.

        Args:
            datapath: Describes an the connection between the controller
                and the OpenFlow switch onto which the new flow will be
                installed.
            match: Packets must match this for the flow rule to be
                applied to them. If another flow with the same exact
                match exists on the switch already, it will be
                overridden.
            actions: List. Describe what the switch should do with
            matching packets. There are many types of actions in the
            OpenFlow specs, for example OFPActionOutput.
            priority (int): Priority level of flow entry.
            idle_timeout (int): Idle time before discarding (seconds).
                A value of 0 (default) means no timeout.
            hard_timeout (int): Max time before discarding (seconds).
                A value of 0 (default) means no timeout.
            table_id (int): table id of target flow table.
        """
        instructions = [
            parser.OFPInstructionActions(
                ofproto.OFPIT_APPLY_ACTIONS, actions
            )
        ]
        flowmod = parser.OFPFlowMod(
            datapath,
            match=match,
            cookie=cookie,
            instructions=instructions,
            priority=priority,
            hard_timeout=hard_timeout,
            idle_timeout=idle_timeout,
            table_id=table_id
        )
        datapath.send_msg(flowmod)

    def remove_flows(self, datapath, table_id):
        """Removing all flow entries."""
        parser = datapath.ofproto_parser
        ofproto = datapath.ofproto
        empty_match = parser.OFPMatch()
        instructions = []
        flow_mod = self.remove_table_flows(datapath, table_id,
                                           empty_match, instructions)
        print("deleting all flow entries in table ", table_id)
        datapath.send_msg(flow_mod)

    def remove_table_flows(self, datapath, table_id, match, instructions):
        """Create OFP flow mod message to remove flows from table."""
        ofproto = datapath.ofproto
        flow_mod = datapath.ofproto_parser.OFPFlowMod(datapath, 0, 0, table_id,
                                                      ofproto.OFPFC_DELETE, 0, 0,
                                                      1,
                                                      ofproto.OFPCML_NO_BUFFER,
                                                      ofproto.OFPP_ANY,
                                                      ofproto.OFPG_ANY, 0,
                                                      match, instructions)
        return flow_mod

    def send_pkt(self, datapath, data, port=ofproto.OFPP_FLOOD):
        """
        Send a packet from the controller to a switch where it will be
        emitted into the network.

        Args:
            datapath: Describes an OpenFlow switch to which the packet
                will be sent for emittance.
            data: The packet to emit.
            port: The port on which the packet will be emitted.
        """
        actions = [parser.OFPActionOutput(port)]
        out = parser.OFPPacketOut(
            datapath=datapath,
            actions=actions,
            in_port=ofproto.OFPP_CONTROLLER,
            data=data,
            buffer_id=ofproto.OFP_NO_BUFFER)
        datapath.send_msg(out)

    # Helper method for sending instructions to switch.
    def program_instruction(self, datapath, match, instructions, priority=0,
                            hard_timeout=0, idle_timeout=0, table_id=0):
        """
        This method programs an instruction into a switch flow table.
        """
        flowmod = parser.OFPFlowMod(
            datapath,
            match=match,
            instructions=instructions,
            priority=priority,
            hard_timeout=hard_timeout,
            idle_timeout=idle_timeout,
            table_id=table_id
        )
        datapath.send_msg(flowmod)

    def handle_arp(self, datapath, in_port, eth, data):
        """
        This method implements a simple mechanism to install
        forwarding rules for ARP packets. Packets that are
        not handled by any of these rules are flooded to
        nearby switches.
        """
        ofproto = datapath.ofproto

        src = eth.src

        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP, eth_dst=src)

        # Progamm a flow that forwards ARP packets to directly connected
        # network nodes so we don't have to bother with subsequent
        # ARP packets anymore.
        actions = [parser.OFPActionOutput(in_port)]
        self.program_flow(datapath, match, actions, priority=1)

        # Flood the received ARP message on all ports of the switch
        self.send_pkt(datapath, data, port=ofproto.OFPP_FLOOD)

    # This decorator makes sure that the function below is invoked
    # every time a new switch is connected to our controller.
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def __cockpit_app_switch_features_handler(self, ev):
        datapath = ev.msg.datapath

        print("switch with id {:d} connected".format(datapath.id))

        # Install default flow, which will forward all otherwise
        # unmatched packets to the controller.
        self.program_flow(
            datapath,
            parser.OFPMatch(),  # match on every packet
            [parser.OFPActionOutput(
                ofproto.OFPP_CONTROLLER,
                ofproto.OFPCML_NO_BUFFER
            )],
            cookie=100000000000,
            hard_timeout=0,  # never delete this flow
            idle_timeout=0  # never delete this flow
        )

        # Prevent truncation of packets
        datapath.send_msg(
            datapath.ofproto_parser.OFPSetConfig(
                datapath,
                datapath.ofproto.OFPC_FRAG_NORMAL,
                0xffff
            )
        )
