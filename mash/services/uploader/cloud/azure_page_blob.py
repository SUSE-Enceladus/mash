# Copyright (c) 2018 SUSE Linux GmbH.  All rights reserved.
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
from mash.mash_exceptions import (
    MashAzurePageBlobZeroPageError,
    MashAzurePageBlobAlignmentViolation,
    MashAzurePageBlobSetupError,
    MashAzurePageBlobUpdateError
)


class PageBlob(object):
    """
    Page blob iterator to control a stream of data to an Azure page blob
    """
    def __init__(self, blob_service, blob_name, container, byte_size):
        """
        Create a new page blob of the specified byte_size with
        name blob_name in the specified container. An azure page
        blob must be 512 byte aligned
        """
        self.container = container
        self.blob_service = blob_service
        self.blob_name = blob_name

        self.__validate_page_alignment(byte_size)

        self.rest_bytes = byte_size
        self.page_start = 0

        try:
            self.blob_service.create_blob(
                self.container, self.blob_name, byte_size
            )
        except Exception as e:
            raise MashAzurePageBlobSetupError(
                '%s: %s' % (type(e).__name__, format(e))
            )

    def next(self, data_stream, max_chunk_byte_size=None, max_attempts=5):
        if not max_chunk_byte_size:
            max_chunk_byte_size = self.blob_service.MAX_CHUNK_GET_SIZE
        max_chunk_byte_size = int(max_chunk_byte_size)

        requested_bytes = min(
            self.rest_bytes, max_chunk_byte_size
        )

        if requested_bytes != max_chunk_byte_size:
            zero_page = self.__read_zero_page(requested_bytes)
        else:
            zero_page = self.__read_zero_page(max_chunk_byte_size)

        data = data_stream.read(requested_bytes)

        if not data:
            raise StopIteration()

        length = len(data)
        page_end = self.page_start + length - 1

        if not data == zero_page:
            upload_errors = []
            while len(upload_errors) < max_attempts:
                try:
                    self.blob_service.update_page(
                        self.container,
                        self.blob_name,
                        data,
                        self.page_start,
                        page_end
                    )
                    break
                except Exception as e:
                    upload_errors.append(
                        '%s: %s' % (type(e).__name__, format(e))
                    )

            if len(upload_errors) == max_attempts:
                raise MashAzurePageBlobUpdateError(
                    'Page update failed with: %s' % '\n'.join(upload_errors)
                )

        self.rest_bytes -= length
        self.page_start += length

        return self.page_start

    def __iter__(self):
        return self

    def __validate_page_alignment(self, byte_size):
        remainder = byte_size % 512
        if remainder != 0:
            raise MashAzurePageBlobAlignmentViolation(
                'Uncompressed size %d is not 512 byte aligned' % byte_size
            )

    def __read_zero_page(self, requested_bytes):
        try:
            with open('/dev/zero', 'rb') as zero_stream:
                return zero_stream.read(requested_bytes)
        except Exception as e:
            raise MashAzurePageBlobZeroPageError(
                'Reading zero page failed with: %s' % format(e)
            )
