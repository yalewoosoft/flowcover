import csv
import random
import sys

import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd
import time
import os
from timeit import default_timer as timer
from utils import GraphGenerator
from utils import FlowGenerator
from utils import SetCover

num_switchs = int(sys.argv[1])

erdos_renyi_graph = GraphGenerator.erdos_renyi_generator(n=num_switchs, p=0.1)  # Example parameters
waxman_graph = GraphGenerator.waxman_generator_1(n=num_switchs, alpha=0.1, beta=0.1)  # Example parameters

graphs = {
    'Erdos-Renyi': erdos_renyi_graph,
    'Waxman': waxman_graph
}


def save_timing_results(graph_type,num_switchs, calc_time,times):
    filename = 'data/timing_results_average.csv'

    # Ensure the data directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Append results to the CSV file
    with open(filename, 'a', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        if csvfile.tell() == 0:  # Check if file is empty to write header
            csvwriter.writerow(['Type of graph', 'Number of switches', 'Calculation Time (ms)', 'Times'])
        csvwriter.writerow([type,num_switchs,calc_time * 1000,times])


for type,graph in graphs.items():
    for times in range(3):
        flows = FlowGenerator.generate_random_flows(20000, graph)
        # Construction Timer
        switch_flows = FlowGenerator.generate_switch_flow_list(flows)
        # Calculate Timer
        calc_time_start = timer()
        flows_list = list(flows.keys())
        SetCover.set_cover_solve(flows_list, switch_flows)
        calc_time_end = timer()
        calc_time_elapsed = calc_time_end - calc_time_start
        # Save Result
        save_timing_results(type, num_switchs, calc_time_elapsed,times)
