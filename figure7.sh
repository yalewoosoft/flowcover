#!/bin/bash

num_switches=40
loss_switch_ratio=0.1
packet_loss_ratio=0.01
killall python3
killall python3.9
#rm stats/*
rm logs/*
rm /tmp/trafgen*
screen -XS mininet quit
screen -XS controller quit
mn -c

for num_flows in  4000 4500 5000 5500 6000; do
  rm /tmp/mininet_started.flag
  echo Starting emulation with num flows $num_flows...
  screen -dmS mininet -L -Logfile logs/screen_mininet_$num_flows.log python3 -m network.SimulatedNetwork --num-switches=$num_switches --random-type=waxman --loss-switch-ratio=$loss_switch_ratio --packet-loss-ratio=$packet_loss_ratio --num-bytes-sent=100000 --bitrate=1MB
  echo Waiting for Mininet to start...
  while [ ! -f /tmp/mininet_started.flag ]; do
    sleep 1
  done
  echo Mininet started.
  screen -dmS controller -L -Logfile logs/screen_controller_$num_flows.log python3 -m controller.Controller --flowcover-num-flows=$num_flows --flowcover-timeout=900
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
  mv stats/trafgen_stats.json stats/trafgen_stats_waxman_$num_flows.json
  mv stats/flow_stats.json stats/flow_stats_waxman_$num_flows.json
  killall python3
  killall python3.9
  rm /tmp/trafgen*
done
