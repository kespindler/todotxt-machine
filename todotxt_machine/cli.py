#!/usr/bin/env python
# coding=utf-8
import argparse
import sys
import os
import random
from collections import OrderedDict

# import ipdb; # ipdb.set_trace()
# import pprint
# pp = pprint.PrettyPrinter(indent=4).pprint

# Import the correct version of configparser
if sys.version_info[0] >= 3:
    import configparser
    config_parser_module = configparser
elif sys.version_info[0] < 3:
    import ConfigParser
    config_parser_module = ConfigParser

import todotxt_machine
from todotxt_machine.todo import Todos, Todo
from todotxt_machine.widgets.main import UrwidUI
from todotxt_machine.colorscheme import ColorScheme
from todotxt_machine.keys import KeyBindings


def exit_with_error(message):
    sys.stderr.write(message.strip(' \n')+'\n')
    print(__doc__.split('\n\n')[1])
    exit(1)


def get_real_path(filename, description):
    # expand enviroment variables and username, get canonical path
    file_path = os.path.realpath(os.path.expanduser(os.path.expandvars(filename)))

    if os.path.isdir(file_path):
        exit_with_error("ERROR: Specified {0} file is a directory.".format(description))

    if not os.path.exists(file_path):
        directory = os.path.dirname(file_path)
        if os.path.isdir(directory):
            # directory exists, but no todo.txt file - create an empty one
            open(file_path, 'a').close()
        else:
            exit_with_error("ERROR: The directory: '{0}' does not exist\n\nPlease create the directory or specify a different\n{0} file on the command line.".format(directory, description))

    return file_path


def main():
    random.seed()

    # Parse command line
    parser = argparse.ArgumentParser()
    parser.add_argument('--todo', nargs='?')
    parser.add_argument('--done', nargs='?')
    parser.add_argument('--config', nargs='?', default='~/.todotxt-machinerc')
    parser.add_argument('--version', action='version', version=todotxt_machine.version)
    parser.add_argument('--show-default-bindings', action='store_true', default=False)

    subparsers = parser.add_subparsers(dest='subparser_name', help='sub-command help')

    subparser = subparsers.add_parser('curses')
    subparser = subparsers.add_parser('add')
    subparser.add_argument('body')

    if len(sys.argv) == 1:
        sys.argv.append('curses')
    args = parser.parse_args()
    # Validate readline editing mode option (docopt doesn't handle this)
    # if arguments['--readline-editing-mode'] not in ['vi', 'emacs']:
    #     exit_with_error("--readline-editing-mode must be set to either vi or emacs\n")

    # Parse config file
    cfg = config_parser_module.ConfigParser(allow_no_value=True)
    cfg.add_section('keys')

    if args.show_default_bindings:
        d = {k: ", ".join(v['keys']) for k, v in KeyBindings({}).key_bindings.items()}
        cfg._sections['keys'] = OrderedDict(sorted(d.items(), key=lambda t: t[0]))
        cfg.write(sys.stdout)
        exit(0)

    cfg.add_section('settings')
    cfg.read(os.path.expanduser(args.config))

    # Load keybindings specified in the [keys] section of the config file
    keyBindings = KeyBindings(dict(cfg.items('keys')))

    # load the colorscheme defined in the user config, else load the default scheme
    colorscheme = ColorScheme(dict(cfg.items('settings') ).get('colorscheme', 'default'), cfg)

    # Load the todo.txt file specified in the [settings] section of the config file
    # a todo.txt file on the command line takes precedence
    todotxt_file = dict(cfg.items('settings')).get('file', args.todo)
    if args.todo:
        todotxt_file = args.todo

    if todotxt_file is None:
        exit_with_error("ERROR: No todo file specified. Either specify one as an argument on the command line or set it in your configuration file ({0}).".format(arguments['--config']))

    # Load the done.txt file specified in the [settings] section of the config file
    # a done.txt file on the command line takes precedence
    donetxt_file = dict(cfg.items('settings') ).get('archive', args.done)
    if args.done:
        donetxt_file = args.done

    todotxt_file_path = get_real_path(todotxt_file, 'todo.txt')

    if donetxt_file is not None:
        donetxt_file_path = get_real_path(donetxt_file, 'done.txt')
    else:
        donetxt_file_path = None

    try:
        with open(todotxt_file_path, "r") as todotxt_file:
            todos = Todos(todotxt_file.readlines(), todotxt_file_path, donetxt_file_path)
    except:
        exit_with_error("ERROR: unable to open {0}\n\nEither specify one as an argument on the command line or set it in your configuration file ({0}).".format(todotxt_file_path, arguments['--config']))
        todos = Todos([], todotxt_file_path, donetxt_file_path)

    if args.subparser_name == 'curses':
        view = UrwidUI(todos, keyBindings, colorscheme)
        view.main()
    if args.subparser_name == 'add':
        todos.create_todo(args.body, 0)
        idx = todos.append(args.body, False)

    todos.save()
    # print("Writing: {0}".format(todotxt_file_path))
    exit(0)

if __name__ == '__main__':
    main()
