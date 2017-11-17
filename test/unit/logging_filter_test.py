from collections import namedtuple
from mock import Mock

from mash.log.filter import (
    SchedulerLoggingFilter,
    BaseServiceFilter
)
import os


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


class TestBaseServiceFilter(object):
    def setup(self):
        self.log_filter = BaseServiceFilter()
        self.record = Mock()
        self.record.msg = 'Log Message!'

    def test_filter_with_job_id(self):
        self.record.job_id = '123'
        assert self.log_filter.filter(self.record) is True
        assert self.record.newline == os.linesep
        assert self.record.job == 'Job[123]:'

    def test_filter_no_job_id(self):
        delattr(self.record, 'job_id')
        assert self.log_filter.filter(self.record) is True
        assert self.record.newline == os.linesep
        assert self.record.job == ''
