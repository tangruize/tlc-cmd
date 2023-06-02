#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import argparse
import signal
import os
import time
import inotify.adapters
from collections import defaultdict
from trace_reader import TraceReader

break_inotify = False

def sigint_handler(signum, frame):
    print('Caught SIGINT, Ctrl+C again to exit')
    break_inotify = True
    signal.signal(signal.SIGINT, signal.SIG_DFL)

tr = TraceReader(True)
finish_file = "MC.out"
processed_files_set = set()
total_states = 0
total_actions = defaultdict(lambda: 0)
distinct_states = 0
distinct_actions = defaultdict(lambda: 0)
diameters = defaultdict(lambda: 0)
states = set()

def process_file(fn, delete=False):
    global processed_files_set, total_states, distinct_states, total_actions, distinct_actions, diameters
    diameter = 0
    for state in tr.trace_reader(fn):
        diameter += 1
        action = state['_action']
        state['_action'] = 0
        state_hash = hash(str(state))
        if state_hash not in states:
            states.add(state_hash)
            distinct_states += 1
            distinct_actions[action] += 1
        total_states += 1
        total_actions[action] += 1
    if diameter:
        diameters[diameter] += 1
    processed_files_set.add(fn)
    if delete and fn != finish_file:
        os.remove(fn)


prev_time = 0
def print_progress(period=5):
    global prev_time
    current_time = time.time()
    if current_time - prev_time >= period:
        print()
        print('Processed: {}, total states: {}, distinct states: {}'.format(len(processed_files_set), total_states, len(states)))
        print('Diameters:')
        for k in diameters:
            print(' ', k, ':', diameters[k])
        print('Actions:')
        for k in distinct_actions:
            print(' ', k, ':', distinct_actions[k], '/', total_actions[k])
        prev_time = current_time

def is_trace_file(fn):
    return fn.startswith("trace_") or fn == finish_file

def iterate_dir(trace_dir, use_inotify=True, delete=False):
    os.chdir(trace_dir)
    if use_inotify:
        i = inotify.adapters.Inotify()
        i.add_watch('.')
        while True:
            event = None

            for event in i.event_gen(yield_nones=False, timeout_s=1):
                (_, type_names, _, filename) = event
                event = None
                if type_names == ['IN_CLOSE_WRITE']:
                    if not is_trace_file(filename) and filename != finish_file:
                        continue
                    process_file(filename, delete=delete)
                    print_progress()
                    if filename == finish_file or break_inotify:
                        event = ""
                        break
            print_progress()
            if event is not None:
                break
    file_list = set([i for i in os.listdir() if is_trace_file(i) or i == finish_file]) - processed_files_set
    for i in file_list:
        process_file(i, delete=delete)
        print_progress()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get simulation mode summary')
    parser.add_argument(dest='trace_dir', action='store', help='Trace dir')
    parser.add_argument('-r', dest='remove', action='store_true', help='Remove processed files')
    parser.add_argument('-i', dest='iterate', action='store_true', help='Iterate dir instead of using inotify')
    arg_parser = parser.parse_args()
    if not arg_parser.iterate:
        signal.signal(signal.SIGINT, sigint_handler)
    iterate_dir(arg_parser.trace_dir, not arg_parser.iterate, arg_parser.remove)
