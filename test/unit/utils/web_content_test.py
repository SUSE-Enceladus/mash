from unittest.mock import (
    Mock, patch, call
)
from py.test import raises

from mash.utils.web_content import WebContent
from mash.mash_exceptions import MashWebContentException


class TestWebContent(object):
    def setup(self):
        self.web = WebContent('http://example.com')
        with open('../data/index.html') as index:
            self.request_result = index.read()

    @patch('mash.utils.web_content.Request')
    @patch('mash.utils.web_content.urlopen')
    def test_fetch_index_list(self, mock_urlopen, mock_Request):
        location = Mock()
        location.read.return_value = self.request_result
        mock_urlopen.return_value = location
        result = self.web.fetch_index_list('SLES12-Azure-BYOS')
        mock_Request.assert_called_once_with('http://example.com')
        mock_urlopen.assert_called_once_with(mock_Request.return_value)
        assert result[0] == \
            'SLES12-Azure-BYOS.x86_64-0.2.4-Build3.549-raw.tar.bz2'
        mock_Request.side_effect = Exception
        with raises(MashWebContentException):
            self.web.fetch_index_list('SLES12-Azure-BYOS')

    @patch('mash.utils.web_content.Request')
    @patch('mash.utils.web_content.urlopen')
    @patch('mash.utils.web_content.urlretrieve')
    def test_fetch_file(self, mock_urlretrieve, mock_urlopen, mock_Request):
        location = Mock()
        location.read.return_value = self.request_result
        mock_urlopen.return_value = location
        result = self.web.fetch_file(
            'SLES12-Azure-BYOS', '.packages', 'target'
        )
        mock_urlretrieve.assert_called_once_with(
            'http://example.com/SLES12-Azure-BYOS'
            '.x86_64-0.2.4-Build3.549-vmx.packages', 'target'
        )
        assert result == \
            'SLES12-Azure-BYOS.x86_64-0.2.4-Build3.549-vmx.packages'
        mock_Request.side_effect = Exception
        with raises(MashWebContentException):
            self.web.fetch_file('SLES12-Azure-BYOS', '.packages', 'target')

    @patch('mash.utils.web_content.Request')
    @patch('mash.utils.web_content.urlopen')
    @patch('mash.utils.web_content.urlretrieve')
    def test_fetch_files(self, mock_urlretrieve, mock_urlopen, mock_Request):
        location = Mock()
        location.read.return_value = self.request_result
        mock_urlopen.return_value = location
        result = self.web.fetch_files(
            'SLES12-Azure-BYOS', ['.packages', 'vhdfixed.xz.sha256'],
            'target_dir'
        )
        assert mock_urlretrieve.call_args_list == [
            call(
                'http://example.com/'
                'SLES12-Azure-BYOS.x86_64-0.2.4-Build3.549-vmx.packages',
                'target_dir/'
                'SLES12-Azure-BYOS.x86_64-0.2.4-Build3.549-vmx.packages'
            ),
            call(
                'http://example.com/'
                'SLES12-Azure-BYOS.x86_64-0.2.4-Build3.549.vhdfixed.xz.sha256',
                'target_dir/'
                'SLES12-Azure-BYOS.x86_64-0.2.4-Build3.549.vhdfixed.xz.sha256'
            )
        ]
        assert result == [
            'target_dir/'
            'SLES12-Azure-BYOS.x86_64-0.2.4-Build3.549-vmx.packages',
            'target_dir/'
            'SLES12-Azure-BYOS.x86_64-0.2.4-Build3.549.vhdfixed.xz.sha256'
        ]
        mock_Request.side_effect = Exception
        with raises(MashWebContentException):
            self.web.fetch_files(
                'SLES12-Azure-BYOS', ['.packages', 'vhdfixed.xz.sha256'],
                'target_dir'
            )
