from pytest import raises
from unittest.mock import patch
from unittest.mock import Mock
from collections import namedtuple

import os
from mash.mash_exceptions import MashCommandException
from mash.utils.command import Command


class TestCommand(object):
    @patch('subprocess.Popen')
    def test_run_raises_error(self, mock_popen):
        mock_process = Mock()
        mock_process.communicate = Mock(
            return_value=[str.encode('stdout'), str.encode('stderr')]
        )
        mock_process.returncode = 1
        mock_popen.return_value = mock_process
        with raises(MashCommandException):
            Command.run(['command', 'args'])

    @patch('subprocess.Popen')
    def test_run_failure(self, mock_popen):
        mock_popen.side_effect = MashCommandException('Run failure')
        with raises(MashCommandException):
            Command.run(['command', 'args'])

    def test_run_invalid_environment(self):
        with raises(MashCommandException):
            Command.run(['command', 'args'], {'HOME': '/root'})

    @patch('subprocess.Popen')
    def test_run_does_not_raise_error(self, mock_popen):
        mock_process = Mock()
        mock_process.communicate = Mock(
            return_value=[str.encode(''), str.encode('')]
        )
        mock_process.returncode = 1
        mock_popen.return_value = mock_process
        result = Command.run(['command', 'args'], os.environ, False)
        assert result.error == '(no output on stderr)'
        assert result.output == '(no output on stdout)'

    @patch('os.access')
    @patch('os.path.exists')
    @patch('subprocess.Popen')
    def test_run(self, mock_popen, mock_exists, mock_access):
        mock_exists.return_value = True
        command_run = namedtuple(
            'command', ['output', 'error', 'returncode']
        )
        run_result = command_run(
            output='stdout',
            error='stderr',
            returncode=0
        )
        mock_process = Mock()
        mock_process.communicate = Mock(
            return_value=[str.encode('stdout'), str.encode('stderr')]
        )
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        mock_access.return_value = True
        assert Command.run(['command', 'args']) == run_result
