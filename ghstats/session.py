import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ghstats.config import DB_CONNECTION_STRING, GITHUB_USERNAME, GITHUB_OAUTH_TOKEN

engine = create_engine(DB_CONNECTION_STRING)

Session = sessionmaker(bind=engine)


class SessionManager(object):
    def __init__(self, session_maker):
        self._session_maker = session_maker
        self.session = None

    def _start_session(self):
        if self.session is None:
            self.session = self._session_maker()

    def _end_session(self):
        if self.session is not None:
            self.session.close()
        self.session = None

    def __enter__(self):
        """
        :rtype : sqlalchemy.orm.session.Session
        """
        self._start_session()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.session.rollback()
            self._end_session()
            return False
        else:
            self.session.commit()
            self._end_session()
            return True


def get_gh_session():
    s = requests.Session()
    s.auth = (GITHUB_USERNAME, GITHUB_OAUTH_TOKEN)
    s.headers.update({'Accept': 'application/vnd.github.v3+json'})
    s.headers.update({'User-Agent': GITHUB_USERNAME})
    return s


db_session_manager = SessionManager(Session)
gh_session_manager = get_gh_session()
