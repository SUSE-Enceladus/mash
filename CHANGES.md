v12.1.1 (2022-03-28)
====================

- Fix parameter order in start change set call
  [\#814](https://github.com/SUSE-Enceladus/mash/pull/814)
- Fix aws mp bug. Cast dict keys to a list before use
  [\#815](https://github.com/SUSE-Enceladus/mash/pull/815)
- Require all change set attrs
  [\#816](https://github.com/SUSE-Enceladus/mash/pull/816)

v12.1.0 (2022-03-24)
====================

- The default key for token identity is now "sub"
  [\#801](https://github.com/SUSE-Enceladus/mash/pull/801)
- Default guest os features to empty list
  [\#802](https://github.com/SUSE-Enceladus/mash/pull/802)
- Bump the size of generated ssh keys to 4096
  [\#803](https://github.com/SUSE-Enceladus/mash/pull/803)
- Change whitelist to allowlist
  [\#804](https://github.com/SUSE-Enceladus/mash/pull/804)
- Add handling for EC2 MP publishing
  [\#805](https://github.com/SUSE-Enceladus/mash/pull/805)
  [\#809](https://github.com/SUSE-Enceladus/mash/pull/809)

v12.0.0 (2022-02-17)
====================

- Update code for breaking changes in flask-jwt-extended >= 4.0.2
  [\#796](https://github.com/SUSE-Enceladus/mash/pull/796)

v11.6.0 (2022-02-09)
====================

- Add sle-micro enum to mash job distro arg
  [\#798](https://github.com/SUSE-Enceladus/mash/pull/798)
- Add a 5 minute wait before checking images during Aliyun replication
  [\#799](https://github.com/SUSE-Enceladus/mash/pull/799)
- Fix pytest 7 compatibility. Use setup_method instead setup
  [\#800](https://github.com/SUSE-Enceladus/mash/pull/800)

v11.5.0 (2022-01-21)
====================

- Add ssh_user option for all jobs
  [\#797](https://github.com/SUSE-Enceladus/mash/pull/797)

v11.4.2 (2022-01-04)
====================

- Fix exception logging for aliyun replicate class
  [\#795](https://github.com/SUSE-Enceladus/mash/pull/795)

v11.4.1 (2021-12-17)
====================

- Add rpm-macros to build requirements in spec.

v11.4.0 (2021-12-10)
====================

- Log Aliyun replication errors.
  [\#790](https://github.com/SUSE-Enceladus/mash/pull/790)
- Log if Aliyun image id is None during replication.
  [\#792](https://github.com/SUSE-Enceladus/mash/pull/792)

v11.3.0 (2021-10-13)
====================

- Add a slow rollout policy to new GCE images.
  [\#780](https://github.com/SUSE-Enceladus/mash/pull/780)
- Format Aliyun date in image description if it exists.
  [\#789](https://github.com/SUSE-Enceladus/mash/pull/789)

v11.2.0 (2021-07-21)
====================

- Handle gvnic option for GCE.
  [\#778](https://github.com/SUSE-Enceladus/mash/pull/778)
- Allow RS256 signing algorithm.
  [\#779](https://github.com/SUSE-Enceladus/mash/pull/779)
- Random choice requires an indexable type.
  [\#781](https://github.com/SUSE-Enceladus/mash/pull/781)
- Drop requirement on idna.
  [\#782](https://github.com/SUSE-Enceladus/mash/pull/782)
- Drop version limit on werkzeug.
  [\#783](https://github.com/SUSE-Enceladus/mash/pull/783)
- Use temporary key pairs for aliyun testing.
  [\#784](https://github.com/SUSE-Enceladus/mash/pull/784)
- Provide replacement image for aliyun deprecation.
  [\#785](https://github.com/SUSE-Enceladus/mash/pull/785)

v11.1.0 (2021-06-14)
===================

- Relax dateutil requirements.
  [\#773](https://github.com/SUSE-Enceladus/mash/pull/773)
- Always pass in jwt algorithms for decoding.
  [\#774](https://github.com/SUSE-Enceladus/mash/pull/774)
- Drop jwt error routing workaround.
  [\#776](https://github.com/SUSE-Enceladus/mash/pull/776)
- Track image id per region for job status.
  [\#777](https://github.com/SUSE-Enceladus/mash/pull/777)

v11.0.0 (2021-05-07)
===================

- Update Azure instance list to handle gen1 and gen2.
  [\#767](https://github.com/SUSE-Enceladus/mash/pull/767)
- Add versioning to API (v1).
- Migrate to flask-restx.
  [\#768](https://github.com/SUSE-Enceladus/mash/pull/768)
- Remove any duplicate regions from EC2 list.
  [\#770](https://github.com/SUSE-Enceladus/mash/pull/770)
- Fix SAS URL for Azure publish.
  [\#771](https://github.com/SUSE-Enceladus/mash/pull/771)

v10.0.0 (2021-04-07)
===================

- Add helper error message when tests fail.
  [\#735](https://github.com/SUSE-Enceladus/mash/pull/735)
- Raise exception if offer doc not updated.
  [\#739](https://github.com/SUSE-Enceladus/mash/pull/739)
- Add paging for list job route.
  [\#746](https://github.com/SUSE-Enceladus/mash/pull/746)
- Use latest Azure SDK packages.
  [\#757](https://github.com/SUSE-Enceladus/mash/pull/757)
- Integrate Aliyun cloud.
  [\#766](https://github.com/SUSE-Enceladus/mash/pull/766)

v9.2.0 (2021-03-12)
===================

- Use gp3 as the default root volume for EC2 images
  [\#726](https://github.com/SUSE-Enceladus/mash/pull/726)
- Add all failed conditions to errors.
  [\#736](https://github.com/SUSE-Enceladus/mash/pull/736)
- Break image creation loop on failure.
  [\#737](https://github.com/SUSE-Enceladus/mash/pull/737)

v9.1.1 (2020-11-19)
===================

- Fail eagerly in ec2 testing.
  [\#724](https://github.com/SUSE-Enceladus/mash/pull/724)
- Add service name info to msg when jobs fail.
  [\#725](https://github.com/SUSE-Enceladus/mash/pull/725)

v9.1.0 (2020-11-04)
===================

- Remove reference to iteration.
  [\#717](https://github.com/SUSE-Enceladus/mash/pull/717)
- Fix guest os features keys for image creation.
  [\#718](https://github.com/SUSE-Enceladus/mash/pull/718)
- Add use_build_time job flag.
  [\#719](https://github.com/SUSE-Enceladus/mash/pull/719)
- Test instances with SEV_CAPABLE flag set.
  [\#720](https://github.com/SUSE-Enceladus/mash/pull/720)
- Add force replace image option for jobs.
  [\#721](https://github.com/SUSE-Enceladus/mash/pull/721)
- Remove upper requirement on crypto package.
  [\#722](https://github.com/SUSE-Enceladus/mash/pull/722)
- Raise exception if storing creds fails.
  [\#723](https://github.com/SUSE-Enceladus/mash/pull/723)

v9.0.0 (2020-09-30)
===================

- Update list of valid service names in readme.
  [\#673](https://github.com/SUSE-Enceladus/mash/pull/673)
- Cleanup s3 raw image upload.
  [\#674](https://github.com/SUSE-Enceladus/mash/pull/674)
- Cloud_image_name and description are not required.
  [\#675](https://github.com/SUSE-Enceladus/mash/pull/675)
- Use user email for notifications.
  [\#676](https://github.com/SUSE-Enceladus/mash/pull/676)
- Remove deprecated string format usage.
  [\#682](https://github.com/SUSE-Enceladus/mash/pull/682)
- Add MASH cleanup service.
  [\#697](https://github.com/SUSE-Enceladus/mash/pull/697)
- Cleanup unused share snapshot arg.
  [\#705](https://github.com/SUSE-Enceladus/mash/pull/705)
- Set a prefix for img-proof tests.
  [\#706](https://github.com/SUSE-Enceladus/mash/pull/706)
- Handle error when getting classic sa keys.
  [\#713](https://github.com/SUSE-Enceladus/mash/pull/713)
- Migrate to GCE SDK from Libcloud.
- Add job status API.
  [\#716](https://github.com/SUSE-Enceladus/mash/pull/716)

v8.0.0 (2020-06-19)
===================

- Provide log callback to img-proof.
  [\#663](https://github.com/SUSE-Enceladus/mash/pull/663)
- Move required arg validation to utils.
  [\#665](https://github.com/SUSE-Enceladus/mash/pull/665)
- Pass job logger to ec2imgutils.
  [\#666](https://github.com/SUSE-Enceladus/mash/pull/666)
- Rename all service to be consistent.
  [\#667](https://github.com/SUSE-Enceladus/mash/pull/667)
- Don't sleep if there's no region replication.
  [\#668](https://github.com/SUSE-Enceladus/mash/pull/668)
- Reorder job validation.
  [\#669](https://github.com/SUSE-Enceladus/mash/pull/669)
- Update ec2imgutils version requirement.
  [\#670](https://github.com/SUSE-Enceladus/mash/pull/670)
- Set cloud image name as instance attr.
  [\#671](https://github.com/SUSE-Enceladus/mash/pull/671)
- Remove trailing and leading whitespace.
  [\#672](https://github.com/SUSE-Enceladus/mash/pull/672)

v7.0.0 (2020-06-01)
===================

- Change secure boot options.
  [\#649](https://github.com/SUSE-Enceladus/mash/pull/649)
- Fix image project bug.
  [\#650](https://github.com/SUSE-Enceladus/mash/pull/650)
- Extend length of sas blob url.
  [\#651](https://github.com/SUSE-Enceladus/mash/pull/651)
- Log message if image not in region.
  [\#652](https://github.com/SUSE-Enceladus/mash/pull/652)
- Better handle the delete message.
  [\#653](https://github.com/SUSE-Enceladus/mash/pull/653)
- Add additional upload option and raw tarball upload for Azure.
  [\#654](https://github.com/SUSE-Enceladus/mash/pull/654)
- Add snapshot sharing for EC2 images.
  [\#655](https://github.com/SUSE-Enceladus/mash/pull/655)
- Fix logging in listener service classes.
  [\#656](https://github.com/SUSE-Enceladus/mash/pull/656)
- Accept credentials URL without trailing slash.
  [\#657](https://github.com/SUSE-Enceladus/mash/pull/657)
- Cleanup on EC2 create failure.
  [\#658](https://github.com/SUSE-Enceladus/mash/pull/658)
- Remove accounts file example.
  [\#659](https://github.com/SUSE-Enceladus/mash/pull/659)
- Update snapshot sharing option for ec2 jobs.
  [\#660](https://github.com/SUSE-Enceladus/mash/pull/660)
- Add flag in ec2 testing.
  [\#661](https://github.com/SUSE-Enceladus/mash/pull/661)

v6.0.0 (2020-04-22)
===================

- Handle both interrupts and terminate signals.
  [\#639](https://github.com/SUSE-Enceladus/mash/pull/639)
- Implement oauth2/oidc authentication route.
  [\#640](https://github.com/SUSE-Enceladus/mash/pull/640)
- Fix werkzeug regression in unit tests.
  [\#641](https://github.com/SUSE-Enceladus/mash/pull/641)
- Subject is now an arg when sending a message.
  [\#642](https://github.com/SUSE-Enceladus/mash/pull/642)
- Implement password reset API.
  [\#643](https://github.com/SUSE-Enceladus/mash/pull/643)
- Integrate dissalow licenses and packages options.
  [\#644](https://github.com/SUSE-Enceladus/mash/pull/644)
- Update descriptions for all job doc args.
  [\#646](https://github.com/SUSE-Enceladus/mash/pull/646)
- Update regions and helper images for ec2.
  [\#647](https://github.com/SUSE-Enceladus/mash/pull/647)
- Add uefi and secure boot options for testing.
  [\#648](https://github.com/SUSE-Enceladus/mash/pull/648)

v5.2.0 (2020-03-10)
===================

- Delete all user credentials when user deleted.
  [\#634](https://github.com/SUSE-Enceladus/mash/pull/634)
- Update default development port for credentials.
  [\#635](https://github.com/SUSE-Enceladus/mash/pull/635)
- Add configuration options for thread pool count.
  [\#636](https://github.com/SUSE-Enceladus/mash/pull/636)
- Use debug level in img-proof testing.
  [\#637](https://github.com/SUSE-Enceladus/mash/pull/637)

v5.1.0 (2020-02-24)
===================

- Integrate OCI cloud framework to the image pipeline.
- Add utility for generating fingerprint.
  [\#610](https://github.com/SUSE-Enceladus/mash/pull/610)
- Add temporary version requirement on werkzeug.
- Ignore wsgi.py file in credentials dir.
  [\#626](https://github.com/SUSE-Enceladus/mash/pull/626)

v5.0.1 (2020-1-21)
===================

- Add missing comma in setup.py to fix build.

v5.0.0 (2020-1-21)
===================

- Add upload consistency to all cloud frameworks.
  [\#609](https://github.com/SUSE-Enceladus/mash/pull/609)

v4.4.0 (2019-12-20)
===================

- Add utf encoding to spec check section.
  [\#602](https://github.com/SUSE-Enceladus/mash/pull/602)
- Add app context to cli runner for cli tests.
  [\#603](https://github.com/SUSE-Enceladus/mash/pull/603)
- Add cloud account option for ec2 jobs.
  [\#604](https://github.com/SUSE-Enceladus/mash/pull/604)
- Add image cleanup to ec2 testing class.
  [\#605](https://github.com/SUSE-Enceladus/mash/pull/605)
- Update job deletion message.
  [\#606](https://github.com/SUSE-Enceladus/mash/pull/606)

v4.3.0 (2019-11-23)
===================

- Add image name to email notification template.
  [\#572](https://github.com/SUSE-Enceladus/mash/pull/572)
- Inject configuration into services.
  [\#573](https://github.com/SUSE-Enceladus/mash/pull/573)
- Move send email methods to new class.
  [\#575](https://github.com/SUSE-Enceladus/mash/pull/575)
- Add flask mgmt command for cleanup tokens.
  [\#577](https://github.com/SUSE-Enceladus/mash/pull/577)
- Log unhandled exceptions in API.
  [\#578](https://github.com/SUSE-Enceladus/mash/pull/578)
- Handle ec2 job doc without cloud accounts.
  [\#579](https://github.com/SUSE-Enceladus/mash/pull/579)
- Add source regions to raw image uploader args.
  [\#580](https://github.com/SUSE-Enceladus/mash/pull/580)
- Fix GCE cleanup integration.
  [\#582](https://github.com/SUSE-Enceladus/mash/pull/582)
- Cleanup azure image and blob on test failure.
  [\#583](https://github.com/SUSE-Enceladus/mash/pull/583)
- Azure remove account list
  [\#585](https://github.com/SUSE-Enceladus/mash/pull/585)
- Implement Azure SAS URL upload.
  [\#586](https://github.com/SUSE-Enceladus/mash/pull/586)
- Use yaml safe load instead of load.
  [\#587](https://github.com/SUSE-Enceladus/mash/pull/587)
- Remove account list handling from GCE.
  [\#588](https://github.com/SUSE-Enceladus/mash/pull/588)
- Fix retry region testing.
  [\#589](https://github.com/SUSE-Enceladus/mash/pull/589)
- Update the version for obs-img-utils.
  [\#591](https://github.com/SUSE-Enceladus/mash/pull/591)
- Fix upper version requirements for dependencies.
  [\#597](https://github.com/SUSE-Enceladus/mash/pull/597)
- Fix typo in job conditions schema.
  [\#598](https://github.com/SUSE-Enceladus/mash/pull/598)
- Distro is an optional argument.
  [\#599](https://github.com/SUSE-Enceladus/mash/pull/599)
- Add disk generation option for Azure publish.
  [\#600](https://github.com/SUSE-Enceladus/mash/pull/600)
- Handle image conditions changes from obs-img-utils.
  [\#601](https://github.com/SUSE-Enceladus/mash/pull/601)

v4.2.0 (2019-10-04)
===================

- Add email whitelist config option.
  [\#571](https://github.com/SUSE-Enceladus/mash/pull/571)

v4.1.0 (2019-10-02)
===================

- Cleanup requirements names in spec.
  [\#565](https://github.com/SUSE-Enceladus/mash/pull/565)
- Add ARM instance types.
  [\#567](https://github.com/SUSE-Enceladus/mash/pull/567)
- Remove dependency on test dir.
  [\#568](https://github.com/SUSE-Enceladus/mash/pull/568)
- Add conditions wait time job option.
  [\#569](https://github.com/SUSE-Enceladus/mash/pull/569)
- Add raw image uploader service.
  [\#570](https://github.com/SUSE-Enceladus/mash/pull/570)

v4.0.1 (2019-09-27)
===================

- Remove credentials service entry point. Credentials
  service is not a systemd unit.

v4.0.0 (2019-09-27)
===================

- API authentication and credentials service migration.
- Add authentication to API.
- Move Account handling from datastore to database.
- Simplify credentials service, only stores/retrieves 
  credentials as encrypted json files.
- Convert credentials service to an API vs an AMQP based 
  service.
- Add full set of API endpoints for account, user, token 
  and auth handling.
- Setup simple API endpoints for job handling (to be 
  built upon).
- [\564](https://github.com/SUSE-Enceladus/mash/pull/564)

v3.4.0 (2019-08-06)
===================

- Add new AWS region me-south-1.
  [\#499](https://github.com/SUSE-Enceladus/mash/pull/499)
- Get new session for each boto3 client.
  [\#502](https://github.com/SUSE-Enceladus/mash/pull/502)
- Check ec2 image status in waiter. Instead of using waiter from boto3.
  [\#505](https://github.com/SUSE-Enceladus/mash/pull/505)
- Add copyright notice to api/routes init module.
  [\#508](https://github.com/SUSE-Enceladus/mash/pull/508)
- Use flask-restplus to serve class based api views.
- Split up job add endpoints by cloud framework.
- Split account delete endpoints by cloud framework.
- Serve api specification json to api/spec.

v3.3.0 (2019-07-26)
===================

- Add .db sqlite extension to gitignore.
  [\#491](https://github.com/SUSE-Enceladus/mash/pull/491)
- Split up API schema.
  [\#492](https://github.com/SUSE-Enceladus/mash/pull/492)
- Fix version creep in spec.
  [\#494](https://github.com/SUSE-Enceladus/mash/pull/494)
- Add search/replace strings for spec version.
  [\#495](https://github.com/SUSE-Enceladus/mash/pull/495)
- Configurable subnet in EC2
  [\#496](https://github.com/SUSE-Enceladus/mash/pull/496)
- Add subnet option to accounts in ec2 job doc.
  [\#497](https://github.com/SUSE-Enceladus/mash/pull/497)
- Remove any instance types that are not everywhere.
  [\#498](https://github.com/SUSE-Enceladus/mash/pull/498)

v3.2.0 (2019-07-22)
===================

- Testing service: retry test in fallback region
  [\#489](https://github.com/SUSE-Enceladus/mash/pull/489)
- Add guest os features option for gce.
  [\#490](https://github.com/SUSE-Enceladus/mash/pull/490)

v3.1.0 (2019-07-17)
===================

- Run Azure upload in separate process.
  [\#480](https://github.com/SUSE-Enceladus/mash/pull/480)
- Remove very large instance from GCE.
  [\#486](https://github.com/SUSE-Enceladus/mash/pull/486)
- Migrate obs service to obs-img-utils.
  [\#488](https://github.com/SUSE-Enceladus/mash/pull/488)

v3.0.1 (2019-06-09)
===================

- Update azure storage package requirements.
  [\#475](https://github.com/SUSE-Enceladus/mash/pull/475)

v3.0.0 (2019-06-06)
===================

- Refactor service job classes to use post_init workflow.
  [\#431](https://github.com/SUSE-Enceladus/mash/pull/431)
- Move account/credentials functions to new datastore class.
  [\#435](https://github.com/SUSE-Enceladus/mash/pull/435)
- Check each key in job creator tests.
  [\#439](https://github.com/SUSE-Enceladus/mash/pull/439)
- Remove unused uploader conventions classes.
  [\#441](https://github.com/SUSE-Enceladus/mash/pull/441)
- Rename test_deprecation_start_job.
  [\#442](https://github.com/SUSE-Enceladus/mash/pull/442)
- Create service classes as Pipeline instances.
  [\#443](https://github.com/SUSE-Enceladus/mash/pull/443)
- Remove azure deprecation functionality.
  [\#444](https://github.com/SUSE-Enceladus/mash/pull/444)
- Add new AWS region ap-east-1.
  [\#445](https://github.com/SUSE-Enceladus/mash/pull/445)
- Update layout diagram.
  [\#446](https://github.com/SUSE-Enceladus/mash/pull/446)
- Fix fetch index list href retrieval.
  [\#447](https://github.com/SUSE-Enceladus/mash/pull/447)
- Use service exchange name for log module name.
  [\#448](https://github.com/SUSE-Enceladus/mash/pull/448)
- Migrate uploader classes to pipeline workflow
  [\#449](https://github.com/SUSE-Enceladus/mash/pull/449)
- Handle any uncaught exceptions from datastore.
  [\#450](https://github.com/SUSE-Enceladus/mash/pull/450)
- Make run_job method public.
  [\#451](https://github.com/SUSE-Enceladus/mash/pull/451)
- GCE family is optional.
  [\#452](https://github.com/SUSE-Enceladus/mash/pull/452)
- Move credentials methods to pipeline service.
  [\#453](https://github.com/SUSE-Enceladus/mash/pull/453)
- Set image name as base attr.
  [\#454](https://github.com/SUSE-Enceladus/mash/pull/454)
- Move next/prev methods to pipeline service.
  [\#455](https://github.com/SUSE-Enceladus/mash/pull/455)
- Migrate job specific methods.
  [\#459](https://github.com/SUSE-Enceladus/mash/pull/459)
- Wait for gce create image to complete.
  [\#460](https://github.com/SUSE-Enceladus/mash/pull/460)
- Remove references to pint service.
  [\#464](https://github.com/SUSE-Enceladus/mash/pull/464)
- Add is_publishing_account option to gce jobs.
  [\#466](https://github.com/SUSE-Enceladus/mash/pull/466)
- Add use root swap option for ec2 upload.
  [\#467](https://github.com/SUSE-Enceladus/mash/pull/467)
- Make distro option an enum.
  [\#469](https://github.com/SUSE-Enceladus/mash/pull/469)
- Update dependencies and name for ipa.
  [\#470](https://github.com/SUSE-Enceladus/mash/pull/470)
- Add image cleanup for gce.
  [\#472](https://github.com/SUSE-Enceladus/mash/pull/472)
- Rename pipeline service to listener service.
  [\#473](https://github.com/SUSE-Enceladus/mash/pull/473)
- Remove F821 from ignore list in config.
  [\#474](https://github.com/SUSE-Enceladus/mash/pull/474)

v2.5.0 (2019-04-11)
===================

- Add more details to readme.
  [\#430](https://github.com/SUSE-Enceladus/mash/pull/430)
- Remove unused validate message method.
  [\#432](https://github.com/SUSE-Enceladus/mash/pull/432)
- No need for instance var to hold msg properties.
  [\#433](https://github.com/SUSE-Enceladus/mash/pull/433)
- Move account keys to jc and creds services.
  [\#434](https://github.com/SUSE-Enceladus/mash/pull/434)
- Explicitly set showInGui to True in azure publish.
  [\#438](https://github.com/SUSE-Enceladus/mash/pull/438)

v2.4.0 (2019-03-26)
===================

- Update Azure publishing and deprecation workflow.
  [\#425](https://github.com/SUSE-Enceladus/mash/pull/425)
- Move get job log file method to base config.
  [\#426](https://github.com/SUSE-Enceladus/mash/pull/426)
- Use full extension for ec2 and azure image files.
  [\#427](https://github.com/SUSE-Enceladus/mash/pull/427)
- Provide region to UploadImage class in init.
  [\#428](https://github.com/SUSE-Enceladus/mash/pull/428)
- Job creator classes don't override init method.
  [\#429](https://github.com/SUSE-Enceladus/mash/pull/429)

v2.3.0 (2019-03-15)
===================

- Improve message for uploading, add region.
  [\#417](https://github.com/SUSE-Enceladus/mash/pull/417)
- Add billing codes option for ec2 publish jobs.
  [\#419](https://github.com/SUSE-Enceladus/mash/pull/419)
- Remove last region handling in uploader.
  [\#421](https://github.com/SUSE-Enceladus/mash/pull/421)
- Deep copy the regions list from cloud data.
  [\#423](https://github.com/SUSE-Enceladus/mash/pull/423)
- Download images to job specific dir.
  [\#424](https://github.com/SUSE-Enceladus/mash/pull/424)

v2.2.0 (2019-03-08)
===================

- Add Pull Request Template.
  [\#411](https://github.com/SUSE-Enceladus/mash/pull/411)
- Add email notifications.
  [\#412](https://github.com/SUSE-Enceladus/mash/pull/412)
- Add testing account option.
  [\#413](https://github.com/SUSE-Enceladus/mash/pull/413)

v2.1.0 (2019-02-22)
===================

- Integrate azure deprecation class.
  [\#387](https://github.com/SUSE-Enceladus/mash/pull/387)
- Start mash services after rabbitmq-server.
  [\#388](https://github.com/SUSE-Enceladus/mash/pull/388)
- Make OBS package conditions expressive.
  [\#389](https://github.com/SUSE-Enceladus/mash/pull/389)
- Move schema to api module where it's used.
  [\#390](https://github.com/SUSE-Enceladus/mash/pull/390)
- Move start jobs to base pipeline class.
  [\#391](https://github.com/SUSE-Enceladus/mash/pull/391)
- Cleanup start/stop service methods.
  [\#392](https://github.com/SUSE-Enceladus/mash/pull/392)
- Ack job doc message only after the job is saved.
  [\#393](https://github.com/SUSE-Enceladus/mash/pull/393)
- Move listener message args to list.
  [\#394](https://github.com/SUSE-Enceladus/mash/pull/394)
- Fixup systemd unit files for required services.
  [\#395](https://github.com/SUSE-Enceladus/mash/pull/395)
- Same defaults for ec2 options.
  [\#398](https://github.com/SUSE-Enceladus/mash/pull/398)
- Move get status message impl to pipeline class.
  [\#399](https://github.com/SUSE-Enceladus/mash/pull/399)
- Handle job verification better.
  [\#400](https://github.com/SUSE-Enceladus/mash/pull/400)
- Make accounts and groups optional in job doc.
  [\#401](https://github.com/SUSE-Enceladus/mash/pull/401)
- Remove random region handling for ec2 jobs.
  [\#402](https://github.com/SUSE-Enceladus/mash/pull/402)
- Ensure vpc is cleaned on ipa failure.
  [\#403](https://github.com/SUSE-Enceladus/mash/pull/403)
- Move image exists inside try block.
  [\#404](https://github.com/SUSE-Enceladus/mash/pull/404)
- Allow no tests in job doc.
  [\#405](https://github.com/SUSE-Enceladus/mash/pull/405)
- Better error message for empty image files.
  [\#406](https://github.com/SUSE-Enceladus/mash/pull/406)
- If no image matches image name raise exception.
  [\#409](https://github.com/SUSE-Enceladus/mash/pull/409)

v2.0.0 (2019-02-04)
===================

- Old cloud image name is optional.
  [\#372](https://github.com/SUSE-Enceladus/mash/pull/372)
- Implement Azure publishing.
  [\#373](https://github.com/SUSE-Enceladus/mash/pull/373)
- Update max workers default.
  [\#374](https://github.com/SUSE-Enceladus/mash/pull/374)
- Remove timeout from Azure copy blob function.
  [\#375](https://github.com/SUSE-Enceladus/mash/pull/375)
- Add architecture option to support aarch64.
  [\#377](https://github.com/SUSE-Enceladus/mash/pull/377)
- Add cleanup_images option.
  [\#379](https://github.com/SUSE-Enceladus/mash/pull/379)
- Wait for obs conditions to be met.
  [\#380](https://github.com/SUSE-Enceladus/mash/pull/380)
- Fix old cloud image name bug in job creator.
  [\#381](https://github.com/SUSE-Enceladus/mash/pull/381)
- Add GCE handling to replication and publisher.
  [\#382](https://github.com/SUSE-Enceladus/mash/pull/382)
- Implement GCE deprecation class.
  [\#383](https://github.com/SUSE-Enceladus/mash/pull/383)
- Move create auth file method to mash utils.
  [\#384](https://github.com/SUSE-Enceladus/mash/pull/384)
- Skip cred request in gce publish/replicate.
  [\#385](https://github.com/SUSE-Enceladus/mash/pull/385)
- Remove references to provider.
  [\#386](https://github.com/SUSE-Enceladus/mash/pull/386)

v1.4.0 (2019-01-03)
===================

- Fix us-west-2 helper ami id.
  [\#364](https://github.com/SUSE-Enceladus/mash/pull/364)
- Remove types that are not in all regions.
  [\#365](https://github.com/SUSE-Enceladus/mash/pull/365)
- Add source regions setter in replication job.
  [\#366](https://github.com/SUSE-Enceladus/mash/pull/366)
- Add prev service to base service class.
  [\#367](https://github.com/SUSE-Enceladus/mash/pull/367)
- Combine pipeline methods.
  [\#368](https://github.com/SUSE-Enceladus/mash/pull/368)
- Refactor credentials deletion.
  [\#369](https://github.com/SUSE-Enceladus/mash/pull/369)
- Rename base service to mash service.
  [\#370](https://github.com/SUSE-Enceladus/mash/pull/370)
- Add base mash job class for shared methods.
  [\#371](https://github.com/SUSE-Enceladus/mash/pull/371)

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
