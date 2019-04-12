# Copyright (c) 2019 SUSE LLC.  All rights reserved.
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

from mash.services.pipeline_service import PipelineService


class TestingService(PipelineService):
    """
    Implementation of testing service. Launches an instance of the
    image in the given cloud framework and tests image using IPA.

    * :attr:`custom_args`
    """
    __test__ = False

    def service_init(self):
        """
        Initialize testing service class.

        Setup private key file and ipa timeout.
        """
        self.listener_msg_args.append('source_regions')
        self.status_msg_args.append('source_regions')
