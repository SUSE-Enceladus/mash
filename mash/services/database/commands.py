# Copyright (c) 2020 SUSE LLC.  All rights reserved.
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

import click

from flask.cli import AppGroup, with_appcontext
from mash.services.database.utils.tokens import prune_expired_tokens

tokens_cli = AppGroup('tokens')


@tokens_cli.command(name='cleanup')
@with_appcontext
def cleanup_tokens():
    try:
        rows_deleted = prune_expired_tokens()
    except Exception as error:
        click.echo(
            'Unable to cleanup tokens: {error}'.format(
                error=error
            )
        )
    else:
        click.echo(
            'Removed {rows_deleted} expired token(s).'.format(
                rows_deleted=rows_deleted
            )
        )
