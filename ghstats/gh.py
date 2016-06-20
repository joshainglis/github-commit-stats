import logging
from typing import List, Tuple

from ghstats.config import BASE_GH_URL
from ghstats.orm.orm import Repo, Organisation, Team, User, Email, Commit, File
from ghstats.utils import logger, get_all, parse_gh_date

logging.basicConfig()
logger.setLevel(logging.DEBUG)


def get_orgs(db_session, gh_session, orgs):
    """
    Given a list of organisation login names, get them from github and insert into DB if they do not already exist

    :param db_session: the database session
    :type db_session: sqlalchemy.orm.session.Session
    :param gh_session: the requests session with the github api
    :type gh_session: requests.sessions.Session
    :param orgs: list of organisation login names
    :type orgs: List[str]
    :return: the list of all organisations in the database after adding any new ones
    :rtype: Union[None, List[ghstats.orm.orm.Organisation]]
    """
    existing = db_session.query(Organisation).all()  # type: List[Organisation]
    new = set(orgs) - {row.name for row in existing}
    for org in new:
        (org,), _ = get_all(gh_session, '{}/orgs/{}'.format(BASE_GH_URL, org))
        # ensure this isn't just a name change and if so, update the name
        org_row = db_session.query(Organisation).filter(Organisation.ext_id == org['id']).scalar()  # type: Organisation
        if org_row is not None:
            org_row.name = org['login']
        else:
            org_row = Organisation(ext_id=org['id'], name=org['login'])
            db_session.add(org_row)
            existing.append(org_row)
    return existing


def get_team(db_session, gh_session, team, org):
    """
    get or create the team from the given team object from the github api

    :param db_session: the database session
    :type db_session: sqlalchemy.orm.session.Session
    :param gh_session: the requests session with the github api
    :type gh_session: requests.sessions.Session
    :param team: a github team object from API
    :type team: dict
    :param org: an Organisation row object
    :type org: ghstats.orm.orm.Organisation
    :return: a Team row object
    :rtype: ghstats.orm.orm.Team
    """
    team_row = db_session.query(Team).filter(Team.ext_id == team['id']).scalar()  # type: Team
    if team_row is not None:
        if team_row.name != team['slug']:
            team_row.name = team['slug']
    else:
        team_row = Team(ext_id=team['id'], name=team['slug'], org=org)
        db_session.add(team_row)
    members, _ = get_all(gh_session, '{}/teams/{}/members'.format(BASE_GH_URL, team_row.ext_id))
    member_rows = db_session.query(User).filter(User.ext_id.in_([member['id'] for member in members])).all()
    for member_row in member_rows:
        if member_row not in team_row.users:
            team_row.users.append(member_row)
    return team_row


def get_teams(db_session, gh_session, orgs):
    """
    Given a list of organisation objects, get all associated teams from github and insert them into DB if they do not
    already exist

    :param db_session: the database session
    :type db_session: sqlalchemy.orm.session.Session
    :param gh_session: the requests session with the github api
    :type gh_session: requests.sessions.Session
    :param orgs: list of Organisation row objects
    :type orgs: List[ghstats.orm.orm.Organisation]
    :return: a list of all associated team objects
    :rtype: Union[None, List[ghstats.orm.orm.Team]]
    """
    team_rows = []
    for org in orgs:
        teams, _ = get_all(gh_session, '{}/orgs/{}/teams'.format(BASE_GH_URL, org.name))
        for team in teams:
            team_rows.append(get_team(db_session, gh_session, team, org))
    return team_rows


def get_repo(db_session, repo, org):
    """
    get or create the Repo row object from the given repo object from the github api

    :param db_session: the database session
    :type db_session: sqlalchemy.orm.session.Session
    :param repo: repo object from the github api
    :type repo: dict
    :param org: Organisation row object
    :type org: ghstats.orm.orm.Organisation
    """
    repo_row = db_session.query(Repo).filter(Repo.ext_id == repo['id']).scalar()  # type: Repo
    if repo_row is not None:
        if repo_row.name != repo['name']:
            repo_row.name = repo['name']
    else:
        repo_row = Repo(ext_id=repo['id'], name=repo['name'], org=org)
        db_session.add(repo_row)
    return repo_row


def get_repos(db_session, gh_session, orgs):
    """
    Given a list of organisation objects, get all associated repositories from github and insert them into DB if they
    do not already exist

    :param db_session: the database session
    :type db_session: sqlalchemy.orm.session.Session
    :param gh_session: the requests session with the github api
    :type gh_session: requests.sessions.Session
    :param orgs: list of Organisation row objects
    :type orgs: List[ghstats.orm.orm.Organisation]
    :return: a list of all associated team objects
    :rtype: Union[List[ghstats.orm.orm.Repo], None]
    """
    repo_rows = []
    for org in orgs:
        repos, _ = get_all(gh_session, '{}/orgs/{}/repos'.format(BASE_GH_URL, org.name))
        for repo in repos:
            repo_rows.append(get_repo(db_session, repo, org))
    return repo_rows


