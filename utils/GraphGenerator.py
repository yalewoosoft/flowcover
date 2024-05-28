from networkx import Graph
from itertools import product
from random import random
def erdos_renyi_generator(n: int, p: float) -> Graph:
    g = Graph()
    g.add_nodes_from(range(1, n+1))
    for s1, s2 in product(range(1, n + 1), range(1, n + 1)):
        if s1 == s2:
            continue
        x = random()
        if x <= p:
            g.add_edge(s1, s2)
    return g

def linear_generator(n: int) -> Graph:
    g = Graph()
    g.add_nodes_from(range(1, n+1))
    for i in range(1, n):
        g.add_edge(i, i+1)
    return g