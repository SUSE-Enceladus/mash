from unittest.mock import patch, Mock

from mash.mash_exceptions import MashException
from mash.services.obs_service import main


class TestOBS(object):
    @patch('mash.services.obs_service.OBSConfig')
    @patch('mash.services.obs_service.OBSImageBuildResultService')
    def test_main(self, mock_OBSImageBuildResultService, mock_config):
        config = Mock()
        mock_config.return_value = config

        main()
        mock_OBSImageBuildResultService.assert_called_once_with(
            service_exchange='obs',
            config=config
        )

    @patch('mash.services.obs_service.OBSConfig')
    @patch('mash.services.obs_service.OBSImageBuildResultService')
    @patch('sys.exit')
    def test_main_mash_error(
        self, mock_exit, mock_OBSImageBuildResultService, mock_conofig
    ):
        mock_OBSImageBuildResultService.side_effect = MashException('error')
        main()
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.obs_service.OBSConfig')
    @patch('mash.services.obs_service.OBSImageBuildResultService')
    @patch('sys.exit')
    def test_main_keyboard_interrupt(
        self, mock_exit, mock_OBSImageBuildResultService, mock_config
    ):
        mock_OBSImageBuildResultService.side_effect = KeyboardInterrupt
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.obs_service.OBSConfig')
    @patch('mash.services.obs_service.OBSImageBuildResultService')
    @patch('sys.exit')
    def test_main_system_exit(
        self, mock_exit, mock_OBSImageBuildResultService, mock_config
    ):
        mock_OBSImageBuildResultService.side_effect = SystemExit
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.obs_service.OBSConfig')
    @patch('mash.services.obs_service.OBSImageBuildResultService')
    @patch('sys.exit')
    def test_main_unexpected_error(
        self, mock_exit, mock_OBSImageBuildResultService, mock_config
    ):
        mock_OBSImageBuildResultService.side_effect = Exception
        main()
        mock_exit.assert_called_once_with(1)
