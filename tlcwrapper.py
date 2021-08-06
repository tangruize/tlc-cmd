#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import sys
import re
import os
import subprocess
import requests

from collections import OrderedDict
from configparser import ConfigParser
from itertools import chain, zip_longest, product
from shutil import copy2
from datetime import datetime
from io import StringIO

debug = True


class BatchConfig:
    """Yield TLCConfigFile cfg files"""

    def __init__(self, cfg):
        self.cfg = cfg
        self.dup_option_info = OrderedDict()
        self.cfg_content = []
        self._parse_cfg()

    def _parse_cfg(self):
        pre_opt_kv = ['', '']
        pre_no = -1

        def rm_non_dup_option():
            if pre_no in self.dup_option_info and len(self.dup_option_info[pre_no]) <= 1:
                self.dup_option_info.pop(pre_no)

        with open(self.cfg, 'r') as f:
            for no, line in enumerate(f):
                self.cfg_content.append(line)
                line = line.rstrip()
                if len(line) == 0 or line[0] in '#;[ ':
                    continue
                opt_kv = line.split(':', 1)
                if len(opt_kv) != 2:
                    continue
                if opt_kv[0] == pre_opt_kv[0]:
                    self.dup_option_info[pre_no].append(line)
                    self.cfg_content[-1] = ''
                else:
                    rm_non_dup_option()
                    self.dup_option_info[no] = [line]
                    pre_no = no
                pre_opt_kv = opt_kv
            rm_non_dup_option()

    def get(self):
        """yield cfg StringIO"""
        keys = list(self.dup_option_info.keys())
        values = list(self.dup_option_info.values())
        for comb in product(*values):
            for i, no in enumerate(keys):
                self.cfg_content[no] = comb[i] + '\n'
            yield comb, StringIO(''.join(self.cfg_content))


