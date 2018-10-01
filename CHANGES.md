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
