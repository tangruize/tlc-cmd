#!/usr/bin/python3

# usage: python3 trace_reader.py -h

class TraceReader:
    LIST_IS_SEQ = "seq"
    LIST_IS_SET = "set"

    def __init__(self, save_action_name=False):
        self._matching = {'{': ('}', self._braces), '<': ('$', self._chevrons),
            '[': (']', self._brackets), '(': (')', self._parentheses)}

        self._string_dict = {"TRUE": True, "FALSE": False}
        self._user_dict = dict()
        self._kv_outside_handler = lambda k, v: (k, v)
        self._kv_inside_handler = lambda k, v: (k, v)
        self._list_handler = lambda s, k: s
        self.save_action_name = save_action_name


    # find '}$])' for '{<[('
    def _find_next_match(self, string):
        level = 0
        char = string[0]
        match_char = self._matching[char][0]
        for i, c in enumerate(string):
            if c == char:
                level += 1
            elif c == match_char:
                level -= 1
                if level == 0:
                    return i
        assert False


    # return a list
    def _lists(self, string, kind):
        l = list()
        if not string:
            return self._list_handler(l, kind)
        processed, pos, length = 0, 0, len(string)
        while pos < length:
            if string[pos] in self._matching or string[pos] == ',':
                if string[pos] != ',':
                    pos = pos + self._find_next_match(string[pos:]) + 1
                l.append(self._variable_converter(string[processed:pos]))
                processed = pos + 2
                pos += 1
            pos += 1
        if pos != processed:
            l.append(self._variable_converter(string[processed:pos]))
        return self._list_handler(l, kind)


    # < string $
    def _chevrons(self, string):
        return self._lists(string, kind=self.LIST_IS_SEQ)


    # { string } (we treat set as list)
    def _braces(self, string):
        return self._lists(string, kind=self.LIST_IS_SET)


    # return a dict
    def _dict_common(self, string, arrow, sep, value_seq_len):
        d = dict()
        processed, pos, length = 0, 0, len(string)
        key, value = '', ''
        while True:
            if string[pos] == arrow[0]:
                key = string[processed:pos - 1]
                pos += len(arrow)
                processed = pos + 1
            if string[pos] == sep[0]:
                value = string[processed:pos - value_seq_len]
                pos += len(sep)
                processed = pos + 1
                key, value = self._kv_inside_handler(
                    key, self._variable_converter(value))
                d[key] = value
            pos += 1
            if pos >= length:
                break
            if string[pos] in self._matching:
                pos = pos + self._find_next_match(string[pos:])
        value = string[processed:]
        key, value = self._kv_inside_handler(
            key, self._variable_converter(value))
        d[key] = value
        return d


    # [ string ]
    def _brackets(self, string):
        return self._dict_common(string, '|->', ',', 0)


    # ( string )
    def _parentheses(self, string):
        return self._dict_common(string, ':>', '@@', 1)


    # convert string to python variable
    def _variable_converter(self, string):
        if string[0] in self._matching:
            return self._matching[string[0]][1](string[1:-1].strip())
        if string in self._user_dict:
            return self._user_dict[string]
        if string in self._string_dict:
            return self._string_dict[string]
        if string[0] == '"':
            return string[1:-1]
        try:
            return int(string)
        except ValueError:
            return string


    # callback handlers
    def set_user_dict(self, user_dict):
        self._user_dict = user_dict


    def set_kv_handler(self, kv_handler, inside=False):
        if inside:
            self._kv_inside_handler = kv_handler
        else:
            self._kv_outside_handler = kv_handler


    def set_list_handler(self, list_handler):
        self._list_handler = list_handler


    # convert MC.out to trace file
    @staticmethod
    def get_converted_string(file):
        if not hasattr(file, 'read'):
            f = open(file)
        else:
            f = file

        n_state = 0
        start_msg = 'The behavior up to this point is:'
        end_msg = ['Progress', 'The number of states generated', 'Worker: rmi']
        for line in f:
            if 'TLC Server' in line:
                continue
            if line[0] != '@':
                start_msg = 'Error: ' + start_msg
            break
        for line in f:
            if line.startswith(start_msg):
                yield '-' * 16 + ' MODULE MC_trace ' + '-' * 16 + '\n'
                break
        for line in f:
            if line[0] in '/ ':
                yield line
            elif line.startswith('State') or line[0].isdigit():
                yield r'\*' + line[line.find(':')+1:]
                n_state = n_state + 1
                yield 'STATE_{} == \n'.format(n_state)
            elif line == '\n':
                yield '\n' * 2
            elif any(line.startswith(x) for x in end_msg):
                yield '=' * 49 + '\n'
                break
            else:
                if line[0] != '@':
                    pass

        f.close()


    @staticmethod
    def get_action_name(line):
        start = line.find('<')
        end = line.find(' ', start)
        if end > start > 0:
            return line[start+1:end]
        return None


    # read trace file and yield states as python objects
    def trace_reader_with_state_str(self, file):
        if not hasattr(file, 'read'):
            f = open(file)
        else:
            f = file

        if f.read(2) != '--':
            f = self.get_converted_string(f)

        state = dict()
        variable = ""
        lines = []
        cur_action = None
        cur_action_line = None
        for line in f:
            if line.startswith(r'\*'):
                cur_action_line = line
                if self.save_action_name:
                    cur_action = self.get_action_name(line)
            elif line[0] in "-=S":
                if state:
                    yield state, ''.join(lines).strip()
                    state = dict()
                if cur_action is not None:
                    state['_action'] = cur_action
                lines = [] if cur_action_line is None else [cur_action_line]
            elif line[0] in "/\n":
                if variable:
                    k, v = variable.split('=')
                    k, v = k.rstrip(), v.lstrip()
                    # replace to 1-char keywords, replace '>' to a uniq key
                    k, v = self._kv_outside_handler(k, self._variable_converter(
                        v.replace('<<', '<').replace('>>', '$')))
                    state[k] = v
                variable = line.strip()[3:]
                lines.append(line)
            else:
                variable += " " + line.strip()
                lines.append(line)

        f.close()


    def trace_reader(self, file):
        for state, _ in self.trace_reader_with_state_str(file):
            yield state


