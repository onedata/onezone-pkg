import json
import requests
import sys
import time
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from subprocess import STDOUT, check_call, check_output

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# get packages
packages = check_output(['ls', '/root/pkg']).split()
packages = sorted(packages, reverse=True)
oz_panel_package = \
    [path for path in packages if path.startswith('oz-panel') and
     path.endswith('.rpm')][0]
cluster_manager_package = \
    [path for path in packages if path.startswith('cluster-manager') and
     path.endswith('.rpm')][0]
oz_worker_package = \
    [path for path in packages if path.startswith('oz-worker') and
     path.endswith('.rpm')][0]
onezone_package = \
    [path for path in packages if path.startswith('onezone') and
     path.endswith('.rpm')][0]

# get couchbase
check_call(['wget', 'http://packages.couchbase.com/releases/4.5.1/couchbase'
                    '-server-community-4.5.1-centos7.x86_64.rpm'])

# install packages
check_call(['yum', '-y', 'install',
            'couchbase-server-community-4.5.1-centos7.x86_64.rpm'],
           stderr=STDOUT)
check_call(['yum', '-y', '--enablerepo=onedata',
            'install', '/root/pkg/' + oz_panel_package], stderr=STDOUT)
check_call(['yum', '-y', '--enablerepo=onedata',
            'install', '/root/pkg/' + cluster_manager_package], stderr=STDOUT)
check_call(['yum', '-y', '--enablerepo=onedata', 'install',
            '/root/pkg/' + oz_worker_package], stderr=STDOUT)
check_call(['yum', '-y', 'install', '/root/pkg/' + onezone_package],
           stderr=STDOUT)

# package installation validation
check_call(['service', 'oz_panel', 'status'])
check_call(['ls', '/etc/cluster_manager/app.config'])
check_call(['ls', '/etc/oz_worker/app.config'])

# configure onezone
with open('/root/data/config.yml', 'r') as f:
    r = requests.post(
        'https://127.0.0.1:9443/api/v3/onepanel/zone/configuration',
        auth=('admin', 'password'),
        headers={'content-type': 'application/x-yaml'},
        data=f.read(),
        verify=False)

    loc = r.headers['location']
    status = 'running'
    while status == 'running':
        r = requests.get('https://127.0.0.1:9443' + loc,
                         auth=('admin', 'password'),
                         verify=False)
        print(r.text)
        assert r.status_code == 200
        status = json.loads(r.text)['status']
        time.sleep(5)

assert status == 'ok'

# validate onezone configuration
check_call(['service', 'cluster_manager', 'status'])
check_call(['service', 'oz_worker', 'status'])

# stop onezone services
for service in ['workers', 'managers', 'databases']:
    r = requests.patch(
        'https://127.0.0.1:9443/api/v3/onepanel/zone/{0}?started=false'.format(
            service),
        auth=('admin', 'password'),
        headers={'content-type': 'application/json'},
        verify=False)
    assert r.status_code == 204

sys.exit(0)
