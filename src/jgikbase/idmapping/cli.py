"""
CLI tools for the ID Mapping system.
"""

from typing import List, IO
import sys
import argparse
from jgikbase.idmapping.core.arg_check import not_none, no_Nones_in_iterable
import traceback
from pathlib import Path
from jgikbase.idmapping.builder import IDMappingBuilder
from jgikbase.idmapping.core.user_lookup import LocalUserLookup
from jgikbase.idmapping.core.user import Username

# TODO CLI integration tests. Not super important IMO.


class IDMappingCLI:
    """
    The main CLI class.
    """

    _PROG = 'id_mapper'
    _USER = '--user'
    _LIST = '--list-users'
    _CREATE = '--create'
    _NEW_TOKEN = '--new-token'
    _ADMIN = '--admin'

    _TRUE = 'true'
    _FALSE = 'false'

    def __init__(
            self,
            builder: IDMappingBuilder,
            args: List[str],
            stdout: IO[str],
            stderr: IO[str]
            ) -> None:
        """
        Create the CLI.

        :param args: the command line arguments without the program name.
        :param stdout: the standard out stream.
        :param stderr: the standard error stream.
        :raises TypeError: if any of the arguments are None.
        """
        not_none(builder, 'builder')
        no_Nones_in_iterable(args, 'args')
        not_none(stdout, 'stdout')
        not_none(stderr, 'stderr')
        self._builder = builder
        self._args = args
        self._stdout = stdout
        self._stderr = stderr

    def execute(self) -> int:
        """
        Run the CLI with the given arguments.

        :returns: the exit code for the program.
        """
        a = self._parse_args()
        if not self._check_inputs(a):
            return 1
        try:
            luh = self._builder.build_local_user_lookup(Path(a.config))
        except Exception as e:
            self._handle_error(e, a.verbose)
            return 1
        if a.list_users:
            return self._list_users(luh, a.verbose)
        # ok, so user must have a valid value at this point
        u = Username(a.user)
        if a.create:
            return self._create_user(luh, u, a.verbose)
        if a.new_token:
            return self._new_token(luh, u, a.verbose)
        return self._admin(luh, u, a.admin, a.verbose)

    def _check_inputs(self, args):
        if sum((args.list_users, bool(args.user))) != 1:
            self._stderr.write('Exactly one of {} or {} must be specified.\n'.format(
                self._LIST, self._USER))
            return False
        if args.user:
            if sum((args.create, bool(args.admin), args.new_token)) != 1:
                self._stderr.write('Exactly one of {}, {}, or {} must be specified.\n'.format(
                    self._CREATE, self._NEW_TOKEN, self._ADMIN))
                return False
            if args.admin and args.admin not in [self._TRUE, self._FALSE]:
                self._stderr.write("{} must have a value of '{}' or '{}'.\n".format(
                    self._ADMIN, self._TRUE, self._FALSE))
                return False
            try:
                Username(args.user)
            except Exception as e:
                self._handle_error(e, args.verbose)
                return False
        return True

    def _list_users(self, local_user_handler: LocalUserLookup, verbose):
        try:
            users = local_user_handler.get_users()
        except Exception as e:
            self._handle_error(e, verbose)
            return 1
        self._stdout.write('* indicates an administrator:\n')
        userstr = {u.name: users[u] for u in users}   # may want to make comparable
        for u in sorted(userstr):
            admin = userstr[u]
            self._stdout.write('{}{}\n'.format(u, ' *' if admin else ''))
        return 0

    def _create_user(
            self,
            local_user_handler: LocalUserLookup,
            username: Username,
            verbose):
        try:
            t = local_user_handler.create_user(username)
        except Exception as e:
            self._handle_error(e, verbose)
            return 1
        self._stdout.write('Created user {} with token:\n{}\n'.format(username.name, t.token))
        return 0

    def _new_token(
            self,
            local_user_handler: LocalUserLookup,
            username: Username,
            verbose):
        try:
            t = local_user_handler.new_token(username)
        except Exception as e:
            self._handle_error(e, verbose)
            return 1
        self._stdout.write("Replaced user {}'s token with token:\n{}\n".format(
            username.name, t.token))
        return 0

    def _admin(
            self,
            local_user_handler: LocalUserLookup,
            username: Username,
            admin: str,
            verbose):
        try:
            local_user_handler.set_user_as_admin(username, admin == self._TRUE)
        except Exception as e:
            self._handle_error(e, verbose)
            return 1
        self._stdout.write("Set user {}'s admin state to {}.\n".format(username.name, admin))
        return 0

    def _parse_args(self) -> argparse.Namespace:
        parser = argparse.ArgumentParser(description='ID Mapping system CLI', prog=self._PROG,
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument(self._LIST, action='store_true',
                            help='List system users and whether they are administrators. ' +
                            'All other arguments are ignored.')
        parser.add_argument(self._USER, help='The name of the user to modify or create.')
        parser.add_argument(self._CREATE, action='store_true',
                            help='Create a user. Requires the {} option.'.format(self._USER))
        parser.add_argument(self._NEW_TOKEN, action='store_true',
                            help='Make a new token for a user. Requires the {} option.'.format(
                                self._USER, self._CREATE))
        parser.add_argument(self._ADMIN, help=(
            "Set whether the user is an admin ('{}') or not ('{}'). Any other values are " +
            'not permitted. Requires the {} option.').format(self._TRUE, self._FALSE, self._USER))
        parser.add_argument('--config', default='./deploy.cfg',
                            help='The location of the configuration file.')
        parser.add_argument('--verbose', action='store_true', help='Print stack trace on error.')
        return parser.parse_args(self._args)

    def _handle_error(self, exception, verbose=False):
        self._stderr.write('Error: {}\n'.format(exception.args[0]))
        if verbose:
            self._stderr.write(traceback.format_exc() + '\n')


if __name__ == '__main__':
    # manually tested
    exit(IDMappingCLI(IDMappingBuilder(), sys.argv[1:], sys.stdout, sys.stderr).execute())
