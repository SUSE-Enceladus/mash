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


class MashError(Exception):
    """
    Base class to handle all known exceptions.

    Specific exceptions are implemented as sub classes of MashError

    Attributes

    * :attr:`message`
        Exception message text
    """
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return format(self.message)


class MashPikaConnectionError(MashError):
    """
    Exception raised of connection to RabbitMQ server failed
    """


class MashVersionExpressionError(MashError):
    """
    Exception raised if the version information in a job
    condition description is invalid
    """


class MashConfigError(MashError):
    """
    Exception raised if config file can not be read
    """


class MashImageDownloadError(MashError):
    """
    Exception raised if download of image file failed
    """


class MashLogSetupError(MashError):
    """
    Exception raised if log file setup failed
    """


class MashOBSLookupError(MashError):
    """
    Exception raised if a request to OBS failed
    """


class MashOBSResultError(MashError):
    """
    Exception raised if the OBS result request failed
    """


class MashJobRetireError(MashError):
    """
    Exception raised if the pickle dump of an OBSImageBuildResult failed
    """
