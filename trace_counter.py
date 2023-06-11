#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import argparse
import os
import time
import sys
from trace_reader import TraceReader
from multiprocessing import Pool, cpu_count

tr = TraceReader(hashable=True)
hash_file = None
default_hash_filename = 'hashfile'

# Mapper
def process_file(fn):
    l = []
    for state in tr.trace_reader(fn):
        l.append(str(hash(state)))
    hash_file.write('{}\n'.format(' '.join(l)))


# Tasks submmitter, reducer and printer
class ProgressManager:
    def __init__(self, hashfile, nproc, trace_dir=None, period=5, period_ntrace=0, logfile=None):
        if logfile is not None:
            self.logfile = open(logfile, 'w')
        else:
            self.logfile = sys.stdout
        self.hash_file_ro = open(hashfile, 'r')
        if trace_dir is not None:
            os.chdir(trace_dir)
        self.prev_time = 0
        self.nproc = nproc
        self.pool = Pool(processes=self.nproc)
        self.mapper = process_file
        self.submitted = 0
        self.processed = 0
        self.total_states = 0
        self.period = period
        self.period_ntrace = period_ntrace
        self.states = set()
        self.traces = set()

    def reduce(self):
        for line in self.hash_file_ro:
            self.traces.add(line)
            states = line.strip().split()
            self.states.update(map(int, states))
            self.processed += 1
            self.total_states += len(states)
            if self.period_ntrace > 0 and self.processed % self.period_ntrace == 0:
                self.print_progress(period=0)
            else:
                self.print_progress()
        self.print_progress(period=0)
    
    def print(self, *args, **kwargs):
        print(*args, **kwargs, file=self.logfile, flush=True)

    def print_progress(self, period=None):
        current_time = time.time() if period != 0 else self.prev_time
        if period is None:
            period = self.period
        if current_time - self.prev_time >= period:
            processed = self.processed if self.processed > 0 else self.submitted - len(self.pool._cache)
            submitted = self.submitted if self.submitted > 0 else processed
            p_ratio = 0 if submitted == 0 else processed / submitted
            if self.processed == 0:
                self.print('processed/total traces: {}/{} ({:.3g}%)'.format(
                            processed, self.submitted, p_ratio * 100))
            else:
                u_ratio = 0 if processed == 0 else len(self.traces) / processed
                s_ratio = 0 if self.total_states == 0 else len(self.states) / self.total_states
                self.print('unique/processed/total traces: {}/{}/{} ({:.3g}% {:.3g}%), distinct/total states: {}/{} ({:.3g}%)'.format(
                    len(self.traces), processed, submitted, u_ratio * 100, p_ratio * 100,
                    len(self.states), self.total_states, s_ratio * 100))
            self.prev_time = current_time
    
    def map(self, fn):
        self.pool.apply_async(self.mapper, args=(fn,))
        self.submitted += 1
    
    def is_trace_file(self, fn: str):
        return fn.startswith("trace_") or fn == 'MC.out'
    
    def iterate_dir(self):
        for i in os.listdir():
            if self.is_trace_file(i):
                self.map(i)
            self.print_progress()
        self.pool.close()
        self.print('Submit finished')
        while len(self.pool._cache) != 0:
            time.sleep(self.period)
            self.print_progress()
        self.pool.join()
        self.print('Map finished')
        self.reduce()
        self.print('Reduce finished')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simulation unique traces and distinct states counter')
    parser.add_argument(dest='trace_dir', action='store', help='Trace dir')
    parser.add_argument('-p', dest='nproc', action='store', type=int, default=cpu_count(), help='Number of processes')
    parser.add_argument('-n', dest='ntrace', action='store', type=int, default=0, help='Print progress every n traces')
    parser.add_argument('-l', dest='logfile', action='store', help='Log output to file')
    parser.add_argument('-f', dest='hashfile', action='store', help='Hash file')
    parser.add_argument('-r', dest='reduce', action='store_true', help='Reduce only')
    args = parser.parse_args()
    if args.hashfile is None:
        args.hashfile = default_hash_filename
    if not args.reduce:
        if os.path.exists(args.hashfile):
            os.remove(args.hashfile)
        hash_file = open(args.hashfile, 'a', buffering=1)
        process_man = ProgressManager(hashfile=args.hashfile, nproc=args.nproc, trace_dir=args.trace_dir,
                                      period_ntrace=args.ntrace, logfile=args.logfile)
        process_man.iterate_dir()
    else:
        process_man = ProgressManager(hashfile=args.hashfile, nproc=args.nproc, trace_dir=args.trace_dir,
                                      period_ntrace=args.ntrace, logfile=args.logfile)
        process_man.reduce()
