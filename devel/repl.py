#!/usr/bin/env -S bash -c '"$(dirname $(readlink $0 || echo $0))/../env/bin/python" "$0" "$@"'
# PYTHON_ARGCOMPLETE_OK
# set environment variable _ARC_DEBUG to debug argcomplete

import argparse
import asyncio
import os
import code

import argcomplete

try:
    from devel.development import RawTextArgumentDefaultsHelpFormatter
except ImportError:
    class RawTextArgumentDefaultsHelpFormatter(
        argparse.ArgumentDefaultsHelpFormatter,
        argparse.RawTextHelpFormatter):
        pass

user = os.environ.get("USER")
if user == "dzem":
    default_path = "/home/dzem/HOMECTRL"
elif user == "chmielu":
    default_path = "/home/chmielu/workspace/HOMECTRL"
else:
    default_path = ""


class REPL:
    argparser = argparse.ArgumentParser(
        prog='repl',
        description='DZEM HomeCtrl Devel - REPL - python REPL with HomeCtrl environment',
        add_help=True, formatter_class=RawTextArgumentDefaultsHelpFormatter)
    argparser.add_argument("--path", "-p", help="Set working directory to specified path", default=default_path)

    @classmethod
    def parse_args(cls, args=None):
        argcomplete.autocomplete(cls.argparser)
        return cls.argparser.parse_args(args)

    def __init__(self, parsed_args):
        self.args = parsed_args

    async def main(self):
        os.chdir(self.args.path)
        print("CWD: " + os.getcwd())
        code.interact(local=globals())

    def run(self):
        try:
            asyncio.run(self.main())
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    REPL(REPL.parse_args()).run()
