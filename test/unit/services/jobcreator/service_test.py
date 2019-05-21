import json

from pytest import raises
from unittest.mock import call, MagicMock, Mock, patch

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
        self.jobcreator.add_account_key = 'add_account'
        self.jobcreator.delete_account_key = 'delete_account'
        self.jobcreator.service_exchange = 'jobcreator'
        self.jobcreator.listener_queue = 'listener'
        self.jobcreator.job_document_key = 'job_document'
        self.jobcreator.services = [
            'obs', 'uploader', 'testing', 'replication',
            'publisher', 'deprecation'
        ]

    @patch.object(JobCreatorService, 'set_logfile')
    @patch.object(JobCreatorService, 'start')
    @patch.object(JobCreatorService, 'bind_queue')
    def test_jobcreator_post_init(
        self, mock_bind_queue,
        mock_start, mock_set_logfile
    ):
        self.jobcreator.config = self.config
        self.config.get_log_file.return_value = \
            '/var/log/mash/job_creator_service.log'

        self.jobcreator.post_init()

        self.config.get_log_file.assert_called_once_with('jobcreator')
        mock_set_logfile.assert_called_once_with(
            '/var/log/mash/job_creator_service.log'
        )

        mock_bind_queue.assert_has_calls([
            call('jobcreator', 'add_account', 'listener'),
            call('jobcreator', 'delete_account', 'listener')
        ])
        mock_start.assert_called_once_with()

    @patch.object(JobCreatorService, '_publish')
    def test_jobcreator_handle_service_message(
            self, mock_publish
    ):
        def check_base_attrs(job_data, cloud=True):
            assert job_data['id'] == '12345678-1234-1234-1234-123456789012'
            assert job_data['utctime'] == 'now'
            assert job_data['last_service'] == 'deprecation'
            assert job_data['notification_email'] == 'test@fake.com'
            assert job_data['notification_type'] == 'single'

            if cloud:
                assert job_data['cloud'] == 'ec2'

        self.jobcreator.jobs = {}
        self.jobcreator.cloud_data = {
            'ec2': {
                'regions': {
                    'aws': ['ap-northeast-1', 'ap-northeast-2'],
                    'aws-cn': ['cn-north-1'],
                    'aws-us-gov': ['us-gov-west-1']
                },
                'helper_images': {
                    'ap-northeast-1': 'ami-383c1956',
                    'ap-northeast-2': 'ami-249b554a',
                    'cn-north-1': 'ami-bcc45885',
                    'us-gov-west-1': 'ami-c2b5d7e1'
                }
            }
        }
        message = MagicMock()

        with open('../data/job.json', 'r') as job_doc:
            job = json.load(job_doc)

        self.jobcreator.jobs['12345678-1234-1234-1234-123456789012'] = job

        account_info = {
            "test-aws-gov": {
                "partition": "aws-us-gov",
                "region": "us-gov-west-1"
            },
            "test-aws": {
                "additional_regions": [
                    {
                        "name": "ap-northeast-3",
                        "helper_image": "ami-82444aff"
                    }
                ],
                "partition": "aws",
                "region": "ap-northeast-1"
            }
        }

        message.body = JsonFormat.json_message({
            'start_job': {
                'id': '12345678-1234-1234-1234-123456789012',
                'accounts_info': account_info
            }
        })
        self.jobcreator._handle_service_message(message)

        # Credentials Job Doc

        data = json.loads(mock_publish.mock_calls[0][1][2])['credentials_job']
        check_base_attrs(data)
        assert 'test-aws-gov' in data['cloud_accounts']
        assert 'test-aws' in data['cloud_accounts']
        assert data['requesting_user'] == 'user1'

        # OBS Job Doc

        data = json.loads(mock_publish.mock_calls[1][1][2])['obs_job']
        check_base_attrs(data, cloud=False)
        assert data['cloud_architecture'] == 'aarch64'
        assert data['download_url'] == \
            'http://download.opensuse.org/repositories/Cloud:Tools/images'
        assert data['image'] == 'test_image_oem'

        for condition in data['conditions']:
            if 'image' in condition:
                assert condition['image'] == 'version'
            else:
                assert condition['build_id'] == '1.1'
                assert condition['package_name'] == 'openssl'
                assert condition['version'] == '13.4.3'

        # Uploader Job Doc

        data = json.loads(mock_publish.mock_calls[2][1][2])['uploader_job']
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

        # Replication Job Doc

        data = json.loads(mock_publish.mock_calls[4][1][2])['replication_job']
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

        data = json.loads(mock_publish.mock_calls[5][1][2])['publisher_job']
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

        data = json.loads(mock_publish.mock_calls[6][1][2])['deprecation_job']
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
    def test_jobcreator_handle_service_message_azure(
        self, mock_publish
    ):
        def check_base_attrs(job_data, cloud=True):
            assert job_data['id'] == '12345678-1234-1234-1234-123456789012'
            assert job_data['utctime'] == 'now'
            assert job_data['last_service'] == 'deprecation'
            assert job_data['notification_email'] == 'test@fake.com'
            assert job_data['notification_type'] == 'single'

            if cloud:
                assert job_data['cloud'] == 'azure'

        self.jobcreator.jobs = {}
        self.jobcreator.cloud_data = {'azure': {}}
        message = MagicMock()

        with open('../data/azure_job.json', 'r') as job_doc:
            job = json.load(job_doc)

        self.jobcreator.jobs['12345678-1234-1234-1234-123456789012'] = job

        account_info = {
            "test-azure": {
                "region": "southcentralus",
                "source_resource_group": "sc_res_group1",
                "source_container": "sccontainer1",
                "source_storage_account": "scstorage1",
                "destination_resource_group": "sc_res_group2",
                "destination_container": "sccontainer2",
                "destination_storage_account": "scstorage2"
            },
            "test-azure2": {
                "region": "centralus",
                "source_resource_group": "c_res_group1",
                "source_container": "ccontainer1",
                "source_storage_account": "cstorage1",
                "destination_resource_group": "c_res_group2",
                "destination_container": "ccontainer2",
                "destination_storage_account": "cstorage2"
            }
        }

        message.body = json.dumps({
            'start_job': {
                'id': '12345678-1234-1234-1234-123456789012',
                'accounts_info': account_info
            }
        })
        self.jobcreator._handle_service_message(message)

        # Credentials Job Doc

        data = json.loads(mock_publish.mock_calls[0][1][2])['credentials_job']
        check_base_attrs(data)
        assert 'test-azure' in data['cloud_accounts']
        assert 'test-azure2' in data['cloud_accounts']
        assert data['requesting_user'] == 'user1'

        # OBS Job Doc

        data = json.loads(mock_publish.mock_calls[1][1][2])['obs_job']
        check_base_attrs(data, cloud=False)
        assert data['cloud_architecture'] == 'x86_64'
        assert data['download_url'] == \
            'http://download.opensuse.org/repositories/Cloud:Tools/images'
        assert data['image'] == 'test_image_oem'

        for condition in data['conditions']:
            if 'image' in condition:
                assert condition['image'] == 'version'
            else:
                assert condition['build_id'] == '1.1'
                assert condition['package_name'] == 'openssl'
                assert condition['version'] == '13.4.3'

        # Uploader Job Doc

        data = json.loads(mock_publish.mock_calls[2][1][2])['uploader_job']
        check_base_attrs(data)
        assert data['cloud_architecture'] == 'x86_64'
        assert data['cloud_image_name'] == 'new_image_123'
        assert data['image_description'] == 'New Image #123'

        for region, info in data['target_regions'].items():
            if region == 'centralus':
                assert info['account'] == 'test-azure2'
                assert info['container'] == 'ccontainer1'
                assert info['resource_group'] == 'c_res_group1'
                assert info['storage_account'] == 'cstorage1'
            else:
                assert region == 'southcentralus'
                assert info['account'] == 'test-azure'
                assert info['container'] == 'container1'
                assert info['resource_group'] == 'rg-1'
                assert info['storage_account'] == 'sa1'

        # Testing Job Doc

        data = json.loads(mock_publish.mock_calls[3][1][2])['testing_job']
        check_base_attrs(data)
        assert data['distro'] == 'sles'
        assert data['instance_type'] == 'Basic_A2'
        assert data['tests'] == ['test_stuff']

        for region, info in data['test_regions'].items():
            if region == 'centralus':
                assert info['account'] == 'test-azure2'
            else:
                assert region == 'southcentralus'
                assert info['account'] == 'test-azure'

        # Replication Job Doc

        data = json.loads(mock_publish.mock_calls[4][1][2])['replication_job']
        check_base_attrs(data)
        assert data['cleanup_images']
        assert data['image_description'] == 'New Image #123'

        for region, info in data['replication_source_regions'].items():
            if region == 'centralus':
                assert info['account'] == 'test-azure2'
                assert info['source_container'] == 'ccontainer1'
                assert info['source_resource_group'] == 'c_res_group1'
                assert info['source_storage_account'] == 'cstorage1'
                assert info['destination_container'] == 'ccontainer2'
                assert info['destination_resource_group'] == 'c_res_group2'
                assert info['destination_storage_account'] == 'cstorage2'
            else:
                assert region == 'southcentralus'
                assert info['account'] == 'test-azure'
                assert info['source_container'] == 'container1'
                assert info['source_resource_group'] == 'rg-1'
                assert info['source_storage_account'] == 'sa1'
                assert info['destination_container'] == 'container2'
                assert info['destination_resource_group'] == 'rg-2'
                assert info['destination_storage_account'] == 'sa2'

        # Publisher Job Doc

        data = json.loads(mock_publish.mock_calls[5][1][2])['publisher_job']
        check_base_attrs(data)
        assert data['emails'] == 'jdoe@fake.com'
        assert data['image_description'] == 'New Image #123'
        assert data['label'] == 'New Image 123'
        assert data['offer_id'] == 'sles'
        assert data['publisher_id'] == 'suse'
        assert data['sku'] == '123'
        assert data['vm_images_key'] == 'key123'

        for region in data['publish_regions']:
            assert region['account'] in ('test-azure', 'test-azure2')
            if region['account'] == 'test-azure':
                assert region['destination_container'] == 'container2'
                assert region['destination_resource_group'] == 'rg-2'
                assert region['destination_storage_account'] == 'sa2'
            else:
                assert region['destination_container'] == 'ccontainer2'
                assert region['destination_resource_group'] == 'c_res_group2'
                assert region['destination_storage_account'] == 'cstorage2'

        # Deprecation Job Doc

        data = json.loads(mock_publish.mock_calls[6][1][2])['deprecation_job']
        check_base_attrs(data)

    @patch.object(JobCreatorService, '_publish')
    def test_jobcreator_handle_service_message_gce(
        self, mock_publish
    ):
        def check_base_attrs(job_data, cloud=True):
            assert job_data['id'] == '12345678-1234-1234-1234-123456789012'
            assert job_data['utctime'] == 'now'
            assert job_data['last_service'] == 'deprecation'
            assert job_data['notification_email'] == 'test@fake.com'
            assert job_data['notification_type'] == 'single'

            if cloud:
                assert job_data['cloud'] == 'gce'

        self.jobcreator.jobs = {}
        self.jobcreator.cloud_data = {'gce': {}}
        message = MagicMock()

        with open('../data/gce_job.json', 'r') as job_doc:
            job = json.load(job_doc)

        self.jobcreator.jobs['12345678-1234-1234-1234-123456789012'] = job

        account_info = {
            "test-gce": {
                "region": "us-west1",
                "bucket": "images"
            },
            "test-gce2": {
                "region": "us-west2",
                "bucket": "images"
            }
        }

        message.body = json.dumps({
            'start_job': {
                'id': '12345678-1234-1234-1234-123456789012',
                'accounts_info': account_info
            }
        })
        self.jobcreator._handle_service_message(message)

        # Credentials Job Doc

        data = json.loads(mock_publish.mock_calls[0][1][2])['credentials_job']
        check_base_attrs(data)
        assert 'test-gce' in data['cloud_accounts']
        assert 'test-gce2' in data['cloud_accounts']
        assert data['requesting_user'] == 'user1'

        # OBS Job Doc

        data = json.loads(mock_publish.mock_calls[1][1][2])['obs_job']
        check_base_attrs(data, cloud=False)
        assert data['cloud_architecture'] == 'x86_64'
        assert data['download_url'] == \
            'http://download.opensuse.org/repositories/Cloud:Tools/images'
        assert data['image'] == 'test_image_oem'

        for condition in data['conditions']:
            if 'image' in condition:
                assert condition['image'] == 'version'
            else:
                assert condition['build_id'] == '1.1'
                assert condition['package_name'] == 'openssl'
                assert condition['version'] == '13.4.3'

        # Uploader Job Doc

        data = json.loads(mock_publish.mock_calls[2][1][2])['uploader_job']
        check_base_attrs(data)
        assert data['cloud_architecture'] == 'x86_64'
        assert data['cloud_image_name'] == 'new_image_123'
        assert data['image_description'] == 'New Image #123'

        for region, info in data['target_regions'].items():
            if region == 'us-west2':
                assert info['account'] == 'test-gce2'
                assert info['bucket'] == 'images'
                assert info['family'] == 'sles-15'
                assert info['testing_account'] is None
            else:
                assert region == 'us-west1'
                assert info['account'] == 'test-gce'
                assert info['bucket'] == 'images'
                assert info['family'] == 'sles-15'
                assert info['testing_account'] is None

        # Testing Job Doc

        data = json.loads(mock_publish.mock_calls[3][1][2])['testing_job']
        check_base_attrs(data)
        assert data['distro'] == 'sles'
        assert data['instance_type'] == 'n1-standard-1'
        assert data['tests'] == ['test_stuff']

        for region, info in data['test_regions'].items():
            if region == 'us-west2':
                assert info['account'] == 'test-gce2'
                assert info['testing_account'] is None
            else:
                assert region == 'us-west1'
                assert info['account'] == 'test-gce'
                assert info['testing_account'] is None

        # Replication Job Doc

        data = json.loads(mock_publish.mock_calls[4][1][2])['replication_job']
        check_base_attrs(data)

        # Publisher Job Doc

        data = json.loads(mock_publish.mock_calls[5][1][2])['publisher_job']
        check_base_attrs(data)

        # Deprecation Job Doc

        data = json.loads(mock_publish.mock_calls[6][1][2])['deprecation_job']
        check_base_attrs(data)
        assert data['old_cloud_image_name'] == 'old_new_image_123'
        assert 'test-gce' in data['deprecation_accounts']
        assert 'test-gce2' in data['deprecation_accounts']

    @patch.object(JobCreatorService, 'send_email_notification')
    def test_jobcreator_handle_invalid_service_message(
        self, mock_send_email_notification
    ):
        message = MagicMock()
        message.body = 'invalid message'

        with open('../data/job.json', 'r') as job_doc:
            job = json.load(job_doc)

        self.jobcreator.jobs = {'123': job}

        self.jobcreator._handle_service_message(message)
        self.jobcreator.log.error.assert_called_once_with(
            'Invalid message received: '
            'Expecting value: line 1 column 1 (char 0).'
        )

        # Invalid accounts
        message.body = '{"invalid_job": "123"}'

        self.jobcreator._handle_service_message(message)
        self.jobcreator.log.warning.assert_called_once_with(
            'Job failed, accounts do not exist.',
            extra={'job_id': '123'}
        )
        mock_send_email_notification.assert_called_once_with(
            '123', 'test@fake.com', None, 'failed', 'now', 'deprecation',
            error=None
        )

    @patch.object(JobCreatorService, '_publish')
    def test_jobcreator_handle_listener_message_add(
        self, mock_publish
    ):
        message = MagicMock()

        # Test add ec2 account message
        message.method = {'routing_key': 'add_account'}
        message.body = JsonFormat.json_message({
            "account_name": "test-aws",
            "credentials": {
                "access_key_id": "123456",
                "secret_access_key": "654321"
            },
            "group": "group1",
            "partition": "aws",
            "cloud": "ec2",
            "requesting_user": "user1"
        })

        self.jobcreator._handle_listener_message(message)

        mock_publish.assert_called_once_with(
            'credentials', 'add_account',
            JsonFormat.json_message(json.loads(message.body))
        )
        message.ack.assert_called_once_with()

        message.ack.reset_mock()
        mock_publish.reset_mock()

        # Test add azure account message
        message.method = {'routing_key': 'add_account'}
        message.body = JsonFormat.json_message({
            "account_name": "test-azure",
            "container_name": "container1",
            "credentials": {
                "clientId": "123456",
                "clientSecret": "654321",
                "subscriptionId": "654321",
                "tenantId": "654321"
            },
            "group": "group1",
            "cloud": "azure",
            "region": "southcentralus",
            "requesting_user": "user1",
            "resource_group": "rg_123",
            "storage_account": "sa_1"
        })

        self.jobcreator._handle_listener_message(message)

        mock_publish.assert_called_once_with(
            'credentials', 'add_account',
            JsonFormat.json_message(json.loads(message.body))
        )
        message.ack.assert_called_once_with()

    @patch.object(JobCreatorService, '_publish')
    def test_jobcreator_handle_listener_message_delete(
        self, mock_publish
    ):
        message = MagicMock()
        message.method = {'routing_key': 'delete_account'}
        message.body = JsonFormat.json_message({
            "account_name": "test-aws",
            "cloud": "ec2",
            "requesting_user": "user2"
        })

        self.jobcreator._handle_listener_message(message)

        mock_publish.assert_called_once_with(
            'credentials', 'delete_account',
            JsonFormat.json_message(json.loads(message.body))
        )
        message.ack.assert_called_once_with()

    def test_jobcreator_handle_listener_message_unkown(self):
        message = MagicMock()
        message.method = {'routing_key': 'add_user'}
        message.body = '{}'
        self.jobcreator._handle_listener_message(message)

        self.jobcreator.log.warning.assert_called_once_with(
            'Received unknown message type: add_user. '
            'Message: {0}'.format(message.body)
        )

    def test_jobcreator_handle_invalid_listener_message(self):
        message = MagicMock()
        message.body = 'invalid message'

        self.jobcreator._handle_listener_message(message)
        self.jobcreator.log.warning.assert_called_once_with(
            'Invalid message received: invalid message.'
        )

        message.ack.assert_called_once_with()

    @patch.object(JobCreatorService, '_publish')
    def test_jobcreator_publish_delete_job_message(self, mock_publish):
        message = MagicMock()
        message.body = '{"job_delete": "1"}'
        self.jobcreator._handle_service_message(message)
        mock_publish.assert_has_calls([
            call(
                'obs', 'job_document',
                JsonFormat.json_message({"obs_job_delete": "1"})
            )
        ])

    @patch.object(JobCreatorService, 'publish_job_doc')
    def test_jobcreator_process_new_job(self, mock_publish_doc):
        self.jobcreator.jobs = {}

        with open('../data/job.json', 'r') as job_doc:
            job = json.dumps(json.load(job_doc))

        message = MagicMock()
        message.body = job

        self.jobcreator._handle_service_message(message)

        assert self.jobcreator.jobs['12345678-1234-1234-1234-123456789012']
        mock_publish_doc.assert_called_once_with(
            'credentials',
            JsonFormat.json_message({
                "credentials_job_check": {
                    "id": "12345678-1234-1234-1234-123456789012",
                    "cloud": "ec2",
                    "cloud_accounts": [
                        {
                            "name": "test-aws-gov"
                        }
                    ],
                    "cloud_groups": ["test"],
                    "requesting_user": "user1"
                }
            })
        )

    @patch.object(JobCreatorService, 'publish_job_doc')
    def test_jobcreator_process_new_azure_job(
        self, mock_publish_doc
    ):
        self.jobcreator.jobs = {}

        with open('../data/azure_job.json', 'r') as job_doc:
            job = json.dumps(json.load(job_doc))

        message = MagicMock()
        message.body = job

        self.jobcreator._handle_service_message(message)

        assert self.jobcreator.jobs['12345678-1234-1234-1234-123456789012']
        mock_publish_doc.assert_called_once_with(
            'credentials',
            JsonFormat.json_message({
                "credentials_job_check": {
                    "id": "12345678-1234-1234-1234-123456789012",
                    "cloud": "azure",
                    "cloud_accounts": [
                        {
                            "name": "test-azure",
                            "region": "southcentralus",
                            "source_resource_group": "rg-1",
                            "source_storage_account": "sa1",
                            "source_container": "container1",
                            "destination_resource_group": "rg-2",
                            "destination_storage_account": "sa2",
                            "destination_container": "container2"
                        }
                    ],
                    "cloud_groups": ["test-azure-group"],
                    "requesting_user": "user1"
                }
            })
        )

    @patch.object(JobCreatorService, 'consume_queue')
    @patch.object(JobCreatorService, 'stop')
    def test_jobcreator_start(self, mock_stop, mock_consume_queue):
        self.jobcreator.channel = self.channel

        self.jobcreator.start()
        self.channel.start_consuming.assert_called_once_with()

        mock_consume_queue.assert_has_calls([
            call(self.jobcreator._handle_service_message),
            call(
                self.jobcreator._handle_listener_message,
                queue_name='listener'
            )
        ])
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
