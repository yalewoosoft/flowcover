import networkx as nx
from random import random, choice,shuffle,randint
from utils.GraphGenerator import *
from pprint import pprint


def generate_random_flows(m: int, topology: nx.Graph) -> dict[int, list[int]]:
    """
    Generate random flows in a topology. Ensures no flow is the same and uses backtracking when no unvisited neighbors are available.
    :param m: Number of flows to generate.
    :param topology: Networkx graph representing the topology.
    :return: Dictionary of flow IDs to path lists.
    """
    flows = {}
    flow_id = 0
    nodes = list(topology.nodes())
    all_paths = set()

    def generate_path(start_node):
        path = [int(start_node)]
        visited = {start_node}
        path_length = randint(1, len(nodes))
        current_node = start_node

        for _ in range(path_length - 1):
            neighbors = [n for n in topology.neighbors(current_node) if n not in visited and topology.has_edge(current_node, n)]
            if not neighbors:
                break
            next_node = choice(neighbors)
            path.append(int(next_node))
            visited.add(next_node)
            current_node = next_node

        return tuple(path)

    while len(flows) < m:
        start_node = choice(nodes)
        path = generate_path(start_node)
        if path not in all_paths and len(path) > 1:
            all_paths.add(path)
            flows[flow_id] = list(path)
            flow_id += 1

    return flows


def generate_switch_flow_list(flows:dict[int, list[int]]) -> dict[int, [int]]:
        """
        TODO: Converts the dict of flows to the dict of switches where the flow passes through
        Output format: a dict that maps switch ids to a list of flow ids that run on the switch.
        Use self.flows
        :return:
        """
        switch_flow_dict = {}

        for flow_id, switches in flows.items():
            for switch_id in switches:
                switch_id = int(switch_id)
                switch_flow_dict.setdefault(switch_id, set()).add(flow_id)

        return {switch_id: list(flow_ids) for switch_id, flow_ids in switch_flow_dict.items()}

if "__main__" == __name__:
    topology = erdos_renyi_generator(200,0.4)
    flows = generate_random_flows(10000,topology)
    for flow_id, paths in flows.items():
        print(flow_id, paths)


