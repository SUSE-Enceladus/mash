from mash.services.uploader.conventions.amazon import ConventionsAmazon


class TestConventionsBase(object):
    def setup(self):
        self.conventions = ConventionsAmazon()

    def test_is_valid_name(self):
        self.conventions.is_valid_name('name')
