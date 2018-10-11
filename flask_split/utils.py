# -*- coding: utf-8 -*-
"""
    flask_split.utils
    ~~~~~~~~~~~~~~~~~

    Generic utility functions.

    :copyright: (c) 2012-2015 by Janne Vanhala.
    :license: MIT, see LICENSE for more details.
"""

try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

from flask import current_app
import redis


urlparse.uses_netloc.append('redis')


def _get_redis_connection():
    """
    Return a Redis connection based on the Flask application's configuration.

    The connection parameters are retrieved from `REDIS_URL` configuration
    variable.

    :return: an instance of :class:`redis.Connection`
    """
    url = current_app.config.get('REDIS_URL', 'redis://localhost:6379')
    return redis.from_url(url, decode_responses=True)
