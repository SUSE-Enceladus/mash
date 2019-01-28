import pytest

from unittest.mock import patch

from mash.services.jobcreator.gce_job import GCEJob


class TestJobCreatorGCEJob(object):
    @patch.object(GCEJob, '_get_account_info')
    def setup(self, mock_get_acnt_info):
        self.job = GCEJob(
            '123', {}, {}, 'gce', ['test-gce'], [], 'test-user', 'pint',
            'now', 'test-image', 'test-cloud-image',
            'test-old-cloud-image-name', 'test-project', 'image description',
            'sles', 'test-stuff',
            [{"package": ["name", "and", "constraints"]}], 'instance type'
        )

    @pytest.mark.parametrize(
        'method',
        [
            'get_deprecation_regions'
        ]
    )
    def test_not_implemented_methods(self, method):
        # Test methods that are not implemented yet
        with pytest.raises(NotImplementedError) as error:
            getattr(self.job, method)()

        assert 'TODO' == str(error.value)