class TLCConfigFile:
    """generate TLC config file: MC.cfg and MC.tla"""
    model_sym_pat = re.compile(r'\[model value]<symmetrical>{(.*)}')
    model_pat = re.compile(r'\[model value]{(.*)}')
    tag = '\\* Generated by ' + os.path.basename(__file__)

    def __init__(self, cfg, output_cfg_fn, output_tla_fn):
        self.cfg = cfg
        self.output_cfg_fn = output_cfg_fn
        self.output_tla_fn = output_tla_fn
        self.top_module = re.sub(r'.tla$', '', os.path.basename(cfg.get('options', 'target')))
        self.output_cfg = []
        self.output_tla = []
        self.parse()

    def _add_behavior(self, specifier, prefix, value):
        behavior_name = '{}'.format(prefix)
        behavior_value = '{} ==\n{}'.format(behavior_name, value)
        self.output_cfg.append('{}\n{}'.format(specifier, behavior_name))
        self.output_tla.append(behavior_value)

    def _parse_behavior(self):
        """parse behavior section"""
        if 'behavior' in self.cfg:
            behavior = self.cfg['behavior']
            init_predicate = behavior.get('init')
            next_state = behavior.get('next')
            temporal_formula = behavior.get('temporal formula')
            if (init_predicate or next_state) and (not init_predicate or not next_state or temporal_formula):
                raise ValueError('[behavior] choose one or none: "init/next" **OR** "temporal formula"')
            if temporal_formula:
                self._add_behavior('SPECIFICATION', 'spec', temporal_formula)
            else:
                self._add_behavior('INIT', 'init', init_predicate)
                self._add_behavior('NEXT', 'next', next_state)

    def _add_specifications(self, keyword, specifier, prefix):
        """invariants and properties share the same parser"""
        if keyword in self.cfg:
            spec = self.cfg[keyword]
            spec_names = '\n'.join('{}_{}'.format(prefix, i) for i in spec)
            if spec_names != '':
                self.output_cfg.append('{}\n{}'.format(specifier, spec_names))
                spec_values = '\n'.join('{}_{} ==\n{}'.format(prefix, i, spec[i]) for i in spec)
                self.output_tla.append(spec_values)

    def _parse_invariants(self):
        """parse invariants section"""
        self._add_specifications('invariants', 'INVARIANT', 'inv')

    def _parse_properties(self):
        """parse properties section"""
        self._add_specifications('properties', 'PROPERTY', 'prop')

    def _parse_state_constraint(self):
        """parse state constraint section"""
        self._add_specifications('state constraint', 'CONSTRAINT', 'constr')

    def _parse_action_constraint(self):
        """parse action constraint section"""
        self._add_specifications('action constraint', 'ACTION_CONSTRAINT', 'action_constr')

    def _parse_constants(self, keyword='constants', prefix='const'):
        """parse constants section"""
        if keyword in self.cfg:
            symmetrical = []
            constants = self.cfg[keyword]
            for name in constants:
                value = constants[name]
                is_model_value = False
                is_symmetrical = False
                if self.model_sym_pat.match(value):
                    is_model_value = True
                    value = self.model_sym_pat.match(value).groups()[0].replace(' ', '').split(',')
                    if len(value) <= 1:
                        print('Warning: "{}: {}": <symmetrical> ignored'.format(name, constants[name]), file=sys.stderr)
                    else:
                        is_symmetrical = True
                elif self.model_pat.match(value):
                    is_model_value = True
                    value = self.model_pat.match(value).groups()[0].replace(' ', '').split(',')
                elif value == '[model value]':
                    is_model_value = True
                    value = name
                if is_model_value:
                    if isinstance(value, list):  # set of model values
                        model_val = '\n'.join('{} = {}'.format(i, i) for i in value)
                        cfg_str = 'CONSTANTS\n{}\nCONSTANT\n{} <- const_{}'.format(model_val, name, name)
                        model_val = ', '.join(i for i in value)
                        tla_str = 'CONSTANTS\n{}\nconst_{} ==\n{{{}}}'.format(model_val, name, model_val)
                        if is_symmetrical:  # symmetry set
                            # cfg_str = '{}\nSYMMETRY symm_{}'.format(cfg_str, name)
                            # tla_str = '{}\nsymm_{} ==\nPermutations(const_{})'.format(tla_str, name, name)
                            symmetrical.append('Permutations(const_{})'.format(name))
                    else:  # model value
                        cfg_str = 'CONSTANT {} = {}'.format(name, value)
                        tla_str = None
                else:  # ordinary assignment
                    cfg_str = 'CONSTANT\n{} <- {}_{}'.format(name, prefix, name)
                    tla_str = '{}_{} == \n{}'.format(prefix, name, value)
                self.output_cfg.append(cfg_str)
                self.output_tla.append(tla_str)
            if symmetrical:
                self.output_cfg.append('SYMMETRY symm_{}'.format(len(symmetrical)))
                self.output_tla.append('symm_{} ==\n{}'.format(len(symmetrical), ' \\union '.join(symmetrical)))

    def _parse_override(self):
        """parse override section"""
        self._parse_constants(keyword='override', prefix='over')

    def _parse_const_expr(self):
        """parse const expr section"""
        if 'const expr' in self.cfg:
            const_expr = self.cfg.get('const expr', 'expr', fallback=None)
            if const_expr:
                self.output_cfg.append(None)
                val = 'const_expr'
                self.output_tla.append('{} ==\n{}\nASSUME PrintT(<<"$!@$!@$!@$!@$!",{}>>)'.format(val, const_expr, val))

    def _parse_additional_definitions(self):
        """parse additional definitions section"""
        if 'additional definitions' in self.cfg:
            self.output_cfg.append(None)
            spec = self.cfg['additional definitions']
            spec_values = '\n'.join(spec[i] for i in spec)
            self.output_tla.append(spec_values)

    def parse(self):
        self.output_cfg = []
        self.output_tla = []
        self._parse_behavior()
        self._parse_invariants()
        self._parse_properties()
        self._parse_constants()
        self._parse_override()
        self._parse_const_expr()
        self._parse_state_constraint()
        self._parse_action_constraint()
        self._parse_additional_definitions()

    def write(self, output_cfg_fn=None, output_tla_fn=None):
        """write parsed buf to file"""
        if output_cfg_fn is None:
            output_cfg_fn = self.output_cfg_fn
        if output_tla_fn is None:
            output_tla_fn = self.output_tla_fn
        with open(output_cfg_fn, 'w') as cfg_f:
            cfg_f.write('{} on {}\n'.format(self.tag, datetime.now()))
            cfg_f.write('\n\n'.join(filter(None, self.output_cfg)))
            cfg_f.write('\n')
        with open(output_tla_fn, 'w') as tla_f:
            module = '---- MODULE {} ----\n'.format(output_tla_fn.rstrip('.tla'))
            tla_f.write(module)
            tla_f.write('EXTENDS {}, TLC\n'.format(self.top_module))
            tla_f.write('\n----\n\n'.join(filter(None, self.output_tla)))
            tla_f.write('\n{}\n'.format('=' * len(module)))
            tla_f.write('{} on {}\n'.format(self.tag, datetime.now()))


