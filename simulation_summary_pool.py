#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import argparse
import os
import time
from copy import copy
from collections import defaultdict
from trace_reader import TraceReader
from multiprocessing import Pool, cpu_count

tr = TraceReader(save_action_name=True, hashable=True)

# Data
class SimulationSummaryData:
    @staticmethod
    def default_0():
        return 0
    def __init__(self) -> None:
        self.processed_files = set()
        self.total_states = 0
        self.total_actions = defaultdict(self.default_0)
        self.diameters = defaultdict(self.default_0)
        self.states = dict()
        self.distinct_actions = None


# Mapper
class SimulationSummaryMapper:
    def __init__(self, is_delete=False, finish_file='MC.out'):
        self.is_delete = is_delete
        self.finish_file = finish_file

    def process_file(self, fn):
        diameter = 0
        data = SimulationSummaryData()
        for state in tr.trace_reader(fn):
            diameter += 1
            action = state['_action']
            state['_action'] = 0
            state_hash = hash(state)
            if state_hash not in data.states:
                data.states[state_hash] = action
            else:
                pass  # we did not check the equality if hashes are the same
            data.total_states += 1
            data.total_actions[action] += 1
        if diameter:
            data.diameters[diameter] += 1
        data.processed_files.add(fn)
        if self.is_delete and fn != self.finish_file:
            os.remove(fn)
        return data


# Tasks submmitter, reducer and printer
class ProgressManager:
    def __init__(self, nproc, is_delete=False, trace_dir=None, finish_file='MC.out', period=5):
        if trace_dir is not None:
            os.chdir(trace_dir)
        self.prev_time = 0
        self.nproc = nproc
        self.pool = Pool(processes=self.nproc)
        self.mapper = SimulationSummaryMapper(is_delete=is_delete, finish_file=finish_file)
        self.data = SimulationSummaryData()
        self.submitted = 0
        self.finish_file = finish_file
        self.period = period
        self.results = []

    def reduce(self, data: SimulationSummaryData, reduce_actions=False):
        if data is not None:
            self.data.processed_files.update(data.processed_files)
            self.data.total_states += data.total_states
            self.data.states.update(data.states)
            for j in data.diameters:
                self.data.diameters[j] += data.diameters[j]
            for j in data.total_actions:
                self.data.total_actions[j] += data.total_actions[j]
        if reduce_actions:
            self.data.distinct_actions = defaultdict(lambda: 0)
            for value in self.data.states.values():
                self.data.distinct_actions[value] += 1
                
    def reduce_result(self, reduce_actions=False):
        for r in self.results:
            if r.ready():
                self.reduce(r.get(), reduce_actions=reduce_actions)
                self.results.remove(r)
            self.print_progress()

    def print_progress(self, period=None):
        current_time = time.time()
        if period is None:
            period = self.period
        if current_time - self.prev_time >= period:
            p_ratio = 0 if self.submitted == 0 else len(self.data.processed_files) / self.submitted
            s_ratio = 0 if self.data.total_states == 0 else len(self.data.states) / self.data.total_states
            print('Processed: {}/{} ({:.1f}%), distinct/total states: {}/{} ({:.1f}%)'.format(
                len(self.data.processed_files), self.submitted, p_ratio * 100,
                len(self.data.states), self.data.total_states, s_ratio * 100))
            if period == 0:
                print('Diameters:')
                for key, value in sorted(self.data.diameters.items(), key=lambda x: x[0]):
                    print("  {} : {}".format(key, value))
                print('Actions:')
                for k in self.data.total_actions:
                    print(' ', k, ':', self.data.distinct_actions[k], '/', self.data.total_actions[k])
            self.prev_time = current_time
    
    def map(self, fn):
        self.results.append(self.pool.apply_async(self.mapper.process_file, args=(fn,)))
        self.submitted += 1
    
    def is_trace_file(self, fn):
        return fn.startswith("trace_") or fn == self.finish_file
    
    def iterate_dir(self):
        for i in os.listdir():
            if self.is_trace_file(i):
                self.map(i)
            # if self.submitted % 1000 == 0:
            #     self.reduce_result()
            self.print_progress()
        self.pool.close()
        print('Map finished')
        while True:
            self.reduce_result()
            if len(self.results) == 0:
                self.reduce(data=None, reduce_actions=True)
                break
            self.print_progress()
        print('Reduce finished')
        self.pool.join()
        self.print_progress(period=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get simulation mode summary')
    parser.add_argument(dest='trace_dir', action='store', help='Trace dir')
    parser.add_argument('-r', dest='remove', action='store_true', help='Remove processed files')
    parser.add_argument('-p', dest='nproc', action='store', type=int, default=cpu_count(), help='Number of processes')
    arg_parser = parser.parse_args()
    process_man = ProgressManager(nproc=arg_parser.nproc, is_delete=arg_parser.remove, trace_dir=arg_parser.trace_dir)
    process_man.iterate_dir()
