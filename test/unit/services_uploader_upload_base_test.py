from mock import Mock
from pytest import raises

from mash.services.uploader.upload_base import UploadBase


class TestUploadBase(object):
    def setup(self):
        self.credentials = Mock()
        self.uploader = UploadBase(
            self.credentials, 'file', 'name', 'description', None
        )

    def test_upload(self):
        with raises(NotImplementedError):
            self.uploader.upload()
