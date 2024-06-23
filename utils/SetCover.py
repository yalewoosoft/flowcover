import heapq
import random
import itertools
def weight(s: [int]) -> int:
    return 122 + 78 * (len(s))

def set_cover_solve(f: [int], s: dict[int, [int]]) -> dict[int, [int]]:
    uncovered_flows = set(f)
    picked_switch = {}
    flow_to_switch_ids = {}
    weight_of_switch = {}
    pq = []
    entry_finder = {}
    REMOVED = '<removed-task>'
    counter = itertools.count()

    single_flow_weight = weight([0])  # Assume this calculates weight for a single flow
    single_flow_ratio = single_flow_weight / 1

    # Process each switch and their associated flows
    for switch_id, flows in s.items():
        weight_of_switch[switch_id] = weight(flows)  # Calculate and store the weight for each switch
        for flow in flows:
            if flow not in flow_to_switch_ids:
                flow_to_switch_ids[flow] = []
            flow_to_switch_ids[flow].append(switch_id)

    def add_or_update_switch(switch_id, flows):
        'Add a new switch or update the priority of an existing switch'
        intersection = set(flows).intersection(uncovered_flows)
        if intersection:
            ratio = weight_of_switch[switch_id] / len(intersection)
            if switch_id in entry_finder and entry_finder[switch_id][2] != REMOVED:
                remove_switch(switch_id)
            count = next(counter)
            entry = [ratio, count, switch_id, flows]
            entry_finder[switch_id] = entry
            heapq.heappush(pq, entry)

    def remove_switch(switch_id):
        'Mark an existing switch as REMOVED.'
        entry = entry_finder.pop(switch_id)
        entry[2] = REMOVED

    def pop_switch():
        'Pop and return the switch with the lowest ratio that is not removed.'
        while pq:
            ratio, count, switch_id, flows = heapq.heappop(pq)
            if switch_id != REMOVED:
                del entry_finder[switch_id]
                return ratio, switch_id, flows
        raise KeyError("pop from an empty priority queue")

    # Initialize priority queue
    for switch_id, flows in s.items():
        add_or_update_switch(switch_id, flows)

    while uncovered_flows:
        to_updated_switch = set()
        if not pq:
            print("Priority queue is empty, no more switches to pick.")
            break

        if pq[0][0] > single_flow_ratio:
            # Randomly pick a flow and cover it
            flow = random.choice(list(uncovered_flows))
            chosen_switch = random.choice(flow_to_switch_ids[flow])
            picked_switch[chosen_switch] = picked_switch.get(chosen_switch, []) + [flow]
            uncovered_flows.remove(flow)
            for affected_switch in flow_to_switch_ids[flow]:
                if affected_switch in entry_finder:
                    add_or_update_switch(affected_switch, s[affected_switch])
            print(f"Randomly picked switch {chosen_switch} for single flow {flow} due to high ratio in the pq {pq[0][0]}.")
            continue

        current_ratio, switch_id, flows = pop_switch()
        newly_covered_flows = set(flows).intersection(uncovered_flows)
        if newly_covered_flows:
            picked_switch[switch_id] = flows
            uncovered_flows.difference_update(newly_covered_flows)
            print(f"Picked switch {switch_id} covering flows {flows} with ratio {current_ratio}.")

            # Update priorities for all affected switches
            for flow in newly_covered_flows:
                for affected_switch in flow_to_switch_ids[flow]:
                    to_updated_switch.add(affected_switch)
            for switch_id in to_updated_switch:
                add_or_update_switch(switch_id,s[switch_id])

    if uncovered_flows:
        print("Not all flows could be covered with the available switches.")
    else:
        print("All flows have been successfully covered.")

    return picked_switch


if "__main__" == __name__:
    f =[1,2,3,4,5,6,7,8,9]
    s = {
        1:[1,2,3],
        2:[1,2],
        3:[1,2,4,5],
        4:[2,5],
        5:[3,5,6],
        6:[3,4,6],
        7:[2,4,7,8,9]
    }
    print(set_cover_solve(f,s))