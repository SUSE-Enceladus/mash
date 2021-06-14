import pytest

from unittest.mock import Mock, patch

from mash.services.test.aliyun_job import AliyunTestJob
from mash.mash_exceptions import MashTestException
from mash.services.test.config import TestConfig


class TestAliyunTestJob(object):
    def setup(self):
        self.job_config = {
            'id': '1',
            'last_service': 'test',
            'cloud': 'aliyun',
            'requesting_user': 'user1',
            'account': 'test-aliyun',
            'bucket': 'images',
            'region': 'cn-beijing',
            'security_group_id': 'sg1',
            'vswitch_id': 'vs1',
            'tests': ['test_stuff'],
            'utctime': 'now'
        }
        self.config = TestConfig(config_file='test/data/mash_config.yaml')

    def test_aliyun_missing_key(self):
        del self.job_config['account']

        with pytest.raises(MashTestException):
            AliyunTestJob(self.job_config, self.config)

    @patch.object(AliyunTestJob, 'cleanup_image')
    @patch('mash.services.test.aliyun_job.os')
    @patch('mash.services.test.aliyun_job.create_ssh_key_pair')
    @patch('mash.services.test.aliyun_job.random')
    @patch('mash.utils.mash_utils.NamedTemporaryFile')
    @patch('mash.services.test.img_proof_helper.test_image')
    def test_aliyun_image_proof(
        self, mock_test_image, mock_temp_file, mock_random,
        mock_create_ssh_key_pair, mock_os, mock_cleanup_image
    ):
        tmp_file = Mock()
        tmp_file.name = '/tmp/acnt.file'
        mock_temp_file.return_value = tmp_file
        mock_test_image.return_value = (
            0,
            {
                'tests': [
                    {
                        "outcome": "passed",
                        "test_index": 0,
                        "name": "test_sles_aliyun_metadata.py::test_sles_aliyun_metadata[paramiko://10.0.0.10]"
                    }
                ],
                'summary': {
                    "duration": 2.839970827102661,
                    "passed": 1,
                    "num_tests": 1
                },
                'info': {
                    'log_file': 'test.log',
                    'results_file': 'test.results',
                    'instance': 'instance-abc'
                }
            }
        )
        mock_random.choice.return_value = 'ecs.t5-lc1m1.small'
        mock_os.path.exists.return_value = False

        job = AliyunTestJob(self.job_config, self.config)
        job._log_callback = Mock()
        mock_create_ssh_key_pair.assert_called_once_with('/var/lib/mash/ssh_key')
        job.credentials = {
            'test-aliyun': {
                'access_key': '123456789',
                'access_secret': '987654321'
            }
        }
        job.status_msg['cloud_image_name'] = 'name.qcow2'
        job.status_msg['object_name'] = 'name.qcow2'
        job.status_msg['source_regions'] = {'cn-beijing': 'i-123456'}
        job.run_job()

        mock_test_image.assert_called_once_with(
            'aliyun',
            access_key_id=None,
            availability_domain=None,
            cleanup=True,
            compartment_id=None,
            description=job.description,
            distro='sles',
            image_id='i-123456',
            instance_type='ecs.t5-lc1m1.small',
            log_level=10,
            oci_user_id=None,
            region='cn-beijing',
            secret_access_key=None,
            security_group_id='sg1',
            service_account_file=None,
            signing_key_file=None,
            signing_key_fingerprint=None,
            ssh_key_name=None,
            ssh_private_key_file='/var/lib/mash/ssh_key',
            ssh_user='ali-user',
            subnet_id=None,
            tenancy=None,
            tests=['test_stuff'],
            timeout=600,
            enable_secure_boot=False,
            image_project=None,
            log_callback=job._log_callback,
            prefix_name='mash',
            sev_capable=None,
            access_key='123456789',
            access_secret='987654321',
            v_switch_id='vs1',
            use_gvnic=None
        )
        job._log_callback.info.reset_mock()

        # Failed job test
        mock_test_image.side_effect = Exception('Tests broken!')

        job.run_job()

        job._log_callback.warning.assert_called_once_with(
            'Image tests failed in region: cn-beijing.'
        )
        assert 'Tests broken!' in job._log_callback.error.mock_calls[0][1][0]

    @patch('mash.services.test.aliyun_job.create_ssh_key_pair')
    @patch('mash.services.test.aliyun_job.AliyunImage')
    def test_aliyun_image_cleanup_after_test(
        self,
        mock_aliyun_image,
        mock_create_ssh_key_pair
    ):
        aliyun_image = Mock()
        mock_aliyun_image.return_value = aliyun_image

        job = AliyunTestJob(self.job_config, self.config)
        job._log_callback = Mock()
        job.cloud_image_name = 'name.qcow2'
        job.object_name = 'name.qcow2'
        credentials = {
            'access_key': '123456789',
            'access_secret': '987654321'
        }

        job.cleanup_image(credentials)

        job._log_callback.info.assert_called_once_with(
            'Cleaning up image: name.qcow2 in region: cn-beijing.'
        )

        # Test failed cleanup
        job._log_callback.info.reset_mock()
        aliyun_image.delete_compute_image.side_effect = Exception(
            'Image not found!'
        )
        aliyun_image.delete_storage_blob.side_effect = Exception(
            'Image not found!'
        )
        job.cleanup_image(credentials)

        job._log_callback.info.assert_called_once_with(
            'Cleaning up image: name.qcow2 in region: cn-beijing.'
        )
        assert job._log_callback.warning.call_count == 2
