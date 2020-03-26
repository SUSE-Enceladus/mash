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

import smtplib

from email.message import EmailMessage


class EmailNotification(object):
    """
    For sending job notification emails.
    """

    def __init__(self, host, port, user, password, ssl, log_callback=None):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.log_callback = log_callback

        if ssl:
            self.smtp_class = smtplib.SMTP_SSL
        else:
            self.smtp_class = smtplib.SMTP

    def _create_email_message(self, msg, subject, to_email):
        """
        Return notification email message object.
        """
        email_msg = EmailMessage()

        email_msg['Subject'] = subject
        email_msg['From'] = self.user
        email_msg['To'] = to_email

        email_msg.set_content(msg)

        return email_msg

    def _send_email(self, email_msg):
        """
        Send email message using smtp server.

        :param email_msg:  email.message.EmailMessage
        """
        try:
            smtp_server = self.smtp_class(self.host, self.port)

            if self.user and self.password:
                smtp_server.login(self.user, self.password)

            smtp_server.send_message(email_msg)
        except Exception as error:
            if self.log_callback:
                self.log_callback.warning(
                    'Unable to send notification email: {0}'.format(error)
                )

    def send_notification(self, content, subject, notification_email):
        """
        Send job notification email.
        """
        email_msg = self._create_email_message(content, subject, notification_email)
        self._send_email(email_msg)
