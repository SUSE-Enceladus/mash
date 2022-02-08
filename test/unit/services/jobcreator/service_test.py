import json

from pytest import raises
from unittest.mock import MagicMock, Mock, patch

from mash.services.mash_service import MashService
from mash.services.jobcreator.service import JobCreatorService
from mash.utils.json_format import JsonFormat


class TestJobCreatorService(object):

    @patch.object(MashService, '__init__')
    def setup_method(self, method, mock_base_init):
        services = [
            'obs', 'upload', 'create', 'test', 'raw_image_upload',
            'replicate', 'publish', 'deprecate'
        ]
        mock_base_init.return_value = None
        self.config = Mock()
        self.config.config_data = None
        self.config.get_service_names.return_value = services
        self.channel = Mock()
        self.channel.basic_ack.return_value = None

        self.tag = Mock()
        self.method = {'delivery_tag': self.tag}

        self.message = MagicMock(
            channel=self.channel,
            method=self.method,
        )

        self.jobcreator = JobCreatorService()

        self.jobcreator.log = Mock()
        self.jobcreator.service_exchange = 'jobcreator'
        self.jobcreator.service_queue = 'service'
        self.jobcreator.job_document_key = 'job_document'
        self.jobcreator.services = services

    @patch('mash.services.jobcreator.service.EmailNotification')
    @patch('mash.services.jobcreator.service.setup_logfile')
    @patch.object(JobCreatorService, 'start')
    @patch.object(JobCreatorService, 'bind_queue')
    def test_jobcreator_post_init(
        self, mock_bind_queue,
        mock_start, mock_setup_logfile,
        mock_email_notif
    ):
        self.jobcreator.config = self.config
        self.config.get_log_file.return_value = \
            '/var/log/mash/job_creator_service.log'

        self.jobcreator.post_init()

        self.config.get_log_file.assert_called_once_with('jobcreator')
        mock_setup_logfile.assert_called_once_with(
            '/var/log/mash/job_creator_service.log'
        )

        mock_bind_queue.call_count == 9
        mock_start.assert_called_once_with()
        assert mock_email_notif.call_count == 1

    @patch.object(JobCreatorService, '_publish')
    def test_jobcreator_handle_service_message(self, mock_publish):
        def check_base_attrs(job_data, cloud=True):
            assert job_data['id'] == '12345678-1234-1234-1234-123456789012'
            assert job_data['utctime'] == 'now'
            assert job_data['last_service'] == 'deprecate'
            assert job_data['notification_email'] == 'test@fake.com'

            if cloud:
                assert job_data['cloud'] == 'ec2'

        with open('test/data/job.json', 'r') as job_doc:
            job = json.load(job_doc)

        job['target_account_info'] = {
            'us-gov-west-1': {
                'account': 'test-aws-gov',
                'target_regions': ['us-gov-west-1'],
                'helper_image': 'ami-c2b5d7e1',
                'subnet': 'subnet-12345',
                'partition': 'aws-us-gov'
            },
            'ap-northeast-1': {
                'account': 'test-aws',
                'target_regions': [
                    'ap-northeast-1', 'ap-northeast-2', 'ap-northeast-3'
                ],
                'helper_image': 'ami-383c1956',
                'subnet': 'subnet-54321',
                'partition': 'aws'
            }
        }
        del job['cloud_accounts']
        del job['cloud_groups']
        job['notification_email'] = 'test@fake.com'

        message = MagicMock()
        message.body = JsonFormat.json_message(job)
        self.jobcreator._handle_service_message(message)

        # OBS Job Doc

        data = json.loads(mock_publish.mock_calls[0][1][2])['obs_job']
        check_base_attrs(data, cloud=False)
        assert data['cloud_architecture'] == 'aarch64'
        assert data['download_url'] == \
            'http://download.opensuse.org/repositories/Cloud:Tools/images'
        assert data['image'] == 'test_image_oem'
        assert data['profile'] == 'Proxy'
        assert data['conditions_wait_time'] == 500

        for condition in data['conditions']:
            if 'package_name' in condition:
                assert condition['release'] == '1.1'
                assert condition['package_name'] == 'openssl'
                assert condition['version'] == '13.4.3'
            else:
                assert condition['version'] == '8.13.21'

        # Upload Job Doc

        data = json.loads(mock_publish.mock_calls[1][1][2])['upload_job']
        check_base_attrs(data)
        assert data['cloud_image_name'] == 'new_image_123'

        # Create Job Doc

        data = json.loads(mock_publish.mock_calls[2][1][2])['create_job']
        check_base_attrs(data)
        assert data['cloud_architecture'] == 'aarch64'
        assert data['cloud_image_name'] == 'new_image_123'
        assert data['image_description'] == 'New Image #123'

        for region, info in data['target_regions'].items():
            if region == 'ap-northeast-1':
                assert info['account'] == 'test-aws'
                assert info['helper_image'] == 'ami-383c1956'
                assert info['billing_codes'] is None
            else:
                assert region == 'us-gov-west-1'
                assert info['account'] == 'test-aws-gov'
                assert info['helper_image'] == 'ami-c2b5d7e1'
                assert info['billing_codes'] is None

        # Test Job Doc

        data = json.loads(mock_publish.mock_calls[3][1][2])['test_job']
        check_base_attrs(data)
        assert data['distro'] == 'sles'
        assert data['instance_type'] == 't2.micro'
        assert data['tests'] == ['test_stuff']

        for region, info in data['test_regions'].items():
            if region == 'ap-northeast-1':
                assert info['account'] == 'test-aws'
                assert info['partition'] == 'aws'
            else:
                assert region == 'us-gov-west-1'
                assert info['account'] == 'test-aws-gov'
                assert info['partition'] == 'aws-us-gov'

        # Raw Image Upload Job Doc

        data = json.loads(mock_publish.mock_calls[4][1][2])['raw_image_upload_job']
        check_base_attrs(data)
        assert data['raw_image_upload_type'] == 's3bucket'
        assert data['raw_image_upload_account'] == 'account'
        assert data['raw_image_upload_location'] == 'location'

        # Replicate Job Doc

        data = json.loads(mock_publish.mock_calls[5][1][2])['replicate_job']
        check_base_attrs(data)
        assert data['image_description'] == 'New Image #123'

        for region, info in data['replicate_source_regions'].items():
            if region == 'ap-northeast-1':
                assert info['account'] == 'test-aws'
                assert 'ap-northeast-1' in info['target_regions']
                assert 'ap-northeast-2' in info['target_regions']
                assert 'ap-northeast-3' in info['target_regions']
            else:
                assert region == 'us-gov-west-1'
                assert info['account'] == 'test-aws-gov'
                assert 'us-gov-west-1' in info['target_regions']

        # Publish Job Doc

        data = json.loads(mock_publish.mock_calls[6][1][2])['publish_job']
        check_base_attrs(data)
        assert data['allow_copy'] == 'none'
        assert data['share_with'] == 'all'

        for region in data['publish_regions']:
            if region['account'] == 'test-aws-gov':
                assert region['helper_image'] == 'ami-c2b5d7e1'
                assert 'us-gov-west-1' in region['target_regions']
            else:
                assert region['account'] == 'test-aws'
                assert region['helper_image'] == 'ami-383c1956'
                assert 'ap-northeast-1' in region['target_regions']
                assert 'ap-northeast-2' in region['target_regions']
                assert 'ap-northeast-3' in region['target_regions']

        # Deprecate Job Doc

        data = json.loads(mock_publish.mock_calls[7][1][2])['deprecate_job']
        check_base_attrs(data)
        assert data['old_cloud_image_name'] == 'old_new_image_123'

        for region in data['deprecate_regions']:
            if region['account'] == 'test-aws-gov':
                assert region['helper_image'] == 'ami-c2b5d7e1'
                assert 'us-gov-west-1' in region['target_regions']
            else:
                assert region['account'] == 'test-aws'
                assert region['helper_image'] == 'ami-383c1956'
                assert 'ap-northeast-1' in region['target_regions']
                assert 'ap-northeast-2' in region['target_regions']
                assert 'ap-northeast-3' in region['target_regions']

    @patch.object(JobCreatorService, '_publish')
    def test_jobcreator_handle_service_message_azure(self, mock_publish):
        def check_base_attrs(job_data, cloud=True):
            assert job_data['id'] == '12345678-1234-1234-1234-123456789012'
            assert job_data['utctime'] == 'now'
            assert job_data['last_service'] == 'deprecate'
            assert job_data['notification_email'] == 'test@fake.com'

            if cloud:
                assert job_data['cloud'] == 'azure'

        with open('test/data/azure_job.json', 'r') as job_doc:
            job = json.load(job_doc)

        job['notification_email'] = 'test@fake.com'
        message = MagicMock()
        message.body = json.dumps(job)
        self.jobcreator._handle_service_message(message)

        # OBS Job Doc

        data = json.loads(mock_publish.mock_calls[0][1][2])['obs_job']
        check_base_attrs(data, cloud=False)
        assert data['cloud_architecture'] == 'x86_64'
        assert data['download_url'] == \
            'http://download.opensuse.org/repositories/Cloud:Tools/images'
        assert data['image'] == 'test_image_oem'

        for condition in data['conditions']:
            if 'package_name' in condition:
                assert condition['release'] == '1.1'
                assert condition['package_name'] == 'openssl'
                assert condition['version'] == '13.4.3'
            else:
                assert condition['version'] == '8.13.21'

        # Upload Job Doc

        data = json.loads(mock_publish.mock_calls[1][1][2])['upload_job']
        check_base_attrs(data)
        assert data['cloud_image_name'] == 'new_image_123'
        assert data['account'] == 'test-azure'
        assert data['container'] == 'container1'
        assert data['resource_group'] == 'rg-1'
        assert data['storage_account'] == 'sa1'
        assert data['additional_uploads'] == ['sha256']

        # create Job Doc

        data = json.loads(mock_publish.mock_calls[2][1][2])['create_job']
        check_base_attrs(data)
        assert data['account'] == 'test-azure'
        assert data['container'] == 'container1'
        assert data['resource_group'] == 'rg-1'
        assert data['storage_account'] == 'sa1'

        # Test Job Doc

        data = json.loads(mock_publish.mock_calls[3][1][2])['test_job']
        check_base_attrs(data)
        assert data['distro'] == 'sles'
        assert data['instance_type'] == 'Basic_A2'
        assert data['tests'] == ['test_stuff']
        assert data['region'] == 'southcentralus'
        assert data['account'] == 'test-azure'
        assert data['container'] == 'container1'
        assert data['resource_group'] == 'rg-1'
        assert data['storage_account'] == 'sa1'

        # Raw Image Upload Job Doc

        data = json.loads(mock_publish.mock_calls[4][1][2])['raw_image_upload_job']
        check_base_attrs(data)
        assert data['raw_image_upload_type'] == 's3bucket'
        assert data['raw_image_upload_account'] == 'account'
        assert data['raw_image_upload_location'] == 'location'

        # Publish Job Doc

        data = json.loads(mock_publish.mock_calls[6][1][2])['publish_job']
        check_base_attrs(data)
        assert data['image_description'] == 'New Image #123'
        assert data['label'] == 'New Image 123'
        assert data['offer_id'] == 'sles'
        assert data['publisher_id'] == 'suse'
        assert data['sku'] == '123'
        assert data['generation_id'] == 'image-gen2'
        assert data['cloud_image_name_generation_suffix'] == 'gen2'
        assert data['vm_images_key'] == 'key123'
        assert data['account'] == 'test-azure'
        assert data['container'] == 'container1'
        assert data['resource_group'] == 'rg-1'
        assert data['storage_account'] == 'sa1'

        # Deprecate Job Doc

        data = json.loads(mock_publish.mock_calls[7][1][2])['deprecate_job']
        check_base_attrs(data)

    @patch.object(JobCreatorService, '_publish')
    def test_jobcreator_handle_service_message_gce(self, mock_publish):
        def check_base_attrs(job_data, cloud=True):
            assert job_data['id'] == '12345678-1234-1234-1234-123456789012'
            assert job_data['utctime'] == 'now'
            assert job_data['last_service'] == 'deprecate'
            assert job_data['notification_email'] == 'test@fake.com'

            if cloud:
                assert job_data['cloud'] == 'gce'

        with open('test/data/gce_job.json', 'r') as job_doc:
            job = json.load(job_doc)

        job['notification_email'] = 'test@fake.com'
        message = MagicMock()
        message.body = json.dumps(job)
        self.jobcreator._handle_service_message(message)

        # OBS Job Doc

        data = json.loads(mock_publish.mock_calls[0][1][2])['obs_job']
        check_base_attrs(data, cloud=False)
        assert data['cloud_architecture'] == 'x86_64'
        assert data['download_url'] == \
            'http://download.opensuse.org/repositories/Cloud:Tools/images'
        assert data['image'] == 'test_image_oem'

        for condition in data['conditions']:
            if 'package_name' in condition:
                assert condition['release'] == '1.1'
                assert condition['package_name'] == 'openssl'
                assert condition['version'] == '13.4.3'
            else:
                assert condition['version'] == '8.13.21'

        # Upload Job Doc

        data = json.loads(mock_publish.mock_calls[1][1][2])['upload_job']
        check_base_attrs(data)
        assert data['cloud_image_name'] == 'new_image_123'
        assert data['region'] == 'us-west1'
        assert data['account'] == 'test-gce'
        assert data['bucket'] == 'images'

        # create Job Doc

        data = json.loads(mock_publish.mock_calls[2][1][2])['create_job']
        check_base_attrs(data)
        assert data['image_description'] == 'New Image #123'
        assert data['region'] == 'us-west1'
        assert data['account'] == 'test-gce'
        assert data['bucket'] == 'images'
        assert data['family'] == 'sles-15'
        assert data['guest_os_features'] == ['UEFI_COMPATIBLE']

        # Test Job Doc

        data = json.loads(mock_publish.mock_calls[3][1][2])['test_job']
        check_base_attrs(data)
        assert data['distro'] == 'sles'
        assert data['instance_type'] == 'n1-standard-1'
        assert data['tests'] == ['test_stuff']
        assert data['region'] == 'us-west1'
        assert data['account'] == 'test-gce'
        assert data['testing_account'] == 'testacnt1'
        assert data['image_project'] == 'test'

        # Raw Image Upload Job Doc
        data = json.loads(mock_publish.mock_calls[4][1][2])['raw_image_upload_job']
        check_base_attrs(data)
        assert data['raw_image_upload_type'] == 's3bucket'
        assert data['raw_image_upload_account'] == 'account'
        assert data['raw_image_upload_location'] == 'location'

        # Replicate Job Doc

        data = json.loads(mock_publish.mock_calls[5][1][2])['replicate_job']
        check_base_attrs(data)

        # Publish Job Doc

        data = json.loads(mock_publish.mock_calls[6][1][2])['publish_job']
        check_base_attrs(data)

        # Deprecate Job Doc

        data = json.loads(mock_publish.mock_calls[7][1][2])['deprecate_job']
        check_base_attrs(data)
        assert data['old_cloud_image_name'] == 'old_new_image_123'
        assert data['account'] == 'test-gce'

    @patch.object(JobCreatorService, '_publish')
    def test_jobcreator_handle_service_message_oci(self, mock_publish):
        def check_base_attrs(job_data, cloud=True):
            assert job_data['id'] == '12345678-1234-1234-1234-123456789012'
            assert job_data['utctime'] == 'now'
            assert job_data['last_service'] == 'deprecate'

            if cloud:
                assert job_data['cloud'] == 'oci'

        with open('test/data/oci_job.json', 'r') as job_doc:
            job = json.load(job_doc)

        message = MagicMock()
        message.body = json.dumps(job)
        self.jobcreator._handle_service_message(message)

        # OBS Job Doc

        data = json.loads(mock_publish.mock_calls[0][1][2])['obs_job']
        check_base_attrs(data, cloud=False)
        assert data['cloud_architecture'] == 'x86_64'
        assert data['download_url'] == \
            'http://download.opensuse.org/repositories/Cloud:Tools/images'
        assert data['image'] == 'test_image_oem'

        # Upload Job Doc

        data = json.loads(mock_publish.mock_calls[1][1][2])['upload_job']
        check_base_attrs(data)
        assert data['cloud_image_name'] == 'new_image_123'
        assert data['region'] == 'us-phoenix-1'
        assert data['account'] == 'test-oci'
        assert data['bucket'] == 'images2'
        assert data['availability_domain'] == 'Omic:PHX-AD-1'
        assert data['compartment_id'] == 'ocid1.compartment.oc1..'
        assert data['oci_user_id'] == 'ocid1.user.oc1..'
        assert data['tenancy'] == 'ocid1.tenancy.oc1..'

        # create Job Doc

        data = json.loads(mock_publish.mock_calls[2][1][2])['create_job']
        check_base_attrs(data)
        assert data['image_description'] == 'New Image #123'
        assert data['region'] == 'us-phoenix-1'
        assert data['account'] == 'test-oci'
        assert data['bucket'] == 'images2'

        # Test Job Doc

        data = json.loads(mock_publish.mock_calls[3][1][2])['test_job']
        check_base_attrs(data)
        assert data['distro'] == 'sles'
        assert data['instance_type'] == 'VM.Standard2.1'
        assert data['tests'] == ['test_stuff']
        assert data['region'] == 'us-phoenix-1'
        assert data['account'] == 'test-oci'

        # Raw Image Upload Job Doc
        data = json.loads(mock_publish.mock_calls[4][1][2])['raw_image_upload_job']
        check_base_attrs(data)
        assert data['raw_image_upload_type'] is None

        # Replicate Job Doc

        data = json.loads(mock_publish.mock_calls[5][1][2])['replicate_job']
        check_base_attrs(data)

        # Publish Job Doc

        data = json.loads(mock_publish.mock_calls[6][1][2])['publish_job']
        check_base_attrs(data)

        # Deprecate Job Doc

        data = json.loads(mock_publish.mock_calls[7][1][2])['deprecate_job']
        check_base_attrs(data)
        assert data['old_cloud_image_name'] == 'old_new_image_123'
        assert data['account'] == 'test-oci'

    def test_jobcreator_handle_invalid_service_message(self):
        message = MagicMock()
        message.body = 'invalid message'

        with open('test/data/job.json', 'r') as job_doc:
            job = json.load(job_doc)

        self.jobcreator.jobs = {'123': job}

        self.jobcreator._handle_service_message(message)
        self.jobcreator.log.error.assert_called_once_with(
            'Invalid message received: '
            'Expecting value: line 1 column 1 (char 0).'
        )

    @patch.object(JobCreatorService, 'send_notification')
    @patch('mash.services.jobcreator.service.handle_request')
    def test_jobcreator_handle_status_message(
        self,
        mock_handle_request,
        mock_send_notif
    ):
        data = {
            'publish_status': {
                'id': '12345678-1234-1234-1234-123456789012',
                'state': 'running',
                'status': 'success',
                'notification_email': 'test@fake.com',
                'last_service': 'publish',
                'errors': []
            }
        }
        message = MagicMock()
        message.body = json.dumps(data)
        self.jobcreator.database_api_url = 'http://localhost:5007/'

        self.jobcreator._handle_status_message(message)
        assert mock_send_notif.call_count == 1

        # Request failed
        mock_handle_request.side_effect = Exception('Not found')
        self.jobcreator._handle_status_message(message)
        self.jobcreator.log.error.assert_called_once_with(
            'Job status update failed: Not found'
        )

        # Fake service
        data['fake_status'] = data['publish_status']
        del data['publish_status']
        message.body = json.dumps(data)

        self.jobcreator._handle_status_message(message)
        self.jobcreator.log.warning.assert_called_once_with(
            'Unkown service message received for fake service.'
        )

        # Invalid message
        message.body = 'Not json'
        self.jobcreator.log.error.reset_mock()

        self.jobcreator._handle_status_message(message)
        self.jobcreator.log.error.assert_called_once_with(
            'Invalid message received: Expecting value: line 1 column 1 (char 0).'
        )

    def test_get_next_service(self):
        result = self.jobcreator._get_next_service('deprecate')
        assert result is None

    @patch.object(JobCreatorService, 'consume_queue')
    @patch.object(JobCreatorService, 'stop')
    def test_jobcreator_start(self, mock_stop, mock_consume_queue):
        self.jobcreator.channel = self.channel

        self.jobcreator.start()
        self.channel.start_consuming.assert_called_once_with()

        mock_consume_queue.call_count == 9
        mock_stop.assert_called_once_with()

    @patch.object(JobCreatorService, 'consume_queue')
    @patch.object(JobCreatorService, 'stop')
    def test_jobcreator_start_exception(self, mock_stop, mock_consume_queue):
        self.channel.start_consuming.side_effect = KeyboardInterrupt()
        self.jobcreator.channel = self.channel

        self.jobcreator.start()
        mock_stop.assert_called_once_with()
        mock_stop.reset_mock()

        self.channel.start_consuming.side_effect = Exception(
            'Cannot start job creator service.'
        )

        with raises(Exception) as error:
            self.jobcreator.start()

        assert 'Cannot start job creator service.' == str(error.value)

    @patch.object(JobCreatorService, 'close_connection')
    def test_jobcreator_stop(self, mock_close_connection):
        self.jobcreator.channel = self.channel

        self.jobcreator.stop()
        self.channel.stop_consuming.assert_called_once_with()
        mock_close_connection.assert_called_once_with()

    def test_create_notification_content(self):
        # Failed message
        msg = self.jobcreator._create_notification_content(
            '1', 'failed', 'test_image',
            ['Invalid publish permissions!']
        )

        assert 'Job failed' in msg

        # Job finished with success
        msg = self.jobcreator._create_notification_content(
            '1', 'success', 'test_image'
        )

        assert 'Job finished successfully' in msg

        # Service with success
        msg = self.jobcreator._create_notification_content(
            '1', 'success', 'test_image'
        )

    def test_send_email_notification(self):
        job_id = '12345678-1234-1234-1234-123456789012'
        to = 'test@fake.com'

        notif_class = Mock()
        self.jobcreator.notification_class = notif_class
        self.jobcreator.config = self.config

        self.jobcreator.send_notification(
            job_id, to, 'periodic', 'failed',
            'test_image'
        )
        assert notif_class.send_notification.call_count == 1

    @patch.object(JobCreatorService, '_publish')
    def test_jobcreator_handle_service_message_aliyun(self, mock_publish):
        def check_base_attrs(job_data, cloud=True):
            assert job_data['id'] == '12345678-1234-1234-1234-123456789012'
            assert job_data['utctime'] == 'now'
            assert job_data['last_service'] == 'deprecate'

            if cloud:
                assert job_data['cloud'] == 'aliyun'

        with open('test/data/aliyun_job.json', 'r') as job_doc:
            job = json.load(job_doc)

        message = MagicMock()
        message.body = json.dumps(job)
        self.jobcreator._handle_service_message(message)

        # OBS Job Doc

        data = json.loads(mock_publish.mock_calls[0][1][2])['obs_job']
        check_base_attrs(data, cloud=False)
        assert data['cloud_architecture'] == 'x86_64'
        assert data['download_url'] == \
            'http://download.opensuse.org/repositories/Cloud:Tools/images'
        assert data['image'] == 'test_image_oem'

        # Upload Job Doc

        data = json.loads(mock_publish.mock_calls[1][1][2])['upload_job']
        check_base_attrs(data)
        assert data['cloud_image_name'] == 'new_image_123'
        assert data['region'] == 'cn-beijing'
        assert data['account'] == 'test-aliyun'
        assert data['bucket'] == 'images'

        # create Job Doc

        data = json.loads(mock_publish.mock_calls[2][1][2])['create_job']
        check_base_attrs(data)
        assert data['image_description'] == 'New Image #123'
        assert data['region'] == 'cn-beijing'
        assert data['account'] == 'test-aliyun'
        assert data['bucket'] == 'images'
        assert data['platform'] == 'SUSE'

        # Test Job Doc

        data = json.loads(mock_publish.mock_calls[3][1][2])['test_job']
        check_base_attrs(data)
        assert data['distro'] == 'sles'
        assert data['instance_type'] == 'ecs.t5-lc1m1.small'
        assert data['tests'] == ['test_stuff']
        assert data['region'] == 'cn-beijing'
        assert data['account'] == 'test-aliyun'

        # Raw Image Upload Job Doc
        data = json.loads(mock_publish.mock_calls[4][1][2])['raw_image_upload_job']
        check_base_attrs(data)
        assert data['raw_image_upload_type'] == 's3bucket'

        # Replicate Job Doc

        data = json.loads(mock_publish.mock_calls[5][1][2])['replicate_job']
        check_base_attrs(data)
        assert data['account'] == 'test-aliyun'

        # Publish Job Doc

        data = json.loads(mock_publish.mock_calls[6][1][2])['publish_job']
        check_base_attrs(data)
        assert data['account'] == 'test-aliyun'
        assert data['launch_permission'] == 'HIDDEN'

        # Deprecate Job Doc

        data = json.loads(mock_publish.mock_calls[7][1][2])['deprecate_job']
        check_base_attrs(data)
        assert data['old_cloud_image_name'] == 'old_new_image_123'
        assert data['account'] == 'test-aliyun'
