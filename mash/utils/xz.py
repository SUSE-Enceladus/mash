# Copyright (c) 2017 SUSE Linux GmbH.  All rights reserved.
#
# This file is part of mash.
#
# mash is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# mash is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with mash.  If not, see <http://www.gnu.org/licenses/>
#
import lzma
import os


class XZ(object):
    """
    Implements decompression of lzma compressed files
    """
    LZMA_STREAM_BUFFER_SIZE = 8192

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lzma_stream.close()

    def __init__(self, lzma_stream, buffer_size=LZMA_STREAM_BUFFER_SIZE):
        self.buffer_size = int(buffer_size)
        self.lzma = lzma.LZMADecompressor()
        self.lzma_stream = lzma_stream
        self.buffered_bytes = b''

    def read(self, size):
        if self.lzma.eof and not self.buffered_bytes:
            return None

        chunks = self.buffered_bytes

        bytes_uncompressed = len(chunks)
        while not self.lzma.eof and bytes_uncompressed < size:
            chunks += self.lzma.decompress(
                self.lzma.unused_data + self.lzma_stream.read(self.buffer_size)
            )
            bytes_uncompressed = len(chunks)

        self.buffered_bytes = chunks[size:]
        return chunks[:size]

    @classmethod
    def close(self):
        self.lzma_stream.close()

    @classmethod
    def open(self, file_name, buffer_size=LZMA_STREAM_BUFFER_SIZE):
        self.lzma_stream = open(file_name, 'rb')
        return XZ(self.lzma_stream, buffer_size)

    @classmethod
    def uncompressed_size(self, file_name):
        with lzma.open(file_name) as lzma_stream:
            lzma_stream.seek(0, os.SEEK_END)
            return lzma_stream.tell()
