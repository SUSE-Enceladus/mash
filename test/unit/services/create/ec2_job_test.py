from pytest import raises
from unittest.mock import Mock, patch

from mash.services.create.ec2_job import EC2CreateJob
from mash.mash_exceptions import MashUploadException
from mash.services.base_config import BaseConfig


class TestAmazonCreateJob(object):
    def setup_method(self):
        self.config = BaseConfig(
            config_file='test/data/mash_config.yaml'
        )

        self.credentials = {
            'test': {
                'access_key_id': 'access-key',
                'secret_access_key': 'secret-access-key'
            }
        }
        job_doc = {
            'cloud_architecture': 'aarch64',
            'id': '1',
            'last_service': 'create',
            'cloud': 'ec2',
            'requesting_user': 'user1',
            'utctime': 'now',
            'target_regions': {
                'us-east-1': {
                    'account': 'test',
                    'billing_codes': None,
                    'regions': ['us-east-1', 'us-east-2']
                }
            },
            'cloud_image_name': 'name v{date}',
            'image_description': 'description',
            'use_build_time': True,
            'tpm_support': 'v2.0',
            'imds_version': 'v2.0',
            'upload_workers': 4,
            'upload_retries': 5,
            'upload_timeout': 600,
            'write_zero_blocks': True
        }
        self.job = EC2CreateJob(job_doc, self.config)
        self.job._log_callback = Mock()
        self.job.status_msg['image_file'] = 'file'
        self.job.status_msg['build_time'] = '1601061355'
        self.job.status_msg['source_regions'] = {'us-east-1': 'ami_id'}
        self.job.credentials = self.credentials

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'id': '1',
            'last_service': 'create',
            'requesting_user': 'user1',
            'cloud': 'ec2',
            'utctime': 'now'
        }

        with raises(MashUploadException):
            EC2CreateJob(job_doc, self.config)

        job_doc['target_regions'] = {'name': {'account': 'info'}}
        with raises(MashUploadException):
            EC2CreateJob(job_doc, self.config)

        job_doc['cloud_image_name'] = 'name'
        with raises(MashUploadException):
            EC2CreateJob(job_doc, self.config)

    def test_missing_date_format_exception(self):
        self.job.status_msg['build_time'] = 'unknown'

        with raises(MashUploadException):
            self.job.run_job()

    @patch('mash.services.create.ec2_job.cleanup_all_ec2_images')
    @patch('mash.services.create.ec2_job.image_exists')
    @patch('mash.services.create.ec2_job.cleanup_ec2_image')
    @patch('mash.services.create.ec2_job.get_client')
    @patch('mash.services.create.ec2_job.EC2ImageUploader')
    def test_create(
        self, mock_EC2ImageUploader, mock_get_client, mock_cleanup_image,
        mock_image_exists, mock_cleanup_all_images
    ):
        mock_image_exists.return_value = False

        ec2_upload = Mock()
        ec2_upload.create_image.return_value = 'ami_id'
        mock_EC2ImageUploader.return_value = ec2_upload

        self.job.run_job()
        mock_get_client.assert_called_once_with(
            'ec2', 'access-key', 'secret-access-key', 'us-east-1'
        )
        mock_EC2ImageUploader.assert_called_once_with(
            access_key='access-key',
            backing_store='gp3',
            billing_codes=None,
            ena_support=True,
            image_arch='arm64',
            image_description='description',
            image_name='name v20200925',
            root_volume_size=10,
            secret_key='secret-access-key',
            sriov_type='simple',
            wait_count=3,
            log_callback=self.job._log_callback,
            image_tags=None,
            tpm_support='v2.0',
            boot_mode='uefi-preferred',
            imds_support='v2.0',
            upload_workers=4,
            upload_retries=5,
            upload_timeout=600,
            write_zero_blocks=True
        )
        ec2_upload.set_region.assert_called_once_with('us-east-1')
        ec2_upload.create_image.assert_called_once_with('file')
        ec2_upload.create_image_use_root_swap.assert_not_called()

        # Image create error
        ec2_upload.create_image.side_effect = ['ami_id', Exception('Failed!')]
        mock_cleanup_image.side_effect = Exception
        self.job.target_regions['us-east-2'] = {
            'account': 'test',
            'billing_codes': None,
            'regions': ['us-east-2']
        }

        self.job.run_job()

        self.job._log_callback.error.assert_called_once_with(
            'Image creation in account test failed with: Failed!'
        )
        mock_cleanup_image.assert_called_once_with(
            'access-key',
            'secret-access-key',
            self.job._log_callback,
            'us-east-1',
            image_id='ami_id'
        )

        # Image exists and not force replace image
        mock_image_exists.return_value = True
        self.job.run_job()

        msg = 'Image creation in account test failed with: name' \
              ' v20200925 already exists. Use force_replace_image ' \
              'to replace the existing image.'
        assert msg in self.job.status_msg['errors']

        # Image exists and force replace image
        self.job.force_replace_image = True
        self.job.run_job()
        assert mock_cleanup_all_images.call_count == 1

    def _root_swap_job(self, region_info, **kwargs):
        job_doc = {
            'cloud_architecture': 'aarch64',
            'id': '1',
            'last_service': 'upload',
            'cloud': 'ec2',
            'requesting_user': 'user1',
            'utctime': 'now',
            'target_regions': {'us-east-1': region_info},
            'cloud_image_name': 'name',
            'image_description': 'description',
            'upload_workers': 4,
            'write_zero_blocks': True
        }
        job_doc.update(kwargs)
        job = EC2CreateJob(job_doc, self.config)
        job._log_callback = Mock()
        job.status_msg['image_file'] = 'file'
        job.credentials = self.credentials
        return job

    @patch('mash.services.create.ec2_job.image_exists')
    @patch('mash.services.create.ec2_job.get_client')
    @patch('mash.services.create.ec2_job.EC2ImageUploader')
    def test_create_root_swap(
        self, mock_EC2ImageUploader, mock_get_client, mock_image_exists
    ):
        mock_image_exists.return_value = False

        ec2_upload = Mock()
        ec2_upload.create_image_use_root_swap.return_value = 'ami_id'
        mock_EC2ImageUploader.return_value = ec2_upload

        job = self._root_swap_job(
            {
                'account': 'test',
                'helper_image': 'ami-bc5b48d0',
                'billing_codes': None,
                'use_root_swap': True,
                'subnet': 'subnet-123456789',
                'regions': ['us-east-1']
            },
            launch_inst_type='m1.large'
        )
        job.run_job()

        kwargs = mock_EC2ImageUploader.call_args[1]
        assert kwargs['launch_ami'] == 'ami-bc5b48d0'
        assert kwargs['launch_inst_type'] == 'm1.large'
        assert kwargs['vpc_subnet_id'] == 'subnet-123456789'
        assert kwargs['upload_workers'] == 4
        assert kwargs['write_zero_blocks'] is True
        # The donor instance is not accessed, no ssh or security group
        for key in (
            'security_group_ids', 'ssh_key_pair_name', 'use_grub2',
            'ssh_key_private_key_file', 'bootkernel', 'image_virt_type',
            'inst_user_name', 'ssh_timeout', 'use_private_ip'
        ):
            assert key not in kwargs
        ec2_upload.create_image_use_root_swap.assert_called_once_with('file')
        ec2_upload.create_image.assert_not_called()
        assert job.status_msg['source_regions'] == {'us-east-1': 'ami_id'}

    @patch('mash.services.create.ec2_job.image_exists')
    @patch('mash.services.create.ec2_job.get_client')
    @patch('mash.services.create.ec2_job.EC2ImageUploader')
    def test_create_root_swap_defaults(
        self, mock_EC2ImageUploader, mock_get_client, mock_image_exists
    ):
        """No subnet and no instance type, default VPC and instance type"""
        mock_image_exists.return_value = False

        ec2_upload = Mock()
        ec2_upload.create_image_use_root_swap.return_value = 'ami_id'
        mock_EC2ImageUploader.return_value = ec2_upload

        job = self._root_swap_job({
            'account': 'test',
            'helper_image': 'ami-bc5b48d0',
            'billing_codes': None,
            'use_root_swap': True,
            'subnet': None,
            'regions': ['us-east-1']
        })
        job.run_job()

        kwargs = mock_EC2ImageUploader.call_args[1]
        assert kwargs['launch_inst_type'] == 't3.micro'
        assert kwargs['vpc_subnet_id'] == ''
        ec2_upload.create_image_use_root_swap.assert_called_once_with('file')

    @patch('mash.services.create.ec2_job.image_exists')
    @patch('mash.services.create.ec2_job.get_client')
    @patch('mash.services.create.ec2_job.EC2ImageUploader')
    def test_create_no_root_swap_ignores_helper_settings(
        self, mock_EC2ImageUploader, mock_get_client, mock_image_exists
    ):
        """Without root swap the helper settings are not passed on"""
        mock_image_exists.return_value = False

        ec2_upload = Mock()
        ec2_upload.create_image.return_value = 'ami_id'
        mock_EC2ImageUploader.return_value = ec2_upload

        job = self._root_swap_job(
            {
                'account': 'test',
                'helper_image': 'ami-bc5b48d0',
                'billing_codes': None,
                'use_root_swap': False,
                'subnet': 'subnet-123456789',
                'regions': ['us-east-1']
            },
            launch_inst_type='m1.large'
        )
        job.run_job()

        kwargs = mock_EC2ImageUploader.call_args[1]
        for key in ('launch_ami', 'launch_inst_type', 'vpc_subnet_id'):
            assert key not in kwargs
        ec2_upload.create_image.assert_called_once_with('file')
        ec2_upload.create_image_use_root_swap.assert_not_called()
        assert job.status_msg['source_regions'] == {'us-east-1': 'ami_id'}
