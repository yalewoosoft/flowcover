#!/bin/bash

# Array of different numbers of flows to test
declare -a switch_numbers=( 200 400 600 800 1000 1200 1400 1600 1800 2000 )

# Loop through each flow count and run Controller.py
for number in "${switch_numbers[@]}"
do
    echo "Running figure_6.py with --flowcover-num-flows=$number"
    python figure_6.py $number
done
