from sqlalchemy import Column, func, String, Table, ForeignKey, DateTime, text, Integer, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, BYTEA
from sqlalchemy.orm import relationship

from ghstats.config import BASE_GH_URL
from ghstats.orm import GHDBase

organisation_user_table = Table(
    'organisation_user', GHDBase.metadata,
    Column('org_id', UUID(as_uuid=True), ForeignKey('orgs.id'), primary_key=True),
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
)

team_user_table = Table(
    'team_user', GHDBase.metadata,
    Column('team_id', UUID(as_uuid=True), ForeignKey('teams.id'), primary_key=True),
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
)

commit_parent_table = Table(
    'commit_parent', GHDBase.metadata,
    Column('child_id', UUID(as_uuid=True), ForeignKey('commits.id'), primary_key=True),
    Column('parent_id', UUID(as_uuid=True), ForeignKey('commits.id'), primary_key=True)
)


class Named(object):
    __tablename__ = ''
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    name = Column(String, nullable=False)
    added_at = Column(DateTime(timezone=False), server_default=text("timezone('utc', now())"))

    @property
    def url(self):
        return '{}/{}/{}'.format(BASE_GH_URL, self.__tablename__, self.name)

    def __init__(self, name=name):
        self.name = name


class UniqueNamed(Named):
    name = Column(String, nullable=False, unique=True)


class ExtID(object):
    ext_id = Column(Integer, nullable=False, unique=True)


class Email(GHDBase):
    __tablename__ = 'emails'
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    email = Column(String, nullable=False, unique=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    user = relationship("User", back_populates="emails")
    committed = relationship("Commit", back_populates='committer_email',
                             primaryjoin='Email.id == Commit.committer_email_id')
    authored = relationship("Commit", back_populates='author_email',
                            primaryjoin='Email.id == Commit.author_email_id')

    def __init__(self, email, user=None):
        self.email = email
        if user is not None:
            self.user = user


class User(UniqueNamed, ExtID, GHDBase):
    __tablename__ = 'users'

    orgs = relationship("Organisation", secondary=organisation_user_table, back_populates="users")
    teams = relationship("Team", secondary=team_user_table, back_populates="users")
    emails = relationship("Email", back_populates='user')
    committed = relationship("Commit", back_populates='committer', primaryjoin="User.id == Commit.committer_id")
    authored = relationship("Commit", back_populates='author', primaryjoin="User.id == Commit.author_id")

    def __init__(self, ext_id, name, orgs=None, teams=None, emails=None, committed=None, authored=None):
        super().__init__(name=name)
        self.ext_id = ext_id
        if orgs is not None:
            self.orgs = orgs
        if teams is not None:
            self.teams = teams
        if emails is not None:
            self.emails = emails
        if committed is not None:
            self.committed = committed
        if authored is not None:
            self.authored = authored


class Team(UniqueNamed, ExtID, GHDBase):
    __tablename__ = 'teams'

    org_id = Column(UUID(as_uuid=True), ForeignKey('orgs.id'))
    org = relationship("Organisation", back_populates="teams")
    users = relationship("User", secondary=team_user_table, back_populates="teams")
    ext_id = Column(Integer, nullable=False, unique=True)

    def __init__(self, ext_id, name, org, users=None):
        super().__init__(name=name)
        self.org = org
        self.ext_id = ext_id
        if users is not None:
            self.users = users


class Organisation(UniqueNamed, ExtID, GHDBase):
    __tablename__ = 'orgs'

    users = relationship("User", secondary=organisation_user_table, back_populates="orgs")
    repos = relationship("Repo", back_populates="org")
    teams = relationship("Team", back_populates="org")

    def __init__(self, ext_id, name, users=None, repos=None, teams=None):
        super().__init__(name=name)
        self.ext_id = ext_id
        if users is not None:
            self.users = users
        if repos is not None:
            self.repos = repos
        if teams is not None:
            self.teams = teams


class Repo(Named, ExtID, GHDBase):
    __tablename__ = 'repos'
    __table_args__ = (
        UniqueConstraint('name', 'org_id', name='unique_repo_name_per_org'),
    )


    org_id = Column(UUID(as_uuid=True), ForeignKey('orgs.id'))
    org = relationship("Organisation", back_populates="repos")
    commits = relationship("Commit")
    refs = relationship("Ref", back_populates="repo")

    def __init__(self, ext_id, name, org, commits=None):
        super().__init__(name=name)
        self.ext_id = ext_id

        self.org = org
        if commits is not None:
            self.commits = commits

    @property
    def url(self):
        return '{}/{}/{}/{}'.format(BASE_GH_URL, self.__tablename__, self.org.name, self.name)


class Commit(Named, GHDBase):
    __tablename__ = 'commits'

    __table_args__ = (
        Index('committed_at_index', 'committed_at'),
        Index('authored_at_index', 'authored_at'),
    )

    committer_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    committer = relationship("User", back_populates="committed", foreign_keys=[committer_id])
    committer_email_id = Column(UUID(as_uuid=True), ForeignKey('emails.id'))
    committer_email = relationship("Email", back_populates="committed", foreign_keys=[committer_email_id])
    committed_at = Column(DateTime(timezone=False))
    author_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    author = relationship("User", back_populates="authored", foreign_keys=[author_id])
    author_email_id = Column(UUID(as_uuid=True), ForeignKey('emails.id'))
    author_email = relationship("Email", back_populates="authored", foreign_keys=[author_email_id])
    authored_at = Column(DateTime(timezone=False))
    repo_id = Column(UUID(as_uuid=True), ForeignKey('repos.id'))
    repo = relationship("Repo", back_populates="commits")
    sha = Column(BYTEA(length=40), nullable=False, unique=True)
    additions = Column(Integer)
    deletions = Column(Integer)
    files = relationship('File', back_populates='commit')
    parents = relationship(
        "Commit",
        secondary="commit_parent",
        primaryjoin="Commit.id == commit_parent.c.child_id",
        secondaryjoin="Commit.id == commit_parent.c.parent_id",
        backref="children"
    )
    refs = relationship('Ref', back_populates='head')

    def __init__(self, sha, name, repo, additions, deletions, committer=None, committer_email=None, committed_at=None,
                 author=None, author_email=None, authored_at=None):
        super().__init__(name)
        self.repo = repo
        self.sha = sha
        self.additions = additions
        self.deletions = deletions
        if committer is not None:
            self.committer = committer
        if committer_email is not None:
            self.committer_email = committer_email
        if committed_at is not None:
            self.committed_at = committed_at
        if author is not None:
            self.author = author
        if author_email is not None:
            self.author_email = author_email
        if authored_at is not None:
            self.authored_at = authored_at


class File(GHDBase):
    __tablename__ = 'files'
    __table_args__ = (
        Index('filename_index', 'filename'),
        Index('status_index', 'status'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    filename = Column(String, nullable=False)
    additions = Column(Integer, nullable=False, default=0)
    deletions = Column(Integer, nullable=False, default=0)
    status = Column(String)
    commit_id = Column(UUID(as_uuid=True), ForeignKey('commits.id'))
    commit = relationship('Commit', back_populates='files')

    def __init__(self, commit, filename, status, additions, deletions):
        self.commit = commit
        self.filename = filename
        self.status = status
        self.additions = additions
        self.deletions = deletions


class Ref(Named, GHDBase):
    __tablename__ = 'refs'

    head_id = Column(UUID(as_uuid=True), ForeignKey('commits.id'))
    head = relationship('Commit', back_populates='refs')
    repo_id = Column(UUID(as_uuid=True), ForeignKey('repos.id'))
    repo = relationship("Repo", back_populates="refs")
