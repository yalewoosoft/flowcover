#!/usr/bin/env bash

if [ "$1" = '5' ]; then
  # Reproduce Figure 5
  python3 -m network.SimulatedNetwork --num-switches=200 --random-type=erdos-renyi --erdos-renyi-prob=0.1
  sleep 300
  python3 -m controller.Controller --flowcover-num-flows=1000
  python3 -m controller.Controller --flowcover-num-flows=10000
  python3 -m controller.Controller --flowcover-num-flows=20000
  python3 -m controller.Controller --flowcover-num-flows=30000
  python3 -m controller.Controller --flowcover-num-flows=40000
  python3 -m controller.Controller --flowcover-num-flows=50000
elif [ "$1" = '7.1' ]; then
  # Reproduce Figure 7
  python3 -m network.SimulatedNetwork --num-switches=200 --random-type=erdos-renyi --erdos-renyi-prob=0.1 --loss-switch-ratio=0.01 --packet-loss-ratio=0.1
  sleep 300
  python3 -m controller.Controller --flowcover-num-flows=1000
  python3 -m controller.Controller --flowcover-num-flows=10000
  python3 -m controller.Controller --flowcover-num-flows=20000
  python3 -m controller.Controller --flowcover-num-flows=30000
  python3 -m controller.Controller --flowcover-num-flows=40000
  python3 -m controller.Controller --flowcover-num-flows=50000
elif [ "$1" = '7.2' ]; then
  # Reproduce Figure 5
  python3 -m network.SimulatedNetwork --num-switches=200 --random-type=waxman --loss-switch-ratio=0.01 --packet-loss-ratio=0.1
  sleep 300
  python3 -m controller.Controller --flowcover-num-flows=1000
  python3 -m controller.Controller --flowcover-num-flows=10000
  python3 -m controller.Controller --flowcover-num-flows=20000
  python3 -m controller.Controller --flowcover-num-flows=30000
  python3 -m controller.Controller --flowcover-num-flows=40000
  python3 -m controller.Controller --flowcover-num-flows=50000
fi
