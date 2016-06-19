import logging
import re
import time
from collections import defaultdict
from datetime import datetime
from typing import Iterable, List, Tuple, Optional

from requests.sessions import Session as GHSession
from sqlalchemy.orm.session import Session as SQLASession

from ghstats.config import ORGINISATIONS, BASE_GH_URL
from ghstats.orm.orm import Repo, Organisation, Team, User, Email, Commit, File
from ghstats.session import db_session_manager, gh_session_manager

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

LINK_RE = re.compile(r'<(?P<link>.+)>; rel="next"')
PROJECT_RE = re.compile(r'https://api.github.com/repos/(?:{})/(.+?)/'.format('|'.join(ORGINISATIONS)))


def hms(s):
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return h, m, s


def get_all(s, url, agg, status_code=200, insert_procedure=None, db_session=None):
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
        logger.error(r.text)
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
        agg, status_code = get_all(gh_session, url, agg)
    return agg


def insert_repo(db_session, repo, org=None):
    row = db_session.query(Repo).filter(Repo.ext_id == repo['id']).scalar()
    if row is None:
        if org is None:
            org = db_session.query(Organisation).filter(Organisation.ext_id == repo['owner']['id']).one()
        row = Repo(ext_id=repo['id'], name=repo['name'], org=org)
        db_session.add(row)
    return row


def get_orgs(db_session: SQLASession, gh_session: GHSession, orgs: Iterable[str]) -> Iterable[Organisation]:
    existing = db_session.query(Organisation).all()  # type: List[Organisation]
    new = set(orgs) - {row.name for row in existing}
    for org in new:
        (org,), _ = get_all(gh_session, '{}/orgs/{}'.format(BASE_GH_URL, org), [])
        # ensure this isn't just a name change and if so, update the name
        org_row = db_session.query(Organisation).filter(Organisation.ext_id == org['id']).scalar()  # type: Organisation
        if org_row is not None:
            org_row.name = org['login']
        else:
            org_row = Organisation(ext_id=org['id'], name=org['login'])
            db_session.add(org_row)
            existing.append(org_row)
    return existing


def get_teams(db_session: SQLASession, gh_session: GHSession, orgs: Iterable[Organisation]) -> Iterable[Team]:
    team_rows = []
    for org in orgs:
        teams, _ = get_all(gh_session, '{}/orgs/{}/teams'.format(BASE_GH_URL, org.name), [])
        for team in teams:
            team_row = db_session.query(Team).filter(Team.ext_id == team['id']).scalar()  # type: Team
            if team_row is not None:
                if team_row.name != team['slug']:
                    team_row.name = team['slug']
            else:
                team_row = Team(ext_id=team['id'], name=team['slug'], org=org)
                db_session.add(team_row)
            members, _ = get_all(gh_session, '{}/teams/{}/members'.format(BASE_GH_URL, team_row.ext_id), [])
            member_rows = db_session.query(User).filter(User.ext_id.in_([member['id'] for member in members])).all()
            for member_row in member_rows:
                if member_row not in team_row.users:
                    team_row.users.append(member_row)
            team_rows.append(team_row)
    return team_rows


def get_repos(db_session: SQLASession, gh_session: GHSession, orgs: Iterable[Organisation]) -> Iterable[Repo]:
    repo_rows = []
    for org in orgs:
        repos, _ = get_all(gh_session, '{}/orgs/{}/repos'.format(BASE_GH_URL, org.name), [])
        for repo in repos:
            repo_row = db_session.query(Repo).filter(Repo.ext_id == repo['id']).scalar()  # type: Repo
            if repo_row is not None:
                if repo_row.name != repo['name']:
                    repo_row.name = repo['name']
            else:
                repo_row = Repo(ext_id=repo['id'], name=repo['name'], org=org)
                db_session.add(repo_row)
            repo_rows.append(repo_row)
    return repo_rows


def get_or_add_user(db_session: SQLASession, gh_session: GHSession, user: dict, org: Organisation = None):
    user_row = db_session.query(User).filter(User.ext_id == user['id']).scalar()  # type: User
    if user_row is not None:
        if user_row.name != user['login']:
            user_row.name = user['login']
        if org is not None and org not in user_row.orgs:
            user_row.orgs.append(org)
    else:
        user_row = User(ext_id=user['id'], name=user['login'])
        if org is not None:
            user_row.orgs.append(org)
        db_session.add(user_row)
        (user_info,), _ = get_all(gh_session, user_row.url, [])
        email = user_info['email']
        if email is not None:
            email_row = db_session.query(Email).filter(Email.email == email).scalar()  # type: Email
            if email_row is None:
                email_row = Email(email, user_row)
                db_session.add(email_row)
    return user_row


