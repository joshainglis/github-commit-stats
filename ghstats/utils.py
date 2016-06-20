import logging
import re
import time
from datetime import datetime

logger = logging.getLogger(__name__)
LINK_RE = re.compile(r'<(?P<link>.+)>; rel="next"')


def hms(seconds):
    """
    Convert seconds to hours, minutes, seconds

    :param seconds: number os seconds
    :type seconds: int
    :return: hours, minutes, seconds
    :rtype: Tuple[int, int, int]
    """
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return hours, minutes, seconds


def time_to_reset(response):
    """
    Get number of seconds until github resets rate limit

    :param response: the response from a github api call
    :type response: requests.models.Response
    :return: number of seconds until github resets rate limit
    :rtype: int
    """
    return int(float(response.headers.get('x-ratelimit-reset')) - time.time())


def rate_limit_remaining(response):
    """
    Get number of requests left until github applies rate limit

    :param response: the response from a github api call
    :type response: requests.models.Response
    :return: number of requests left until github applies rate limit
    :rtype: int
    """
    return int(response.headers.get('x-ratelimit-remaining'))


def get_all(session, url, agg=None):
    """
    Go through all pages of a request and return the aggregated result

    :param session: the requests session
    :type session: requests.sessions.Session
    :param url: github api url to get
    :type url: str
    :param agg: a list to add the results from the query to
    :type agg: list
    :return: the aggregated list of results, response code
    :rtype: Tuple[list, int]
    """
    agg = [] if agg is None else agg
    response = session.get(url)
    rate_limit = rate_limit_remaining(response)
    if rate_limit < 5:
        time.sleep(time_to_reset(response) + 60)
    logger.debug('{:<6}{:<10}{}'.format(rate_limit, '{}:{}:{}'.format(*hms(time_to_reset(response))), url))
    if response.status_code == 202:
        time.sleep(2)
        return get_all(session, url, agg)
    try:
        resp = response.json()
        if isinstance(resp, list):
            agg += resp
        else:
            agg.append(resp)
    except ValueError:
        logger.error(response.text)
    next_page = LINK_RE.match(response.headers['link']) if 'link' in response.headers else None
    if next_page:
        return get_all(session, next_page.group('link'), agg)
    else:
        return agg, response.status_code


def parse_gh_date(date):
    """
    return the given ISO 8601 timestamp as a datetime object

    :param date: a timestamp in ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ
    :type date: str
    :return: the timestamp as a datetime object
    :rtype: datetime.datetime
    """
    return datetime.strptime(date, '%Y-%m-%dT%H:%M:%SZ')
