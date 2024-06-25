#!/bin/bash

num_switches=20
num_flows=10
loss_switch_ratio=0.1
killall python3
killall python3.9
rm stats/*
rm logs/*
screen -XS mininet quit
screen -XS controller quit
mn -c

for packet_loss_ratio in 0 0.02 0.04 0.06 0.08 0.1; do
  echo Starting emulation with loss ratio $packet_loss_ratio...
  screen -dmS mininet -L -Logfile logs/screen_mininet_$packet_loss_ratio.log python3 -m network.SimulatedNetwork --num-switches=$num_switches --random-type=erdos-renyi --erdos-renyi-prob=0.5 --loss-switch-ratio=$loss_switch_ratio --packet-loss-ratio=$packet_loss_ratio --num-bytes-sent=100000 --bitrate=100MB
  sleep 60 # this needs to be better timed?
  screen -dmS controller -L -Logfile logs/screen_controller_$packet_loss_ratio.log python3 -m controller.Controller --flowcover-num-flows=$num_flows
  echo Waiting for mininet to quit...
  while screen -list | grep -q mininet
  do
    sleep 1 # wait for mininet to quit
  done
  echo Mininet exited. Saving stats.
  sleep 30
  screen -XS mininet quit
  screen -XS controller quit
  sleep 5
  mv stats/trafgen_stats.json stats/trafgen_stats_$packet_loss_ratio.json
  mv stats/flow_stats.json stats/flow_stats_$packet_loss_ratio.json
  killall python3
  killall python3.9
done