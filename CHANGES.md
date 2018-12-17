v1.3.0 (2018-12-17)
===================

- Cleanup cloud image name in replication jobs.
  [\#357](https://github.com/SUSE-Enceladus/mash/pull/357)
- Set cloud image name in uploader service.
  [\#358](https://github.com/SUSE-Enceladus/mash/pull/358)
- Add data for new EC2 regions.
  [\#359](https://github.com/SUSE-Enceladus/mash/pull/359)
- Simplify listener messages.
  [\#360](https://github.com/SUSE-Enceladus/mash/pull/360)
- Catch generic exception in update image status.
  [\#361](https://github.com/SUSE-Enceladus/mash/pull/361)
- Add next service attribute to services.
  [\#362](https://github.com/SUSE-Enceladus/mash/pull/362)

v1.2.0 (2018-12-11)
===================

- Add keys to accounts template for GCE.
  [\#347](https://github.com/SUSE-Enceladus/mash/pull/347)
- Pass job last service to all services.
  [\#348](https://github.com/SUSE-Enceladus/mash/pull/348)
- OBS service should not be a valid option.
  [\#349](https://github.com/SUSE-Enceladus/mash/pull/349)
- Update MASH requirements to use ec2imgutils.
  [\#350](https://github.com/SUSE-Enceladus/mash/pull/350)
- Only add additional regions when none provided.
  [\#352](https://github.com/SUSE-Enceladus/mash/pull/352)
- Use temporary subnet and security group.
  [\#353](https://github.com/SUSE-Enceladus/mash/pull/353)
- Use temporary subnet and security group.
  [\#354](https://github.com/SUSE-Enceladus/mash/pull/354)

v1.1.0 (2018-11-12)
===================

- Fix typo in ec2 instance type list.
  [\#316](https://github.com/SUSE-Enceladus/mash/pull/316)
- Remove redundant job id from jc delete message.
  [\#319](https://github.com/SUSE-Enceladus/mash/pull/319)
- Add IPA timeout option.
  [\#322](https://github.com/SUSE-Enceladus/mash/pull/322)
- Remove service based configs from testing data.
  [\#323](https://github.com/SUSE-Enceladus/mash/pull/323)
- Update accounts file location in config.
  [\#324](https://github.com/SUSE-Enceladus/mash/pull/324)
- Integrate Azure replication.
  [\#328](https://github.com/SUSE-Enceladus/mash/pull/328)
- Re-raise exceptions in event loop.
  [\#329](https://github.com/SUSE-Enceladus/mash/pull/329)
- Cleanup flake8 warnings.
  [\#330](https://github.com/SUSE-Enceladus/mash/pull/330)
- Add missing types in provider account schemas.
  [\#331](https://github.com/SUSE-Enceladus/mash/pull/331)
- Enable GCE endpoints.
  [\#332](https://github.com/SUSE-Enceladus/mash/pull/332)
- Use ARM endpoint for Azure upload.
  [\#333](https://github.com/SUSE-Enceladus/mash/pull/333)
- Add python3.7 build target for ci testing.
  [\#334](https://github.com/SUSE-Enceladus/mash/pull/334)
- Use setter methods in job classes.
  [\#335](https://github.com/SUSE-Enceladus/mash/pull/335)
- Add python3.7 to supported versions in setup.py.
  [\#336](https://github.com/SUSE-Enceladus/mash/pull/336)
- Fernet key rotation requires cryptography > 2.2.
  [\#338](https://github.com/SUSE-Enceladus/mash/pull/338)
- Cleanup GCE uploader integration.
  [\#339](https://github.com/SUSE-Enceladus/mash/pull/339)
- Fix key rotation.
  [\#342](https://github.com/SUSE-Enceladus/mash/pull/342)
- Fix ec2 account update.
  [\#343](https://github.com/SUSE-Enceladus/mash/pull/343)
- Drop uploader event loop.
  [\#345](https://github.com/SUSE-Enceladus/mash/pull/345)

v1.0.0 (2018-10-01)
===================

- Move run tests method to base testing job class.
- Integrate GCE through testing service.
- Make share with and allow copy optional.
- Add comment on pytest __test__ usage.
- Delete job doc logging from obs and uploader.

v0.2.0 (2018-09-21)
===================

- Select random instance type if None provided in job doc.
- Print traceback in log if unexpected exception in IPA testing.
- Set date in cloud image name based on expected {date} format string.
- Move job logs to a jobs dir.
- Fix bug fetch image name should have period appended.
- Fix bug, log error and set failed status before sending message
  in OBS service.
- Send delete message to uploader if OBS serivice receives a delete
  job message.
- Unbind job keys from uploader listener queue when job deleted.
- Remove utctime special handling in uploader.
- Use cloud image name with .vhd appended for blob name instead
  of the file name.

v0.1.0 (2018-09-14)
===================

- Update requirements in spec and setup.
- Update private key in testing service to match IPA.
- Send status message on obs job failure.
- Improve error message for web content exceptions.
- Use file name in Azure storage instead of image name.
  + Azure image blobs must have .vhd extension.
- Log IPA results file location in job log.
- Remove arch evaluation.
  + Arch is expected to be x86\_64.
- Combine download\_root, project and repository into 
  download\_url argument.

v0.0.1 (2018-08-27)
===================

- Initial release.
