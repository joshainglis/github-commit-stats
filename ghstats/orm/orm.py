from sqlalchemy import Column, func, String, Table, ForeignKey, DateTime, text, Integer
from sqlalchemy.dialects.postgresql import UUID, BYTEA
from sqlalchemy.orm import relationship

from ghstats.config import BASE_GH_URL
from ghstats.orm import GHDBase

organisation_user_table = Table(
    'organisation_user', GHDBase.metadata,
    Column('org_id', UUID(as_uuid=True), ForeignKey('orgs.id')),
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'))
)

team_user_table = Table(
    'team_user', GHDBase.metadata,
    Column('team_id', UUID(as_uuid=True), ForeignKey('teams.id')),
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'))
)


class Named(object):
    __tablename__ = ''
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    name = Column(String, nullable=False)
    added_at = Column(DateTime(timezone=False), server_default=text("timezone('utc', now())"))

    @property
    def url(self):
        return '{}/{}/{}'.format(BASE_GH_URL, self.__tablename__, self.name)

    def __init__(self, name, *args, **kwargs):
        self.name = name


class ExtID(object):
    ext_id = Column(Integer, nullable=False, unique=True)

    def __init__(self, ext_id, *args, **kwargs):
        self.ext_id = ext_id


class Email(GHDBase):
    __tablename__ = 'emails'
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    email = Column(String, nullable=False, unique=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    user = relationship("User", back_populates="emails")

    def __init__(self, email, user):
        self.email = email
        self.user = user


class User(Named, ExtID, GHDBase):
    __tablename__ = 'users'

    orgs = relationship("Organisation", secondary=organisation_user_table, back_populates="users")
    teams = relationship("Team", secondary=team_user_table, back_populates="users")
    emails = relationship("Email", back_populates='user')
    committed = relationship("Commit", back_populates='committer', primaryjoin="User.id == Commit.committer_id")
    authored = relationship("Commit", back_populates='author', primaryjoin="User.id == Commit.author_id")

    def __init__(self, ext_id, name, orgs=None, teams=None, emails=None, committed=None, authored=None):
        super().__init__(name=name, ext_id=ext_id)
        self.orgs = orgs
        self.teams = teams
        self.emails = emails
        self.committed = committed
        self.authored = authored


class Team(Named, ExtID, GHDBase):
    __tablename__ = 'teams'

    org_id = Column(UUID(as_uuid=True), ForeignKey('orgs.id'))
    org = relationship("Organisation", back_populates="teams")
    users = relationship("User", secondary=team_user_table, back_populates="orgs")
    ext_id = Column(Integer, nullable=False, unique=True)

    def __init__(self, ext_id, name, org, users=None):
        super().__init__(name=name, ext_id=ext_id)
        self.org = org
        self.users = users


class Organisation(Named, ExtID, GHDBase):
    __tablename__ = 'orgs'

    users = relationship("User", secondary=organisation_user_table, back_populates="orgs")
    repos = relationship("Repo", back_populates="org")
    teams = relationship("Team", back_populates="org")

    def __init__(self, ext_id, name, users=None, repos=None, teams=None):
        super().__init__(name=name, ext_id=ext_id)
        self.users = users
        self.repos = repos
        self.teams = teams


class Repo(Named, ExtID, GHDBase):
    __tablename__ = 'repos'

    org_id = Column(UUID(as_uuid=True), ForeignKey('orgs.id'))
    org = relationship("Organisation", back_populates="repos")
    commits = relationship("Commit")

    def __init__(self, ext_id, name, org, commits=None):
        super().__init__(name=name, ext_id=ext_id)
        self.org = org
        self.commits = commits

    @property
    def url(self):
        return '{}/{}/{}/{}'.format(BASE_GH_URL, self.__tablename__, self.org.name, self.name)


class Commit(Named, GHDBase):
    __tablename__ = 'commits'

    committer_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    committer = relationship("User", back_populates="commits", foreign_keys=[committer_id])
    author_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    author = relationship("User", back_populates="authored", foreign_keys=[author_id])
    repo_id = Column(UUID(as_uuid=True), ForeignKey('repos.id'))
    repo = relationship("Repo", back_populates="commits")
    sha = Column(BYTEA(length=40), nullable=False, unique=True)

    def __init__(self, name, committer, author, repo):
        super().__init__(name)
        self.committer = committer
        self.author = author
        self.repo = repo
