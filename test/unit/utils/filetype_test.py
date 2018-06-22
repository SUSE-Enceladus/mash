from mash.utils.filetype import FileType


class TestFileType:
    def setup(self):
        self.filetype_xz = FileType('../data/blob.xz')
        self.filetype_not_xz = FileType('../data/id_test')

    def test_is_xz(self):
        assert self.filetype_xz.is_xz() is True

    def test_not_xz(self):
        assert self.filetype_not_xz.is_xz() is False

    def test_get_size(self):
        assert self.filetype_xz.get_size() == 4
        assert self.filetype_not_xz.get_size() == 1679
