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

import logging
import sys

# project
from mash.mash_exceptions import MashException
from mash.services.testing.service import TestingService


def main():
    """
    mash - obs service application entry point
    """
    logging.basicConfig()
    log = logging.getLogger('mash')
    log.setLevel(logging.INFO)

    testing = None
    try:
        # run service, enter main loop
        testing = TestingService(
            host='localhost', service_exchange='testing'
        )
        testing.start()
    except MashException as e:
        # known exception
        log.error('%s: %s', type(e).__name__, format(e))
        sys.exit(1)
    except KeyboardInterrupt:
        log.info('Bye')
        sys.exit(0)
    except SystemExit as e:
        # user exception, program aborted by user
        sys.exit(e)
    except Exception:
        # exception we did no expect, show python backtrace
        log.error('Unexpected error:')
        raise
    finally:
        if testing:
            testing.stop()