def get_users(db_session: SQLASession, gh_session: GHSession, orgs: Iterable[Organisation]) -> Iterable[User]:
    user_rows = []
    for org in orgs:
        users, _ = get_all(gh_session, '{}/orgs/{}/members'.format(BASE_GH_URL, org.name), [])
        for user in users:
            user_rows.append(get_or_add_user(db_session, gh_session, user, org=org))
    return user_rows


def get_user_from_email(db_session: SQLASession, email: str) -> Optional[User]:
    if email is None:
        return None
    email_row = db_session.query(Email).filter(Email.email == email).scalar()  # type: Email
    if email_row is not None:
        return email_row.user
    return None


def parse_gh_date(date):
    return datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')


def _get_user_info_from_commit(db_session: SQLASession, gh_commit: dict, kind: str) -> \
        Tuple[Optional[User], Optional[Email]]:
    email = gh_commit['commit'][kind]['email']
    gh_user = gh_commit[kind]
    email_row = None
    user_row = None
    if email:
        email_row = db_session.query(Email).filter(Email.email == email).scalar()
        if email_row is None:
            email_row = Email(email)
            db_session.add(email_row)
    if gh_user is not None:
        user_row = get_or_add_user(db_session, gh_session, gh_user)
        if email_row is not None and user_row not in email_row.user:
            email_row.user.append(user_row)
    else:
        user_row = get_user_from_email(db_session, email)
    return user_row, email_row


def get_author(db_session, gh_commit):
    return _get_user_info_from_commit(db_session, gh_commit, 'author')


def get_committer(db_session, gh_commit):
    return _get_user_info_from_commit(db_session, gh_commit, 'committer')


def get_commits(db_session: SQLASession, gh_session: GHSession, repos: Iterable[Repo]) -> Iterable[Commit]:
    for repo in repos:
        get_commit_q = db_session.query(Commit.sha).filter(Commit.repo_id == repo.id)
        existing_commits = {commit.sha for commit in get_commit_q.all()}
        commits, _ = get_all(gh_session, '{}/commits'.format(repo.url), [])
        new = (sha for sha in (c['sha'].encode() for c in commits) if sha not in existing_commits)
        for commit_sha in new:
            (commit,), _ = get_all(gh_session, '{}/commits/{}'.format(repo.url, commit_sha.decode()), [])
            committer, committer_email = get_committer(db_session, commit)
            author, author_email = get_author(db_session, commit)
            new_commit = Commit(
                name=commit['commit']['message'],
                sha=commit_sha,
                repo=repo,
                additions=commit['stats']['additions'],
                deletions=commit['stats']['deletions'],
                committer=committer,
                committer_email=committer_email,
                committed_at=parse_gh_date(commit['commit']['committer']['date']),
                author=author,
                author_email=author_email,
                authored_at=parse_gh_date(commit['commit']['author']['date']),
            )
            db_session.add(new_commit)
            for file in commit['files']:
                new_file = File(
                    commit=new_commit,
                    filename=file['filename'],
                    status=file['status'],
                    additions=file['additions'],
                    deletions=file['deletions'],
                )
                db_session.add(new_file)
            db_session.commit()


if __name__ == '__main__':
    with db_session_manager as db_session, gh_session_manager as gh_session:
        orgs = get_orgs(db_session, gh_session, ORGINISATIONS)
        db_session.commit()
        users = get_users(db_session, gh_session, orgs)
        db_session.commit()
        teams = get_teams(db_session, gh_session, orgs)
        db_session.commit()
        repos = get_repos(db_session, gh_session, orgs)
        db_session.commit()
        commits = get_commits(db_session, gh_session, repos)
        # repos = get_all_repos(ORGINISATIONS, gh_session)
        # iixlabs_repos, status_code = get_all(gh_session, "https://api.github.com/orgs/iixlabs/repos", [])
        # iixlabs_repos, status_code = get_all(gh_session, "https://api.github.com/orgs/cloudrouter/repos", iixlabs_repos)
        # stats = fetch(gh_session, get_queue(iixlabs_repos, 'url', '/stats/contributors'))
        # commits = fetch(gh_session, get_queue(iixlabs_repos, 'url', '/commits'))
        # icommits = fetch(gh_session, [y['url'] for x in commits.values() for y in x])
        # langs = fetch(gh_session, get_queue(iixlabs_repos, 'url', '/languages'))

        # df_lang = pd.DataFrame(get_languages_dict(langs))
