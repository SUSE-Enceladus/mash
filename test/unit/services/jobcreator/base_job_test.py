from mash.services.jobcreator.base_job import BaseJob


class TestJobCreatorBaseJob(object):
    def setup(self):
        self.job = BaseJob(
            {}, 'ec2', ['test-aws'], [], 'test-user', 'pint', 'now',
            'test-image', 'test-cloud-image',
            'test-project', 'image description', 'sles', 'test-stuff',
            [{"package": ["name", "and", "constraints"]}],
            'instance type', 'test-old-cloud-image-name'
        )

    def test_base_job_empty_methods(self):
        # Test methods that are extended by child classes
        # base methods just pass
        self.job._get_account_info()
        self.job.get_deprecation_message()
        self.job.get_publisher_message()
        self.job.get_replication_message()
        self.job.get_replication_source_regions()
        self.job.get_testing_regions()
        self.job.get_uploader_regions()
        self.job.post_init()
