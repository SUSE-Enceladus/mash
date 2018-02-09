from pytz import utc
from unittest.mock import patch
from unittest.mock import call
from unittest.mock import Mock

from test.unit.test_helper import (
    patch_open
)

from mash.services.uploader.service import UploadImageService
from mash.services.base_service import BaseService
from mash.utils.json_format import JsonFormat


class TestUploadImageService(object):
    @patch('mash.services.uploader.service.UploaderConfig')
    @patch('mash.services.base_service.BaseService.set_logfile')
    @patch('mash.services.uploader.service.BackgroundScheduler')
    @patch.object(UploadImageService, '_process_message')
    @patch.object(UploadImageService, 'restart_jobs')
    @patch.object(BaseService, '__init__')
    @patch('os.listdir')
    @patch('logging.getLogger')
    @patch('atexit.register')
    def setup(
        self, mock_register, mock_log, mock_listdir,
        mock_BaseService, mock_restart_jobs, mock_process_message,
        mock_BackgroundScheduler, mock_set_logfile,
        mock_UploaderConfig
    ):
        scheduler = Mock()
        mock_BackgroundScheduler.return_value = scheduler
        config = Mock()
        config.get_log_file.return_value = 'logfile'
        mock_UploaderConfig.return_value = config
        self.log = Mock()
        mock_listdir.return_value = ['job']
        mock_BaseService.return_value = None

        self.uploader = UploadImageService()
        self.uploader.log = self.log
        self.uploader.consume_queue = Mock()
        self.uploader.bind_service_queue = Mock()
        self.uploader.channel = Mock()
        self.uploader.channel.is_open = True
        self.uploader.close_connection = Mock()

        self.uploader.service_exchange = 'uploader'
        self.uploader.service_queue = 'service'
        self.uploader.job_document_key = 'job_document'
        self.uploader.credentials_queue = 'credentials'

        self.uploader.post_init()

        mock_set_logfile.assert_called_once_with('logfile')

        mock_BackgroundScheduler.assert_called_once_with(timezone=utc)
        scheduler.start.assert_called_once_with()
        mock_restart_jobs.assert_called_once_with(self.uploader._schedule_job)

        self.uploader.consume_queue.assert_called_once_with(
            mock_process_message, 'service'
        )
        self.uploader.channel.start_consuming.assert_called_once_with()

        self.uploader.channel.start_consuming.side_effect = Exception
        self.uploader.post_init()
        self.uploader.channel.stop_consuming.assert_called_once_with()
        self.uploader.close_connection.assert_called_once_with()

    def test_send_job_response(self):
        self.uploader._send_job_response('815', {})
        self.uploader.log.info.assert_called_once_with(
            {}, extra={'job_id': '815'}
        )

    @patch.object(BaseService, 'publish_job_result')
    @patch.object(UploadImageService, '_delete_job')
    def test_send_job_result(
        self, mock_delete_job, mock_publish_job_result
    ):
        self.uploader.jobs['815'] = {
            'nonstop': False,
            'uploader_result': {
                'status': None,
                'source_regions': {}
            }
        }
        trigger_info = {
            'job_status': 'success',
            'upload_region': 'region',
            'cloud_image_id': 'image_id'
        }
        self.uploader._send_job_result('815', True, trigger_info)
        mock_publish_job_result.assert_called_once_with(
            'testing', '815', JsonFormat.json_message(
                self.uploader.jobs['815']['uploader_result']
            )
        )
        mock_delete_job.assert_called_once_with('815')

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

    @patch.object(UploadImageService, '_send_control_response')
    def test_process_message_for_service_data(
        self, mock_send_control_response
    ):
        message = Mock()
        message.method = {'routing_key': '123'}
        message.body = '{"image_file": ["image", "sum"], "status": "success"}'
        self.uploader._process_message(message)
        assert self.uploader.jobs['123']['system_image_file'] == 'image'
        message.body = '{"credentials": {}}'
        self.uploader._process_message(message)
        assert self.uploader.jobs['123']['credentials'] == {}
        assert self.uploader.jobs['123']['ready'] is True

    @patch.object(UploadImageService, '_add_job')
    @patch.object(UploadImageService, '_send_control_response')
    def test_process_message_for_job_documents(
        self, mock_send_control_response, mock_add_job
    ):
        message = Mock()
        message.method = {'routing_key': 'job_document'}
        message.body = '{"uploader_job": {"id": "123", ' + \
            '"utctime": "now", "cloud_image_name": "name", ' + \
            '"image_description": "description", ' + \
            '"provider": "ec2", ' +\
            '"target_regions": {"eu-central-1": { ' +\
            '"helper_image": "ami-bc5b48d0", "account": "test-aws"}}}}'
        self.uploader._process_message(message)
        message.ack.assert_called_once_with()
        mock_add_job.assert_called_once_with(
            {
                'uploader_job': {
                    'id': '123',
                    'utctime': 'now',
                    'cloud_image_name': 'name',
                    'image_description': 'description',
                    'provider': 'ec2',
                    'target_regions': {
                        'eu-central-1': {
                            'helper_image': 'ami-bc5b48d0',
                            'account': 'test-aws'
                        }
                    }
                }
            }
        )
        mock_send_control_response.reset_mock()
        message.body = '{"unknown_command": "4711"}'
        self.uploader._process_message(message)
        message.body = 'foo'
        self.uploader._process_message(message)
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
            "uploader_job": {
                "id": "123",
                "cloud_image_name": "name",
                "image_description": "description",
                "provider": "ec2",
                "target_regions": {
                    "eu-central-1": {
                        "helper_image": "ami-bc5b48d0",
                        "account": "test-aws"
                    }
                },
                "utctime": "now"
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
        mock_schedule_job.assert_called_once_with(job_data['uploader_job'])
        assert mock_validate_job_description.call_args_list == [
            call(job_data), call(job_data)
        ]
        mock_persist_job_config.assert_called_once_with(
            job_data['uploader_job']
        )

    @patch('os.remove')
    def test_delete_job(self, mock_os_remove):
        assert self.uploader._delete_job('815') == {
            'message': 'Job does not exist, can not delete it', 'ok': False
        }
        upload_image = [Mock()]
        upload_image[0].job_file = 'job_file'
        self.uploader.jobs = {'815': {'uploader': upload_image}}
        assert self.uploader._delete_job('815') == {
            'message': 'Job Deleted', 'ok': True
        }
        mock_os_remove.assert_called_once_with('job_file')
        assert '815' not in self.uploader.jobs
        self.uploader.jobs = {'815': {'uploader': upload_image}}
        mock_os_remove.side_effect = Exception('remove_error')
        assert self.uploader._delete_job('815') == {
            'message': 'Job deletion failed: remove_error', 'ok': False
        }

    @patch('mash.services.uploader.service.dateutil.parser.parse')
    def test_validate_job_description(self, mock_dateutil_parse):
        mock_dateutil_parse.side_effect = Exception('mytime')
        job_data = {}
        assert self.uploader._validate_job_description(job_data) == {
            'message': 'Invalid job: no uploader_job', 'ok': False
        }
        job_data = {"uploader_job": {}}
        assert self.uploader._validate_job_description(job_data) == {
            'message': 'Invalid job: no job id', 'ok': False
        }
        job_data = {"uploader_job": {"id": "123"}}
        assert self.uploader._validate_job_description(job_data) == {
            'message': 'Invalid job: no cloud image name', 'ok': False
        }
        job_data = {"uploader_job": {"id": "123", "cloud_image_name": "foo"}}
        assert self.uploader._validate_job_description(job_data) == {
            'message': 'Invalid job: no cloud image description', 'ok': False
        }
        job_data = {
            "uploader_job": {
                "id": "123",
                "cloud_image_name": "foo",
                "image_description": "bar"
            }
        }
        assert self.uploader._validate_job_description(job_data) == {
            'message': 'Invalid job: no cloud provider', 'ok': False
        }
        job_data = {
            "uploader_job": {
                "id": "123",
                "cloud_image_name": "foo",
                "image_description": "bar",
                "provider": "EC2"
            }
        }
        assert self.uploader._validate_job_description(job_data) == {
            'message': 'Invalid job: EC2 provider not supported', 'ok': False
        }
        job_data = {
            "uploader_job": {
                "id": "123",
                "cloud_image_name": "foo",
                "image_description": "bar",
                "provider": "ec2"
            }
        }
        assert self.uploader._validate_job_description(job_data) == {
            'message': 'Invalid job: no target regions record', 'ok': False
        }
        job_data = {
            "uploader_job": {
                "id": "123",
                "cloud_image_name": "foo",
                "image_description": "bar",
                "provider": "ec2",
                "target_regions": {
                    "us-east-1": {
                        "helper_image": "ami-bc5b48d0",
                        "account": "test-aws"
                    }
                }
            }
        }
        assert self.uploader._validate_job_description(job_data) == {
            'message': 'Invalid job: no time given', 'ok': False
        }
        job_data = {
            "uploader_job": {
                "id": "123",
                "cloud_image_name": "foo",
                "image_description": "bar",
                "provider": "ec2",
                "target_regions": {
                    "us-east-1": {
                        "helper_image": "ami-bc5b48d0",
                        "account": "test-aws"
                    }
                },
                "utctime": "mytime"
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

    @patch.object(UploadImageService, 'bind_queue')
    @patch.object(UploadImageService, '_start_job')
    def test_schedule_job(self, mock_start_job, mock_bind_queue):
        job = {
            'id': '123',
            'cloud_image_name': 'b',
            'image_description': 'a',
            'job_file': 'job_file',
            'utctime': 'Wed Oct 11 17:50:26 UTC 2017',
            'provider': 'ec2',
            'target_regions': {
                'us-east-1': {
                    'helper_image': 'ami-bc5b48d0',
                    'account': 'test-aws'
                }
            }
        }
        self.uploader.config = Mock()
        uploader_args = self.uploader._get_uploader_arguments_per_region(job)
        self.uploader._schedule_job(job)
        self.uploader.scheduler.add_job.assert_called_once_with(
            mock_start_job, 'date', args=[job, False, uploader_args[0], True],
            run_date='2017-10-11T17:50:26+00:00',
            timezone='utc'
        )
        self.uploader.scheduler.add_job.reset_mock()
        job['utctime'] = 'always'
        self.uploader._schedule_job(job)
        self.uploader.scheduler.add_job.assert_called_once_with(
            mock_start_job, args=[job, True, uploader_args[0], True]
        )
        self.uploader.scheduler.add_job.reset_mock()
        mock_bind_queue.reset_mock()
        job['utctime'] = 'now'
        self.uploader._schedule_job(job)
        self.uploader.scheduler.add_job.assert_called_once_with(
            mock_start_job, args=[job, False, uploader_args[0], True]
        )
        assert mock_bind_queue.call_args_list == [
            call('uploader', '123', 'service'),
            call('credentials', '123', 'ec2')
        ]

    @patch('mash.services.uploader.service.UploadImage')
    @patch.object(UploadImageService, '_send_job_response')
    @patch.object(UploadImageService, '_image_already_uploading')
    @patch.object(UploadImageService, '_send_job_result')
    @patch.object(UploadImageService, '_wait_until_ready')
    @patch('mash.services.uploader.service.time.sleep')
    def test_start_job(
        self, mock_sleep, mock_wait_until_ready,
        mock_send_job_result, mock_image_already_uploading,
        mock_send_job_response, mock_UploadImage
    ):
        upload_image = Mock()
        uploader = self.uploader

        def done_after_one_iteration(self):
            uploader.jobs['123']['ready'] = False

        mock_image_already_uploading.return_value = False
        mock_UploadImage.return_value = upload_image
        job = {
            'id': '123',
            'cloud_image_name': 'b',
            'image_description': 'a',
            'job_file': 'job_file',
            'utctime': 'now',
            'provider': 'ec2',
            'target_regions': {
                'us-east-1': {
                    'helper_image': 'ami-bc5b48d0',
                    'account': 'test-aws'
                }
            }
        }
        uploader.jobs['123'] = {
            'ready': True,
            'uploader': [],
            'credentials': {'test-aws': {}},
            'system_image_file': 'image'
        }
        uploader_args = uploader._get_uploader_arguments_per_region(job)
        uploader._start_job(job, False, uploader_args[0], False)

        mock_wait_until_ready.assert_called_once_with('123')

        mock_UploadImage.assert_called_once_with(
            '123', 'job_file', False, 'ec2', {}, 'b', 'a',
            False, {
                'launch_ami': 'ami-bc5b48d0', 'region': 'us-east-1',
                'account': 'test-aws'
            }
        )
        upload_image.set_log_handler.assert_called_once_with(
            mock_send_job_response
        )
        upload_image.set_result_handler.assert_called_once_with(
            mock_send_job_result
        )
        upload_image.set_image_file.assert_called_once_with('image')
        upload_image.upload.assert_called_once_with()

        mock_UploadImage.reset_mock()

        mock_send_job_response.reset_mock()
        mock_sleep.side_effect = done_after_one_iteration
        uploader._start_job(job, True, uploader_args[0], False)
        mock_UploadImage.assert_called_once_with(
            '123', 'job_file', True, 'ec2', {}, 'b', 'a',
            False, {
                'launch_ami': 'ami-bc5b48d0', 'region': 'us-east-1',
                'account': 'test-aws'
            }
        )
        assert mock_send_job_response.call_args_list == [
            call(
                '123', 'Region [us-east-1]: Waiting for image/credentials data'
            ),
            call(
                '123', 'Waiting 30sec before next try...'
            )
        ]
        mock_sleep.assert_called_once_with(30)

    @patch('mash.services.uploader.service.time.sleep')
    def test_wait_until_ready(self, mock_sleep):
        uploader = self.uploader
        uploader.jobs = {'123': {}}

        def done_after_one_iteration(self):
            uploader.jobs['123']['ready'] = True

        mock_sleep.side_effect = done_after_one_iteration
        uploader._wait_until_ready('123')
        mock_sleep.assert_called_once_with(1)

    def test_image_already_uploading(self):
        uploader = Mock()
        self.uploader.jobs = {'123': {}}
        assert self.uploader._image_already_uploading('123', uploader) is False
        uploader.system_image_file = 'image_A'
        self.uploader.jobs['123']['system_image_file'] = 'image_B'
        assert self.uploader._image_already_uploading('123', uploader) is False
        uploader.system_image_file = \
            self.uploader.jobs['123']['system_image_file']
        assert self.uploader._image_already_uploading('123', uploader) is True
