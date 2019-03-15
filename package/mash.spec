#
# spec file for package mash
#
# Copyright (c) 2017 SUSE LINUX GmbH, Nuernberg, Germany.
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.

# Please submit bugfixes or comments via http://bugs.opensuse.org/
#


Name:           mash
Version:        2.3.0
Release:        0
Url:            https://github.com/SUSE-Enceladus/mash
Summary:        Public Cloud Release Tool
License:        GPL-3.0+
Group:          System/Management
Source:         mash-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-adal
BuildRequires:  python3-apache-libcloud
BuildRequires:  python3-azure-mgmt-compute
BuildRequires:  python3-azure-mgmt-resource
BuildRequires:  python3-azure-mgmt-storage
BuildRequires:  python3-azure-storage
BuildRequires:  python3-boto3
BuildRequires:  python3-cryptography >= 2.3.0
BuildRequires:  python3-jsonschema
BuildRequires:  python3-PyYAML
BuildRequires:  python3-PyJWT
BuildRequires:  python3-amqpstorm >= 2.4.0
BuildRequires:  python3-APScheduler >= 3.3.1
BuildRequires:  python3-python-dateutil >= 2.6.0
BuildRequires:  python3-python-dateutil < 3.0.0
BuildRequires:  python3-ec2imgutils
BuildRequires:  python3-ipa>=3.0.0
BuildRequires:  python3-ipa-tests>=3.0.0
BuildRequires:  python3-lxml
BuildRequires:  python3-Flask
BuildRequires:  python3-requests
Requires:       rabbitmq-server
Requires:       python3-adal
Requires:       python3-apache-libcloud
Requires:       python3-azure-mgmt-compute
Requires:       python3-azure-mgmt-resource
Requires:       python3-azure-mgmt-storage
Requires:       python3-azure-storage
Requires:       python3-boto3
Requires:       python3-cryptography >= 2.3.0
Requires:       python3-jsonschema
Requires:       python3-PyYAML
Requires:       python3-PyJWT
Requires:       python3-amqpstorm >= 2.4.0
Requires:       python3-APScheduler >= 3.3.1
Requires:       python3-python-dateutil >= 2.6.0
Requires:       python3-python-dateutil < 3.0.0
Requires:       python3-ec2imgutils
Requires:       python3-ipa>=3.0.0
Requires:       python3-ipa-tests>=3.0.0
Requires:       python3-lxml
Requires:       python3-Flask
Requires:       python3-requests
Requires:       apache2
Requires:       apache2-mod_wsgi-python3
Requires(pre):  pwdutils
BuildArch:      noarch

%description
Public Cloud Release Tool for release automation from image
build in obs to image available for customers in the public
cloud

%prep
%setup -q -n mash-%{version}

%build
python3 setup.py build

%install
python3 setup.py install --prefix=%{_prefix} --root=%{buildroot}

mkdir -p %{buildroot}%{_localstatedir}/log/%{name}

install -D -m 644 config/mash_config.yaml \
    %{buildroot}%{_sysconfdir}/%{name}/mash_config.yaml

install -D -m 644 mash/wsgi.py \
    %{buildroot}%{_localstatedir}/lib/%{name}/wsgi.py

install -D -m 644 config/mash.conf \
    %{buildroot}%{_sysconfdir}/apache2/vhosts.d/mash.conf

install -D -m 644 config/mash_obs.service \
    %{buildroot}%{_unitdir}/mash_obs.service

install -D -m 644 config/mash_uploader.service \
    %{buildroot}%{_unitdir}/mash_uploader.service

install -D -m 644 config/mash_logger.service \
    %{buildroot}%{_unitdir}/mash_logger.service

install -D -m 644 config/mash_credentials.service \
    %{buildroot}%{_unitdir}/mash_credentials.service

install -D -m 644 config/mash_job_creator.service \
    %{buildroot}%{_unitdir}/mash_job_creator.service

install -D -m 644 config/mash_testing.service \
    %{buildroot}%{_unitdir}/mash_testing.service

install -D -m 644 config/mash_replication.service \
    %{buildroot}%{_unitdir}/mash_replication.service

install -D -m 644 config/mash_publisher.service \
    %{buildroot}%{_unitdir}/mash_publisher.service

install -D -m 644 config/mash_deprecation.service \
    %{buildroot}%{_unitdir}/mash_deprecation.service

%pre
%{_bindir}/getent group mash > /dev/null || %{_sbindir}/groupadd mash
%{_bindir}/getent passwd mash > /dev/null || %{_sbindir}/useradd -r -g mash -s %{_bindir}/false -c "User for MASH" -d %{_localstatedir}/lib/mash mash

%files
%defattr(-,root,root,-)
%{python3_sitelib}/*
%dir %attr(755, mash, mash)%{_localstatedir}/log/mash
%dir %attr(755, mash, mash)%{_localstatedir}/lib/mash
%dir %attr(755, mash, mash)%{_sysconfdir}/%{name}
%attr(640, mash, mash)%{_localstatedir}/lib/%{name}/wsgi.py
%dir %{_sysconfdir}/apache2
%dir %{_sysconfdir}/apache2/vhosts.d
%config(noreplace) %attr(640, mash, mash)%{_sysconfdir}/apache2/vhosts.d/mash.conf
%config(noreplace) %attr(640, mash, mash)%{_sysconfdir}/%{name}/mash_config.yaml

%{_bindir}/mash-obs-service
%{_unitdir}/mash_obs.service

%{_bindir}/mash-uploader-service
%{_unitdir}/mash_uploader.service

%{_bindir}/mash-logger-service
%{_unitdir}/mash_logger.service

%{_bindir}/mash-credentials-service
%{_unitdir}/mash_credentials.service

%{_bindir}/mash-job-creator-service
%{_unitdir}/mash_job_creator.service

%{_bindir}/mash-testing-service
%{_unitdir}/mash_testing.service

%{_bindir}/mash-replication-service
%{_unitdir}/mash_replication.service

%{_bindir}/mash-publisher-service
%{_unitdir}/mash_publisher.service

%{_bindir}/mash-deprecation-service
%{_unitdir}/mash_deprecation.service

%changelog
