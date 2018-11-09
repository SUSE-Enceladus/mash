from pytest import raises
from unittest.mock import patch

from mash.services.uploader.conventions import Conventions
from mash.mash_exceptions import MashConventionsException


class TestConventions(object):
    @patch('mash.services.uploader.conventions.ConventionsAmazon')
    def test_conventions_amazon(self, mock_ConventionsAmazon):
        Conventions('ec2')
        mock_ConventionsAmazon.assert_called_once_with()
        with raises(MashConventionsException):
            Conventions('foo')

    @patch('mash.services.uploader.conventions.ConventionsAzure')
    def test_conventions_azure(self, mock_ConventionsAzure):
        Conventions('azure')
        mock_ConventionsAzure.assert_called_once_with()
        with raises(MashConventionsException):
            Conventions('foo')

    @patch('mash.services.uploader.conventions.ConventionsGCE')
    def test_conventions_gce(self, mock_ConventionsGCE):
        Conventions('gce')
        mock_ConventionsGCE.assert_called_once_with()
