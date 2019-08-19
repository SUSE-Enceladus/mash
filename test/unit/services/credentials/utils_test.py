from pytest import raises

from unittest.mock import Mock, patch

from mash.mash_exceptions import MashLogSetupException
from mash.services.credentials.utils import (
    setup_logfile,
    setup_rabbitmq_log_handler,
    add_job_to_queue,
    get_job_file,
    restart_jobs,
    save_job,
    remove_job,
    remove_job_from_queue
)


@patch('mash.services.credentials.utils.logging')
@patch('mash.services.credentials.utils.os')
def test_setup_logfile(mock_os, mock_logging):
    mock_os.path.isdir.return_value = False
    mock_os.path.dirname.return_value = '/file/dir'

    setup_logfile('/file/dir/fake.path')
    mock_os.makedirs.assert_called_once_with('/file/dir')
    mock_logging.FileHandler.assert_called_once_with(
        filename='/file/dir/fake.path', encoding='utf-8'
    )

    mock_os.makedirs.side_effect = Exception('Cannot create dir')
    with raises(MashLogSetupException):
        setup_logfile('fake.path')


@patch('mash.services.credentials.utils.logging')
@patch('mash.services.credentials.utils.RabbitMQHandler')
def test_setup_rabbitmq_log_handler(mock_rabbit, mock_logging):
    handler = Mock()
    formatter = Mock()
    mock_rabbit.return_value = handler
    mock_logging.Formatter.return_value = formatter

    setup_rabbitmq_log_handler('localhost', 'user1', 'pass')

    mock_rabbit.assert_called_once_with(
        host='localhost',
        username='user1',
        password='pass',
        routing_key='mash.logger'
    )
    handler.setFormatter.assert_called_once_with(formatter)


def test_add_job_to_queue():
    jobs = {}
    job_doc = {'id': '1'}

    add_job_to_queue(job_doc, jobs)
    assert '1' in jobs


def test_get_job_file():
    assert get_job_file('/job/dir/', '1') == '/job/dir/job-1.json'


@patch('mash.services.credentials.utils.add_job_to_queue')
@patch('mash.services.credentials.utils.load_json')
@patch('mash.services.credentials.utils.os')
def test_restart_jobs(mock_os, mock_load_json, mock_add_job):
    jobs = {}
    job_doc = {'id': '1', 'job': 'data'}
    mock_os.listdir.return_value = ['job-1.json']
    mock_load_json.return_value = job_doc

    restart_jobs('/jobs/', jobs)
    mock_add_job.assert_called_once_with(job_doc, jobs)


@patch('mash.services.credentials.utils.persist_json')
@patch('mash.services.credentials.utils.get_job_file')
def test_save_job(mock_get_job_file, mock_persist_json):
    mock_get_job_file.return_value = '/jobs/job-1.json'
    save_job({'id': '1', 'job': 'data'}, '/jobs/')
    assert mock_persist_json.call_count == 1


@patch('mash.services.credentials.utils.remove_file')
@patch('mash.services.credentials.utils.get_job_file')
def test_remove_job(mock_get_job_file, mock_remove_file):
    mock_get_job_file.return_value = '/jobs/job-1.json'

    remove_job('/jobs/', '1')
    mock_remove_file.assert_called_once_with('/jobs/job-1.json')


def test_remove_job_from_queue():
    jobs = {'1': {'important': 'stuff'}}
    remove_job_from_queue('1', jobs)
    assert '1' not in jobs
