from pytest import raises
from unittest.mock import (
    MagicMock, Mock, patch
)

from mash.services.create.oci_job import OCICreateJob
from mash.mash_exceptions import MashCreateException
from mash.services.base_config import BaseConfig


class TestOCICreateJob(object):
    def setup(self):
        self.config = BaseConfig(
            config_file='test/data/mash_config.yaml'
        )

        self.credentials = {
            'test': {
                'signing_key': 'test key',
                'fingerprint': 'fake fingerprint'
            }
        }
        job_doc = {
            'id': '1',
            'last_service': 'create',
            'cloud': 'oci',
            'requesting_user': 'user1',
            'utctime': 'now',
            'region': 'us-phoenix-1',
            'account': 'test',
            'bucket': 'images',
            'cloud_image_name': 'sles-12-sp4-v20180909',
            'image_description': 'description 20180909',
            'oci_user_id': 'ocid1.user.oc1..',
            'tenancy': 'ocid1.tenancy.oc1..',
            'compartment_id': 'ocid1.compartment.oc1..',
            'operating_system': 'SLES',
            'operating_system_version': '12SP2'
        }

        self.job = OCICreateJob(job_doc, self.config)
        self.job.credentials = self.credentials

    def test_post_init_incomplete_arguments(self):
        job_doc = {
            'id': '1',
            'last_service': 'create',
            'requesting_user': 'user1',
            'cloud': 'oci',
            'utctime': 'now'
        }

        with raises(MashCreateException):
            OCICreateJob(job_doc, self.config)

    @patch('mash.services.create.oci_job.ComputeClientCompositeOperations')
    @patch('mash.services.create.oci_job.ComputeClient')
    @patch('builtins.open')
    def test_create(
        self, mock_open, mock_compute_client, mock_compute_client_composite
    ):
        open_handle = MagicMock()
        open_handle.__enter__.return_value = open_handle
        mock_open.return_value = open_handle

        compute_client = MagicMock()
        mock_compute_client.return_value = compute_client

        compute_composite_client = Mock()
        mock_compute_client_composite.return_value = compute_composite_client

        self.job.source_regions = {
            'cloud_image_name': 'sles-12-sp4-v20180909',
            'object_name': 'sles-12-sp4-v20180909.tar.gz',
            'namespace': 'sles'
        }
        self.job.run_job()

        compute_composite_client.create_image_and_wait_for_state.call_count == 1
