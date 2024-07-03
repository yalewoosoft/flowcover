#!/bin/bash

num_switches=40
num_flows=2000
packet_loss_ratio=0.01
killall python3
killall python3.9
# rm stats/*
rm logs/*
rm /tmp/trafgen*
screen -XS mininet quit
screen -XS controller quit
mn -c

for loss_switch_ratio in 0.18; do
  rm /tmp/mininet_started.flag
  echo Starting emulation with loss ratio $loss_switch_ratio...
  screen -dmS mininet -L -Logfile logs/screen_mininet_$loss_switch_ratio.log python3 -m network.SimulatedNetwork --num-switches=$num_switches --random-type=erdos-renyi --erdos-renyi-prob=0.2 --loss-switch-ratio=$loss_switch_ratio --packet-loss-ratio=$packet_loss_ratio --num-bytes-sent=100000 --bitrate=1MB
  echo Waiting for Mininet to start...
  while [ ! -f /tmp/mininet_started.flag ]; do
    sleep 1
  done
  echo Mininet started.
  screen -dmS controller -L -Logfile logs/screen_controller_$loss_switch_ratio.log python3 -m controller.Controller --flowcover-num-flows=$num_flows --flowcover-timeout=900
  echo Waiting for mininet to quit...
  while screen -list | grep -q mininet
  do
    sleep 1 # wait for mininet to quit
  done
  echo Mininet exited.
  while screen -list | grep -q controller
  do
    sleep 1 # wait for controller to quit
  done
  echo Controller exited. Saving stats.
  screen -XS mininet quit
  screen -XS controller quit
  sleep 5
  mv stats/trafgen_stats.json stats/trafgen_stats_$loss_switch_ratio.json
  mv stats/flow_stats.json stats/flow_stats_$loss_switch_ratio.json
  killall python3
  killall python3.9
  rm /tmp/trafgen*
done
