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
import time
import logging
import sys

# project
from mash.mash_exceptions import MashException
from mash.services.obs.service import OBSImageBuildResultService


def main(event_loop=True):
    """
    mash - obs service application entry point
    """
    obs = None
    try:
        logging.basicConfig()
        log = logging.getLogger('mash')
        log.setLevel(logging.DEBUG)
        # run service, enter main loop
        obs = OBSImageBuildResultService(
            host='localhost', service_exchange='obs',
        )
        while event_loop:
            time.sleep(5)
    except MashException as e:
        # known exception
        log.error('%s: %s', type(e).__name__, format(e))
        sys.exit(1)
    except KeyboardInterrupt:
        log.info('bye')
        sys.exit(0)
    except SystemExit as e:
        # user exception, program aborted by user
        sys.exit(e)
    except Exception:
        # exception we did no expect, show python backtrace
        log.error('Unexpected error:')
        raise
    finally:
        if obs:
            obs.close_connection()
