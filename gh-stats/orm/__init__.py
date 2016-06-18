import os

from josha.config import DB_CONNECTION_STRING
from josha.orm.orm import GHDBase

def get_engine(username, password, host, port=5432, database='', pool_size=20, max_overflow=0):
    """

    :type username: str
    :type password: str
    :type host: str
    :type port: int
    :type database: str
    :param pool_size:
    :type pool_size: int
    :param max_overflow:
    :type max_overflow: int
    :rtype: sqlalchemy.engine.Engine
    """
    engine = create_engine(
        'postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}'.format(
            username=username,
            password=password,
            host=host,
            port=port,
            database=database
        ),
        pool_size=pool_size,
        max_overflow=max_overflow
    )
    return engine


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


if __name__ == '__main__':
    from sqlalchemy import create_engine
    engine = create_engine(DB_CONNECTION_STRING)
    GHDBase.metadata.create_all(engine)