if __name__ == '__main__':
    import json
    import argparse

    # arg parser
    parser = argparse.ArgumentParser(
        description="Read TLA traces into Python objects")

    parser.add_argument(dest='trace_file', action='store',
                        help='TLA trace file')
    parser.add_argument('-o', dest='json_file', action='store', required=False,
                        help="output to json file")
    parser.add_argument('-i', dest='indent', action='store', required=False,
                        type=int, help="json file indent")
    parser.add_argument('-p', dest='handler', action='store', required=False,
                        help="python user_dict and list/kv handers")
    parser.add_argument('-a', dest='action', action='store_true', required=False,
                        help="save action name in '_action' key if available")
    args = parser.parse_args()

    tr = TraceReader(args.action)

    if args.handler:
        import sys
        import os

        try:
            sys.path.insert(1, os.path.dirname(args.handler))
            handler_module = __import__(
                os.path.basename(args.handler).replace('.py', ''))
            sys.path.pop(1)
        except ModuleNotFoundError:
            print("Warning: cannot import module '{}'".format(args.handler),
                  file=sys.stderr)
            handler_module = None

        if hasattr(handler_module, "user_dict"):
            tr.set_user_dict(handler_module.user_dict)
        if hasattr(handler_module, "list_handler"):
            tr.set_list_handler(handler_module.list_handler)
        if hasattr(handler_module, "outside_kv_handler"):
            tr.set_kv_handler(handler_module.outside_kv_handler, inside=False)
        if hasattr(handler_module, "inside_kv_handler"):
            tr.set_kv_handler(handler_module.inside_kv_handler, inside=True)

    # Examples:
    # set_user_dict and set_kv_handler usage example
    # tr.set_user_dict({"Nil": None})
    
    # def kv_handler(k, v):
    #     if k != 'messages':
    #         return k, v
    #     v.sort(key=lambda i: i['seq'])
    #     return k, v
    
    # tr.set_kv_handler(kv_handler, False)

    states = list(tr.trace_reader(args.trace_file))

    if args.json_file:
        with open(args.json_file, 'w') as f:
            json.dump(states, f, indent=args.indent)
            f.write('\n')
    else:
        print(json.dumps(states, indent=args.indent))
