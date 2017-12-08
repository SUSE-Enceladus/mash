# Copyright (c) 2017 SUSE Linux GmbH.  All rights reserved.
#
# This file is part of mash.
#
# mash is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# mash is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with mash.  If not, see <http://www.gnu.org/licenses/>
#
import os
import subprocess
from collections import namedtuple

from builtins import bytes

# project
from mash.mash_exceptions import MashCommandException


class Command(object):
    """
    Implements command invocation

    An instance of Command provides methods to
    invoke external commands
    """
    @classmethod
    def run(self, command, custom_env=None, raise_on_error=True):
        """
        Execute a program and block the caller. The return value
        is a hash containing the stdout, stderr and return code
        information. Unless raise_on_error is set to false an
        exception is thrown if the command exits with an error
        code not equal to zero

        :param list command: command and arguments
        :param list custom_env: custom os.environ
        :param bool raise_on_error: control error behaviour

        :return: (string).output
        :return: (string).error
        :return: (int).returncode
        :rtype: tuple
        """
        command_type = namedtuple(
            'command', ['output', 'error', 'returncode']
        )
        environment = os.environ
        if custom_env:
            environment = custom_env
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment
            )
        except Exception as e:
            raise MashCommandException(
                '%s: %s: %s' % (command[0], type(e).__name__, format(e))
            )
        output, error = process.communicate()
        if process.returncode != 0 and not error:
            error = bytes(b'(no output on stderr)')
        if process.returncode != 0 and not output:
            output = bytes(b'(no output on stdout)')
        if process.returncode != 0 and raise_on_error:
            raise MashCommandException(
                '%s: stderr: %s, stdout: %s' % (
                    command[0], error.decode(), output.decode()
                )
            )
        return command_type(
            output=output.decode(),
            error=error.decode(),
            returncode=process.returncode
        )
