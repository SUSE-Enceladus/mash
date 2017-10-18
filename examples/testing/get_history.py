import time
from osc.core import conf, http_GET
from urllib import urlencode
from xml.etree import cElementTree


def get_history(apiurl, prj, current_package, repository, arch):
    conf.get_config()

    url = ''.join([
        '/'.join([
            apiurl,
            'build',
            prj,
            repository,
            arch,
            '_jobhistory'
        ]),
        '?',
        urlencode({'package': current_package})
    ])

    results = http_GET(url)
    root = cElementTree.parse(results).getroot()

    status = {}
    for node in root.findall('jobhist'):
        et = int(node.get('endtime'))

        status[node.get('package')] = {
            'reason': node.get('reason'),
            'code': node.get('code'),
            'endtime': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(et))
        }

    return status


results = get_history(
    'https://api.opensuse.org',
    'home:seanmarlow:branches:devel:languages:python',
    'python-flake8',
    'openSUSE_Leap_42.3',
    'x86_64'
)

print(results)
