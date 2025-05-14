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

%define python python
%{?sle15_python_module_pythons}

Name:           mash
Version:        13.15.0
Release:        0
Url:            https://github.com/SUSE-Enceladus/mash
Summary:        Public Cloud Release Tool
License:        GPL-3.0+
Group:          System/Management
Source:         mash-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildRequires:  file
BuildRequires:  python-rpm-macros
BuildRequires:  python311-pip
BuildRequires:  python311-setuptools
BuildRequires:  python311-wheel
BuildRequires:  python311-boto3
BuildRequires:  python311-cryptography >= 2.2.0
BuildRequires:  python311-PyYAML
BuildRequires:  python311-PyJWT
BuildRequires:  python311-amqpstorm >= 2.4.0
BuildRequires:  python311-APScheduler >= 3.3.1
BuildRequires:  python311-python-dateutil >= 2.6.0
BuildRequires:  python311-ec2imgutils >= 9.0.3
BuildRequires:  python311-img-proof >= 7.14.0
BuildRequires:  python311-img-proof-tests >= 7.14.0
BuildRequires:  python311-Flask
BuildRequires:  python311-flask-restx
BuildRequires:  python311-Flask-SQLAlchemy
BuildRequires:  python311-Flask-Migrate
BuildRequires:  python311-flask-jwt-extended
BuildRequires:  python311-requests
BuildRequires:  python311-obs-img-utils >= 1.0.0
BuildRequires:  python311-oci-sdk
BuildRequires:  python311-gceimgutils
BuildRequires:  python311-aliyun-img-utils >= 1.4.0
BuildRequires:  python311-azure-img-utils >= 2.0.0
BuildRequires:  python311-Werkzeug
BuildRequires:  python311-jmespath
Requires:       file
Requires:       rabbitmq-server
Requires:       python311-boto3
Requires:       python311-cryptography >= 2.2.0
Requires:       python311-PyYAML
Requires:       python311-PyJWT
Requires:       python311-amqpstorm >= 2.4.0
Requires:       python311-APScheduler >= 3.3.1
Requires:       python311-python-dateutil >= 2.6.0
Requires:       python311-ec2imgutils >= 9.0.3
Requires:       python311-img-proof >= 7.14.0
Requires:       python311-img-proof-tests >= 7.14.0
Requires:       python311-Flask
Requires:       python311-flask-restx
Requires:       python311-Flask-SQLAlchemy
Requires:       python311-Flask-Migrate
Requires:       python311-flask-jwt-extended
Requires:       python311-requests
Requires:       python311-obs-img-utils >= 1.0.0
Requires:       python311-oci-sdk
Requires:       python311-gceimgutils
Requires:       python311-aliyun-img-utils >= 1.4.0
Requires:       python311-azure-img-utils >= 2.0.0
Requires:       python311-Werkzeug
Requires:       python311-jmespath
Requires:       apache2
Requires:       apache2-mod_wsgi-python311
Requires(pre):  pwdutils
BuildArch:      noarch

%description
Public Cloud Release Tool for release automation from image
build in obs to image available for customers in the public
cloud

%prep
%autosetup -n mash-%{version}

%build
%pyproject_wheel

%install
%pyproject_install

mkdir -p %{buildroot}%{_localstatedir}/log/%{name}

install -D -m 644 config/mash_config.yaml \
    %{buildroot}%{_sysconfdir}/%{name}/mash_config.yaml

install -D -m 644 mash/services/api/wsgi.py \
    %{buildroot}%{_localstatedir}/lib/%{name}/wsgi.py

install -D -m 644 config/mash.conf \
    %{buildroot}%{_sysconfdir}/apache2/vhosts.d/mash.conf

install -D -m 644 mash/services/credentials/wsgi.py \
    %{buildroot}%{_localstatedir}/lib/%{name}/credentials/wsgi.py

install -D -m 644 config/credentials.conf \
    %{buildroot}%{_sysconfdir}/apache2/vhosts.d/credentials.conf

install -D -m 644 mash/services/database/wsgi.py \
    %{buildroot}%{_localstatedir}/lib/%{name}/database/wsgi.py

install -D -m 644 config/database.conf \
    %{buildroot}%{_sysconfdir}/apache2/vhosts.d/database.conf

