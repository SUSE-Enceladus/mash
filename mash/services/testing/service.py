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

from mash.services.base_service import BaseService
from mash.services.testing.config import TestingConfig


class TestingService(BaseService):
    """
    Implementation of testing service. Launches an instance of the
    image in the given cloud provider and tests image using IPA.

    * :attr:`custom_args`
    """
    __test__ = False

    def post_init(self, custom_args=None):
        """
        Initialize testing service class.

        Setup config and bind to jobcreator queue to receive jobs.
        """
        self.config = TestingConfig()

        try:
            self.start()
        except KeyboardInterrupt:
            pass
        except Exception:
            raise
        finally:
            self.stop()

    def start(self):
        """
        Start testing service.
        """
        self.channel.start_consuming()

    def stop(self):
        """
        Stop testing service.
        Stop consuming queues and close pika connections.
        """
        self.channel.stop_consuming()
        self.close_connection()
