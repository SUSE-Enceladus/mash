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

from mash.services.base_service import BaseService
from mash.services.replication.config import ReplicationConfig


class ReplicationService(BaseService):
    """
    Implementation of replication service.

    Handles the replication of images in public cloud providers.
    """

    def post_init(self):
        """
        Initialize replication service class.
        """
        self.config = ReplicationConfig()
        self.set_logfile(self.config.get_log_file())

        self.jobs = {}

        self.start()

    def start(self):
        """
        Start replication service.
        """
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            pass
        except Exception:
            raise
        finally:
            self.stop()

    def stop(self):
        """
        Stop replication service.

        Stop consuming queues and close pika connections.
        """
        self.channel.stop_consuming()
        self.close_connection()
