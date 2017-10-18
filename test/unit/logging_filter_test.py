from collections import namedtuple

from mash.logging_filter import SchedulerLoggingFilter


class TestSchedulerLoggingFilter(object):
    def setup(self):
        self.log_filter = SchedulerLoggingFilter()
        self.record_type = namedtuple(
            'record_type', ['msg']
        )

    def test_filter_inactive(self):
        record = self.record_type(msg='some message')
        assert self.log_filter.filter(record) is True

    def test_filter_for_max_instances_reached(self):
        record = self.record_type(
            msg='maximum number of running instances reached'
        )
        assert self.log_filter.filter(record) is False
