from unittest.mock import MagicMock, Mock, patch

from mash.services.mash_service import MashService
from mash.services.deprecation.service import DeprecationService
from mash.services.deprecation.azure_job import AzureDeprecationJob
from mash.services.deprecation.ec2_job import EC2DeprecationJob
from mash.services.deprecation.gce_job import GCEDeprecationJob
from mash.utils.json_format import JsonFormat

open_name = "builtins.open"


class TestDeprecationService(object):

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
            "deprecation_result": {
                "id": "1",
                "status": "failed"
            }
        })
        self.status_message = JsonFormat.json_message({
            "deprecation_result": {
                "cloud_image_name": "image123",
                "id": "1",
                "status": "success"
            }
        })

        self.deprecation = DeprecationService()
        self.deprecation.jobs = {}
        self.deprecation.log = Mock()

        self.deprecation.service_exchange = 'deprecation'
        self.deprecation.service_queue = 'service'
        self.deprecation.listener_queue = 'listener'
        self.deprecation.job_document_key = 'job_document'
        self.deprecation.listener_msg_key = 'listener_msg'
        self.deprecation.next_service = 'pint'

    @patch.object(DeprecationService, '_create_job')
    def test_deprecation_add_job(self, mock_create_job):
        job_config = {
            'id': '1', 'cloud': 'ec2', 'utctime': 'now',
        }

        self.deprecation.add_job(job_config)

        mock_create_job.assert_called_once_with(
            EC2DeprecationJob,
            job_config
        )

    @patch.object(DeprecationService, '_create_job')
    def test_deprecation_add_job_gce(self, mock_create_job):
        job_config = {
            'id': '1', 'cloud': 'gce', 'utctime': 'now',
        }

        self.deprecation.add_job(job_config)

        mock_create_job.assert_called_once_with(
            GCEDeprecationJob,
            job_config
        )

    @patch.object(DeprecationService, '_create_job')
    def test_deprecation_add_job_azure(self, mock_create_job):
        job_config = {
            'id': '1', 'cloud': 'azure', 'utctime': 'now',
        }

        self.deprecation.add_job(job_config)

        mock_create_job.assert_called_once_with(
            AzureDeprecationJob,
            job_config
        )

    def test_deprecation_add_job_exists(self):
        job = Mock()
        job.id = '1'
        self.deprecation.jobs['1'] = job
        job_config = {
            'id': '1', 'image_desc': 'image 123',
            'cloud': 'ec2', 'utctime': 'now',
        }

        self.deprecation.add_job(job_config)
        self.deprecation.log.warning.assert_called_once_with(
            'Job already queued.',
            extra={'job_id': '1'}
        )

    def test_deprecation_add_job_invalid_cloud(self):
        job_config = {
            'id': '1', 'image_desc': 'image 123',
            'cloud': 'fake', 'utctime': 'now',
        }

        self.deprecation.add_job(job_config)
        self.deprecation.log.exception.assert_called_once_with(
            'Cloud fake is not supported.'
        )

    def test_deprecation_get_status_message(self):
        job = Mock()
        job.id = '1'
        job.status = 'success'
        job.cloud_image_name = 'image123'

        data = self.deprecation.get_status_message(job)
        assert data == self.status_message

    def test_deprecation_get_status_message_error(self):
        job = Mock()
        job.id = '1'
        job.status = 'failed'

        data = self.deprecation.get_status_message(job)
        assert data == self.error_message
