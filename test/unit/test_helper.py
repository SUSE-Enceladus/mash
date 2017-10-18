import sys
from collections import namedtuple
from mock import (
    MagicMock,
    patch
)

# mock open calls
patch_open = patch("{0}.open".format(
    sys.version_info.major < 3 and "__builtin__" or "builtins")
)


def mock_open():
    """
    Mock open function.

    :return: mock object
    """
    mock = MagicMock()
    handle = MagicMock()
    handle.write.return_value = None
    handle.__enter__.return_value = handle
    mock.return_value = handle

    return mock


def context_manager():
    context_manager_type = namedtuple(
        'context_manager_type', [
            'context_manager_mock', 'file_mock', 'enter_mock', 'exit_mock'
        ]
    )

    context_manager_mock = MagicMock()
    file_mock = MagicMock()
    enter_mock = MagicMock()
    exit_mock = MagicMock()
    enter_mock.return_value = file_mock
    setattr(context_manager_mock, '__enter__', enter_mock)
    setattr(context_manager_mock, '__exit__', exit_mock)

    return context_manager_type(
        context_manager_mock=context_manager_mock,
        file_mock=file_mock,
        enter_mock=enter_mock,
        exit_mock=exit_mock
    )
