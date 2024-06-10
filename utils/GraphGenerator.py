from networkx import Graph
from itertools import product
from random import random, choice
from math import sqrt, ceil, exp
def erdos_renyi_generator(n: int, p: float) -> Graph:
    g = Graph()
    g.add_nodes_from(range(1, n+1))
    for s1, s2 in product(range(1, n + 1), range(1, n + 1)):
        if s1 >= s2:
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

def waxman_generator_1(n: int, alpha: float, beta: float) -> Graph:
    g = Graph()
    g.add_nodes_from(range(1, n + 1))
    side_length = ceil(sqrt(n))
    all_possible_coords = list(product(range(1, side_length+1), range(1, side_length+1)))
    coords: dict[int, (int, int)] = {}
    for i in range(1, n+1):
        x, y = choice(all_possible_coords)
        coords[i] = (x, y)
    dist: dict[(int, int), float] = {}
    for i, j in product(coords.keys(), coords.keys()):
        i_coords = coords[i]
        j_coords = coords[j]
        dist_i_j = sqrt((i_coords[0] - j_coords[0])**2 + (i_coords[1] - j_coords[1])**2)
        dist[(i, j)] = dist_i_j
    L = max(dist.values())
    for i, j in product(range(1, n + 1), range(1, n + 1)):
        if i >= j:
            continue
        p = beta * exp(-dist[(i, j)] / (L * alpha))
        x = random()
        if x <= p:
            g.add_edge(i, j)
    return g

def waxman_generator_2(n: int, alpha: float, beta: float, L: float) -> Graph:
    g = Graph()
    g.add_nodes_from(range(1, n + 1))
    dist: dict[(int, int), float] = {}
    for i, j in product(range(1, n+1), range(1, n+1)):
        if i == j:
            dist[(i, j)] = 0
        else:
            dist[(i, j)] = random() * L
    for i, j in product(range(1, n + 1), range(1, n + 1)):
        if i >= j:
            continue
        p = beta * exp(-dist[(i, j)] / (L * alpha))
        x = random()
        if x <= p:
            g.add_edge(i, j)
    return g