from pytz import utc
from unittest.mock import patch
from unittest.mock import call
from unittest.mock import Mock

from .test_helper import (
    patch_open,
    context_manager
)

from mash.services.uploader.service import UploadImageService
from mash.services.base_service import BaseService


class TestUploadImageService(object):
    @patch('mash.services.uploader.service.UploaderConfig')
    @patch('mash.services.base_service.BaseService.set_logfile')
    @patch('mash.services.uploader.service.pickle.load')
    @patch('mash.services.uploader.service.BackgroundScheduler')
    @patch.object(UploadImageService, '_control_in')
    @patch.object(UploadImageService, '_send_job_response')
    @patch.object(UploadImageService, '_send_listen_response')
    @patch.object(UploadImageService, 'restart_jobs')
    @patch.object(BaseService, '__init__')
    @patch('os.listdir')
    @patch('logging.getLogger')
    @patch('atexit.register')
    @patch_open
    def setup(
        self, mock_open, mock_register, mock_log, mock_listdir,
        mock_BaseService, mock_restart_jobs, mock_send_listen_response,
        mock_send_job_response, mock_control_in,
        mock_BackgroundScheduler, mock_pickle_load, mock_set_logfile,
        mock_UploaderConfig
    ):
        scheduler = Mock()
        mock_BackgroundScheduler.return_value = scheduler
        upload_image = Mock()
        mock_pickle_load.return_value = upload_image
        config = Mock()
        config.get_log_file.return_value = 'logfile'
        mock_UploaderConfig.return_value = config
        self.log = Mock()
        context = context_manager()
        mock_open.return_value = context.context_manager_mock
        mock_listdir.return_value = ['job']
        mock_BaseService.return_value = None

        self.uploader = UploadImageService()
        self.uploader.log = self.log
        self.uploader.consume_queue = Mock()
        self.uploader.bind_service_queue = Mock()
        self.uploader.channel = Mock()
        self.uploader.channel.is_open = True
        self.uploader.close_connection = Mock()

        self.uploader.post_init()

        mock_set_logfile.assert_called_once_with('logfile')

        mock_open.assert_called_once_with(
            '/var/tmp/mash/uploader_jobs_done/job', 'rb'
        )
        mock_pickle_load.assert_called_once_with(context.file_mock)
        upload_image.set_log_handler.assert_called_once_with(
            mock_send_job_response
        )
        upload_image.set_result_handler.assert_called_once_with(
            mock_send_listen_response
        )

        mock_BackgroundScheduler.assert_called_once_with(timezone=utc)
        scheduler.start.assert_called_once_with()
        mock_restart_jobs.assert_called_once_with(self.uploader._schedule_job)

        self.uploader.consume_queue.assert_called_once_with(
            mock_control_in,
            self.uploader.bind_service_queue.return_value
        )
        self.uploader.channel.start_consuming.assert_called_once_with()

        self.uploader.channel.start_consuming.side_effect = Exception
        self.uploader.post_init()
        self.uploader.channel.stop_consuming.assert_called_once_with()
        self.uploader.close_connection.assert_called_once_with()
        self.uploader.channel.reset_mock()

        mock_pickle_load.side_effect = Exception('error')
        self.uploader.post_init()
        self.log.error.assert_called_once_with(
            'Could not reload job: error'
        )
        self.log.reset_mock()

    def test_send_job_response(self):
        self.uploader._send_job_response('815', {})
        self.uploader.log.info.assert_called_once_with(
            {}, extra={'job_id': '815'}
        )

    @patch.object(BaseService, 'bind_listener_queue')
    @patch.object(BaseService, 'publish_listener_message')
    @patch.object(UploadImageService, '_send_control_response')
    def test_send_listen_response(
        self, mock_send_control_response,
        mock_publish_listener_message, mock_bind_listener_queue
    ):
        self.uploader.clients['815'] = Mock()
        self.uploader._send_listen_response('815', {})
        mock_bind_listener_queue.assert_called_once_with('815')
        mock_publish_listener_message.assert_called_once_with('815', '{}')
        assert '815' not in self.uploader.clients
        self.uploader.clients['815'] = Mock()
        mock_bind_listener_queue.side_effect = Exception
        self.uploader._send_listen_response('815', {})
        assert '815' in self.uploader.clients

    def test_send_control_response_local(self):
        result = {
            'message': 'message',
            'ok': False
        }
        self.uploader._send_control_response(result, '4711')
        self.uploader.log.error.assert_called_once_with(
            'message',
            extra={'job_id': '4711'}
        )

    def test_send_control_response_public(self):
        result = {
            'message': 'message',
            'ok': True
        }
        self.uploader._send_control_response(result)
        self.uploader.log.info.assert_called_once_with(
            'message',
            extra={}
        )

    @patch.object(UploadImageService, '_delete_job')
    @patch.object(UploadImageService, '_add_job')
    @patch.object(UploadImageService, '_add_to_listener')
    @patch.object(UploadImageService, '_send_control_response')
    def test_control_in(
        self, mock_send_control_response, mock_add_to_listener,
        mock_add_job, mock_delete_job
    ):
        message = Mock()
        message.body = '{"uploadjob": {"id": "123", ' + \
            '"utctime": "now", "cloud_image_name": "name", ' + \
            '"cloud_image_description": "description", ' + \
            '"ec2": {"launch_ami": "ami-bc5b48d0", "region": "eu-central-1"}}}'
        self.uploader._control_in(message)
        message.ack.assert_called_once_with()
        mock_add_job.assert_called_once_with(
            {
                'uploadjob': {
                    'id': '123',
                    'utctime': 'now',
                    'cloud_image_name': 'name',
                    'cloud_image_description': 'description',
                    'ec2': {
                        'launch_ami': 'ami-bc5b48d0',
                        'region': 'eu-central-1'
                    }
                }
            }
        )
        message.body = '{"uploadjob_listen": "4711"}'
        self.uploader._control_in(message)
        mock_add_to_listener.assert_called_once_with(
            '4711'
        )
        message.body = '{"uploadjob_delete": "4711"}'
        self.uploader._control_in(message)
        mock_delete_job.assert_called_once_with(
            '4711'
        )
        mock_send_control_response.reset_mock()
        message.body = '{"unknown_command": "4711"}'
        self.uploader._control_in(message)
        message.body = 'foo'
        self.uploader._control_in(message)
        assert mock_send_control_response.call_args_list == [
            call(
                {
                    'message':
                        "No idea what to do with: {'unknown_command': '4711'}",
                    'ok': False
                },
                None
            ),
            call(
                {
                    'message':
                        'JSON:deserialize error: foo : ' +
                        'Expecting value: line 1 column 1 (char 0)',
                    'ok': False
                }
            )
        ]

    def test_add_to_listener(self):
        assert self.uploader._add_to_listener('815') == {
            'message': 'Job does not exist, can not add to listen pipeline',
            'ok': False
        }
        job = Mock()
        self.uploader.jobs = {'815': job}
        assert self.uploader._add_to_listener('815') == {
            'message': 'Job now in listen pipeline', 'ok': True
        }
        job.call_result_handler.assert_called_once_with()

    @patch.object(UploadImageService, 'persist_job_config')
    @patch.object(UploadImageService, '_validate_job_description')
    @patch.object(UploadImageService, '_schedule_job')
    @patch_open
    def test_add_job(
        self, mock_open,
        mock_schedule_job, mock_validate_job_description,
        mock_persist_job_config
    ):
        job_data = {
            'uploadjob': {
                'id': '123',
                'utctime': 'now',
                'cloud_image_name': 'name',
                'cloud_image_description': 'description',
                'ec2': {
                    'launch_ami': 'ami-bc5b48d0',
                    'region': 'eu-central-1'
                }
            }
        }
        job_info = {
            'ok': False
        }
        mock_validate_job_description.return_value = job_info
        assert self.uploader._add_job(job_data) == job_info
        job_info = {
            'ok': True
        }
        mock_validate_job_description.return_value = job_info
        self.uploader._add_job(job_data)
        mock_schedule_job.assert_called_once_with(job_data['uploadjob'])
        assert mock_validate_job_description.call_args_list == [
            call(job_data), call(job_data)
        ]
        mock_persist_job_config.assert_called_once_with(job_data['uploadjob'])

    @patch('os.remove')
    def test_delete_job(self, mock_os_remove):
        assert self.uploader._delete_job('815') == {
            'message': 'Job does not exist, can not delete it', 'ok': False
        }
        upload_image = Mock()
        upload_image.job_file = 'job_file'
        self.uploader.clients = {'815': None}
        self.uploader.jobs = {'815': upload_image}
        assert self.uploader._delete_job('815') == {
            'message': 'Job Deleted', 'ok': True
        }
        mock_os_remove.assert_called_once_with('job_file')
        upload_image.stop.assert_called_once_with()
        assert '815' not in self.uploader.clients
        assert '815' not in self.uploader.jobs
        self.uploader.jobs = {'815': upload_image}
        mock_os_remove.side_effect = Exception('remove_error')
        assert self.uploader._delete_job('815') == {
            'message': 'Job deletion failed: remove_error', 'ok': False
        }

    @patch('mash.services.uploader.service.dateutil.parser.parse')
    def test_validate_job_description(self, mock_dateutil_parse):
        mock_dateutil_parse.side_effect = Exception('mytime')
        job_data = {}
        assert self.uploader._validate_job_description(job_data) == {
            'message': 'Invalid job: no uploadjob', 'ok': False
        }
        job_data = {"uploadjob": {}}
        assert self.uploader._validate_job_description(job_data) == {
            'message': 'Invalid job: no job id', 'ok': False
        }
        job_data = {"uploadjob": {"id": "123"}}
        assert self.uploader._validate_job_description(job_data) == {
            'message': 'Invalid job: no cloud image name', 'ok': False
        }
        job_data = {"uploadjob": {"id": "123", "cloud_image_name": "foo"}}
        assert self.uploader._validate_job_description(job_data) == {
            'message': 'Invalid job: no cloud image description', 'ok': False
        }
        job_data = {
            "uploadjob": {
                "id": "123",
                "cloud_image_name": "foo",
                "cloud_image_description": "bar"
            }
        }
        assert self.uploader._validate_job_description(job_data) == {
            'message': 'Invalid job: no EC2 parameter record', 'ok': False
        }
        job_data = {
            "uploadjob": {
                "id": "123",
                "cloud_image_name": "foo",
                "cloud_image_description": "bar",
                "ec2": {}
            }
        }
        assert self.uploader._validate_job_description(job_data) == {
            'message': 'Invalid job: no time given', 'ok': False
        }
        job_data = {
            "uploadjob": {
                "id": "123",
                "cloud_image_name": "foo",
                "cloud_image_description": "bar",
                "utctime": "mytime",
                "ec2": {}
            }
        }
        assert self.uploader._validate_job_description(job_data) == {
            'message': 'Invalid job time: mytime', 'ok': False
        }
        mock_dateutil_parse.side_effect = None
        assert self.uploader._validate_job_description(job_data) == {
            'message': 'OK', 'ok': True
        }
        self.uploader.jobs = {'123': None}
        assert self.uploader._validate_job_description(job_data) == {
            'message': 'Job already exists', 'ok': False
        }

    @patch.object(UploadImageService, '_start_job')
    def test_schedule_job_now(self, mock_start_job):
        data = {
            "cloud_image_description": "My Image",
            "cloud_image_name": "ms_image",
            "ec2": {
                "launch_ami": "ami-bc5b48d0",
                "region": "eu-central-1"
            },
            "id": "123",
            "utctime": "now"
        }
        self.uploader._schedule_job(data)
        self.uploader.scheduler.add_job.assert_called_once_with(
            mock_start_job, args=[
                {
                    'id': '123',
                    'cloud_image_name': 'ms_image',
                    'cloud_image_description': 'My Image',
                    'utctime': 'now',
                    'ec2': {
                        'region': 'eu-central-1',
                        'launch_ami': 'ami-bc5b48d0'
                    }
                }, False
            ]
        )

    @patch.object(UploadImageService, '_start_job')
    def test_schedule_job_always(self, mock_start_job):
        data = {
            "cloud_image_description": "a",
            "cloud_image_name": "b",
            "ec2": {},
            "id": "123",
            "utctime": "always"
        }
        self.uploader._schedule_job(data)
        self.uploader.scheduler.add_job.assert_called_once_with(
            mock_start_job, args=[
                {
                    'id': '123',
                    'cloud_image_name': 'b',
                    'cloud_image_description': 'a',
                    'utctime': 'always',
                    'ec2': {}
                }, True
            ]
        )

    @patch.object(UploadImageService, '_start_job')
    def test_schedule_job_at_time(self, mock_start_job):
        data = {
            "cloud_image_description": "a",
            "cloud_image_name": "b",
            "ec2": {},
            "id": "123",
            "utctime": "Wed Oct 11 17:50:26 UTC 2017"
        }
        self.uploader._schedule_job(data)
        self.uploader.scheduler.add_job.assert_called_once_with(
            mock_start_job, 'date', timezone='utc', args=[
                {
                    'id': '123',
                    'cloud_image_name': 'b',
                    'cloud_image_description': 'a',
                    'utctime': 'Wed Oct 11 17:50:26 UTC 2017',
                    'ec2': {}
                }, False
            ], run_date='2017-10-11T17:50:26+00:00'
        )

    @patch('mash.services.uploader.service.UploadImage')
    @patch.object(UploadImageService, '_send_job_response')
    @patch.object(UploadImageService, '_send_listen_response')
    def test_start_job(
        self, mock_send_listen_response, mock_send_job_response,
        mock_UploadImage
    ):
        upload_image = Mock()
        mock_UploadImage.return_value = upload_image
        job = {
            'id': '123',
            'cloud_image_name': 'b',
            'cloud_image_description': 'a',
            'job_file': 'job_file',
            'utctime': 'now|always',
            'ec2': {}
        }
        self.uploader._start_job(job, True)
        mock_UploadImage.assert_called_once_with(
            '123', 'job_file', 'ec2', 'b', 'a',
            service_lookup_timeout_sec=None,
            custom_uploader_args={}
        )
        upload_image.set_log_handler.assert_called_once_with(
            mock_send_job_response
        )
        upload_image.set_result_handler.assert_called_once_with(
            mock_send_listen_response
        )
        upload_image.upload.assert_called_once_with(oneshot=False)

        upload_image.reset_mock()
        mock_UploadImage.reset_mock()
        self.uploader._start_job(job, False)
        mock_UploadImage.assert_called_once_with(
            '123', 'job_file', 'ec2', 'b', 'a',
            service_lookup_timeout_sec=10,
            custom_uploader_args={}
        )
        upload_image.upload.assert_called_once_with(oneshot=True)
