import sys
import os
from operator import itemgetter
from itertools import groupby
import typedbytes


def _key_values_text(sep='\t'):
    for line in sys.stdin:
        yield line.rstrip().split(sep, 1)


def _key_values_tb():
    return typedbytes.PairedInput(sys.stdin).reads()


def _groupby_key_values(kv):
    return ((x, (z[1] for z in y))
            for x, y in groupby(kv, itemgetter(0)))


def _offset_values_text():
    line_count = 0
    for line in sys.stdin:
        yield line_count, line[:-1]
        line_count += len(line)


def _is_io_typedbytes():
    # Only all or nothing typedbytes is supported, just check stream_map_input
    try:
        return os.environ['stream_map_input'] == 'typedbytes'
    except KeyError:
        return False


def _read_in_map():
    if _is_io_typedbytes():
        return _key_values_tb()
    return _offset_values_text()


def _read_in_reduce():
    if _is_io_typedbytes():
        return _key_values_tb()
    return _key_values_text()


def _print_out_text(iter, sep='\t'):
    for out in iter:
        if isinstance(out, tuple):
            print(sep.join(str(x) for x in out))
        else:
            print(str(out))


def _print_out_tb(iter):
    typedbytes.PairedOutput(sys.stdout).writes(iter)


def _print_out(iter):
    if iter:
        _print_out_tb(iter) if _is_io_typedbytes() else _print_out_text(iter)


def _final(func):
    _print_out(func())
    return 0


def _configure_call_close(attr):
    def factory(f):
        def inner(func):
            if func == None:
                return 1
            if isinstance(func, type):
                func = func()
            try:
                func.configure()
            except AttributeError:
                pass
            try:
                try:
                    return f(getattr(func, attr))
                except AttributeError:
                    return f(func)
            except ValueError:  # func not generator, its ok
                return 0
            finally:
                try:
                    _final(func.close)
                except AttributeError:
                    pass
        return inner
    return factory


@_configure_call_close('map')
def _map(func):
    for key, value in _read_in_map():
        _print_out(func(key, value))
    return 0


@_configure_call_close('reduce')
def _reduce(func):
    for key, values in _groupby_key_values(_read_in_reduce()):
        _print_out(func(key, values))
    return 0


def run(mapper=None, reducer=None, combiner=None, **kw):
    funcs = {'map': lambda: _map(mapper),
             'reduce': lambda: _reduce(reducer),
             'combine': lambda: _reduce(combiner)}
    try:
        ret = funcs[sys.argv[1]]()
    except (IndexError, KeyError):
        ret = 1
    if ret and 'doc' in kw:
        print_doc_quit(kw['doc'])
    return ret


def print_doc_quit(doc):
    print(doc)
    sys.exit(1)
