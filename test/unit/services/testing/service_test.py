from unittest.mock import MagicMock, Mock, patch

from mash.services.mash_service import MashService
from mash.services.testing.service import TestingService
from mash.services.testing.azure_job import AzureTestingJob
from mash.services.testing.ec2_job import EC2TestingJob
from mash.services.testing.gce_job import GCETestingJob
from mash.utils.json_format import JsonFormat

open_name = "builtins.open"


class TestIPATestingService(object):

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
        self.testing.listener_msg_args = ['cloud_image_name']
        self.testing.status_msg_args = ['cloud_image_name']

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

    def test_testing_service_init(self):
        self.testing.config = self.config
        self.testing.config.get_ssh_private_key_file.return_value = \
            'private.key'
        self.testing.config.get_ipa_timeout.return_value = 600

        self.testing.service_init()

    @patch.object(TestingService, '_create_job')
    def test_testing_add_job(self, mock_create_job):
        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': job.id, 'cloud': 'ec2'}

        self.testing.add_job({'id': job.id, 'cloud': 'ec2'})

        mock_create_job.assert_called_once_with(
            EC2TestingJob, {
                'id': job.id,
                'cloud': 'ec2'
            }
        )

    @patch.object(TestingService, '_create_job')
    def test_testing_add_azure_job(self, mock_create_job):
        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': job.id, 'cloud': 'azure'}

        self.testing.add_job({'id': job.id, 'cloud': 'azure'})

        mock_create_job.assert_called_once_with(
            AzureTestingJob, {
                'id': job.id,
                'cloud': 'azure'
            }
        )

    @patch.object(TestingService, '_create_job')
    def test_testing_add_gce_job(self, mock_create_job):
        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': job.id, 'cloud': 'gce'}

        self.testing.add_job({'id': job.id, 'cloud': 'gce'})

        mock_create_job.assert_called_once_with(
            GCETestingJob, {
                'id': job.id,
                'cloud': 'gce'
            }
        )

    def test_testing_add_job_exists(self):
        job = Mock()
        job.id = '1'
        job.get_metadata.return_value = {'job_id': job.id}

        self.testing.jobs[job.id] = Mock()
        self.testing.add_job({'id': job.id, 'cloud': 'ec2'})

        self.testing.log.warning.assert_called_once_with(
            'Job already queued.',
            extra={'job_id': job.id}
        )

    def test_testing_add_job_invalid(self):
        self.testing.add_job({'id': '1', 'cloud': 'fake'})
        self.testing.log.error.assert_called_once_with(
            'Cloud fake is not supported.'
        )