def get_user(db_session, gh_session, user, org=None):
    """
    Given a github user object (and optionally an Organisation row object), get the user info from github and store it
    to the DB if it does not already exist

    :param db_session: the database session
    :type db_session: sqlalchemy.orm.session.Session
    :param gh_session: the requests session with the github api
    :type gh_session: requests.sessions.Session
    :param user: github user object.
    :type user: Union[Dict[str, Union[str, bool, int]], None]
    :param org: if available, the organisation row object to associate this user with
    :type org: Union[ghstats.orm.orm.Organisation, None]
    :return: the User row object associated with the given user
    :rtype: Union[ghstats.orm.orm.User, None]
    """
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
        (user_info,), _ = get_all(gh_session, user_row.url)
        email = user_info['email']
        if email is not None:
            email_row = db_session.query(Email).filter(Email.email == email).scalar()  # type: Email
            if email_row is None:
                email_row = Email(email, user_row)
                db_session.add(email_row)
    return user_row


def get_users(db_session, gh_session, orgs):
    """
    Given a list of organisation objects, get all associated users from github and insert them into DB if they
    do not already exist

    :param db_session: the database session
    :type db_session: sqlalchemy.orm.session.Session
    :param gh_session: the requests session with the github api
    :type gh_session: requests.sessions.Session
    :param orgs: list of Organisation row objects
    :type orgs: List[ghstats.orm.orm.Organisation]
    :return: the list of all user row objects in the DB after inserting ay new ones
    :rtype: Union[None, List[ghstats.orm.orm.User]]
    """
    user_rows = []
    for org in orgs:
        users, _ = get_all(gh_session, '{}/orgs/{}/members'.format(BASE_GH_URL, org.name))
        for user in users:
            user_rows.append(get_user(db_session, gh_session, user, org=org))
    return user_rows


def get_user_from_email(db_session, email):
    """
    given an email address, see if it's in the database and return the associated user.

    :param db_session: the database session
    :type db_session: sqlalchemy.orm.session.Session
    :param email: the email to find the associated User from
    :type email: str
    :return: the user associated with the email address, if it exists
    :rtype: Union[ghstats.orm.orm.User, None]
    """
    if email is None:
        return None
    email_row = db_session.query(Email).filter(Email.email == email).scalar()  # type: Email
    if email_row is not None:
        return email_row.user
    return None


def _get_user_info_from_commit(db_session, gh_session, gh_commit, kind):
    """
    given a github commit, return the User and Email row objects of either the 'author' or 'committer'

    :param db_session: the database session
    :type db_session: sqlalchemy.orm.session.Session
    :param gh_session: the requests session with the github api
    :type gh_session: requests.sessions.Session
    :param gh_commit: github commit object from api
    :type gh_commit: dict
    :param kind: one of 'author' or 'committer'
    :type kind: str
    :return: A User row object (if it exists or can be inferred) and an Email row object
    :rtype: Tuple[ghstats.orm.orm.User, ghstats.orm.orm.Email]
    """
    email = gh_commit['commit'][kind]['email']
    gh_user = gh_commit[kind]
    email_row = None
    if email:
        email_row = db_session.query(Email).filter(Email.email == email).scalar()
        if email_row is None:
            email_row = Email(email)
            db_session.add(email_row)
    if gh_user is not None:
        user_row = get_user(db_session, gh_session, gh_user)
        if email_row is not None and email_row.user_id is None:
            email_row.user = user_row
    else:
        user_row = get_user_from_email(db_session, email)
    return user_row, email_row


def get_author(db_session, gh_session, gh_commit):
    """
    given a github commit, return the User and Email row objects of the author

    :param db_session: the database session
    :type db_session: sqlalchemy.orm.session.Session
    :param gh_session: the requests session with the github api
    :type gh_session: requests.sessions.Session
    :param gh_commit: github commit object from api
    :type gh_commit: dict
    :return: A User row object (if it exists or can be inferred) and an Email row object
    :rtype: Tuple[ghstats.orm.orm.User, ghstats.orm.orm.Email]
    """
    return _get_user_info_from_commit(db_session, gh_session, gh_commit, 'author')


def get_committer(db_session, gh_session, gh_commit):
    """
    given a github commit, return the User and Email row objects of the committer

    :param db_session: the database session
    :type db_session: sqlalchemy.orm.session.Session
    :param gh_session: the requests session with the github api
    :type gh_session: requests.sessions.Session
    :param gh_commit: github commit object from api
    :type gh_commit: dict
    :return: A User row object (if it exists or can be inferred) and an Email row object
    :rtype: Tuple[ghstats.orm.orm.User, ghstats.orm.orm.Email]
    """
    return _get_user_info_from_commit(db_session, gh_session, gh_commit, 'committer')


def get_commits(db_session, gh_session, repos):
    """
    given a list of Repo row object get all associated commits and file changes (on the default branch) for each repo.

    :param db_session: the database session
    :type db_session: sqlalchemy.orm.session.Session
    :param gh_session: the requests session with the github api
    :type gh_session: requests.sessions.Session
    :param repos: list of Repo row objects
    :type repos: List[ghstats.orm.orm.Repo]
    """
    for repo in repos:
        get_commit_q = db_session.query(Commit.sha).filter(Commit.repo_id == repo.id)
        existing_commits = {commit.sha for commit in get_commit_q.all()}
        commits, _ = get_all(gh_session, '{}/commits'.format(repo.url))
        new_commits = (sha for sha in (c['sha'].encode() for c in commits if 'sha' in c) if sha not in existing_commits)
        for commit_sha in new_commits:
            exists = db_session.query(Commit.sha).filter(Commit.sha == commit_sha).scalar()
            if exists:
                continue
            (commit,), _ = get_all(gh_session, '{}/commits/{}'.format(repo.url, commit_sha.decode()))
            committer, committer_email = get_committer(db_session, gh_session, commit)
            author, author_email = get_author(db_session, gh_session, commit)
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
