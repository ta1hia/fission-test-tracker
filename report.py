#!/usr/bin/env python
# vim:se sts=4 sw=4 et fenc=utf-8 ft=python:
import json
import sys

import requests

headers = {
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:68.0) Gecko/20100101 Firefox/68.0',
}


def get(path):
    return requests.get('https://treeherder.mozilla.org/api/' + path,
                        headers=headers)


def get_results(path):
    return get(path).json()['results']

def match_xorigin(r):
    pass


PROJECT = 'mozilla-central'
PROJECT_URL = 'project/%s/' % PROJECT
PUSHES_URL = PROJECT_URL + 'push/'
JOBS_URL = PROJECT_URL + 'jobs/'

ARTIFACTS_URL = ('https://firefox-ci-tc.services.mozilla.com'
                 '/api/queue/v1/task/{task_id}/runs/{retry_id}/artifacts')

def get_report(mode='fission'):
    for push in get_results(PUSHES_URL):
        jobs_url = '%s?push_id=%s&count=2000' % (JOBS_URL, push['id'])

        for job in get_results(jobs_url):
            if not (job['job_group_symbol'] == 'test-info' and
                    job['job_type_symbol'] == 'fission' and
                    job['state'] == 'completed' and
                    job['result'] == 'success'):
                continue

            artifacts_url = ARTIFACTS_URL.format(**job)
            for result in requests.get(artifacts_url).json()['artifacts']:
                if result['name'].endswith('test-info-{}.json'.format(mode)): 
                    del push['revisions']
                    url = '%s/%s' % (artifacts_url, result['name'])
                    data = requests.get(url).json()
                    data['push'] = push
                    return data
                    # json.dump(data, sys.stdout, indent=2)
                    # sys.exit(0)
