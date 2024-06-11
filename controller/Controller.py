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
from ryu.ofproto.ofproto_v1_3_parser import OFPFlowStatsRequest
from ryu.ofproto.ofproto_v1_3 import OFPMPF_REQ_MORE
import ryu.ofproto.ofproto_v1_3_parser as parser
import ryu.ofproto.ofproto_v1_3 as ofproto
from ryu.lib import hub
from ryu.lib.packet import packet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ethernet, arp, ipv4, ipv6
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


class Controller(ControllerTemplate):
    topology: nx.Graph
    switch_switch_port: dict[(int, int), int] # (switch id from, to) -> port id
    switch_host_port: dict[(int, int), int] # (switch id, host id) -> port id
    flows: dict[int, [int]] # flow id -> list of switches on flow path
    switch_flows: dict[int, [int]] # switch id -> list of flow ids that pass though it
    polling: dict[int, [int]] # switch id -> flows to poll statistics, [] if not polled
    flow_stats: dict[int, int] # flow id -> number of packets
    switch_configured: dict[int, bool] # switch id -> bool
    online_switches: dict[int, Datapath] # switch id -> switch object
    pid_of_mininet: int

    def __init__(self, *args, **kwargs):
        super(ControllerTemplate, self).__init__(*args, **kwargs)
        self.info('Controller started')
        num_flows = cfg.CONF['flowcover']['num_flows']
        self.read_pid_of_mininet()
        print('Finished Reading PID of mininet')
        self.online_switches = {}
        self.switch_configured = {}
        self.get_initial_topology()
        print('Topology obtained from mininet')
        self.flows = self.generate_random_flows(num_flows)
        print(f'{num_flows} Random flows generated')
        pprint(self.flows)
        self.switch_flows = self.generate_switch_flow_list()
        self.write_flows_to_file()
        print('Flows written to file to notify mininet')
        self.polling = self.set_cover()
        print('SetCover calculation finished, solution:')
        pprint(self.polling)
        self.flow_stats = {}
        self.monitor_thread = hub.spawn(self._monitor)

    def read_pid_of_mininet(self) -> None:
        with open('pid.txt', 'r') as f:
            self.pid_of_mininet = int(f.readline())

    def get_initial_topology(self) -> None:
        self.topology = nx.read_adjlist('topology.bin')
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

        # flows = {}
        # for flow_id, path in enumerate(nx.generate_random_paths(self.topology, sample_size=m, path_length=self.topology.number_of_nodes())):
        #     flows[flow_id] = path
        # print(flows)
        # return flows
        flows = {}
        flow_set = set() # deduplicate
        nodes = list(self.topology.nodes())  # Assume nodes are already integers or convertible to integers
        while len(flow_set) < m:
            source = random.choice(nodes)
            target = random.choice([node for node in nodes if node != source])
            paths = list(nx.all_simple_paths(self.topology, source=source, target=target))
            if paths:
                selected_path = random.choice(paths)
                converted_path = (int(node) for node in selected_path)
                flow_set.add(converted_path)
        for index, flow in zip(range(m), flow_set):
            flows[index] = list(flow)

        return flows

    def generate_switch_flow_list(self) -> dict[int, [int]]:
        """
        TODO: Converts the dict of flows to the dict of switches where the flow passes through
        Output format: a dict that maps switch ids to a list of flow ids that run on the switch.
        Use self.flows
        :return:
        """
        switch_flow_dict = {}

        for flow_id, switches in self.flows.items():
            for switch_id in switches:
                switch_id = int(switch_id)
                switch_flow_dict.setdefault(switch_id, set()).add(flow_id)

        return {switch_id: list(flow_ids) for switch_id, flow_ids in switch_flow_dict.items()}

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
        construction_time_start = timer()
        # Step 1: construction
        flows = list(self.flows.keys())
        switch_flows = self.switch_flows
        #switch_flows = deepcopy(self.switch_flows)
        #for f in flows:
        #    switch_flows[-f] = [f]
        print(f'flows is{flows}')
        print(f'switch_flows is{switch_flows}')
        construction_time_end = timer()
        construction_time_elapsed = construction_time_end - construction_time_start

        calc_time_start = timer()

        # Step 2: calculation
        polling = utils.SetCover.set_cover_solve(flows,switch_flows)
        # call utils.set_cover_solve here
        calc_time_end = timer()
        calc_time_elapsed = calc_time_end - calc_time_start
        # Write two timers to csv
        return polling

    def request_stats(self, datapath: Datapath) -> None:
        """
        TODO: Request statistics according to the result of set cover algorithm.
        Use self.polling.
        To poll all stats on a switch: use OFPFlowStatsRequest as before
        To poll one/some stats on a switch: use OFPFlowStatsRequest with cookies.
        Refer to Ryu documentation for more details.
        """
        datapath_id = int(str(datapath.id), 16)
        for switch_id, flows in self.polling.items():
            if datapath_id ==switch_id:
                for flow_id in flows:
                    cookie = flow_id  # Assuming flow_id can be directly used as a cookie
                    # cookie_mask = 0xFFFFFFFFFFFFFFFF  # Mask to match the exact cookie
                    req = OFPFlowStatsRequest(datapath, 0, ofproto.OFPTT_ALL,
                                                  ofproto.OFPP_ANY, ofproto.OFPG_ANY,
                                                  cookie)
                    datapath.send_msg(req)



    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply_handler(self, ev) -> None:
        """
        TODO: Callback of received statistics. Record the data from individual flow.
        Write results to self.flow_stats.
        """
        body = ev.msg.body

        pprint(body)
        for stat in body:
            flow_id = stat.cookie
            self.flow_stats[flow_id] = stat.packet_count
        pprint(self.flow_stats)


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

    def _monitor(self):
        while True:
            for dp in self.online_switches.values():
                self.request_stats(dp)
            # TODO: write self.flow_stats to a json under the stats/ directory, filename should include the current timestamp!
            # Save flow_stats to a JSON file with a timestamped filename
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"stats/flow_stats_{timestamp}.json"

            # Ensure the stats directory exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            with open(filename, 'w') as f:
                json.dump(self.flow_stats, f, indent=4)
            hub.sleep(10)


    '''
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
    '''

    # This decorator makes sure that the function below is invoked
    # every time a new switch is connected to our controller.
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        """SwitchConnect Callback."""
        print(f"Switch {ev.msg.datapath.id} connected.")
        # self.remove_flows(ev.msg.datapath, 0)
        current_switch_id = int(str(ev.msg.datapath.id),16)
        for flow_id in self.flows:
            switch_list = self.flows[flow_id]
            last_switch_id = int(switch_list[-1])
            last_switch_ip = id_to_ip(last_switch_id)
            for counter, switch_id in enumerate(switch_list):
                switch_id = int(switch_id)
                if switch_id == current_switch_id:
                    dp = ev.msg.datapath
                    parser = dp.ofproto_parser
                    if switch_id == last_switch_id:
                        host_port = self.switch_host_port[(current_switch_id, last_switch_id)]
                        actions = [parser.OFPActionOutput(host_port)]
                    else:
                        next_switch_id = int(switch_list[counter + 1])
                        out_port = self.switch_switch_port[(current_switch_id, next_switch_id)]
                        actions = [parser.OFPActionOutput(out_port)]
                    match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP
                                            , ipv4_dst=last_switch_ip)
                    self.program_flow(cookie=flow_id, datapath=dp, match=match, actions=actions, priority=1)
        self.switch_configured[current_switch_id] = True
        print('-----------------------------------------------')
        self.logger.debug('OFPSwitchFeatures received: '
                          'datapath_id=0x%016x n_buffers=%d '
                          'n_tables=%d auxiliary_id=%d '
                          'capabilities=0x%08x',
                          ev.msg.datapath_id, ev.msg.n_buffers, ev.msg.n_tables,
                          ev.msg.auxiliary_id, ev.msg.capabilities)
        if all(self.switch_configured.values()):
            print('All switches setup complete; sending signal to notify mininet')
            # if all switch configured: notify mininet to start generating traffic
            os.kill(self.pid_of_mininet, signal.SIGUSR1)




def main():
    # Register a new CLI parameter for Ryu; no docs available; see Stackoverflow #25601133
    # CLI param: --flowcover-num-flows
    cfg.CONF.register_cli_opts(
        [
            cfg.IntOpt('num-flows', default=10)
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
