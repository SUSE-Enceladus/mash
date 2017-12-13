from pytest import raises
from unittest.mock import patch

from mash.mash_exceptions import MashJobCreatorException
from mash.services.job_creator_service import main


class TestJobCreatorServiceMain(object):
    @patch('mash.services.job_creator_service.JobCreatorService')
    def test_job_creator_main(self, mock_job_creator_service):
        main()
        mock_job_creator_service.assert_called_once_with(
            host='localhost', service_exchange='jobcreator',
        )

    @patch('mash.services.job_creator_service.JobCreatorService')
    @patch('sys.exit')
    def test_job_creator_main_mash_error(
        self, mock_exit, mock_job_creator_service
    ):
        mock_job_creator_service.side_effect = MashJobCreatorException('error')

        main()
        mock_job_creator_service.assert_called_once_with(
            host='localhost', service_exchange='jobcreator',
        )
        mock_exit.assert_called_once_with(1)

    @patch('mash.services.job_creator_service.JobCreatorService')
    @patch('sys.exit')
    def test_job_creator_main_system_exit(
        self, mock_exit, mock_job_creator_service
    ):
        mock_job_creator_service.side_effect = SystemExit()

        main()
        mock_exit.assert_called_once_with(0)

    @patch('mash.services.job_creator_service.JobCreatorService')
    def test_job_creator_main_unexpected_error(self, mock_job_creator_service):
        mock_job_creator_service.side_effect = Exception('Error!')

        with raises(Exception):
            main()
