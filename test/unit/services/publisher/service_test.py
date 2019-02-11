from unittest.mock import MagicMock, Mock, patch

from mash.services.mash_service import MashService
from mash.services.publisher.service import PublisherService
from mash.services.publisher.azure_job import AzurePublisherJob
from mash.services.publisher.ec2_job import EC2PublisherJob
from mash.services.publisher.gce_job import GCEPublisherJob
from mash.utils.json_format import JsonFormat

open_name = "builtins.open"


class TestPublisherService(object):

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
            "publisher_result": {
                "id": "1",
                "status": "failed"
            }
        })
        self.status_message = JsonFormat.json_message({
            "publisher_result": {
                "cloud_image_name": "image123",
                "id": "1",
                "status": "success"
            }
        })

        self.publisher = PublisherService()
        self.publisher.jobs = {}
        self.publisher.log = Mock()

        self.publisher.service_exchange = 'publisher'
        self.publisher.service_queue = 'service'
        self.publisher.listener_queue = 'listener'
        self.publisher.job_document_key = 'job_document'
        self.publisher.listener_msg_key = 'listener_msg'
        self.publisher.next_service = 'deprecation'

    @patch.object(PublisherService, '_create_job')
    def test_publisher_add_job(self, mock_create_job):
        job_config = {
            'id': '1', 'cloud': 'ec2', 'utctime': 'now',
        }

        self.publisher._add_job(job_config)

        mock_create_job.assert_called_once_with(
            EC2PublisherJob,
            job_config
        )

    @patch.object(PublisherService, '_create_job')
    def test_publisher_add_job_gce(self, mock_create_job):
        job_config = {
            'id': '1', 'cloud': 'gce', 'utctime': 'now',
        }

        self.publisher._add_job(job_config)

        mock_create_job.assert_called_once_with(
            GCEPublisherJob,
            job_config
        )

    @patch.object(PublisherService, '_create_job')
    def test_publisher_add_job_azure(self, mock_create_job):
        job_config = {
            'id': '1', 'cloud': 'azure', 'utctime': 'now',
        }

        self.publisher._add_job(job_config)

        mock_create_job.assert_called_once_with(
            AzurePublisherJob,
            job_config
        )

    def test_publisher_add_job_exists(self):
        job = Mock()
        job.id = '1'
        self.publisher.jobs['1'] = job
        job_config = {
            'id': '1', 'image_desc': 'image 123',
            'cloud': 'ec2', 'utctime': 'now',
        }

        self.publisher._add_job(job_config)
        self.publisher.log.warning.assert_called_once_with(
            'Job already queued.',
            extra={'job_id': '1'}
        )

    def test_publisher_add_job_invalid_cloud(self):
        job_config = {
            'id': '1', 'image_desc': 'image 123',
            'cloud': 'fake', 'utctime': 'now',
        }

        self.publisher._add_job(job_config)
        self.publisher.log.error.assert_called_once_with(
            'Cloud fake is not supported.'
        )

    def test_publisher_get_status_message(self):
        job = Mock()
        job.id = '1'
        job.status = 'success'
        job.cloud_image_name = 'image123'

        data = self.publisher._get_status_message(job)
        assert data == self.status_message

    def test_publisher_get_status_message_error(self):
        job = Mock()
        job.id = '1'
        job.status = 'failed'

        data = self.publisher._get_status_message(job)
        assert data == self.error_message

    def test_publisher_get_listener_msg_args(self):
        args = self.publisher._get_listener_msg_args()
        assert args == ['cloud_image_name']
