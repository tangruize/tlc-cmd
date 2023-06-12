#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import networkx as nx
import argparse
import time
import os
from multiprocessing import Pool, cpu_count
from trace_reader import get_dot_label_string


parser = argparse.ArgumentParser(description='Generate all simple paths of a dot file')
parser.add_argument(dest='dot_file', action='store', help='Dot file')
parser.add_argument('-p', dest='nproc', action='store', type=int, default=cpu_count(), help='Number of processes')
parser.add_argument('-s', dest='save_dir', action='store', help='Save all generated traces')
args = parser.parse_args()


def read_dot(dot_file, save_states=False):
    g = nx.DiGraph()
    s = dict()
    with open(dot_file) as f:
        for line in f:
            if ' -> ' in line:
                a, b = map(int, line.rstrip(';\n').split(' -> '))
                g.add_edge(a, b)
            elif save_states and ' [label="' in line:
                state_hash, label = get_dot_label_string(line)
                s[state_hash] = label
    return g, s


print('Reading dot file ... ', end='')
G, S = read_dot(args.dot_file, save_states=args.save_dir is not None)
roots = [v for v, d in G.in_degree() if d == 0]
leaves = [v for v, d in G.out_degree() if d == 0]
print('done. root: {}, leaves: {}, vertices: {}'.format(len(roots), len(leaves), len(G.nodes())))
all_paths = 0
leaves_processed = 0
leaves_submitted = 0
if args.save_dir:
    save_dir = os.path.join(args.save_dir, 'trace_')
    os.makedirs(args.save_dir, exist_ok=True)
else:
    save_dir = None

prev_time = time.time()
def print_progress(period=5):
    global prev_time
    curr_time = time.time()
    if curr_time - prev_time >= period:
        ratio = 0 if len(leaves) == 0 else leaves_processed / len(leaves)
        print('Processed/submitted/all: {}/{}/{} ({:.3g}%), all paths: {}'.format(
            leaves_processed, leaves_submitted, len(leaves) * len(roots), ratio * 100, all_paths))
        prev_time = curr_time


def process_path(a, b, save_fn_prefix=None):
    if save_fn_prefix is None:
        return sum(1 for _ in nx.all_simple_paths(G, a, b))
    else:
        path_cnt = 0
        for path in nx.all_simple_paths(G, a, b):
            fn = save_fn_prefix + str(path_cnt)
            lines = []
            lines.append('-' * 16 + ' MODULE {} '.format(os.path.basename(fn)) + '-' * 16 + '\n')
            for i, h in enumerate(path):
                lines.append('STATE {} ==\n'.format(i + 1))
                lines.append(S[h])
                lines.append('\n\n')
            lines.append('=' * 49 + '\n')
            path_cnt += 1
            with open(fn, 'w') as f:
                f.writelines(lines)
        return path_cnt


pool = Pool(processes=args.nproc)
results = []
leaf_cnt = 0
for root in roots:
    for leaf in leaves:
        save_prefix = None if save_dir is None else save_dir + str(leaf_cnt) + '_'
        results.append(pool.apply_async(process_path, args=(root, leaf, save_prefix)))
        leaves_submitted += 1
        leaf_cnt += 1
        print_progress()
pool.close()

print('Submit finished')

def reduce_results():
    global results, all_paths, leaves_processed
    for i in range(len(results)-1, -1, -1):
        r = results[i]
        if r.ready():
            all_paths += r.get()
            leaves_processed += 1
            del results[i]
        print_progress()

while True:
    reduce_results()
    if len(results) == 0:
        break

pool.join()
print('Map/reduce finished')
print_progress(period=0)
