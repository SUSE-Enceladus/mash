from mash.services.uploader.conventions.azure import ConventionsAzure


class TestConventionsAzure(object):
    def setup(self):
        self.conventions = ConventionsAzure()

    def test_is_valid_name(self):
        self.conventions.is_valid_name('name')
