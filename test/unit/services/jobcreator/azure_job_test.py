import pytest

from unittest.mock import patch

from mash.services.jobcreator.azure_job import AzureJob


class TestJobCreatorAzureJob(object):
    @patch.object(AzureJob, '_get_account_info')
    def setup(self, mock_get_acnt_info):
        self.job = AzureJob(
            '123', {}, {}, 'azure', ['test-aws'], [], 'test-user', 'pint',
            'now', 'test-image', 'test-cloud-image',
            'test-old-cloud-image-name', 'test-project', 'image description',
            'sles', 'test-stuff',
            [{"package": ["name", "and", "constraints"]}], 'instance type'
        )

    @pytest.mark.parametrize(
        'method',
        [
            'get_deprecation_regions',
            'get_publisher_message',
            'get_publisher_regions'
        ]
    )
    def test_not_implemented_methods(self, method):
        # Test methods that are not implemented yet
        with pytest.raises(NotImplementedError) as error:
            getattr(self.job, method)()

        assert 'TODO' == str(error.value)
