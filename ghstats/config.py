import configparser
import json
import os

config = configparser.ConfigParser()
config.read(os.getenv('GH_DATA_CONFIG', 'config.ini'))

BASE_GH_URL = config.get('GITHUB', 'api_url', fallback='https://api.github.com')
GITHUB_USERNAME = os.getenv('GITHUB_LOGIN', config.get('GITHUB', 'login'))
GITHUB_OAUTH_TOKEN = os.getenv('GITHUB_TOKEN', config.get('GITHUB', 'token'))
ORGINISATIONS = json.loads(config.get('DETAILS', 'orgs'))
CURRENT_IIX_DEVS = json.loads(config.get('DETAILS', 'devs'))

DB_HOST = os.getenv('GH_PG_HOST', config.get('DATABASE', 'host', fallback='localhost'))
DB_PORT = os.getenv('GH_PG_PORT', config.get('DATABASE', 'port', fallback='5432'))
DB_NAME = os.getenv('GH_PG_DB', config.get('DATABASE', 'db', fallback='ghdata'))
DB_USERNAME = os.getenv('GH_PG_UN', config.get('DATABASE', 'username'))
DB_PASSWORD = os.getenv('GH_PG_PW', config.get('DATABASE', 'password'))

DB_CONNECTION_STRING = "postgresql+psycopg2://{un}:{pw}@{host}:{port}/{db}".format(
    un=DB_USERNAME,
    pw=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    db=DB_NAME
)

