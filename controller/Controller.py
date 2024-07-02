import copy
import json
import signal
import sys
import os
import time
import random

from ryu.base import app_manager
from ryu import cfg
from ryu.controller import ofp_event
from ryu.controller.controller import Datapath
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib.packet import icmpv6
from ryu.ofproto.ofproto_v1_3_parser import OFPFlowStatsRequest
from ryu.ofproto.ofproto_v1_3 import OFPMPF_REQ_MORE
from ryu.ofproto import inet
import ryu.ofproto.ofproto_v1_3_parser as parser
import ryu.ofproto.ofproto_v1_3 as ofproto
from ryu.lib import hub
from ryu.lib.packet import packet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet, arp, ipv4, ipv6,tcp
from timeit import default_timer as timer
from netaddr import IPAddress, IPNetwork
from ryu.cmd import manager
from pprint import pprint
from copy import deepcopy
import networkx as nx
import pickle

import utils.SetCover
from utils.HostIdIPConverter import id_to_ip
from .ControllerTemplate import ControllerTemplate
from utils.FlowGenerator import generate_random_flows,generate_switch_flow_list


class Controller(ControllerTemplate):
    timeout: int
    topology: nx.Graph
    switch_switch_port: dict[(int, int), int] # (switch id from, to) -> port id
    switch_host_port: dict[(int, int), int] # (switch id, host id) -> port id
    flows: dict[int, [int]] # flow id -> list of switches on flow path
    switch_flows: dict[int, [int]] # switch id -> list of flow ids that pass though it
    polling: dict[int, [int]] # switch id -> flows to poll statistics, [] if not polled
    flow_stats: dict[int, int] # flow id -> number of packets
    prev_flow_stats: dict[int, int]  # flow id -> number of packets
    switch_configured: dict[int, bool] # switch id -> bool
    online_switches: dict[int, Datapath] # switch id -> switch object
    random_type: str
    pid_of_mininet: int
    unchanged_count:int

    def __init__(self, *args, **kwargs):
        super(ControllerTemplate, self).__init__(*args, **kwargs)
        self.info('Controller started')
        num_flows = cfg.CONF['flowcover']['num_flows']
        self.timeout = cfg.CONF['flowcover']['timeout']
        self.read_pid_of_mininet()
        print('Finished Reading PID of mininet')
        self.online_switches = {}
        self.switch_configured = {}
        self.get_initial_topology()
        print('Topology obtained from mininet')
        print(f'Random Type: {self.random_type}')
        self.flows = self.generate_random_flows(num_flows)
        print(f'{num_flows} Random flows generated')
        pprint(self.flows)
        self.switch_flows = self.generate_switch_flow_list()
        self.write_flows_to_file()
        print('Flows written to file to notify mininet')
        self.polling = self.set_cover()
        print('SetCover calculation finished, solution:')
        self.flow_stats = {}
        self.prev_flow_stats = {}
        self.monitor_thread = hub.spawn(self._monitor)
        self.unchanged_count = 0

    def read_pid_of_mininet(self) -> None:
        with open('pid.txt', 'r') as f:
            self.pid_of_mininet = int(f.readline())

    def get_initial_topology(self) -> None:
        self.topology = nx.read_adjlist('topology.bin')
        with open('random_type.txt', 'r') as f:
            self.random_type = f.readline()
            assert self.random_type in ['erdos-renyi', 'waxman', 'linear']
        with open('switch_switch_port_id.bin', 'rb') as f:
            self.switch_switch_port = pickle.load(f)
        with open('switch_host_port_id.bin', 'rb') as f:
            self.switch_host_port = pickle.load(f)
        # set all switches to not configured
        for s in self.topology.nodes:
            self.switch_configured[int(s)] = False


    def generate_random_flows(self, m: int) -> dict[int, [int]]:
        """
        TODO: select random paths from topology and generate random flows
        m is the number of random flows
        Use self.topology and networkx.
        return value should be a dict that maps flow ids (randomly taken, easiest way is to just increment)
            to a list of switch ids that describe the path,
        """

        return generate_random_flows(m,self.topology)

    def generate_switch_flow_list(self) -> dict[int, [int]]:
        """
        TODO: Converts the dict of flows to the dict of switches where the flow passes through
        Output format: a dict that maps switch ids to a list of flow ids that run on the switch.
        Use self.flows
        :return:
        """

        return generate_switch_flow_list(self.flows)

    def write_flows_to_file(self) -> None:
        with open('random_flows.bin', 'wb') as f:
            pickle.dump(self.flows, f)

    def set_cover(self) -> dict[int, [int]]:
        """
        TODO: transform the flow/switch_flow structure into set cover input and solve it
        Use self.flows and self.switch_flows
        :return: a dict: switch id -> flows to poll
        you might want to create some more helper methods.
        """
        # Step 1: construction
        flows = list(self.flows.keys())
        switch_flows = self.switch_flows
        #switch_flows = deepcopy(self.switch_flows)
        #for f in flows:
        #    switch_flows[-f] = [f]
        print(f'flows is{flows}')
        print(f'switch_flows is{switch_flows}')

        # Step 2: calculation
        polling = utils.SetCover.set_cover_solve(flows,switch_flows)
        # call utils.set_cover_solve here
        return polling

    def request_stats(self, datapath: Datapath) -> None:
        """
        TODO: Request statistics according to the result of set cover algorithm.
        Use self.polling.
        To poll all stats on a switch: use OFPFlowStatsRequest as before
        To poll one/some stats on a switch: use OFPFlowStatsRequest with cookies.
        Refer to Ryu documentation for more details.
        """
        datapath_id = int(datapath.id)
        for switch_id, flows in self.polling.items():
            if datapath_id ==switch_id:
                for flow_id in flows:
                    cookie = flow_id  # Assuming flow_id can be directly used as a cookie
                    cookie_mask = 0xFFFFFFFFFFFFFFFF  # Mask to match the exact cookie
                    req = OFPFlowStatsRequest(datapath, 0, ofproto.OFPTT_ALL,
                                                  ofproto.OFPP_ANY, ofproto.OFPG_ANY,
                                                  cookie, cookie_mask)
                    datapath.send_msg(req)



    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev) -> None:
        #print("count is",self.unchanged_count)
        """
        TODO: Callback of received statistics. Record the data from individual flow.
        Write results to self.flow_stats.
        """
        body = ev.msg.body
        #pprint(body)
        for stat in body:
            flow_id = stat.cookie
            self.flow_stats[flow_id] = stat.byte_count



    @set_ev_cls(ofp_event.EventOFPStateChange,
                [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change_handler(self, ev):
        """
        Register online routers
        """
        datapath = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if datapath.id not in self.online_switches:
                self.logger.debug('register switch: %x', datapath.id)
                self.online_switches[datapath.id] = datapath
        elif ev.state == DEAD_DISPATCHER:
            if datapath.id in self.online_switches:
                self.logger.debug('unregister switch: %x', datapath.id)
                del self.online_switches[datapath.id]
                self.switch_configured[datapath.id] = False

    def _monitor(self):
        while all(self.switch_configured.values()):
            for dp in self.online_switches.values():
                self.request_stats(dp)
            # TODO: write self.flow_stats to a json under the stats/ directory, filename should include the current timestamp!
            # Save flow_stats to a JSON file with a timestamped filename
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"stats/flow_stats.json"

            # Ensure the stats directory exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            with open(filename, 'w') as f:
                json.dump(self.flow_stats, f, indent=4)
            pprint(self.flow_stats)
            if any(v > 0 for v in self.flow_stats.values()) and self.prev_flow_stats == self.flow_stats:
                self.unchanged_count += 1
            else:
                self.unchanged_count = 0
            print(f'Flows stats unchanged for {self.unchanged_count} times.')
            if self.unchanged_count >= 10:
                print("Flow stats stable (10 count). Waiting for server to quit.")
                wait_time_start = timer()
                server_quited: dict[int, bool] = {}
                for flow_id in self.flows.keys():
                    server_quited[flow_id] = False
                while not all(server_quited.values()):
                    time.sleep(1)
                    time_now = timer()
                    wait_time = time_now - wait_time_start
                    print('Current waiting time: ', wait_time)
                    if wait_time >= self.timeout:
                        print(f'Server exit timed out. Force exiting. All remaining flows will be set to zero.')
                        break
                    for flow_id in self.flows.keys():
                        filename = f'/tmp/trafgen_{flow_id}.log'
                        if os.path.exists(filename):
                            server_quited[flow_id] = True
                print("All server exited. Exiting controller and mininet.")
                os.kill(self.pid_of_mininet, signal.SIGUSR2)
                os._exit(0)
            self.prev_flow_stats = deepcopy(self.flow_stats)
            hub.sleep(3)


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
        if eth.ethertype == ether_types.ETH_TYPE_IPV6:
            pkt_ipv6 = pkt.get_protocol(ipv6.ipv6)
            if pkt_ipv6.nxt == 58:
                pkt_icmpv6 = pkt.get_protocol(icmpv6.icmpv6)
                if pkt_icmpv6.type_ == 135:
                    # create neighbor advertisement
                    ndp_dst = pkt_icmpv6.data.dst
                    response_pkt = packet.Packet()
                    response_pkt.add_protocol(
                        ethernet.ethernet(
                            ethertype=ether_types.ETH_TYPE_IPV6,
                            dst=eth.src,
                            src='24:CD:AB:CD:AB:CD'
                        )
                    )
                    response_ipv6 = copy.deepcopy(pkt_ipv6)
                    response_ipv6.dst=pkt_ipv6.src
                    response_ipv6.src=ndp_dst
                    response_ipv6.nxt=58
                    response_pkt.add_protocol(
                        response_ipv6
                    )
                    response_pkt.add_protocol(
                        icmpv6.icmpv6(
                            type_=136,
                            code=0,
                            data=icmpv6.nd_neighbor(
                                dst=ndp_dst,
                                res=0x7,
                                option=icmpv6.nd_option_tla(
                                    hw_src='24:CD:AB:CD:AB:CD'
                                )
                            )
                        )
                    )
                    self.send_pkt(datapath, response_pkt, port=in_port)

    def program_single_flow(self, dp, current_switch_id: int, flow_id: int, priority: int, reverse: bool, count_stats: bool):
        if not reverse:
            switch_list = self.flows[flow_id]
        else:
            switch_list = self.flows[flow_id][::-1]
        first_switch_id = int(switch_list[0])
        first_switch_ip = id_to_ip(first_switch_id)
        last_switch_id = int(switch_list[-1])
        last_switch_ip = id_to_ip(last_switch_id)

        for counter, switch_id in enumerate(switch_list):
            switch_id = int(switch_id)
            if switch_id == current_switch_id:
                if switch_id == last_switch_id:
                    host_port = self.switch_host_port[(current_switch_id, last_switch_id)]
                    actions = [parser.OFPActionOutput(host_port)]
                else:
                    next_switch_id = int(switch_list[counter + 1])
                    out_port = self.switch_switch_port[(current_switch_id, next_switch_id)]
                    actions = [parser.OFPActionOutput(out_port)]
                if count_stats:
                    match = parser.OFPMatch(
                        eth_type=ether_types.ETH_TYPE_IPV6,
                        #ip_proto=inet.IPPROTO_TCP,
                        ipv6_src=f"{first_switch_ip}/64",
                        ipv6_dst=f"{last_switch_ip}/64",
                        ipv6_flabel=flow_id,
                        #tcp_flags=(0x10, 0x13)
                    )
                    self.program_flow(cookie=flow_id, datapath=dp, match=match, actions=actions, priority=priority)
                else:
                    match = parser.OFPMatch(
                        eth_type=ether_types.ETH_TYPE_IPV6,
                        ipv6_src=f"{first_switch_ip}/64",
                        ipv6_dst=f"{last_switch_ip}/64",
                    )
                    self.program_flow(cookie=1000000000, datapath=dp, match=match, actions=actions, priority=priority)




    # This decorator makes sure that the function below is invoked
    # every time a new switch is connected to our controller.
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """SwitchConnect Callback."""
        print(f"Switch {ev.msg.datapath.id} connected.")
        dp = ev.msg.datapath
        parser = dp.ofproto_parser
        current_switch_id = ev.msg.datapath.id
        print(current_switch_id)
        #self.remove_flows(ev.msg.datapath, 0)


        # Forward NDP to controller
        match = parser.OFPMatch(
            eth_type=ether_types.ETH_TYPE_IPV6,
            ip_proto=58,
            icmpv6_type=135,
        )
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER)]
        self.program_flow(cookie=1000000000, datapath=dp, match=match, actions=actions, priority=1)

        # Forward reinjected NDP packet to host
        match = parser.OFPMatch(
            eth_type=ether_types.ETH_TYPE_IPV6,
            ip_proto=58,
            icmpv6_type=136,
        )
        actions = [parser.OFPActionOutput(self.switch_host_port[(current_switch_id, current_switch_id)])]
        self.program_flow(cookie=1000000000, datapath=dp, match=match, actions=actions, priority=1)

        for flow_id in self.flows:
            self.program_single_flow(dp, current_switch_id, flow_id, 2, reverse=False, count_stats=False)
            self.program_single_flow(dp, current_switch_id, flow_id, 2, reverse=True, count_stats=False)
            self.program_single_flow(dp, current_switch_id, flow_id, 3, reverse=False, count_stats=True)

        self.switch_configured[current_switch_id] = True
        # Count how many switches are set up
        num_switches_done = len({k: v for k, v in self.switch_configured.items() if v == True})
        print(f'A total of {num_switches_done} switches were configured.')
        if all(self.switch_configured.values()):
            print('All switches setup complete; sending signal to notify mininet')
            # if all switch configured: notify mininet to start generating traffic
            os.kill(self.pid_of_mininet, signal.SIGUSR1)




def main():
    # Register a new CLI parameter for Ryu; no docs available; see Stackoverflow #25601133
    # CLI param: --flowcover-num-flows --flowcover-timeout
    cfg.CONF.register_cli_opts(
        [
            cfg.IntOpt('num-flows', default=10),
            cfg.IntOpt('timeout', default=900)
        ]
    , 'flowcover')
    sys.argv.append('controller.Controller')
    sys.argv.append('--verbose')
    sys.argv.append('--enable-debugger')
    sys.argv.append('--use-stderr')
    sys.argv.append('--ofp-listen-host=127.0.0.1')
    manager.main()


if __name__ == '__main__':
    main()
