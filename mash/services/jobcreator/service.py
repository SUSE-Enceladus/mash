# Copyright (c) 2017 SUSE Linux GmbH.  All rights reserved.
#
# This file is part of mash.
#
# mash is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# mash is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with mash.  If not, see <http://www.gnu.org/licenses/>
#

import json
import random
import uuid

from mash.services.base_service import BaseService
from mash.services.jobcreator.config import JobCreatorConfig
from mash.services.jobcreator import schema


class JobCreatorService(BaseService):
    """
    Implementation of job creator service.

    Handles the orchestration of jobs for mash.
    """

    def post_init(self):
        """
        Initialize job creator service class.
        """
        self.config = JobCreatorConfig()
        self.set_logfile(self.config.get_log_file(self.service_exchange))
        self.services = self.config.get_service_names()
        self.accounts_file = self.config.get_accounts_file()
        self.encryption_keys_file = self.config.get_encryption_keys_file()

        self.bind_queue(
            self.service_exchange, self.add_account_key, self.listener_queue
        )

        self.start()

    def _get_account_info(
        self, provider, provider_accounts, provider_groups
    ):
        """
        Returns a dictionary of accounts and regions.

        The provided target_regions dictionary may contain a list
        of groups and accounts. An account may have a list of regions.

        If regions are not provided for an account the default list
        of all regions available is used.

        Example: {
            'us-east-1': {
                'account': 'acnt1',
                'target_regions': ['us-east-2', 'us-west-1', 'us-west-2']
            }
        }
        """
        results = {}
        group_accounts = []
        accounts = {}

        account_info = self._get_accounts_from_file()

        # Get dictionary of account names to target regions
        for provider_account in provider_accounts:
            accounts[provider_account['name']] = \
                provider_account['target_regions']

        if provider == 'ec2':
            helper_images = self._get_ec2_helper_images(account_info)

        # Get all accounts from all groups
        for group in provider_groups:
            group_accounts += self._get_accounts_in_group(
                provider, group, account_info
            )

        # Add accounts from groups that don't already exist
        for account in group_accounts:
            if account not in accounts:
                accounts[account] = None

        for account, target_regions in accounts.items():
            if not target_regions:
                # Get default list of all available regions for account
                target_regions = self._get_regions_for_account(
                    provider, account, account_info
                )

            # A random region is selected as source region.
            target = random.choice(target_regions)
            results[target] = {
                'account': account,
                'target_regions': target_regions
            }

            if provider == 'ec2':
                results[target]['helper_image'] = helper_images[target]

        return results

    def _get_accounts_in_group(self, provider, group, accounts):
        """
        Return a list of account names given the group name.
        """
        return accounts[provider]['groups'][group]

    def _get_accounts_from_file(self):
        """
        Return a dictionary of account information from accounts json file.
        """
        with open(self.accounts_file, 'r') as acnt_file:
            accounts = json.load(acnt_file)

        return accounts

    def _get_ec2_helper_images(self, accounts):
        """
        Return a list of helper images for all ec2 regions.
        """
        helper_regions = accounts['ec2']['helper_images']
        return helper_regions

    def _get_regions_for_account(self, provider, account, accounts):
        """
        Return a list of regions based on account name.
        """
        regions_key = accounts[provider]['accounts'][account]
        return accounts[provider]['regions'][regions_key]

    def _handle_service_message(self, message):
        """
        Handle new and delete job messages.
        """
        try:
            job_doc = json.loads(message.body)
            if 'job_delete' in job_doc:
                self.publish_delete_job_message(job_doc['job_delete'])
            else:
                self.validate_message(job_doc, schema.job_message)
                self.proccess_new_job(job_doc)
        except Exception as error:
            self.log.error(
                'Invalid message received: {0}.'.format(error)
            )

        message.ack()

    def _handle_listener_message(self, message):
        """
        Process add account messages.
        """
        try:
            account_message = json.loads(message.body)
            self.validate_message(account_message, schema.add_account)
        except Exception:
            self.log.warning(
                'Invalid message received: {0}.'.format(message.body)
            )
        else:
            if message.method['routing_key'] == 'add_account':
                self.add_account(account_message)
            else:
                self.log.warning(
                    'Received unknown message type: {0}. Message: {1}'.format(
                        message.method['routing_key'],
                        message.body
                    )
                )

        message.ack()

    def _publish_credentials_job(self, base_message, job_doc):
        """
        Build credentials job message and publish to credentials exchange.
        """
        accounts = []
        for provider_account in job_doc['provider_accounts']:
            accounts.append(provider_account['name'])

        credentials_message = {
            'credentials_job': {
                'provider': job_doc.get('provider'),
                'last_service': job_doc.get('last_service'),
                'provider_accounts': accounts,
                'requesting_user': job_doc.get('requesting_user')
            }
        }
        credentials_message['credentials_job'].update(base_message)

        self._publish(
            'credentials', self.job_document_key,
            json.dumps(credentials_message)
        )

    def _publish_deprecation_job(self, base_message, job_doc, region_info):
        """
        Build deprecation job message and publish to deprecation exchange.
        """
        deprecation_regions = []
        for source_region, value in region_info.items():
            deprecation_regions.append(value)

        deprecation_message = {
            'deprecation_job': {
                'provider': job_doc.get('provider'),
                'old_cloud_image_name': job_doc.get('old_cloud_image_name'),
                'deprecation_regions': deprecation_regions
            }
        }
        deprecation_message['deprecation_job'].update(base_message)

        self._publish(
            'deprecation', self.job_document_key,
            json.dumps(deprecation_message)
        )

    def _publish_obs_job(self, base_message, job_doc, region_info):
        """
        Build OBS job message and publish to OBS exchange.
        """
        obs_message = {
            'obs_job': {
                'image': job_doc.get('image'),
                'project': job_doc.get('project'),
            }
        }
        obs_message['obs_job'].update(base_message)

        if job_doc.get('conditions'):
            obs_message['obs_job']['conditions'] = job_doc.get('conditions')

        self._publish('obs', self.job_document_key, json.dumps(obs_message))

    def _publish_pint_job(self, base_message, job_doc, region_info):
        """
        Build pint job message and publish to pint exchange.
        """
        pint_message = {
            'pint_job': {
                'provider': job_doc.get('provider'),
                'cloud_image_name': job_doc.get('cloud_image_name'),
                'old_cloud_image_name': job_doc.get('old_cloud_image_name')
            }
        }
        pint_message['pint_job'].update(base_message)

        self._publish('pint', self.job_document_key, json.dumps(pint_message))

    def _publish_publisher_job(self, base_message, job_doc, region_info):
        """
        Build publisher job message and publish to publisher exchange.
        """
        publish_regions = []
        for source_region, value in region_info.items():
            publish_regions.append(value)

        publisher_message = {
            'publisher_job': {
                'provider': job_doc.get('provider'),
                'allow_copy': job_doc.get('allow_copy'),
                'share_with': job_doc.get('share_with'),
                'publish_regions': publish_regions
            }
        }
        publisher_message['publisher_job'].update(base_message)

        self._publish(
            'publisher', self.job_document_key,
            json.dumps(publisher_message)
        )

    def _publish_replication_job(self, base_message, job_doc, region_info):
        """
        Build replication job message and publish to replication exchange.
        """
        replication_source_regions = {}
        for source_region, value in region_info.items():
            replication_source_regions[source_region] = {
                'account': value['account'],
                'target_regions': value['target_regions']
            }

        replication_message = {
            'replication_job': {
                'image_description': job_doc.get('image_description'),
                'provider': job_doc.get('provider'),
                'replication_source_regions': replication_source_regions
            }
        }
        replication_message['replication_job'].update(base_message)

        self._publish(
            'replication', self.job_document_key,
            json.dumps(replication_message)
        )

    def _publish_testing_job(self, base_message, job_doc, region_info):
        """
        Build testing job message and publish to testing exchange.
        """
        test_regions = {}
        for source_region, value in region_info.items():
            test_regions[source_region] = value['account']

        testing_message = {
            'testing_job': {
                'provider': job_doc.get('provider'),
                'tests': job_doc.get('tests'),
                'test_regions': test_regions
            }
        }
        testing_message['testing_job'].update(base_message)

        if job_doc.get('distro'):
            testing_message['testing_job']['distro'] = job_doc['distro']

        if job_doc.get('instance_type'):
            testing_message['testing_job']['instance_type'] = \
                job_doc['instance_type']

        self._publish(
            'testing', self.job_document_key, json.dumps(testing_message)
        )

    def _publish_uploader_job(self, base_message, job_doc, region_info):
        """
        Build uploader job message and publish to uploader exchange.
        """
        target_regions = {}
        for source_region, value in region_info.items():
            target_regions[source_region] = {
                'account': value['account'],
                'helper_image': value['helper_image']
            }

        uploader_message = {
            'uploader_job': {
                'cloud_image_name': job_doc.get('cloud_image_name'),
                'provider': job_doc.get('provider'),
                'image_description': job_doc.get('image_description'),
                'target_regions': target_regions
            }
        }
        uploader_message['uploader_job'].update(base_message)

        self._publish(
            'uploader', self.job_document_key, json.dumps(uploader_message)
        )

    def _write_accounts_to_file(self, accounts):
        """
        Update accounts file with new accounts dictionary.
        """
        account_info = json.dumps(accounts)
        with open(self.accounts_file, 'w') as acnt_file:
            acnt_file.write(account_info)

    def add_account(self, message):
        """
        Add new provider account to MASH.

        Notify credentials service of new account with encrypted credentials.
        """
        accounts = self._get_accounts_from_file()
        provider = message['provider']
        account_name = message['account_name']

        # Add account
        accounts[provider]['accounts'][account_name] = message['partition']

        # Add group if necessary
        if message.get('group'):
            group = message['group']

            if group not in accounts[provider]['groups']:
                accounts[provider]['groups'][group] = []
            accounts[provider]['groups'][group].append(account_name)

        self._write_accounts_to_file(accounts)

        message['credentials'] = self.encrypt_credentials(
            json.dumps(message['credentials'])
        )

        self._publish('credentials', self.add_account_key, json.dumps(message))

    def proccess_new_job(self, job_doc):
        """
        Split args and send messages to all services to initiate job.
        """
        region_info = self._get_account_info(
            job_doc.get('provider'),
            job_doc.get('provider_accounts'),
            job_doc.get('provider_groups')
        )

        job_id = str(uuid.uuid4())
        base_message = {
            'id': job_id,
            'utctime': job_doc.get('utctime'),
        }

        self._publish_credentials_job(base_message, job_doc)

        for service in self.services:
            if service == 'deprecation':
                self._publish_deprecation_job(
                    base_message, job_doc, region_info
                )
            elif service == 'obs':
                self._publish_obs_job(base_message, job_doc, region_info)
            elif service == 'pint':
                self._publish_pint_job(base_message, job_doc, region_info)
            elif service == 'publisher':
                self._publish_publisher_job(
                    base_message, job_doc, region_info
                )
            elif service == 'replication':
                self._publish_replication_job(
                    base_message, job_doc, region_info
                )
            elif service == 'testing':
                self._publish_testing_job(
                    base_message, job_doc, region_info
                )
            elif service == 'uploader':
                self._publish_uploader_job(
                    base_message, job_doc, region_info
                )

            if service == job_doc.get('last_service'):
                break

    def publish_delete_job_message(self, job_id):
        """
        Publish delete job message to obs and credentials services.

        This will flush the job with the given id out of the pipeline.
        """
        delete_message = {
            "obs_job_delete": job_id
        }
        self._publish(
            'obs', self.job_document_key, json.dumps(delete_message)
        )

        delete_message = {
            "credentials_job_delete": job_id
        }
        self._publish(
            'credentials', self.job_document_key, json.dumps(delete_message)
        )

    def start(self):
        """
        Start job creator service.
        """
        self.consume_queue(self._handle_service_message)
        self.consume_queue(
            self._handle_listener_message, queue_name=self.listener_queue
        )
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            pass
        except Exception:
            raise
        finally:
            self.stop()

    def stop(self):
        """
        Stop job creator service.

        Stop consuming queues and close pika connections.
        """
        self.channel.stop_consuming()
        self.close_connection()
