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


class MashException(Exception):
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


class MashCommandException(MashException):
    """
    Exception raised if an external command called via a Command
    instance has returned with an exit code != 0 or could not
    be called at all.
    """


class MashRabbitConnectionException(MashException):
    """
    Exception raised of connection to RabbitMQ server failed
    """


class MashVersionExpressionException(MashException):
    """
    Exception raised if the version information in a job
    condition description is invalid
    """


class MashConfigException(MashException):
    """
    Exception raised if config file can not be read
    """


class MashCredentialsException(MashException):
    """
    Exception raised if no credentials handler for this cloud provider exists.
    """


class MashConventionsException(MashException):
    """
    Exception raised if no conventions handler for this cloud provider exists.
    """


class MashImageDownloadException(MashException):
    """
    Exception raised if download of image file failed
    """


class MashLogSetupException(MashException):
    """
    Exception raised if log file setup failed
    """


class MashOBSLookupException(MashException):
    """
    Exception raised if a request to OBS failed
    """


class MashUploadException(MashException):
    """
    Exception raised if image upload to csp failed
    """


class MashUploadSetupException(MashException):
    """
    Exception raised if no image upload handler for this cloud provider exists.
    """


class MashLoggerException(MashException):
    """
    Base class to handle all logger service exceptions.
    """


class MashTestingException(MashException):
    """
    Base exception for testing service.
    """


class MashJobCreatorException(MashException):
    """
    Base exception for job creator service.
    """


class MashReplicationException(MashException):
    """
    Base exception for replication service.
    """
