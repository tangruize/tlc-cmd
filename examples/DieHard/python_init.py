def init_replace_init(ri):
    def choose_state(state_num: int, state_dict: dict, state_str: str, is_last_state: bool) -> str:
        if state_dict['BIG'] != 0 or is_last_state:
            return state_str.replace('/', '    /')  # custom state_str
        return ''

    ri.set_chooser_handler(choose_state)


def init_trace_reader(tr):
    def kv_handler(k, v):
        if k != 'big':
            return k, v
        return 'BIG', v  # change variable name 'big' to 'BIG'

    tr.set_kv_handler(kv_handler)
