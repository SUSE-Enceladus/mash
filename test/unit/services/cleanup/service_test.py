from unittest.mock import MagicMock, Mock, patch

from mash.services.cleanup_service import CleanupService
from mash.services.mash_service import MashService


class TestCleanupService(object):

    @patch.object(MashService, '__init__')
    def setup(
        self, mock_base_init
    ):
        mock_base_init.return_value = None

        self.config = Mock()
        self.config.get_download_directory.return_value = '/images'
        self.config.get_max_image_age.return_value = '42'

        self.channel = Mock()
        self.channel.basic_ack.return_value = None
        self.tag = Mock()
        self.method = {'delivery_tag': self.tag}

        self.message = MagicMock(
            channel=self.channel,
            method=self.method
        )

        self.cleanup = CleanupService()
        self.cleanup.log = MagicMock()
        self.cleanup.service_exchange = 'cleanup'
        self.cleanup.service_queue = 'service'
        self.cleanup.channel = self.channel

    @patch('mash.services.cleanup.service.BlockingScheduler')
    @patch('mash.services.cleanup.service.setup_logfile')
    def test_cleanup_post_init(
        self, mock_setup_logfile, mock_scheduler
    ):
        config = Mock()
        config.get_log_file.return_value = '/var/log/mash/cleanup_service.log'
        self.cleanup.config = config

        scheduler = Mock()
        mock_scheduler.return_value = scheduler

        # Test normal run
        self.cleanup.post_init()

        config.get_log_file.assert_called_once_with('cleanup')
        mock_setup_logfile.assert_called_once_with(
            '/var/log/mash/cleanup_service.log'
        )
        scheduler.add_job.assert_called_once_with(
            self.cleanup._purge_images,
            'cron',
            hour='5',
            minute='0'
        )
        scheduler.start.assert_called_once()

    @patch('shutil.rmtree')
    @patch('os.scandir')
    @patch('os.path.isdir')
    def test_cleanup_purge_images(
        self, mock_isdir, mock_scandir, mock_rmtree
    ):
        entry = Mock()
        entry.is_dir.return_value = True
        entry.name = 'foo'
        entry.path = '/images/foo'
        mock_isdir.return_value = True
        mock_scandir.return_value.__enter__.return_value = [entry]
        mtime = Mock()
        mtime.st_mtime = 1
        entry.stat.return_value = mtime

        self.cleanup.config = self.config
        self.config.get_download_directory.return_value = '/images'
        self.config.get_max_image_age.return_value = 42

        self.cleanup._purge_images()

        mock_rmtree.assert_called_once_with('/images/foo')

        mock_isdir.return_value = False
        self.cleanup._purge_images()
