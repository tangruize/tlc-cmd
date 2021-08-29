#!/usr/bin/python3

# usage: python3 trace_reader.py -h

# find '}$])' for '{<[('
def _find_next_match(string):
    level = 0
    char = string[0]
    match_char = _matching[char][0]
    for i, c in enumerate(string):
        if c == char:
            level += 1
        elif c == match_char:
            level -= 1
            if level == 0:
                return i
    assert False


# < string $
def _chevrons(string):
    l = list()
    if not string:
        return _list_handler(l)
    processed, pos, length = 0, 0, len(string)
    while pos < length:
        if string[pos] in _matching or string[pos] == ',':
            if string[pos] != ',':
                pos = pos + _find_next_match(string[pos:]) + 1
            l.append(_variable_converter(string[processed:pos]))
            processed = pos + 2
            pos += 1
        pos += 1
    if pos != processed:
        l.append(_variable_converter(string[processed:pos]))
    return _list_handler(l)


# { string } (we treat set as list)
def _braces(string):
    return _chevrons(string)


# return a dict
def _dict_common(string, arrow, sep, value_seq_len):
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
            key, value = _kv_inside_handler(key, _variable_converter(value))
            d[key] = value
        pos += 1
        if pos >= length:
            break
        if string[pos] in _matching:
            pos = pos + _find_next_match(string[pos:])
    value = string[processed:]
    key, value = _kv_inside_handler(key, _variable_converter(value))
    d[key] = value
    return d


# [ string ]
def _brackets(string):
    return _dict_common(string, '|->', ',', 0)


# ( string )
def _parentheses(string):
    return _dict_common(string, ':>', '@@', 1)


_matching = {'{': ('}', _braces), '<': ('$', _chevrons),
             '[': (']', _brackets), '(': (')', _parentheses)}

_string_dict = {"TRUE": True, "FALSE": False}
_user_dict = dict()
_kv_outside_handler = lambda k, v: (k, v)
_kv_inside_handler = lambda k, v: (k, v)
_list_handler = lambda s: s


# convert string to python variable
def _variable_converter(string):
    if string[0] in _matching:
        return _matching[string[0]][1](string[1:-1].strip())
    if string[0] == '"':
        return string[1:-1]
    if string in _string_dict:
        return _string_dict[string]
    if string in _user_dict:
        return _user_dict[string]
    try:
        return int(string)
    except ValueError:
        return string


# callback handlers
def set_user_dict(user_dict):
    global _user_dict
    _user_dict = user_dict


def set_kv_handler(kv_handler, inside=False):
    global _kv_inside_handler, _kv_outside_handler
    if inside:
        _kv_inside_handler = kv_handler
    else:
        _kv_outside_handler = kv_handler


def set_list_handler(list_handler):
    global _list_handler
    _list_handler = list_handler


# convert MC.out to trace file
def get_converted_string(file):
    if not hasattr(file, 'read'):
        f = open(file)
    else:
        f = file

    n_state = 0
    start_msg = 'The behavior up to this point is:'
    end_msg1 = 'Progress'
    end_msg2 = 'The number of states generated:'
    for line in f:
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
            n_state = n_state + 1
            yield 'STATE_{} == \n'.format(n_state)
        elif line == '\n':
            yield '\n' * 2
        elif line.startswith(end_msg1) or line.startswith(end_msg2):
            yield '=' * 49 + '\n'
            break
        else:
            if line[0] != '@':
                assert False

    f.close()


# read trace file and yield states as python objects
def trace_reader(file):
    if not hasattr(file, 'read'):
        f = open(file)
    else:
        f = file

    if f.read(2) != '--':
        f = get_converted_string(f)

    state = dict()
    variable = ""
    for line in f:
        if line[0] in "-=S":
            if state:
                # states.append(state)
                yield state
                state = dict()
            continue
        elif line[0] in "/\n":
            if variable:
                k, v = variable.split('=')
                k, v = k.rstrip(), v.lstrip()
                # replace to 1-char keywords, replace '>' to a uniq key
                k, v = _kv_outside_handler(k, _variable_converter(
                    v.replace('<<', '<').replace('>>', '$')))
                state[k] = v
            variable = line.strip()[3:]
        else:
            variable += " " + line.strip()

    f.close()


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
    args = parser.parse_args()

    # # set_user_dict and set_kv_handler usage example
    # set_user_dict({"Nil": None})
    #
    # def kv_handler(k, v):
    #     if k != 'messages':
    #         return k, v
    #     v.sort(key=lambda i: i['seq'])
    #     return k, v
    #
    # set_kv_handler(kv_handler, False)

    states = list(trace_reader(args.trace_file))

    if args.json_file:
        with open(args.json_file, 'w') as f:
            json.dump(states, f, indent=args.indent)
            f.write('\n')
    else:
        print(json.dumps(states, indent=args.indent))
