from unittest.mock import patch

from mash.mash_exceptions import MashConfigException
from mash.services.base_config import BaseConfig
from pytest import raises


class TestBaseConfig(object):
    def setup_method(self):
        self.empty_config = BaseConfig('test/data/empty_mash_config.yaml')
        self.config = BaseConfig('test/data/mash_config.yaml')

    def test_get_encryption_keys_file(self):
        enc_keys_file = self.empty_config.get_encryption_keys_file()
        assert enc_keys_file == '/var/lib/mash/encryption_keys'

    def test_get_jwt_algorithm(self):
        algorithm = self.empty_config.get_jwt_algorithm()
        assert algorithm == 'HS256'

    def test_get_jwt_secret(self):
        secret = self.config.get_jwt_secret()
        assert secret == 'abc123'

    def test_get_jwt_secret_empty(self):
        msg = 'jwt_secret must be in config file.'
        with raises(MashConfigException) as error:
            self.empty_config.get_jwt_secret()

        assert msg == str(error.value)

    def test_get_cloud_data(self):
        data = self.config.get_cloud_data()
        assert data['ec2']['regions']['aws-cn'] == ['cn-north-1']
        assert data['ec2']['helper_images']['cn-north-1'] == 'ami-bcc45885'

        with raises(MashConfigException) as error:
            self.empty_config.get_cloud_data()

        assert str(error.value) == \
            'cloud data must be provided in config file.'

    def test_get_service_names(self):
        # Services
        expected = [
            'download', 'upload', 'create', 'test', 'raw_image_upload',
            'replicate', 'publish', 'deprecate'
        ]
        services = self.empty_config.get_service_names()
        assert expected == services

    def test_get_ssh_private_key_file(self):
        assert self.config.get_ssh_private_key_file() == \
            '/var/lib/mash/ssh_key'

        with raises(MashConfigException) as error:
            self.empty_config.get_ssh_private_key_file()

        assert str(error.value) == \
            'ssh_private_key_file is required in MASH configuration file.'

    def test_get_amqp_host(self):
        host = self.empty_config.get_amqp_host()
        assert host == 'localhost'

    def test_get_amqp_user(self):
        user = self.empty_config.get_amqp_user()
        assert user == 'guest'

    def test_get_amqp_pass(self):
        password = self.empty_config.get_amqp_pass()
        assert password == 'guest'

    def test_get_smtp_host(self):
        host = self.empty_config.get_smtp_host()
        assert host == 'localhost'

    def test_get_smtp_port(self):
        port = self.empty_config.get_smtp_port()
        assert port == 25

    def test_get_smtp_ssl(self):
        ssl = self.empty_config.get_smtp_ssl()
        assert not ssl

    def test_get_smtp_user(self):
        user = self.config.get_smtp_user()
        assert user == 'user@test.com'

        with raises(MashConfigException) as error:
            self.empty_config.get_smtp_user()

        msg = 'smtp_user is required in MASH configuration file.'
        assert str(error.value) == msg

    def test_get_smtp_pass(self):
        password = self.config.get_smtp_pass()
        assert password == 'super.secret'

        password = self.empty_config.get_smtp_pass()
        assert password is None

    def test_get_notification_subject(self):
        subject = self.empty_config.get_notification_subject()
        assert subject == '[MASH] Job Status Update'

    def test_get_job_dir(self):
        assert self.config.get_job_directory('test') == \
            '/tmp/jobs/test_jobs/'
        assert self.empty_config.get_job_directory('test') == \
            '/var/lib/mash/test_jobs/'

    def test_get_log_dir(self):
        assert self.config.get_log_directory() == '/tmp/log/'
        assert self.empty_config.get_log_directory() == '/var/log/mash/'

    @patch.object(BaseConfig, 'get_log_directory')
    def test_get_job_log_file(self, mock_get_log_dir):
        mock_get_log_dir.return_value = '/var/log/mash/'
        assert self.empty_config.get_job_log_file('1234') == \
            '/var/log/mash/jobs/1234.log'

    def test_get_credentials_url(self):
        assert self.config.get_credentials_url() == 'http://localhost:5006/'
        assert self.empty_config.get_credentials_url() == \
            'http://localhost:8080/'

    def test_get_database_uri(self):
        assert self.config.get_database_uri() == \
            'sqlite:////var/lib/mash/app.db'

        with raises(MashConfigException):
            self.empty_config.get_database_uri()

    def test_get_download_directory(self):
        assert self.config.get_download_directory() == '/images'
        assert self.empty_config.get_download_directory() == '/var/lib/mash/images/'

    def test_get_max_oci_attempts(self):
        assert self.config.get_max_oci_attempts() == 500
        assert self.empty_config.get_max_oci_attempts() == 100

    def test_get_max_oci_wait_seconds(self):
        assert self.config.get_max_oci_wait_seconds() == 1000
        assert self.empty_config.get_max_oci_wait_seconds() == 2400

    def test_get_oci_upload_process_count(self):
        assert self.config.get_oci_upload_process_count() == 2
        assert self.empty_config.get_oci_upload_process_count() == 3

    def test_get_base_thread_pool_count(self):
        assert self.config.get_base_thread_pool_count() == 20
        assert self.empty_config.get_base_thread_pool_count() == 10

    def test_get_publish_thread_pool_count(self):
        assert self.config.get_publish_thread_pool_count() == 60
        assert self.empty_config.get_publish_thread_pool_count() == 50

    @patch.object(BaseConfig, 'get_auth_methods', lambda x: ['oauth2'])
    def test_get_oauth2_client_id(self):
        with raises(MashConfigException):
            self.config.get_oauth2_client_id()

    @patch.object(BaseConfig, 'get_auth_methods', lambda x: ['oauth2'])
    def test_get_oauth2_client_secret(self):
        with raises(MashConfigException):
            self.config.get_oauth2_client_secret()

    @patch.object(BaseConfig, 'get_auth_methods', lambda x: ['oauth2'])
    def test_get_oauth2_provider_url(self):
        with raises(MashConfigException):
            self.config.get_oauth2_provider_url()

    @patch.object(BaseConfig, 'get_auth_methods', lambda x: ['oauth2'])
    def test_get_oauth2_redirect_ports(self):
        with raises(MashConfigException):
            self.config.get_oauth2_redirect_ports()

    def test_get_database_api_url(self):
        assert self.config.get_database_api_url() == 'http://localhost:5057/'
        assert self.empty_config.get_database_api_url() == \
            'http://localhost:5007/'
