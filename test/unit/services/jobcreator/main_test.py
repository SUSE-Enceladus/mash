from unittest.mock import patch, Mock

from mash.mash_exceptions import MashJobCreatorException
from mash.services.job_creator_service import main


class TestJobCreatorServiceMain(object):
    @patch('mash.services.job_creator_service.BaseConfig')
    @patch('mash.services.job_creator_service.JobCreatorService')
    def test_job_creator_main(self, mock_job_creator_service, mock_config):
        config = Mock()
        mock_config.return_value = config

        main()
        mock_job_creator_service.assert_called_once_with(
            service_exchange='jobcreator',
            config=config
        )

    @patch('mash.services.job_creator_service.BaseConfig')
    @patch('mash.services.job_creator_service.JobCreatorService')
    @patch('sys.exit')
    def test_job_creator_main_mash_error(
        self, mock_exit, mock_job_creator_service, mock_config
    ):
        config = Mock()
        mock_config.return_value = config

        mock_job_creator_service.side_effect = MashJobCreatorException('error')

        main()
        mock_job_creator_service.assert_called_once_with(
            service_exchange='jobcreator',
            config=config
        )
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.job_creator_service.BaseConfig')
    @patch('mash.services.job_creator_service.JobCreatorService')
    @patch('sys.exit')
    def test_main_keyboard_interrupt(
        self, mock_exit, mock_job_creator_service, mock_config
    ):
        mock_job_creator_service.side_effect = KeyboardInterrupt
        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.job_creator_service.BaseConfig')
    @patch('mash.services.job_creator_service.JobCreatorService')
    @patch('sys.exit')
    def test_job_creator_main_system_exit(
        self, mock_exit, mock_job_creator_service, mock_config
    ):
        mock_job_creator_service.side_effect = SystemExit()

        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.job_creator_service.BaseConfig')
    @patch('mash.services.job_creator_service.JobCreatorService')
    @patch('sys.exit')
    def test_job_creator_main_unexpected_error(
        self, mock_exit, mock_job_creator_service, mock_config
    ):
        mock_job_creator_service.side_effect = Exception('Error!')

        main()
        mock_exit.assert_called_once_with(1)
