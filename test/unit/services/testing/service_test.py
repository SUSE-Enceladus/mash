import io

from unittest.mock import call, MagicMock, Mock, patch

from mash.services.base_service import BaseService
from mash.services.testing.service import TestingService
from mash.services.testing.azure_job import AzureTestingJob
from mash.services.testing.ec2_job import EC2TestingJob
from mash.services.testing.gce_job import GCETestingJob
from mash.utils.json_format import JsonFormat

open_name = "builtins.open"


class TestIPATestingService(object):

    @patch.object(BaseService, '__init__')
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

        self.testing = TestingService()
        self.testing.jobs = {}
        self.testing.log = Mock()
        self.testing.service_exchange = 'testing'
        self.testing.service_queue = 'service'
        self.testing.job_document_key = 'job_document'
        self.testing.listener_msg_key = 'listener_msg'
        self.testing.listener_queue = 'listener'
        self.testing.ssh_private_key_file = 'private_ssh_key.file'
        self.testing.next_service = 'replication'
        self.testing.ipa_timeout = 600

        self.error_message = JsonFormat.json_message({
            "testing_result": {
                "id": "1", "status": "failed"
            }
        })

        self.status_message = JsonFormat.json_message({
            "testing_result": {
                "cloud_image_name": "image123",
                "id": "1",
                "source_regions": {"us-east-2": "ami-123456"},
                "status": "success"
            }
        })

    @patch('mash.services.testing.service.os')
    @patch.object(TestingService, '_create_ssh_key_pair')
    def test_testing_service_init(self, mock_create_ssh_key_pair, mock_os):
        mock_os.path.exists.return_value = False
        self.testing.config = self.config
        self.testing.config.get_ssh_private_key_file.return_value = \
            'private.key'
        self.testing.config.get_ipa_timeout.return_value = 600

        self.testing.service_init()
        mock_create_ssh_key_pair.assert_called_once_with()

    @patch.object(TestingService, '_create_job')
    def test_testing_add_job(self, mock_create_job):
        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': job.id, 'provider': 'ec2'}

        self.testing._add_job({'id': job.id, 'provider': 'ec2'})

        mock_create_job.assert_called_once_with(
            EC2TestingJob, {
                'id': job.id,
                'ipa_timeout': 600,
                'provider': 'ec2',
                'ssh_private_key_file': 'private_ssh_key.file'
            }
        )

    @patch.object(TestingService, '_create_job')
    def test_testing_add_azure_job(self, mock_create_job):
        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': job.id, 'provider': 'azure'}

        self.testing._add_job({'id': job.id, 'provider': 'azure'})

        mock_create_job.assert_called_once_with(
            AzureTestingJob, {
                'id': job.id,
                'ipa_timeout': 600,
                'provider': 'azure',
                'ssh_private_key_file': 'private_ssh_key.file'
            }
        )

    @patch.object(TestingService, '_create_job')
    def test_testing_add_gce_job(self, mock_create_job):
        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': job.id, 'provider': 'gce'}

        self.testing._add_job({'id': job.id, 'provider': 'gce'})

        mock_create_job.assert_called_once_with(
            GCETestingJob, {
                'id': job.id,
                'ipa_timeout': 600,
                'provider': 'gce',
                'ssh_private_key_file': 'private_ssh_key.file'
            }
        )

    def test_testing_add_job_exists(self):
        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': job.id}

        self.testing.jobs[job.id] = Mock()
        self.testing._add_job({'id': job.id, 'provider': 'ec2'})

        self.testing.log.warning.assert_called_once_with(
            'Job already queued.',
            extra={'job_id': job.id}
        )

    def test_testing_add_job_invalid(self):
        self.testing._add_job({'id': '1', 'provider': 'fake'})
        self.testing.log.error.assert_called_once_with(
            'Provider fake is not supported.'
        )

    @patch('mash.services.testing.service.rsa')
    def test_create_ssh_key_pair(self, mock_rsa):
        private_key = MagicMock()
        public_key = MagicMock()

        public_key.public_bytes.return_value = b'0987654321'

        private_key.public_key.return_value = public_key
        private_key.private_bytes.return_value = b'1234567890'

        mock_rsa.generate_private_key.return_value = private_key

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value = MagicMock(spec=io.IOBase)
            self.testing._create_ssh_key_pair()
            file_handle = mock_open.return_value.__enter__.return_value
            file_handle.write.assert_has_calls([
                call(b'1234567890'),
                call(b'0987654321')
            ])

    def test_testing_get_status_message(self):
        job = Mock()
        job.id = '1'
        job.status = "success"
        job.cloud_image_name = 'image123'
        job.test_regions = {'us-east-2': {'account': 'test-aws'}}
        job.source_regions = {'us-east-2': 'ami-123456'}

        data = self.testing._get_status_message(job)
        assert data == self.status_message

    def test_testing_get_status_message_error(self):
        job = Mock()
        job.id = '1'
        job.status = "failed"

        data = self.testing._get_status_message(job)
        assert data == self.error_message

    def test_testing_start_job(self):
        job = Mock()
        job.provider = 'ec2'
        job.account = 'test_account'
        job.distro = 'SLES'
        job.image_id = 'image123'
        job.tests = 'test1,test2'
        self.testing.jobs['1'] = job

        self.testing._start_job('1')
        job.test_image.assert_called_once_with()

    def test_testing_get_listener_msg_args(self):
        args = self.testing._get_listener_msg_args()
        assert args == ['cloud_image_name', 'source_regions']
