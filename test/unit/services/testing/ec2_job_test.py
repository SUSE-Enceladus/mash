import jwt

from pytest import raises
from unittest.mock import call, patch

from mash.mash_exceptions import MashTestingException
from mash.services.testing.ec2_job import EC2TestingJob


class TestEC2TestingJob(object):
    def setup(self):
        self.job_config = {
            'account': 'account',
            'distro': 'SLES',
            'id': '1',
            'provider': 'ec2',
            'tests': 'test_stuff',
            'utctime': 'now'
        }

    def test_get_credential_request(self):
        job = EC2TestingJob(**self.job_config)
        request = job._get_credential_request()

        decoded = jwt.decode(
            request,
            'mash',
            algorithm='HS256'
        )

        assert 'credentials' in decoded
        assert decoded['credentials']['csp'] == 'ec2'
        assert decoded['credentials']['account'] == 'account'

    @patch('mash.services.testing.ec2_job.jwt')
    def test_process_credentials(self, mock_jwt):
        mock_jwt.decode.return_value = {
            'credentials': {
                'secret_access_key': '123',
                'access_key_id': 'key123',
                'ssh_key_name': 'temp_key',
                'ssh_private_key': '123456789'
            }
        }

        job = EC2TestingJob(**self.job_config)
        job._process_credentials('fake_msg')

        assert job.secret_access_key == '123'
        assert job.access_key_id == 'key123'
        assert job.ssh_key_name == 'temp_key'
        assert job.ssh_private_key == '123456789'

    @patch('mash.services.testing.ec2_job.jwt')
    def test_process_credentials_error(self, mock_jwt):
        mock_jwt.decode.return_value = {
            'credentials': {
                'error': 'ENOTALLOWED'
            }
        }

        job = EC2TestingJob(**self.job_config)

        msg = 'Credentials not found in token.'
        with raises(MashTestingException) as e:
            job._process_credentials('fake_msg')

        assert str(e.value) == msg

    @patch('mash.services.testing.ec2_job.jwt')
    def test_process_credentials_expired(self, mock_jwt):
        mock_jwt.decode.side_effect = jwt.ExpiredSignatureError()

        job = EC2TestingJob(**self.job_config)

        msg = 'Token has expired, cannot retrieve credentials.'
        with raises(MashTestingException) as e:
            job._process_credentials('fake_msg')

        assert str(e.value) == msg

    @patch('mash.services.testing.ec2_job.jwt')
    def test_process_credentials_invalid(self, mock_jwt):
        mock_jwt.decode.side_effect = jwt.InvalidTokenError('Broken!')

        job = EC2TestingJob(**self.job_config)

        msg = 'Invalid token, cannot retrieve credentials: Broken!'
        with raises(MashTestingException) as e:
            job._process_credentials('fake_msg')

        assert str(e.value) == msg

    @patch('mash.services.testing.ec2_job.test_image')
    @patch.object(EC2TestingJob, 'send_log')
    def test_testing_run_test(self, mock_send_log, mock_test_image):
        mock_test_image.return_value = (
            0,
            {
                'tests': '...',
                'summary': '...',
                'info': {
                    'log_file': 'test.log',
                    'results_file': 'test.results'
                }
            }
        )

        job = EC2TestingJob(**self.job_config)
        job.image_id = 'image123'
        job._run_tests()

        mock_test_image.assert_called_once_with(
            'ec2',
            access_key_id=job.access_key_id,
            account='account',
            desc=job.desc,
            distro='SLES',
            image_id='image123',
            instance_type=job.instance_type,
            log_level=30,
            region=job.region,
            secret_access_key=job.secret_access_key,
            ssh_key_name=job.ssh_key_name,
            ssh_private_key=job.ssh_private_key,
            ssh_user=job.ssh_user,
            tests=['test_stuff']
        )

        mock_send_log.assert_has_calls(
            [call('Log file: test.log'), call('Results file: test.results')]
        )