class TLCWrapper:
    """TLC cmdline options"""
    _script_dir = os.path.dirname(os.path.realpath(__file__))
    tla2tools_jar = os.path.join(_script_dir, 'tla2tools.jar')
    tla2tools_url = 'https://github.com/tlaplus/tlaplus/releases/download/v1.8.0/tla2tools.jar'
    tla2tools_class = 'tlc2.TLC'

    default_config_file = 'config.ini'  # default input file

    # default output files
    default_mc_cfg = 'MC.cfg'
    default_mc_tla = 'MC.tla'
    default_mc_log = 'MC.out'
    default_mc_user = 'MC_user.txt'
    default_mc_states = 'MC_states'
    default_mc_coverage = 'MC_coverage.txt'

    def __init__(self, config_file=None, log_file=True, gen_cfg_fn=None, gen_tla_fn=None):
        """create model dir, chdir, copy files and generate tlc configfile"""
        self._tlc_cmd = ['java', '-XX:+UseParallelGC', '-cp', self.tla2tools_jar, self.tla2tools_class]
        self.simulation_mode = False
        config_file = config_file if config_file is not None else self.default_config_file
        self.cfg = ConfigParser()
        self.cfg.optionxform = str  # case sensitive
        if hasattr(config_file, 'read'):
            self.cfg.read_file(config_file)
        else:
            self.cfg.read(config_file)
        self.orig_cwd = os.getcwd()

        if isinstance(log_file, str):  # if log_file specified, open it before change cwd
            self.log_file = open(log_file, 'w')

        target = self.cfg.get('options', 'target')
        model_name = self.cfg.get('options', 'model name') + datetime.now().strftime("_%Y-%m-%d_%H-%M-%S")
        os.chdir(os.path.dirname(os.path.realpath(target)))
        os.makedirs(model_name, exist_ok=True)
        for file in os.listdir('.'):
            if file.endswith('.tla'):
                copy2(file, model_name)
        os.chdir(model_name)

        if log_file:
            if not isinstance(log_file, str):
                self.log_file = open(self.default_mc_log, 'w')
        else:
            self.log_file = None

        self.gen_cfg_fn = gen_cfg_fn if gen_cfg_fn is not None else self.default_mc_cfg
        self.gen_tla_fn = gen_tla_fn if gen_tla_fn is not None else self.default_mc_tla
        TLCConfigFile(self.cfg, self.gen_cfg_fn, self.gen_tla_fn).write()

        self.options = []
        self._parse_options()

        self.result = None
        self.log_lines = None
        self.init_result()

    def __del__(self):
        if hasattr(self.log_file, 'close'):
            self.log_file.close()
        os.chdir(self.orig_cwd)

    def _parse_options(self):
        """parse options section"""
        self.options = [self.gen_tla_fn, '-config', self.gen_cfg_fn, '-userFile', self.default_mc_user]
        opt = self.cfg['options']

        mem = opt.getint('system memory')
        if mem:
            direct_mem = '-XX:MaxDirectMemorySize=' + str(mem // 3 * 2) + 'm'
            xmx = '-Xmx' + str(mem // 3) + 'm'
            self._tlc_cmd.insert(1, '-Dtlc2.tool.fp.FPSet.impl=tlc2.tool.fp.OffHeapDiskFPSet')
            self._tlc_cmd.insert(1, xmx)
            self._tlc_cmd.insert(1, direct_mem)

        dump_states = opt.get('dump states')
        if dump_states:
            if dump_states.lower() == 'dot':
                self.options += ['-dump', 'dot', self.default_mc_states]
            elif dump_states.lower() != 'false':
                self.options += ['-dump', self.default_mc_states]

        options_list = [opt.get('worker num'), opt.getint('checkpoint minute'), opt.getint('dfs depth'),
                        not opt.getboolean('check deadlock'), opt.getint('coverage minute'),
                        opt.getint('simulation depth'), opt.getint('simulation seed')]
        options = ['-workers', '-checkpoint', '-dfid', '-deadlock', '-coverage', '-depth', '-aril']
        for i, j in zip(options, options_list):
            if j:
                self.options.append(i)
                if not isinstance(j, bool):
                    self.options.append(str(j))

        simulation_options = []
        simulation_traces_num = opt.getint('simulation traces')
        if simulation_traces_num:
            simulation_options.append('num=' + str(simulation_traces_num))
        simulation_dump_traces = opt.getboolean('simulation dump traces')
        if simulation_dump_traces:
            simulation_options.append('file=' + os.path.realpath('.') + '/trace')
        simulation_options_str = ','.join(simulation_options)

        if '-depth' in self.options or '-aril' in self.options or simulation_options_str:
            self.options.append('-simulate')
            if simulation_options_str:
                self.options.append(simulation_options_str)
            self.simulation_mode = True

        if opt.get('other TLC options') is not None:
            for field in opt.get('other TLC options').split('\n'):
                self.options.append(field)

        # I forget what 'simulation actions' is ...
        simulation_actions = opt.get('simulation actions')
        if simulation_actions is not None and simulation_actions.lower() == 'true':
            self._tlc_cmd.insert(1, "-Dtlc2.tool.Simulator.actionStats=true")

    def get_cmd_str(self):
        """get tlc command line"""
        return ' '.join(i for i in chain(self._tlc_cmd, self.options))

    def get_cmd_options(self):
        """get tlc command line list"""
        return self._tlc_cmd + self.options

    def raw_run(self):
        """directly call tlc program without analysing the output"""
        subprocess.call(self._tlc_cmd + self.options)

    def init_result(self):
        result_key = ['start time', 'finish time', 'time consuming',
                      'diameter', 'total states', 'distinct states', 'queued states',
                      'info', 'errors', 'tlc bug', 'warnings', 'error trace', 'other msg',
                      'coverage', 'exit state']
        result_key_is_list = ['info', 'errors', 'tlc bug', 'warnings', 'error trace', 'other msg', 'coverage']
        self.result = OrderedDict(zip_longest(result_key, tuple()))  # fill None
        for key in result_key_is_list:
            self.result[key] = []
        self.log_lines = []

    def download_tla2tools(self):
        if not os.path.isfile(self.tla2tools_jar):
            if debug:
                print('Debug: downloading tla2tools.jar', file=sys.stderr)
            r = requests.get(self.tla2tools_url, allow_redirects=True)
            with open(self.tla2tools_jar, 'wb') as f:
                f.write(r.content)

    def run(self):
        """call tlc and analyse output"""
        self.init_result()  # clear result

        title_printed = False
        title_list = ['Time', 'Diameter', 'States Found', 'Distinct States', 'Queue Size']
        if self.simulation_mode:
            title_list[1] = 'Traces'

        def print_state(time):
            nonlocal title_printed
            value_list = [str(time), self.result['diameter'], self.result['total states'],
                          self.result['distinct states'], self.result['queued states']]
            if all(i is not None for i in value_list):
                if not title_printed:
                    title_printed = True
                    print(('{:<16}' * 5).format(*title_list))
                print(('{:<16}' * 5).format(*value_list))

        progress_pat = re.compile(r'Progress\(([\d,]+)\) at (.*): ([\d,]+) s.*, (-?[\d,]+) d.*, (-?[\d,]+) s')
        # finish_pat = re.compile(r'(\d+) states generated, (\d+) distinct states found, (\d+) states left on queue')

        tmp_lines = []
        message_code = -1  # see https://github.com/jameshfisher/tlaplus/blob/master/tlatools/src/tlc2/output/EC.java
        message_type = -1  # see https://github.com/jameshfisher/tlaplus/blob/master/tlatools/src/tlc2/output/MP.java
        message_type_key = ('info', 'errors', 'tlc bug', 'warnings', 'error trace', 'other msg')

        def process_message():
            if len(tmp_lines) == 0:
                return
            line = '\n'.join(tmp_lines)
            self.result[message_type_key[message_type]].append((datetime.now(), line))
            if message_code == 2185:  # Starting...
                self.result['start time'] = datetime.strptime(line, 'Starting... (%Y-%m-%d %H:%M:%S)')
            elif message_code == 2186:  # Finished in...
                self.result['finish time'] = datetime.strptime(line.split('at')[1], ' (%Y-%m-%d %H:%M:%S)')
                self.result['time consuming'] = self.result['finish time'] - self.result['start time']
                # print_state(self.result['time consuming'])
            elif message_code == 2200 or message_code == 2209:  # Progress...
                groups = progress_pat.match(line).groups()
                self.result['diameter'] = int(groups[0].replace(',', ''))
                self.result['total states'] = int(groups[2].replace(',', ''))
                self.result['distinct states'] = int(groups[3].replace(',', ''))
                self.result['queued states'] = int(groups[4].replace(',', ''))
                current_time = datetime.strptime(groups[1], '%Y-%m-%d %H:%M:%S')
                self.result['time consuming'] = current_time - self.result['start time']
                print_state(self.result['time consuming'])
            elif message_code == 2190:  # Finished computing initial states ...
                states = int(line.split(':')[1].split(' ')[1])
                self.result['diameter'] = 0
                self.result['total states'] = states
                self.result['distinct states'] = states
                self.result['queued states'] = states
                print_state(str(datetime.now() - self.result['start time']).split('.')[0])
            # elif message_code == 2199:  # ... states generated, ... distinct states found, 0 states left on queue.
            #     groups = finish_pat.match(line).groups()
            #     self.result['total states'] = int(groups[0])
            #     self.result['distinct states'] = int(groups[1])
            #     self.result['queued states'] = int(groups[2])
            elif message_code == 2194:  # The depth of the complete state graph search is ...
                diameter = int(line.split(' ')[9].rstrip('.'))
                self.result['diameter'] = diameter
            elif message_code == 2201:  # The coverage statistics
                self.result['coverage'] = [line]
            elif message_code == 2221:  # coverage msg detail
                self.result['coverage'].append(line)
            elif message_code == 2202:  # End of statistics
                self.save_coverage()

        options = self._tlc_cmd + self.options + ['-tool']  # tool mode
        if debug:
            print('Debug:', options, file=sys.stderr)
        self.download_tla2tools()
        process = subprocess.Popen(options, stdout=subprocess.PIPE, universal_newlines=True)

        for msg_line in iter(process.stdout.readline, ''):
            if msg_line == '':  # sentinel
                process_message()
                break
            self.log_lines.append(msg_line)
            if self.log_file:
                self.log_file.write(msg_line)
                self.log_file.flush()
            msg_line = msg_line.rstrip()
            if message_code == -1 and msg_line.startswith('@!@!@STARTMSG'):
                process_message()
                message_code, message_type = tuple(int(i) for i in msg_line.split(' ')[1].split(':'))
            elif message_code != -1 and msg_line.startswith('@!@!@ENDMSG ' + str(message_code)):
                process_message()
                message_code, message_type = -1, -1
                tmp_lines = []
            else:
                tmp_lines.append(msg_line)

        exit_state = process.poll()
        self.result['exit state'] = 0 if exit_state is None else exit_state
        return self.result

    def get_log(self):
        return self.log_lines

    def save_log(self, filename=None):
        """save tlc output to file"""
        if filename is None:
            filename = self.default_mc_log
        with open(filename, 'w') as f:
            f.writelines(self.log_lines)

    def save_coverage(self, filename=None):
        """save coverage msg to file if it has coverage msgs"""
        if filename is None:
            filename = self.default_mc_coverage
        if len(self.result['coverage']) != 0:
            with open(filename, 'w') as f:
                f.write('\n'.join(self.result['coverage']))
                f.write('\n')


def main(config_file, log_file=True):
    for options, config_stringio in BatchConfig(config_file).get():
        if options:
            print('#' * 16)
            print('Options:')
            for i in options:
                print(' ', i)
            print('-' * 16)
        tlc = TLCWrapper(config_stringio, log_file=log_file)
        result = tlc.run()
        for _, msg in result['warnings']:
            print('Warning: ' + msg, file=sys.stderr)
        for _, msg in result['errors']:
            print('Error: ' + msg, file=sys.stderr)
        for _, msg in result['error trace']:
            print(msg, file=sys.stderr)
        print('errors: {}, warnings: {}, exit_state: {}'.format(len(result['errors']), len(result['warnings']),
                                                                result['exit state']), file=sys.stderr)
        del tlc


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('Usage: python3 {} config.ini'.format(sys.argv[0]), file=sys.stderr)
        exit(1)
    if len(sys.argv) > 1:
        main(sys.argv[1])
