from pytest import raises

from mash.services.uploader.conventions.base import ConventionsBase


class TestConventionsBase(object):
    def setup(self):
        self.conventions = ConventionsBase()

    def test_is_valid_name(self):
        with raises(NotImplementedError):
            self.conventions.is_valid_name()
