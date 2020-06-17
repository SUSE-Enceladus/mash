from pytest import raises
from unittest.mock import Mock, patch

from mash.services.mash_job import MashJob
from mash.mash_exceptions import MashJobException


class TestMashJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'test',
            'requesting_user': 'user1',
            'cloud': 'ec2',
            'utctime': 'now'
        }
        self.config = Mock()
        self.config.get_credentials_url.return_value = 'http://localhost:5000'

    def test_missing_key(self):
        del self.job_config['cloud']

        with raises(MashJobException):
            MashJob(self.job_config, self.config)

    def test_valid_job(self):
        job = MashJob(self.job_config, self.config)

        assert job.id == '1'
        assert job.cloud == 'ec2'
        assert job.utctime == 'now'

    @patch('mash.services.mash_job.handle_request')
    def test_request_credentials(self, mock_handle_request):
        callback = Mock()

        job = MashJob(self.job_config, self.config)
        job.log_callback = callback
        job.iteration_count = 0

        response = Mock()
        response.json.return_value = {'acnt1': {'super': 'secret'}}
        mock_handle_request.return_value = response

        job.request_credentials(['acnt1'])

        assert job.credentials['acnt1']['super'] == 'secret'
        mock_handle_request.assert_called_once_with(
            'http://localhost:5000',
            'credentials/',
            'get',
            job_data={
                'cloud': 'ec2',
                'cloud_accounts': ['acnt1'],
                'requesting_user': 'user1'
            }
        )

        # Test credentials already exist
        job.request_credentials(['acnt1'])

        # Test request failed
        mock_handle_request.side_effect = Exception('Failed')
        job.credentials = None

        with raises(MashJobException):
            job.request_credentials(['acnt1'])

    def test_run_job(self):
        job = MashJob(self.job_config, self.config)

        with raises(NotImplementedError):
            job.run_job()

    def test_job_get_job_id(self):
        job = MashJob(self.job_config, self.config)
        metadata = job.get_job_id()
        assert metadata == {'job_id': '1'}

    def test_job_file_property(self):
        job = MashJob(self.job_config, self.config)
        job.job_file = 'test.file'
        assert job.job_file == 'test.file'

    def test_set_cloud_image_name(self):
        job = MashJob(self.job_config, self.config)
        job.cloud_image_name = 'name123'
        assert job.cloud_image_name == 'name123'

    @patch('mash.services.mash_job.logging')
    def test_set_log_callback(self, mock_logging):
        job = MashJob(self.job_config, self.config)
        adapter = Mock()
        mock_logging.LoggerAdapter.return_value = adapter
        job.log_callback = Mock()

        assert job.log_callback == adapter

    @patch.object(MashJob, 'run_job')
    def test_process_job(self, mock_run_job):
        job = MashJob(self.job_config, self.config)
        job._log_callback = Mock()
        job.process_job()
        mock_run_job.assert_called_once_with()
