from unittest.mock import MagicMock, Mock, patch

from mash.services.mash_service import MashService
from mash.services.replication.service import ReplicationService
from mash.services.replication.azure_job import AzureReplicationJob
from mash.services.replication.ec2_job import EC2ReplicationJob
from mash.services.replication.gce_job import GCEReplicationJob
from mash.utils.json_format import JsonFormat

open_name = "builtins.open"


class TestReplicationService(object):

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

        self.error_message = JsonFormat.json_message({
            "replication_result": {
                "id": "1",
                "status": "failed"
            }
        })
        self.status_message = JsonFormat.json_message({
            "replication_result": {
                "cloud_image_name": "image123",
                "id": "1",
                "status": "success"
            }
        })

        self.replication = ReplicationService()
        self.replication.jobs = {}
        self.replication.log = Mock()

        self.replication.service_exchange = 'replication'
        self.replication.service_queue = 'service'
        self.replication.listener_queue = 'listener'
        self.replication.job_document_key = 'job_document'
        self.replication.listener_msg_key = 'listener_msg'
        self.replication.next_service = 'publisher'

    @patch.object(ReplicationService, '_create_job')
    def test_replication_add_job(self, mock_create_job):
        job_config = {
            'id': '1', 'cloud': 'ec2', 'utctime': 'now',
        }

        self.replication._add_job(job_config)

        mock_create_job.assert_called_once_with(
            EC2ReplicationJob,
            job_config
        )

    @patch.object(ReplicationService, '_create_job')
    def test_replication_add_job_azure(self, mock_create_job):
        job_config = {
            'id': '1', 'cloud': 'azure', 'utctime': 'now',
        }

        self.replication._add_job(job_config)

        mock_create_job.assert_called_once_with(
            AzureReplicationJob,
            job_config
        )

    @patch.object(ReplicationService, '_create_job')
    def test_replication_add_job_gce(self, mock_create_job):
        job_config = {
            'id': '1', 'cloud': 'gce', 'utctime': 'now',
        }

        self.replication._add_job(job_config)

        mock_create_job.assert_called_once_with(
            GCEReplicationJob,
            job_config
        )

    def test_replication_add_job_exists(self):
        job = Mock()
        job.id = '1'
        self.replication.jobs['1'] = job
        job_config = {
            'id': '1', 'image_desc': 'image 123',
            'cloud': 'ec2', 'utctime': 'now',
        }

        self.replication._add_job(job_config)
        self.replication.log.warning.assert_called_once_with(
            'Job already queued.',
            extra={'job_id': '1'}
        )

    def test_replication_add_job_invalid_cloud(self):
        job_config = {
            'id': '1', 'image_desc': 'image 123',
            'cloud': 'fake', 'utctime': 'now',
        }

        self.replication._add_job(job_config)
        self.replication.log.error.assert_called_once_with(
            'Cloud fake is not supported.'
        )

    def test_replication_get_status_message(self):
        job = Mock()
        job.id = '1'
        job.status = 'success'
        job.cloud_image_name = 'image123'

        data = self.replication._get_status_message(job)
        assert data == self.status_message

    def test_replication_get_status_message_error(self):
        job = Mock()
        job.id = '1'
        job.status = 'failed'

        data = self.replication._get_status_message(job)
        assert data == self.error_message

    def test_replication_get_listener_msg_args(self):
        args = self.replication._get_listener_msg_args()
        assert args == ['cloud_image_name', 'source_regions']
