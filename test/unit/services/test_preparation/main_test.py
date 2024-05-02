from unittest.mock import patch, Mock

from mash.mash_exceptions import MashTestException
from mash.services.test_preparation_service import main


class TestImgProofTestPreparationServiceMain(object):
    @patch('mash.services.test_preparation_service.BaseJobFactory')
    @patch('mash.services.test_preparation_service.TestPreparationConfig')
    @patch('mash.services.test_preparation_service.ListenerService')
    def test_main(self, mock_test_service, mock_config, mock_factory):
        config = Mock()
        mock_config.return_value = config

        factory = Mock()
        mock_factory.return_value = factory

        main()
        mock_test_service.assert_called_once_with(
            service_exchange='test_preparation',
            config=config,
            custom_args={
                'job_factory': factory
            }
        )

    @patch('mash.services.test_preparation_service.BaseJobFactory')
    @patch('mash.services.test_preparation_service.TestPreparationConfig')
    @patch('mash.services.test_preparation_service.ListenerService')
    @patch('sys.exit')
    def test_test_main_mash_error(
        self, mock_exit, mock_test_service, mock_config, mock_factory
    ):
        config = Mock()
        mock_config.return_value = config
        mock_test_service.side_effect = MashTestException('error')

        factory = Mock()
        mock_factory.return_value = factory

        main()

        mock_test_service.assert_called_once_with(
            service_exchange='test_preparation',
            config=config,
            custom_args={
                'job_factory': factory
            }
        )
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.test_preparation_service.TestPreparationConfig')
    @patch('mash.services.test_preparation_service.ListenerService')
    @patch('sys.exit')
    def test_logger_main_keyboard_interrupt(
        self, mock_exit, mock_test_service, mock_config
    ):
        mock_test_service.side_effect = KeyboardInterrupt()

        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.test_preparation_service.TestPreparationConfig')
    @patch('mash.services.test_preparation_service.ListenerService')
    @patch('sys.exit')
    def test_test_main_system_exit(
        self, mock_exit, mock_test_service, mock_config
    ):
        mock_test_service.side_effect = SystemExit()

        main()
        mock_exit.assert_called_once_with(mock_test_service.side_effect)

    @patch('mash.services.test_preparation_service.TestPreparationConfig')
    @patch('mash.services.test_preparation_service.ListenerService')
    @patch('sys.exit')
    def test_test_main_unexpected_error(
        self, mock_exit, mock_test_service, mock_config
    ):
        mock_test_service.side_effect = Exception('Error!')

        main()
        mock_exit.assert_called_once_with(1)
