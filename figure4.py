
import pandas as pd
import time
import os


from utils import GraphGenerator
from utils.SetCover import set_cover_solve
from utils import FlowGenerator

erdos_renyi_graph = GraphGenerator.erdos_renyi_generator(n=20, p=0.1)  # Example parameters
waxman_graph = GraphGenerator.waxman_generator_1(n=10, alpha=0.1, beta=0.1)  # Example parameters

graphs = {
    'Erdos-Renyi': erdos_renyi_graph,
    'Waxman': waxman_graph
}

number_of_flows = [i for i in range(0, 100001, 10000)]
def calculate_naive_cost(graph, flows):
    # Each request is 122 bytes and each reply is 174 bytes
    request_size = 122
    reply_size = 174
    total_cost = 0

    for flow in flows.values():
        total_cost += request_size + reply_size

    return total_cost
def calculate_optimized_cost(flow_ids, switch_flow_list):
    optimized_set = set_cover_solve(flow_ids, switch_flow_list)
    total_cost = 0

    for switch_id, flows in optimized_set.items():
        total_cost += 122 + 78 + 96 * len(flows)

    return total_cost

results = []

for name, graph in graphs.items():
    for flow_count in number_of_flows:
        flows = FlowGenerator.generate_random_flows(flow_count, graph)
        flow_ids = list(flows.keys())
        switch_flow_list = FlowGenerator.generate_switch_flow_list(flows)

        naive_cost = calculate_naive_cost(graph, flows)
        optimized_cost = calculate_optimized_cost(flow_ids, switch_flow_list)
        results.append({
            'Graph': name,
            'Number of Flows': flow_count,
            'Naive Cost': naive_cost,
            'Optimized Cost': optimized_cost
        })

timestamp = time.strftime("%Y%m%d-%H%M%S")
filename = f"data/figure_4_{timestamp}.csv"

# Ensure the stats directory exists
os.makedirs(os.path.dirname(filename), exist_ok=True)

# Convert results to DataFrame and save as CSV
df = pd.DataFrame(results)
df.to_csv(filename, index=False)

print(f"Results saved to {filename}")