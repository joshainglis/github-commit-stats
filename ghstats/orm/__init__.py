from sqlalchemy import MetaData
from sqlalchemy.ext.declarative import declarative_base

from ghstats.config import DB_CONNECTION_STRING

meta = MetaData(naming_convention={
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
})

GHDBase = declarative_base(metadata=meta)

pg_functions = []
pg_triggers = []


def dcim_base_str(self):
    if hasattr(self, 'id'):
        return '{}::{}'.format(self.__class__.__name__, str(self.id))
    return super(GHDBase, self).__str__()


GHDBase.__str__ = dcim_base_str

if __name__ == '__main__':
    from sqlalchemy import create_engine

    engine = create_engine(DB_CONNECTION_STRING)
    GHDBase.metadata.create_all(engine)
