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
if "__main__" == __name__:
    topology = erdos_renyi_generator(200,0.4)
    flows = generate_random_flows(10000,topology)
    for flow_id, paths in flows.items():
        print(flow_id, paths)


