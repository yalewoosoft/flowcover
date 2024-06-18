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
    all_paths = set()  # To ensure unique paths

    def generate_path(start_node):
        path = []
        stack = [start_node]
        visited = set()

        while stack:
            node = stack.pop()
            if node not in visited:
                visited.add(node)
                path.append(node)
                neighbors = list(topology.neighbors(node))
                shuffle(neighbors)
                for neighbor in neighbors:
                    if neighbor not in visited:
                        stack.append(neighbor)

            # Limit the path length to prevent excessively long paths
            if len(path) >= randint(1, len(nodes)):  # Path length between 2 and min(10, number of nodes)
                break
        return tuple(path)

    while len(flows) < m:
        start_node = choice(nodes)
        path = generate_path(start_node)
        if path not in all_paths and len(path) > 1:  # Ensure path is unique and non-trivial
            all_paths.add(path)
            flows[flow_id] = list(path)
            flow_id += 1

    return flows

if "__main__" == __name__:
    topology = erdos_renyi_generator(200,0.5)
    flows = generate_random_flows(500,topology)
    for flow_id, paths in flows.items():
        print(flow_id, paths)


