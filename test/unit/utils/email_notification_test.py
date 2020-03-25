from unittest.mock import patch, MagicMock

from mash.utils.email_notification import EmailNotification


@patch('mash.utils.email_notification.smtplib')
def test_send_email_notification(mock_smtp):
    to = 'test@fake.com'
    content = 'Some job info in an email'
    host = 'localhost'
    port = 25
    subject = '[MASH] Job Status Update'

    log = MagicMock()
    smtp_server = MagicMock()

    mock_smtp.SMTP_SSL.return_value = smtp_server
    mock_smtp.SMTP.return_value = smtp_server

    notif_class = EmailNotification(
        host,
        port,
        to,
        None,
        False,
        log_callback=log
    )

    # Send email without SSL
    notif_class.send_notification(content, subject, to)
    assert smtp_server.send_message.call_count == 1

    notif_class = EmailNotification(
        host,
        port,
        to,
        'super.secret',
        True,
        log_callback=log
    )

    # Send email with SSL
    notif_class.send_notification(content, subject, to)
    assert smtp_server.send_message.call_count == 2

    # Send error
    smtp_server.send_message.side_effect = Exception('Broke!')
    notif_class.send_notification(content, subject, to)

    log.warning.assert_called_once_with(
        'Unable to send notification email: Broke!'
    )
