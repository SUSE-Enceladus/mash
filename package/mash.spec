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
Version:        4.0.1
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
BuildRequires:  python3-azure-storage-blob
BuildRequires:  python3-boto3
BuildRequires:  python3-cryptography >= 2.2.0
BuildRequires:  python3-PyYAML
BuildRequires:  python3-PyJWT
BuildRequires:  python3-amqpstorm >= 2.4.0
BuildRequires:  python3-APScheduler >= 3.3.1
BuildRequires:  python3-python-dateutil >= 2.6.0
BuildRequires:  python3-python-dateutil < 3.0.0
BuildRequires:  python3-ec2imgutils
BuildRequires:  python3-img-proof >= 4.0.0
BuildRequires:  python3-img-proof-tests >= 4.0.0
BuildRequires:  python3-lxml
BuildRequires:  python3-Flask
BuildRequires:  python3-flask-restplus
BuildRequires:  python3-Flask-SQLAlchemy
BuildRequires:  python3-Flask-Migrate
BuildRequires:  python3-flask-jwt-extended
BuildRequires:  python3-requests
BuildRequires:  python3-obs-img-utils <= 0.0.3
Requires:       rabbitmq-server
Requires:       python3-adal
Requires:       python3-apache-libcloud
Requires:       python3-azure-mgmt-compute
Requires:       python3-azure-mgmt-resource
Requires:       python3-azure-mgmt-storage
Requires:       python3-azure-storage-blob
Requires:       python3-boto3
Requires:       python3-cryptography >= 2.2.0
Requires:       python3-PyYAML
Requires:       python3-PyJWT
Requires:       python3-amqpstorm >= 2.4.0
Requires:       python3-APScheduler >= 3.3.1
Requires:       python3-python-dateutil >= 2.6.0
Requires:       python3-python-dateutil < 3.0.0
Requires:       python3-ec2imgutils
Requires:       python3-img-proof >= 4.0.0
Requires:       python3-img-proof-tests >= 4.0.0
Requires:       python3-lxml
Requires:       python3-Flask
Requires:       python3-flask-restplus
Requires:       python3-Flask-SQLAlchemy
Requires:       python3-Flask-Migrate
Requires:       python3-flask-jwt-extended
Requires:       python3-requests
Requires:       python3-obs-img-utils <= 0.0.3
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

install -D -m 644 mash/services/api/wsgi.py \
    %{buildroot}%{_localstatedir}/lib/%{name}/wsgi.py

install -d -m 755 %{buildroot}%{_localstatedir}/lib/%{name}/migrations
cp -r mash/services/api/migrations/* %{buildroot}%{_localstatedir}/lib/%{name}/migrations/

install -D -m 644 config/mash.conf \
    %{buildroot}%{_sysconfdir}/apache2/vhosts.d/mash.conf

install -D -m 644 mash/services/credentials/wsgi.py \
    %{buildroot}%{_localstatedir}/lib/%{name}/credentials/wsgi.py

install -D -m 644 config/credentials.conf \
    %{buildroot}%{_sysconfdir}/apache2/vhosts.d/credentials.conf

install -D -m 644 config/mash_obs.service \
    %{buildroot}%{_unitdir}/mash_obs.service

install -D -m 644 config/mash_uploader.service \
    %{buildroot}%{_unitdir}/mash_uploader.service

install -D -m 644 config/mash_logger.service \
    %{buildroot}%{_unitdir}/mash_logger.service

install -D -m 644 config/mash_job_creator.service \
    %{buildroot}%{_unitdir}/mash_job_creator.service

install -D -m 644 config/mash_testing.service \
    %{buildroot}%{_unitdir}/mash_testing.service

install -D -m 644 config/mash_raw_image_uploader.service \
    %{buildroot}%{_unitdir}/mash_raw_image_uploader.service

install -D -m 644 config/mash_replication.service \
    %{buildroot}%{_unitdir}/mash_replication.service

install -D -m 644 config/mash_publisher.service \
    %{buildroot}%{_unitdir}/mash_publisher.service

install -D -m 644 config/mash_deprecation.service \
    %{buildroot}%{_unitdir}/mash_deprecation.service

%pre
%{_bindir}/getent group mash > /dev/null || %{_sbindir}/groupadd mash
%{_bindir}/getent passwd mash > /dev/null || %{_sbindir}/useradd -r -g mash -s %{_bindir}/false -c "User for MASH" -d %{_localstatedir}/lib/mash mash

%check
python3 -m pytest

%files
%defattr(-,root,root,-)
%{python3_sitelib}/*
%dir %attr(755, mash, mash)%{_localstatedir}/log/mash
%dir %attr(755, mash, mash)%{_localstatedir}/lib/mash
%dir %attr(755, mash, mash)%{_localstatedir}/lib/mash/credentials
%dir %attr(755, mash, mash)%{_localstatedir}/lib/mash/migrations
%dir %attr(755, mash, mash)%{_localstatedir}/lib/mash/migrations/versions
%dir %attr(755, mash, mash)%{_sysconfdir}/%{name}
%attr(640, mash, mash)%{_localstatedir}/lib/%{name}/wsgi.py
%attr(640, mash, mash)%{_localstatedir}/lib/%{name}/credentials/wsgi.py
%attr(640, mash, mash)%{_localstatedir}/lib/%{name}/migrations/versions/*
%attr(640, mash, mash)%{_localstatedir}/lib/%{name}/migrations/alembic.ini
%attr(640, mash, mash)%{_localstatedir}/lib/%{name}/migrations/env.py
%attr(640, mash, mash)%{_localstatedir}/lib/%{name}/migrations/README
%attr(640, mash, mash)%{_localstatedir}/lib/%{name}/migrations/script.py.mako
%dir %{_sysconfdir}/apache2
%dir %{_sysconfdir}/apache2/vhosts.d
%config(noreplace) %attr(640, mash, mash)%{_sysconfdir}/apache2/vhosts.d/mash.conf
%config(noreplace) %attr(640, mash, mash)%{_sysconfdir}/apache2/vhosts.d/credentials.conf
%config(noreplace) %attr(640, mash, mash)%{_sysconfdir}/%{name}/mash_config.yaml

%{_bindir}/mash-obs-service
%{_unitdir}/mash_obs.service

%{_bindir}/mash-uploader-service
%{_unitdir}/mash_uploader.service

%{_bindir}/mash-logger-service
%{_unitdir}/mash_logger.service

%{_bindir}/mash-job-creator-service
%{_unitdir}/mash_job_creator.service

%{_bindir}/mash-testing-service
%{_unitdir}/mash_testing.service

%{_bindir}/mash-raw-image-uploader-service
%{_unitdir}/mash_raw_image_uploader.service

%{_bindir}/mash-replication-service
%{_unitdir}/mash_replication.service

%{_bindir}/mash-publisher-service
%{_unitdir}/mash_publisher.service

%{_bindir}/mash-deprecation-service
%{_unitdir}/mash_deprecation.service

%changelog
