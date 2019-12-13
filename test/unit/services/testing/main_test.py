from unittest.mock import patch, Mock

from mash.mash_exceptions import MashTestingException
from mash.services.testing_service import main


class TestImgProofTestingServiceMain(object):
    @patch('mash.services.testing_service.BaseJobFactory')
    @patch('mash.services.testing_service.TestingConfig')
    @patch('mash.services.testing_service.ListenerService')
    def test_main(self, mock_testing_service, mock_config, mock_factory):
        config = Mock()
        mock_config.return_value = config

        factory = Mock()
        mock_factory.return_value = factory

        main()
        mock_testing_service.assert_called_once_with(
            service_exchange='testing',
            config=config,
            custom_args={
                'listener_msg_args': ['cloud_image_name', 'source_regions'],
                'status_msg_args': ['source_regions'],
                'job_factory': factory
            }
        )

    @patch('mash.services.testing_service.BaseJobFactory')
    @patch('mash.services.testing_service.TestingConfig')
    @patch('mash.services.testing_service.ListenerService')
    @patch('sys.exit')
    def test_testing_main_mash_error(
        self, mock_exit, mock_testing_service, mock_config, mock_factory
    ):
        config = Mock()
        mock_config.return_value = config
        mock_testing_service.side_effect = MashTestingException('error')

        factory = Mock()
        mock_factory.return_value = factory

        main()

        mock_testing_service.assert_called_once_with(
            service_exchange='testing',
            config=config,
            custom_args={
                'listener_msg_args': ['cloud_image_name', 'source_regions'],
                'status_msg_args': ['source_regions'],
                'job_factory': factory
            }
        )
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.testing_service.TestingConfig')
    @patch('mash.services.testing_service.ListenerService')
    @patch('sys.exit')
    def test_logger_main_keyboard_interrupt(
        self, mock_exit, mock_testing_service, mock_config
    ):
        mock_testing_service.side_effect = KeyboardInterrupt()

        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.testing_service.TestingConfig')
    @patch('mash.services.testing_service.ListenerService')
    @patch('sys.exit')
    def test_testing_main_system_exit(
        self, mock_exit, mock_testing_service, mock_config
    ):
        mock_testing_service.side_effect = SystemExit()

        main()
        mock_exit.assert_called_once_with(mock_testing_service.side_effect)

    @patch('mash.services.testing_service.TestingConfig')
    @patch('mash.services.testing_service.ListenerService')
    @patch('sys.exit')
    def test_testing_main_unexpected_error(
        self, mock_exit, mock_testing_service, mock_config
    ):
        mock_testing_service.side_effect = Exception('Error!')

        main()
        mock_exit.assert_called_once_with(1)
