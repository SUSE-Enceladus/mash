from pytest import raises
from mock import patch
from mock import Mock

from mash.exceptions import MashError
from mash.services.obs_service import main


class TestOBS(object):
    def setup(self):
        self.config = Mock()
        self.config.get_control_port = Mock(return_value=9000)
        self.config.get_log_port = Mock(return_value=9001)
        self.config.get_log_file = Mock(return_value='/tmp/obs_service.log')
        self.config.get_download_directory = Mock(return_value='/tmp')

    @patch('mash.services.obs_service.OBSImageBuildResultService')
    @patch('mash.services.obs_service.OBSConfig')
    def test_main(self, mock_OBSConfig, mock_OBSImageBuildResultService):
        mock_OBSConfig.return_value = self.config
        main(event_loop=False)
        mock_OBSImageBuildResultService.assert_called_once_with(
            host='localhost', service_exchange='obs', logging_exchange='logger',
            custom_args={
                'logfile': '/tmp/obs_service.log',
                'download_dir': '/tmp'
            }
        )

    @patch('mash.services.obs_service.OBSImageBuildResultService')
    @patch('mash.services.obs_service.OBSConfig')
    @patch('sys.exit')
    def test_main_mash_error(
        self, mock_exit, mock_OBSConfig, mock_OBSImageBuildResultService
    ):
        mock_OBSConfig.return_value = self.config
        mock_OBSImageBuildResultService.side_effect = MashError('error')
        main(event_loop=False)
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.obs_service.OBSImageBuildResultService')
    @patch('mash.services.obs_service.OBSConfig')
    @patch('time.sleep')
    @patch('sys.exit')
    def test_main_keyboard_interrupt(
        self, mock_exit, mock_time, mock_OBSConfig,
        mock_OBSImageBuildResultService
    ):
        mock_OBSConfig.return_value = self.config
        mock_time.side_effect = KeyboardInterrupt
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.obs_service.OBSImageBuildResultService')
    @patch('mash.services.obs_service.OBSConfig')
    @patch('time.sleep')
    @patch('sys.exit')
    def test_main_system_exit(
        self, mock_exit, mock_time, mock_OBSConfig,
        mock_OBSImageBuildResultService
    ):
        mock_OBSConfig.return_value = self.config
        mock_time.side_effect = SystemExit()
        main()
        mock_exit.assert_called_once_with(mock_time.side_effect)

    @patch('mash.services.obs_service.OBSImageBuildResultService')
    @patch('mash.services.obs_service.OBSConfig')
    @patch('time.sleep')
    def test_main_unexpected_error(
        self, mock_time, mock_OBSConfig, mock_OBSImageBuildResultService
    ):
        mock_OBSConfig.return_value = self.config
        mock_time.side_effect = Exception
        with raises(Exception):
            main()
