# -*- coding: utf-8 -*-
"""
    flask.ext.split
    ~~~~~~~~~~~~~~~

    A/B testing for your Flask application.

    :copyright: (c) 2012 by Janne Vanhala.
    :license: MIT, see LICENSE for more details.
"""

from .core import ab_test, finished
from .views import split


__all__ = (ab_test, finished, split)


try:
    __version__ = __import__('pkg_resources')\
        .get_distribution('flask_split').version
except Exception:
    __version__ = 'unknown'
