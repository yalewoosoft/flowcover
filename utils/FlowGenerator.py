import networkx as nx
from random import random, choice,shuffle,randint

from networkx import connected_components

from utils.GraphGenerator import *
from math import factorial
from pprint import pprint

def permutation_number(n: int, k: int) -> int:
    return int(factorial(n) / factorial(n-k))
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

    # Validate
    max_flows = 0
    all_scc = connected_components(topology)
    for scc in all_scc:
        num_nodes = len(scc)
        max_flows += sum((permutation_number(num_nodes, k) for k in range(1, num_nodes+1)))
    if m > max_flows:
        raise ValueError(f"Impossible to generate {m} flows for this graph. Either raise generation probability (by changing parameters) or retry.")

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
        if path not in all_paths and len(path) >= 1:
            all_paths.add(path)
            flows[flow_id] = list(path)
            print(f'Flow {flow_id} generated.')
            flow_id += 1

    return flows
if "__main__" == __name__:
    topology = erdos_renyi_generator(200,0)
    flows = generate_random_flows(200,topology)
    for flow_id, paths in flows.items():
        print(flow_id, paths)


