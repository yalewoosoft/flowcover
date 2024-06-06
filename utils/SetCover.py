import heapq
import random
def weight(s: [int]) -> int:
    return 122 + 78 * (len(s))


def set_cover_solve(f: [int], s: dict[int, [int]]) -> dict[int, [int]]:
    uncovered_flows = set(f)
    picked_switch = {}
    flow_to_switch_ids = {}
    weight_of_switch = {}
    single_flow_weight = weight([0])
    single_flow_ratio = single_flow_weight / 1

    # Process each switch and their associated flows
    for switch_id, flows in s.items():
        weight_of_switch[switch_id] = weight(flows)  # Calculate and store the weight for each switch

        for flow in flows:
            if flow not in flow_to_switch_ids:
                flow_to_switch_ids[flow] = []
            flow_to_switch_ids[flow].append(switch_id)

    def update_priority_queue():
        priority_queue = []
        for switch_id, flows in s.items():
            intersection = set(flows).intersection(uncovered_flows)
            if intersection:
                ratio = weight_of_switch[switch_id] / len(intersection)
                heapq.heappush(priority_queue, (ratio, switch_id, flows))
        return priority_queue

    priority_queue = update_priority_queue()

    while uncovered_flows:
        if priority_queue and priority_queue[0][0] <= single_flow_ratio:
            current_ratio, switch_id, flows = heapq.heappop(priority_queue)
            newly_covered_flows = set(flows).intersection(uncovered_flows)
            if newly_covered_flows:
                picked_switch[switch_id] = newly_covered_flows
                uncovered_flows.difference_update(newly_covered_flows)
                priority_queue = update_priority_queue()
                print(f"Picked switch {switch_id} covering flows {newly_covered_flows} with ratio {current_ratio}.")
        else:
            # No efficient switch in priority queue, pick a random flow and cover it
            flow = random.choice(list(uncovered_flows))
            chosen_switch = random.choice(flow_to_switch_ids[flow])
            picked_switch[-1 * chosen_switch] = [flow]
            uncovered_flows.difference_update(s[chosen_switch])
            priority_queue = update_priority_queue()
            print(f"Randomly picked switch {chosen_switch} for single flow {flow} due to high ratio or no better option.")

    if uncovered_flows:
        print("Not all flows could be covered with the available switches.")
    else:
        print("All flows have been successfully covered.")

    return picked_switch


if "__main__" == __name__:
    f =[1,2,3,4,5,6,7]
    s = {
        1:[1,2,3],
        2:[1],
        3:[1,2,4,5],
        4:[2,5],
        5:[3,5,6],
        6:[3,4,6],
        7:[2,4,7]
    }
    print(set_cover_solve(f,s))