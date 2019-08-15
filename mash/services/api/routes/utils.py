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

import sys

from amqpstorm import Connection

from mash.services.api import app

module = sys.modules[__name__]

connection = None
channel = None


def connect():
    module.connection = Connection(
        app.config['AMQP_HOST'],
        app.config['AMQP_USER'],
        app.config['AMQP_PASS'],
        kwargs={'heartbeat': 600}
    )
    module.channel = connection.channel()
    channel.confirm_deliveries()


def publish(exchange, routing_key, message):
    """
    Publish message to the provided exchange with the routing key.
    """
    if not channel or channel.is_closed:
        connect()

    channel.basic.publish(
        body=message,
        routing_key=routing_key,
        exchange=exchange,
        properties={
            'content_type': 'application/json',
            'delivery_mode': 2
        },
        mandatory=True
    )
