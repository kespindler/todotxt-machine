# coding=utf-8
import logging
import os.path as op

logging.basicConfig(filename=op.expanduser('~/.todotxt_machine.log'), level=logging.INFO)

log = logging.getLogger()


def handle_keypress(widget, key, context):
    handler, kwargs = widget.key_bindings.get_handler(key, context)

    if not handler:
        return False
    log.debug('running %s %s', handler, kwargs)
    getattr(widget, handler)(**kwargs)
    return True
