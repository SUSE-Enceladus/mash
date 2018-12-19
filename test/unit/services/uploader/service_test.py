import datetime
import json

from pytest import raises
from pytz import utc
from unittest.mock import patch
from unittest.mock import call
from unittest.mock import Mock

from mash.services.status_levels import (
    FAILED,
    SUCCESS
)

from mash.services.uploader.service import UploadImageService
from mash.services.mash_service import MashService
from mash.utils.json_format import JsonFormat


class TestUploadImageService(object):
    @patch.object(MashService, 'bind_credentials_queue')
    @patch.object(MashService, 'consume_credentials_queue')
    @patch('mash.services.mash_service.MashService.set_logfile')
    @patch('mash.services.uploader.service.BackgroundScheduler')
    @patch.object(UploadImageService, '_process_credentials')
    @patch.object(UploadImageService, '_process_job')
    @patch.object(UploadImageService, '_process_obs_result')
    @patch.object(UploadImageService, 'restart_jobs')
    @patch.object(MashService, '__init__')
    @patch('os.listdir')
    @patch('logging.getLogger')
    @patch('atexit.register')
    def setup(
        self, mock_register, mock_log, mock_listdir,
        mock_MashService, mock_restart_jobs, mock_process_obs_result,
        mock_process_job, mock_process_credentials,
        mock_BackgroundScheduler, mock_set_logfile,
        mock_consume_creds_queue, mock_bind_creds_queue
    ):
        self.job_data_from_preserved_ec2 = {
            'id': '888',
            'last_service': 'uploader',
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
        self.job_data_ec2 = {
            'uploader_job': {
                'id': '123',
                'last_service': 'testing',
                'utctime': 'now',
                'cloud_image_name': 'name-{date}',
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
        self.job_data_azure = {
            'uploader_job': {
                'id': '123',
                'last_service': 'uploader',
                'utctime': 'now',
                'cloud_image_name': 'name',
                'image_description': 'description',
                'provider': 'azure',
                'target_regions': {
                    'westeurope': {
                        'resource_group': 'ms_group',
                        'container': 'ms1container',
                        'storage_account': 'ms1storage',
                        'account': 'test-azure'
                    }
                }
            }
        }
        self.job_data_gce = {
            'uploader_job': {
                'id': '123',
                'last_service': 'uploader',
                'utctime': 'now',
                'cloud_image_name': 'name',
                'image_description': 'description',
                'provider': 'gce',
                'target_regions': {
                    'us-east1': {
                        'account': 'test-gce',
                        'bucket': 'images',
                        'family': 'sles-15'
                    }
                }
            }
        }
        scheduler = Mock()
        mock_BackgroundScheduler.return_value = scheduler
        config = Mock()
        config.get_log_file.return_value = 'logfile'

        self.log = Mock()
        mock_listdir.return_value = ['job']
        mock_MashService.return_value = None

        self.uploader = UploadImageService()
        self.uploader.log = self.log
        self.uploader.config = config
        self.uploader.consume_queue = Mock()
        self.uploader.bind_service_queue = Mock()
        self.uploader.channel = Mock()
        self.uploader.channel.is_open = True
        self.uploader.close_connection = Mock()

        self.uploader.listener_queue = 'listener'
        self.uploader.service_exchange = 'uploader'
        self.uploader.service_queue = 'service'
        self.uploader.job_document_key = 'job_document'
        self.uploader.credentials_queue = 'credentials'
        self.uploader.credentials_response_key = 'response'
        self.uploader.next_service = 'testing'

        self.uploader.post_init()

        mock_set_logfile.assert_called_once_with('logfile')

        mock_BackgroundScheduler.assert_called_once_with(timezone=utc)
        scheduler.start.assert_called_once_with()
        mock_restart_jobs.assert_called_once_with(self.uploader._init_job)

        self.uploader.consume_queue.assert_has_calls([
            call(mock_process_job, 'service'),
            call(mock_process_obs_result, 'listener')
        ])
        self.uploader.channel.start_consuming.assert_called_once_with()
        self.uploader.close_connection.reset_mock()

        self.uploader.channel.start_consuming.side_effect = Exception
        with raises(Exception):
            self.uploader.post_init()
        self.uploader.close_connection.assert_called_once_with()

    @patch.object(MashService, 'persist_job_config')
    def test_init_job(self, mock_persist_job_config):
        self.uploader._init_job(self.job_data_from_preserved_ec2)
        self.uploader._init_job(self.job_data_ec2)
        assert self.uploader.jobs['123'].keys() == \
            self.uploader.jobs['888'].keys()

    def test_job_log(self):
        self.uploader._job_log('815', 'message')
        self.uploader.log.info.assert_called_once_with(
            'message', extra={'job_id': '815'}
        )

    @patch.object(MashService, 'publish_job_result')
    @patch.object(MashService, 'persist_job_config')
    def test_publish_job_result(
        self, mock_persist_job_config, mock_publish_job_result
    ):
        self.uploader._init_job(self.job_data_ec2)
        self.uploader._publish_job_result(
            '123', publish_on_failed_job=True, status=FAILED
        )
        mock_publish_job_result.assert_called_once_with(
            'testing', JsonFormat.json_message(
                {
                    'uploader_result':
                        self.uploader.jobs['123']['uploader_result']
                }
            )
        )
        assert self.uploader.jobs['123']['uploader_result']['status'] == FAILED
        mock_publish_job_result.reset_mock()
        self.uploader._publish_job_result(
            '123', publish_on_failed_job=False, status=FAILED
        )
        assert mock_publish_job_result.called is False

    @patch.object(MashService, 'persist_job_config')
    @patch.object(UploadImageService, '_publish_job_result')
    @patch.object(UploadImageService, '_delete_job')
    def test_send_job_result(
        self, mock_delete_job, mock_publish_job_result, mock_persist_job_config
    ):
        self.uploader._init_job(self.job_data_ec2)
        trigger_info = {
            'job_status': 'success',
            'upload_region': 'region',
            'cloud_image_id': 'image_id'
        }
        self.uploader._send_job_result('123', True, trigger_info)
        mock_publish_job_result.assert_called_once_with(
            '123', publish_on_failed_job=True
        )
        mock_delete_job.assert_called_once_with('123')
        assert self.uploader.jobs['123']['uploader_result']['status'] == SUCCESS
        mock_publish_job_result.reset_mock()
        trigger_info['job_status'] = 'failed'
        self.uploader.jobs['123']['utctime'] = 'always'
        self.uploader._send_job_result('123', True, trigger_info)
        mock_publish_job_result.assert_called_once_with(
            '123', publish_on_failed_job=False
        )
        assert self.uploader.jobs['123']['uploader_result']['status'] == FAILED

    @patch.object(UploadImageService, '_init_job')
    def test_process_job(self, mock_init_job):
        message = Mock()
        data = {
            "uploader_job": {
                "id": "123",
                "last_service": "testing",
                "utctime": "now",
                "cloud_image_name": "name-{date}",
                "image_description": "description",
                "provider": "ec2",
                "target_regions": {
                    "eu-central-1": {
                        "helper_image": "ami-bc5b48d0",
                        "account": "test-aws"
                    }
                }
            }
        }
        message.body = json.dumps(data)

        self.uploader._process_job(message)
        message.ack.assert_called_once_with()
        mock_init_job.assert_called_once_with(self.job_data_ec2)
        message.body = '{"broken_command: "4711"}'
        self.uploader._process_job(message)
        self.uploader.log.error.assert_called_once_with(
            'Error processing job: {"broken_command: "4711"}: '
            'Expecting \':\' delimiter: line 1 column 20 (char 19)'
        )

    @patch.object(UploadImageService, '_handle_obs_image')
    def test_process_obs_result(self, mock_handle_obs_image):
        message = Mock()
        message.body = '{"obs_result": {"id": "123", ' + \
            '"image_file": ["image", "sum"], "status": "success"}}'
        self.uploader._process_obs_result(message)
        message.ack.assert_called_once_with()
        mock_handle_obs_image.assert_called_once_with(
            {
                'obs_result': {
                    'id': '123',
                    'image_file': ['image', 'sum'],
                    'status': 'success'
                }
            }
        )
        message.body = '{"broken_command: "4711"}'
        self.uploader._process_obs_result(message)
        self.uploader.log.error.assert_called_once_with(
            'Invalid obs result: {"broken_command: "4711"}: '
            'Expecting \':\' delimiter: line 1 column 20 (char 19)'
        )

    @patch.object(UploadImageService, '_handle_credentials')
    def test_process_credentials(self, mock_handle_credentials):
        message = Mock()
        message.body = '{"test-aws": {}}'
        self.uploader._process_credentials(message)
        message.ack.assert_called_once_with()
        mock_handle_credentials.assert_called_once_with(
            {'test-aws': {}}
        )
        message.body = '{"broken_command: "4711"}'
        self.uploader._process_credentials(message)
        self.uploader.log.error.assert_called_once_with(
            'Invalid credentials: {"broken_command: "4711"}: '
            'Expecting \':\' delimiter: line 1 column 20 (char 19)'
        )

    @patch.object(UploadImageService, '_job_log')
    @patch.object(UploadImageService, '_schedule_job')
    @patch.object(UploadImageService, '_delete_job')
    @patch.object(UploadImageService, '_publish_job_result')
    @patch.object(UploadImageService, 'publish_credentials_request')
    @patch.object(MashService, 'persist_job_config')
    def test_handle_obs_image(
        self, mock_persist_job_config, mock_publish_credentials_request,
        mock_publish_job_result, mock_delete_job, mock_schedule_job,
        mock_job_log
    ):
        self.uploader._init_job(self.job_data_ec2)
        obs_result = {
            'obs_result': {
                'id': '123',
                'image_file': ['image', 'sum'],
                'status': 'success'
            }
        }
        self.uploader._handle_obs_image(obs_result)
        mock_publish_credentials_request.assert_called_once_with('123')

        self.uploader.jobs['123']['credentials'] = {'test-aws': {}}
        self.uploader._handle_obs_image(obs_result)
        mock_schedule_job.assert_called_once_with('123')

        obs_result['obs_result']['status'] = FAILED
        self.uploader._handle_obs_image(obs_result)
        mock_delete_job.assert_called_once_with('123')
        mock_publish_job_result.assert_called_once_with(
            '123', publish_on_failed_job=True, status='failed'
        )

    @patch.object(UploadImageService, 'decode_credentials')
    @patch.object(UploadImageService, '_schedule_job')
    @patch.object(MashService, 'persist_job_config')
    def test_handle_credentials(
        self, mock_persist_job_config, mock_schedule_job,
        mock_decode_credentials
    ):
        mock_decode_credentials.return_value = '123', {}
        self.uploader._init_job(self.job_data_ec2)
        credentials_result = {'test-aws': {}}
        self.uploader.jobs['123']['system_image_file'] = 'some image'
        self.uploader._handle_credentials(credentials_result)
        mock_schedule_job.assert_called_once_with('123')

    @patch.object(UploadImageService, 'publish_credentials_delete')
    @patch.object(UploadImageService, 'unbind_queue')
    @patch.object(UploadImageService, '_job_log')
    @patch('os.remove')
    def test_delete_job(
        self, mock_os_remove, mock_job_log, mock_unbind_queue,
        mock_publish_creds_delete
    ):
        self.uploader._delete_job('815')
        mock_job_log.assert_called_once_with(
            '815', 'Job does not exist'
        )
        upload_image = [Mock()]
        upload_image[0].job_file = 'job_file'
        self.uploader.jobs = {
            '815': {
                'uploader': upload_image,
                'last_service': 'uploader',
                'job_file': 'job_file'
            }
        }
        mock_job_log.reset_mock()

        self.uploader._delete_job('815')
        mock_publish_creds_delete.assert_called_once_with('815')
        mock_job_log.assert_called_once_with(
            '815', 'Job Deleted'
        )
        mock_os_remove.assert_called_once_with('job_file')
        assert '815' not in self.uploader.jobs
        mock_job_log.reset_mock()

        self.uploader.jobs = {
            '815': {
                'uploader': upload_image,
                'last_service': 'uploader',
                'job_file': 'job_file'
            }
        }
        mock_os_remove.side_effect = Exception('remove_error')
        self.uploader._delete_job('815')
        mock_job_log.assert_called_once_with(
            '815', 'Job deletion failed: remove_error'
        )

    @patch.object(MashService, 'persist_job_config')
    @patch.object(UploadImageService, '_start_job')
    def test_schedule_job_ec2(
        self, mock_start_job, mock_persist_job_config
    ):
        self.uploader._init_job(self.job_data_ec2)
        self.uploader._schedule_job('123')
        self.uploader.scheduler.add_job.assert_called_once_with(
            mock_start_job, args=[
                '123', {
                    'launch_ami': 'ami-bc5b48d0',
                    'account': 'test-aws',
                    'region': 'eu-central-1'
                }, True
            ]
        )

    @patch.object(MashService, 'persist_job_config')
    @patch.object(UploadImageService, '_start_job')
    def test_schedule_job_azure(
        self, mock_start_job, mock_persist_job_config
    ):
        self.uploader._init_job(self.job_data_azure)
        self.uploader._schedule_job('123')
        self.uploader.scheduler.add_job.assert_called_once_with(
            mock_start_job, args=[
                '123', {
                    'resource_group': 'ms_group',
                    'container': 'ms1container',
                    'storage_account': 'ms1storage',
                    'account': 'test-azure',
                    'region': 'westeurope'
                }, True
            ]
        )

    @patch.object(MashService, 'persist_job_config')
    @patch.object(UploadImageService, '_start_job')
    def test_schedule_job_gce(
        self, mock_start_job, mock_persist_job_config
    ):
        self.uploader._init_job(self.job_data_gce)
        self.uploader._schedule_job('123')
        self.uploader.scheduler.add_job.assert_called_once_with(
            mock_start_job, args=[
                '123', {
                    'account': 'test-gce',
                    'bucket': 'images',
                    'family': 'sles-15',
                    'region': 'us-east1'
                }, True
            ]
        )

    @patch('mash.services.uploader.service.UploadImage')
    @patch.object(MashService, 'persist_job_config')
    @patch.object(UploadImageService, '_job_log')
    @patch.object(UploadImageService, '_send_job_result')
    def test_start_job(
        self, mock_send_job_result, mock_job_log, mock_persist_job_config,
        mock_UploadImage
    ):
        mock_persist_job_config.return_value = 'job_file'
        upload_image = Mock()
        mock_UploadImage.return_value = upload_image
        self.uploader._init_job(self.job_data_ec2)
        self.uploader.jobs['123']['credentials'] = {'test-aws': {}}
        self.uploader.jobs['123']['system_image_file'] = 'image'
        self.uploader._start_job(
            '123', {
                'launch_ami': 'ami-bc5b48d0',
                'account': 'test-aws',
                'region': 'eu-central-1'
            }, True
        )
        image_name = 'name-{}'.format(
            datetime.date.today().strftime("%Y%m%d")
        )
        mock_UploadImage.assert_called_once_with(
            '123', 'job_file', 'ec2', {}, image_name, 'description', True, {
                'launch_ami': 'ami-bc5b48d0', 'region': 'eu-central-1',
                'account': 'test-aws'
            }
        )
        upload_image.set_log_handler.assert_called_once_with(
            mock_job_log
        )
        upload_image.set_result_handler.assert_called_once_with(
            mock_send_job_result
        )
        upload_image.set_image_file.assert_called_once_with('image')
        upload_image.upload.assert_called_once_with()
        assert self.uploader.jobs['123']['uploader'] == [upload_image]

    def test_set_upload_date(self):
        name = 'cloud_image_name_{datetime}'
        formatted_name = self.uploader._set_upload_date(name)
        assert name == formatted_name
