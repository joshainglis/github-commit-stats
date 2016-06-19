import logging
import re
import time
from collections import defaultdict

import pandas as pd

from ghstats.config import ORGINISATIONS
from ghstats.orm.orm import Repo
from ghstats.session import db_session_manager, gh_session_manager

logger = logging.getLogger(__name__)

LINK_RE = re.compile(r'<(?P<link>.+)>; rel="next"')
PROJECT_RE = re.compile(r'https://api.github.com/repos/(?:{})/(.+?)/'.format('|'.join(ORGINISATIONS)))


def hms(s):
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return h, m, s


def get_all(s, url, agg, status_code=200, insert_procedure=None):
    r = s.get(url)
    logger.debug('{:<6}{:<10}{}'.format(
        r.headers.get('x-ratelimit-remaining'),
        '{}:{}:{}'.format(*hms(int(float(r.headers.get('x-rateLimit-reset')) - time.time()))),
        url
    ))
    if r.status_code == 202:
        return agg, 202
    try:
        resp = r.json()
        if insert_procedure is not None:
            insert_procedure(resp)
        if isinstance(resp, list):
            agg += r.json()
        else:
            agg.append(resp)
    except ValueError:
        print(r.text)
        pass
    next_page = LINK_RE.match(r.headers['link']) if 'link' in r.headers else None
    if next_page:
        return get_all(s, next_page.group('link'), agg)
    else:
        return agg, r.status_code


def get_queue(lst, key, postfix):
    return [x[key] + postfix for x in lst]


def fetch(s, urls, insert_procedure=None):
    d = {}
    queue = [x for x in urls]
    while queue:
        url = queue.pop(0)
        agg, status_code = get_all(s, url, [], insert_procedure=insert_procedure)
        if status_code == 200:
            d[url] = agg
        elif status_code == 202:
            queue.append(url)
        else:
            print('FAILED: {}: {}'.format(status_code, url))
    return d


def get_languages_dict(langs):
    languages = defaultdict(list)
    for project, lang_list in langs.items():
        project = PROJECT_RE.match(project).group(1)
        for lang_dict in lang_list:
            for language, b in lang_dict.items():
                languages['project'].append(project)
                languages['language'].append(language)
                languages['bytes'].append(b)
    return languages


def get_all_repos(orgs, gh_session, db_session):
    agg = []
    for org in orgs:
        url = "https://api.github.com/orgs/{}/repos".format(org)
        agg, status_code = get_all(gh_session, url, agg, insert_procedure=insert_repo)


def insert_repo(db_session, repo):
    db_session.query(Repo, )
    Repo(repo['name'])


if __name__ == '__main__':
    with db_session_manager as db_session, gh_session_manager as gh_session:
        iixlabs_repos, status_code = get_all(gh_session, "https://api.github.com/orgs/iixlabs/repos", [])
        iixlabs_repos, status_code = get_all(gh_session, "https://api.github.com/orgs/cloudrouter/repos", iixlabs_repos)
        # stats = fetch(gh_session, get_queue(iixlabs_repos, 'url', '/stats/contributors'))
        commits = fetch(gh_session, get_queue(iixlabs_repos, 'url', '/commits'))
        icommits = fetch(gh_session, [y['url'] for x in commits.values() for y in x])
        langs = fetch(gh_session, get_queue(iixlabs_repos, 'url', '/languages'))

    df_lang = pd.DataFrame(get_languages_dict(langs))
