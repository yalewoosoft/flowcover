#!/bin/bash

# Array of different numbers of flows to test
declare -a flow_counts=( 10000 20000 30000 40000 50000 60000 70000 80000 90000 100000 )

# Loop through each flow count and run Controller.py
for flow_count in "${flow_counts[@]}"
do
    echo "Running Controller.py with --flowcover-num-flows=$flow_count"
    python figure5.py $flow_count
done