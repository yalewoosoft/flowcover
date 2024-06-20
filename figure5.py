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

erdos_renyi_graph = GraphGenerator.erdos_renyi_generator(n=50, p=0.1)  # Example parameters
waxman_graph = GraphGenerator.waxman_generator_1(n=50, alpha=0.1, beta=0.1)  # Example parameters

graphs = {
    'Erdos-Renyi': erdos_renyi_graph,
    'Waxman': waxman_graph
}

num_flows = int(sys.argv[1])


def save_timing_results(num_flows, construction_time, calc_time):
    filename = 'data/timing_results.csv'

    # Ensure the data directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    # Append results to the CSV file
    with open(filename, 'a', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        if csvfile.tell() == 0:  # Check if file is empty to write header
            csvwriter.writerow(['Number of Active Flows', 'Construction Time (ms)', 'Calculation Time (ms)'])
        csvwriter.writerow([num_flows, construction_time * 1000, calc_time * 1000])


flows = FlowGenerator.generate_random_flows(num_flows, erdos_renyi_graph)
# Construction Timer
construction_time_start = timer()
switch_flows = FlowGenerator.generate_switch_flow_list(flows)
construction_time_end = timer()
construction_time_elapsed = construction_time_end - construction_time_start
# Calculate Timer
calc_time_start = timer()
flows_list = list(flows.keys())
SetCover.set_cover_solve(flows_list, switch_flows)
calc_time_end = timer()
calc_time_elapsed = calc_time_end - calc_time_start
# Save Result
save_timing_results(len(flows), construction_time_elapsed, calc_time_elapsed)
