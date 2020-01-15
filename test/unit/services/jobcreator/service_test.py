import json

from pytest import raises
from unittest.mock import MagicMock, Mock, patch

from mash.services.mash_service import MashService
from mash.services.jobcreator.service import JobCreatorService
from mash.utils.json_format import JsonFormat


class TestJobCreatorService(object):

    @patch.object(MashService, '__init__')
    def setup(
        self, mock_base_init
    ):
        mock_base_init.return_value = None
        self.config = Mock()
        self.config.config_data = None
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
        self.jobcreator.services = [
            'obs', 'uploader', 'create', 'testing', 'raw_image_uploader',
            'replication', 'publisher', 'deprecation'
        ]

    @patch('mash.services.jobcreator.service.setup_logfile')
    @patch.object(JobCreatorService, 'start')
    @patch.object(JobCreatorService, 'bind_queue')
    def test_jobcreator_post_init(
        self, mock_bind_queue,
        mock_start, mock_setup_logfile
    ):
        self.jobcreator.config = self.config
        self.config.get_log_file.return_value = \
            '/var/log/mash/job_creator_service.log'

        self.jobcreator.post_init()

        self.config.get_log_file.assert_called_once_with('jobcreator')
        mock_setup_logfile.assert_called_once_with(
            '/var/log/mash/job_creator_service.log'
        )

        mock_bind_queue.assert_called_once_with(
            'jobcreator', 'job_document', 'service'
        )
        mock_start.assert_called_once_with()

    @patch.object(JobCreatorService, '_publish')
    def test_jobcreator_handle_service_message(self, mock_publish):
        def check_base_attrs(job_data, cloud=True):
            assert job_data['id'] == '12345678-1234-1234-1234-123456789012'
            assert job_data['utctime'] == 'now'
            assert job_data['last_service'] == 'deprecation'
            assert job_data['notification_email'] == 'test@fake.com'
            assert job_data['notification_type'] == 'single'

            if cloud:
                assert job_data['cloud'] == 'ec2'

        with open('test/data/job.json', 'r') as job_doc:
            job = json.load(job_doc)

        job['target_account_info'] = {
            'us-gov-west-1': {
                'account': 'test-aws-gov',
                'target_regions': ['us-gov-west-1'],
                'helper_image': 'ami-c2b5d7e1',
                'subnet': 'subnet-12345'
            },
            'ap-northeast-1': {
                'account': 'test-aws',
                'target_regions': [
                    'ap-northeast-1', 'ap-northeast-2', 'ap-northeast-3'
                ],
                'helper_image': 'ami-383c1956',
                'subnet': 'subnet-54321'
            }
        }
        del job['cloud_accounts']
        del job['cloud_groups']

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

        # Uploader Job Doc

        data = json.loads(mock_publish.mock_calls[1][1][2])['uploader_job']
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

        # Testing Job Doc

        data = json.loads(mock_publish.mock_calls[3][1][2])['testing_job']
        check_base_attrs(data)
        assert data['distro'] == 'sles'
        assert data['instance_type'] == 't2.micro'
        assert data['tests'] == ['test_stuff']

        for region, info in data['test_regions'].items():
            if region == 'ap-northeast-1':
                assert info['account'] == 'test-aws'
            else:
                assert region == 'us-gov-west-1'
                assert info['account'] == 'test-aws-gov'

        # Raw Image Uploader Job Doc

        data = json.loads(mock_publish.mock_calls[4][1][2])['raw_image_uploader_job']
        check_base_attrs(data)
        assert data['raw_image_upload_type'] == 's3bucket'
        assert data['raw_image_upload_account'] == 'account'
        assert data['raw_image_upload_location'] == 'location'

        # Replication Job Doc

        data = json.loads(mock_publish.mock_calls[5][1][2])['replication_job']
        check_base_attrs(data)
        assert data['image_description'] == 'New Image #123'

        for region, info in data['replication_source_regions'].items():
            if region == 'ap-northeast-1':
                assert info['account'] == 'test-aws'
                assert 'ap-northeast-1' in info['target_regions']
                assert 'ap-northeast-2' in info['target_regions']
                assert 'ap-northeast-3' in info['target_regions']
            else:
                assert region == 'us-gov-west-1'
                assert info['account'] == 'test-aws-gov'
                assert 'us-gov-west-1' in info['target_regions']

        # Publisher Job Doc

        data = json.loads(mock_publish.mock_calls[6][1][2])['publisher_job']
        check_base_attrs(data)
        assert data['allow_copy'] is False
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

        # Deprecation Job Doc

        data = json.loads(mock_publish.mock_calls[7][1][2])['deprecation_job']
        check_base_attrs(data)
        assert data['old_cloud_image_name'] == 'old_new_image_123'

        for region in data['deprecation_regions']:
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
            assert job_data['last_service'] == 'deprecation'
            assert job_data['notification_email'] == 'test@fake.com'
            assert job_data['notification_type'] == 'single'

            if cloud:
                assert job_data['cloud'] == 'azure'

        with open('test/data/azure_job.json', 'r') as job_doc:
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

        for condition in data['conditions']:
            if 'package_name' in condition:
                assert condition['release'] == '1.1'
                assert condition['package_name'] == 'openssl'
                assert condition['version'] == '13.4.3'
            else:
                assert condition['version'] == '8.13.21'

        # Uploader Job Doc

        data = json.loads(mock_publish.mock_calls[1][1][2])['uploader_job']
        check_base_attrs(data)
        assert data['cloud_image_name'] == 'new_image_123'
        assert data['account'] == 'test-azure'
        assert data['container'] == 'container1'
        assert data['resource_group'] == 'rg-1'
        assert data['storage_account'] == 'sa1'

        # create Job Doc

        data = json.loads(mock_publish.mock_calls[2][1][2])['create_job']
        check_base_attrs(data)
        assert data['account'] == 'test-azure'
        assert data['container'] == 'container1'
        assert data['resource_group'] == 'rg-1'
        assert data['storage_account'] == 'sa1'

        # Testing Job Doc

        data = json.loads(mock_publish.mock_calls[3][1][2])['testing_job']
        check_base_attrs(data)
        assert data['distro'] == 'sles'
        assert data['instance_type'] == 'Basic_A2'
        assert data['tests'] == ['test_stuff']
        assert data['region'] == 'southcentralus'
        assert data['account'] == 'test-azure'
        assert data['container'] == 'container1'
        assert data['resource_group'] == 'rg-1'
        assert data['storage_account'] == 'sa1'

        # Raw Image Uploader Job Doc

        data = json.loads(mock_publish.mock_calls[4][1][2])['raw_image_uploader_job']
        check_base_attrs(data)
        assert data['raw_image_upload_type'] == 's3bucket'
        assert data['raw_image_upload_account'] == 'account'
        assert data['raw_image_upload_location'] == 'location'

        # Replication Job Doc

        data = json.loads(mock_publish.mock_calls[5][1][2])['replication_job']
        check_base_attrs(data)
        assert data['cleanup_images']
        assert data['region'] == 'southcentralus'
        assert data['account'] == 'test-azure'
        assert data['source_container'] == 'container1'
        assert data['source_resource_group'] == 'rg-1'
        assert data['source_storage_account'] == 'sa1'
        assert data['destination_container'] == 'container2'
        assert data['destination_resource_group'] == 'rg-2'
        assert data['destination_storage_account'] == 'sa2'

        # Publisher Job Doc

        data = json.loads(mock_publish.mock_calls[6][1][2])['publisher_job']
        check_base_attrs(data)
        assert data['emails'] == 'jdoe@fake.com'
        assert data['image_description'] == 'New Image #123'
        assert data['label'] == 'New Image 123'
        assert data['offer_id'] == 'sles'
        assert data['publisher_id'] == 'suse'
        assert data['sku'] == '123'
        assert data['generation_id'] == 'image-gen2'
        assert data['cloud_image_name_generation_suffix'] == 'gen2'
        assert data['vm_images_key'] == 'key123'
        assert data['account'] == 'test-azure'
        assert data['container'] == 'container2'
        assert data['resource_group'] == 'rg-2'
        assert data['storage_account'] == 'sa2'

        # Deprecation Job Doc

        data = json.loads(mock_publish.mock_calls[7][1][2])['deprecation_job']
        check_base_attrs(data)

    @patch.object(JobCreatorService, '_publish')
    def test_jobcreator_handle_service_message_gce(self, mock_publish):
        def check_base_attrs(job_data, cloud=True):
            assert job_data['id'] == '12345678-1234-1234-1234-123456789012'
            assert job_data['utctime'] == 'now'
            assert job_data['last_service'] == 'deprecation'
            assert job_data['notification_email'] == 'test@fake.com'
            assert job_data['notification_type'] == 'single'

            if cloud:
                assert job_data['cloud'] == 'gce'

        with open('test/data/gce_job.json', 'r') as job_doc:
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

        for condition in data['conditions']:
            if 'package_name' in condition:
                assert condition['release'] == '1.1'
                assert condition['package_name'] == 'openssl'
                assert condition['version'] == '13.4.3'
            else:
                assert condition['version'] == '8.13.21'

        # Uploader Job Doc

        data = json.loads(mock_publish.mock_calls[1][1][2])['uploader_job']
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

        # Testing Job Doc

        data = json.loads(mock_publish.mock_calls[3][1][2])['testing_job']
        check_base_attrs(data)
        assert data['distro'] == 'sles'
        assert data['instance_type'] == 'n1-standard-1'
        assert data['tests'] == ['test_stuff']
        assert data['region'] == 'us-west1'
        assert data['account'] == 'test-gce'
        assert data['testing_account'] == 'testacnt1'

        # Raw Image Uploader Job Doc
        data = json.loads(mock_publish.mock_calls[4][1][2])['raw_image_uploader_job']
        check_base_attrs(data)
        assert data['raw_image_upload_type'] == 's3bucket'
        assert data['raw_image_upload_account'] == 'account'
        assert data['raw_image_upload_location'] == 'location'

        # Replication Job Doc

        data = json.loads(mock_publish.mock_calls[5][1][2])['replication_job']
        check_base_attrs(data)

        # Publisher Job Doc

        data = json.loads(mock_publish.mock_calls[6][1][2])['publisher_job']
        check_base_attrs(data)

        # Deprecation Job Doc

        data = json.loads(mock_publish.mock_calls[7][1][2])['deprecation_job']
        check_base_attrs(data)
        assert data['old_cloud_image_name'] == 'old_new_image_123'
        assert data['account'] == 'test-gce'

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

    @patch.object(JobCreatorService, '_publish')
    def test_jobcreator_publish_delete_job_message(self, mock_publish):
        message = MagicMock()
        message.body = '{"job_delete": "1"}'
        self.jobcreator._handle_service_message(message)
        mock_publish.assert_called_once_with(
            'obs', 'job_document',
            JsonFormat.json_message({"obs_job_delete": "1"})
        )

    @patch.object(JobCreatorService, 'consume_queue')
    @patch.object(JobCreatorService, 'stop')
    def test_jobcreator_start(self, mock_stop, mock_consume_queue):
        self.jobcreator.channel = self.channel

        self.jobcreator.start()
        self.channel.start_consuming.assert_called_once_with()

        mock_consume_queue.assert_called_once_with(
            self.jobcreator._handle_service_message,
            queue_name='service'
        )
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
