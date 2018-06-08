from mash.utils.xz import XZ


class TestXZ:
    def setup(self):
        self.xz = XZ.open('../data/blob.xz')

    def teardown(self):
        self.xz.close()

    def test_read(self):
        assert self.xz.read(128) == b'foo\n'

    def test_read_chunks(self):
        with XZ.open('../data/blob.more.xz') as xz:
            chunk = xz.read(8)
            assert chunk == b'Some dat'
            chunk = xz.read(8)
            assert chunk == b'a so tha'
            chunk = xz.read(8)
            assert chunk == b't we can'
            chunk = xz.read(8)
            assert chunk == b' read it'
            chunk = xz.read(8)
            assert chunk == b' as mult'
            chunk = xz.read(8)
            assert chunk == b'iple chu'
            chunk = xz.read(8)
            assert chunk == b'nks\n'
            chunk = xz.read(8)
            assert chunk is None
            chunk = xz.read(8)
            assert chunk is None

    def test_uncompressed_size(self):
        assert XZ.uncompressed_size('../data/blob.xz') == 4
