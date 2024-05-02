#!/usr/bin/env python
import platform

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

from mash.version import __VERSION__

python_version = platform.python_version().split('.')[0]

with open('.virtualenv.requirements.txt') as f:
    requirements = f.read().splitlines()

config = {
    'name': 'mash',
    'description': 'Public Cloud Release Tool',
    'author': 'PubCloud Development team',
    'url': 'https://github.com/SUSE-Enceladus/mash',
    'download_url': 'https://github.com/SUSE-Enceladus/mash',
    'author_email': 'public-cloud-dev@susecloud.net',
    'version': __VERSION__,
    'install_requires': requirements,
    'packages': ['mash'],
    'entry_points': {
        'console_scripts': [
            'mash-download-service=mash.services.download_service:main',
            'mash-logger-service=mash.services.logger_service:main',
            'mash-job-creator-service=mash.services.job_creator_service:main',
            'mash-test-preparation-service=mash.services.test_preparation_service:main',
            'mash-test-cleanup-service=mash.services.test_cleanup_service:main',
            'mash-test-service=mash.services.test_service:main',
            'mash-upload-service=mash.services.upload_service:main',
            'mash-create-service=mash.services.create_service:main',
            'mash-replicate-service=mash.services.replicate_service:main',
            'mash-publish-service=mash.services.publish_service:main',
            'mash-deprecate-service=mash.services.deprecate_service:main',
            'mash-raw-image-upload-service=mash.services.raw_image_upload_service:main',
            'mash-cleanup-service=mash.services.cleanup_service:main'
        ]
    },
    'include_package_data': True,
    'license': 'GPLv3',
    'zip_safe': False,
    'classifiers': [
        # http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: System :: Operating System'
    ]
}

setup(**config)
