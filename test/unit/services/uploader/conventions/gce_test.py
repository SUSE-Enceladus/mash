from mash.services.uploader.conventions.gce import ConventionsGCE


class TestConventionsGCE(object):
    def setup(self):
        self.conventions = ConventionsGCE()

    def test_is_valid_name(self):
        self.conventions.is_valid_name('name')