install -d -m 755 %{buildroot}%{_localstatedir}/lib/%{name}/database/migrations
cp -r mash/services/database/migrations/* %{buildroot}%{_localstatedir}/lib/%{name}/database/migrations/

install -D -m 644 config/mash_download.service \
    %{buildroot}%{_unitdir}/mash_download.service

install -D -m 644 config/mash_upload.service \
    %{buildroot}%{_unitdir}/mash_upload.service

install -D -m 644 config/mash_create.service \
    %{buildroot}%{_unitdir}/mash_create.service

install -D -m 644 config/mash_logger.service \
    %{buildroot}%{_unitdir}/mash_logger.service

install -D -m 644 config/mash_job_creator.service \
    %{buildroot}%{_unitdir}/mash_job_creator.service

install -D -m 644 config/mash_test.service \
    %{buildroot}%{_unitdir}/mash_test.service

install -D -m 644 config/mash_raw_image_upload.service \
    %{buildroot}%{_unitdir}/mash_raw_image_upload.service

install -D -m 644 config/mash_replicate.service \
    %{buildroot}%{_unitdir}/mash_replicate.service

install -D -m 644 config/mash_publish.service \
    %{buildroot}%{_unitdir}/mash_publish.service

install -D -m 644 config/mash_deprecate.service \
    %{buildroot}%{_unitdir}/mash_deprecate.service

install -D -m 644 config/mash_cleanup.service \
    %{buildroot}%{_unitdir}/mash_cleanup.service

%pre
%{_bindir}/getent group mash > /dev/null || %{_sbindir}/groupadd mash
%{_bindir}/getent passwd mash > /dev/null || %{_sbindir}/useradd -r -g mash -s %{_bindir}/false -c "User for MASH" -d %{_localstatedir}/lib/mash mash

%check
export LANG=en_US.UTF-8
%pytest

%files
%defattr(-,root,root,-)
%{python_sitelib}/*
%dir %attr(755, mash, mash)%{_localstatedir}/log/%{name}
%dir %attr(755, mash, mash)%{_localstatedir}/lib/%{name}
%dir %attr(755, mash, mash)%{_localstatedir}/lib/%{name}/credentials
%dir %attr(755, mash, mash)%{_localstatedir}/lib/%{name}/database
%dir %attr(755, mash, mash)%{_localstatedir}/lib/%{name}/database/migrations
%dir %attr(755, mash, mash)%{_localstatedir}/lib/%{name}/database/migrations/versions
%dir %attr(755, mash, mash)%{_sysconfdir}/%{name}
%attr(640, mash, mash)%{_localstatedir}/lib/%{name}/wsgi.py
%attr(640, mash, mash)%{_localstatedir}/lib/%{name}/credentials/wsgi.py
%attr(640, mash, mash)%{_localstatedir}/lib/%{name}/database/wsgi.py
%attr(640, mash, mash)%{_localstatedir}/lib/%{name}/database/migrations/versions/*
%attr(640, mash, mash)%{_localstatedir}/lib/%{name}/database/migrations/alembic.ini
%attr(640, mash, mash)%{_localstatedir}/lib/%{name}/database/migrations/env.py
%attr(640, mash, mash)%{_localstatedir}/lib/%{name}/database/migrations/README
%attr(640, mash, mash)%{_localstatedir}/lib/%{name}/database/migrations/script.py.mako
%dir %{_sysconfdir}/apache2
%dir %{_sysconfdir}/apache2/vhosts.d
%config(noreplace) %attr(640, mash, mash)%{_sysconfdir}/apache2/vhosts.d/mash.conf
%config(noreplace) %attr(640, mash, mash)%{_sysconfdir}/apache2/vhosts.d/credentials.conf
%config(noreplace) %attr(640, mash, mash)%{_sysconfdir}/apache2/vhosts.d/database.conf
%config(noreplace) %attr(640, mash, mash)%{_sysconfdir}/%{name}/mash_config.yaml

%{_bindir}/mash-download-service
%{_unitdir}/mash_download.service

%{_bindir}/mash-upload-service
%{_unitdir}/mash_upload.service

%{_bindir}/mash-create-service
%{_unitdir}/mash_create.service

%{_bindir}/mash-logger-service
%{_unitdir}/mash_logger.service

%{_bindir}/mash-job-creator-service
%{_unitdir}/mash_job_creator.service

%{_bindir}/mash-test-service
%{_unitdir}/mash_test.service

%{_bindir}/mash-raw-image-upload-service
%{_unitdir}/mash_raw_image_upload.service

%{_bindir}/mash-replicate-service
%{_unitdir}/mash_replicate.service

%{_bindir}/mash-publish-service
%{_unitdir}/mash_publish.service

%{_bindir}/mash-deprecate-service
%{_unitdir}/mash_deprecate.service

%{_bindir}/mash-cleanup-service
%{_unitdir}/mash_cleanup.service

%changelog

