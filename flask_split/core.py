# -*- coding: utf-8 -*-
"""
    flask.ext.split.core
    ~~~~~~~~~~~~~~~~~~~~

    Implements the core functionality for doing A/B tests.

    :copyright: (c) 2012 by Janne Vanhala.
    :license: MIT, see LICENSE for more details.
"""

import re

from flask import current_app, request, session
from redis import ConnectionError

from .models import Alternative, Experiment
from .views import split


@split.record
def init_app(state):
    """
    Prepare the Flask application for Flask-Split.

    :param state: :class:`BlueprintSetupState` instance
    """
    app = state.app

    app.config.setdefault('SPLIT_ALLOW_MULTIPLE_EXPERIMENTS', False)
    app.config.setdefault('SPLIT_DB_FAILOVER', False)
    app.config.setdefault('SPLIT_IGNORE_IP_ADDRESSES', [])
    app.config.setdefault('SPLIT_ROBOT_REGEX', r"""
        (?i)\b(
            Baidu|
            Gigabot|
            Googlebot|
            libwww-perl|
            lwp-trivial|
            msnbot|
            SiteUptime|
            Slurp|
            WordPress|
            ZIBB|
            ZyBorg
        )\b
    """)

    app.jinja_env.globals.update({
        'ab_test': ab_test,
        'finished': finished
    })

    @app.template_filter()
    def percentage(number):
        number *= 100
        if abs(number) < 10:
            return "%.1f%%" % round(number, 1)
        else:
            return "%d%%" % round(number)


def ab_test(experiment_name, *alternatives):
    """
    Start a new A/B test.

    Returns one of the alternatives. If the user has already seen the test,
    they will get the same alternative as before.

    :param experiment_name: Name of the experiment.  You should never use the
        same experiment name to refer to a second experiment.
    :param alternatives: A list of alternatives.  Each item can be either a
        string or a two-tuple of the form (alternative name, weight).  By
        default each alternative has the weight of 1.  The first alternative
        is the control.  Every experiment must have at least  two alternatives.
    """
    try:
        experiment = Experiment.find_or_create(
            experiment_name, *alternatives)
        if experiment.winner:
            return experiment.winner.name
        else:
            forced_alternative = _override(
                experiment.name, experiment.alternative_names)
            if forced_alternative:
                return forced_alternative
            _clean_old_versions(experiment)
            if (_exclude_visitor() or
                    _not_allowed_to_test(experiment.key)):
                _begin_experiment(experiment)

            alternative_name = _get_session().get(experiment.key)
            if alternative_name:
                return alternative_name
            alternative = experiment.next_alternative()
            alternative.increment_participation()
            _begin_experiment(experiment, alternative.name)
            return alternative.name
    except ConnectionError:
        if not current_app.config['SPLIT_DB_FAILOVER']:
            raise
        control = alternatives[0]
        return control[0] if isinstance(control, tuple) else control


def finished(experiment_name, reset=True):
    """
    Track a conversion.

    :param experiment_name: Name of the experiment.
    :param reset: If set to `True` current user's session is reset so that they
        may start the test again in the future.  If set to `False` the user
        will always see the alternative they started with.  Defaults to `True`.
    """
    if _exclude_visitor():
        return
    try:
        experiment = Experiment.find(experiment_name)
        if not experiment:
            return
        alternative_name = _get_session().get(experiment.key)
        if alternative_name:
            alternative = Alternative(alternative_name, experiment_name)
            alternative.increment_completion()
            if reset:
                _get_session().pop(experiment.key, None)
                session.modified = True
    except ConnectionError:
        if not current_app.config['SPLIT_DB_FAILOVER']:
            raise


def _override(experiment_name, alternatives):
    if request.args.get(experiment_name) in alternatives:
        return request.args.get(experiment_name)


def _begin_experiment(experiment, alternative_name=None):
    if not alternative_name:
        alternative_name = experiment.control.name
    _get_session()[experiment.key] = alternative_name
    session.modified = True


def _get_session():
    if 'split' not in session:
        session['split'] = {}
    return session['split']


def _exclude_visitor():
    """
    Return `True` if the current visitor should be excluded from participating
    to the A/B test, or `False` otherwise.
    """
    return _is_robot() or _is_ignored_ip_address()


def _not_allowed_to_test(experiment_key):
    return (
        not current_app.config['SPLIT_ALLOW_MULTIPLE_EXPERIMENTS'] and
        _doing_other_tests(experiment_key)
    )


def _doing_other_tests(experiment_key):
    """
    Return `True` if the current user is doing other experiments than the
    experiment with the key ``experiment_key`` at the moment, or `False`
    otherwise.
    """
    for key in _get_session().iterkeys():
        if key != experiment_key:
            return True
    return False


def _clean_old_versions(experiment):
    for old_key in _old_versions(experiment):
        del _get_session()[old_key]
    session.modified = True


def _old_versions(experiment):
    if experiment.version > 0:
        return [
            key for key in _get_session().iterkeys()
            if key.startswith(experiment.name) and key != experiment.key
        ]
    else:
        return []


def _is_robot():
    """
    Return `True` if the current visitor is a robot or spider, or
    `False` otherwise.

    This function works by comparing the request's user agent with a regular
    expression.  The regular expression can be configured with the
    ``SPLIT_ROBOT_REGEX`` setting.
    """
    robot_regex = current_app.config['SPLIT_ROBOT_REGEX']
    user_agent = request.headers.get('User-Agent', '')
    return re.search(robot_regex, user_agent, flags=re.VERBOSE)


def _is_ignored_ip_address():
    """
    Return `True` if the IP address of the current visitor should be
    ignored, or `False` otherwise.

    The list of ignored IP addresses can be configured with the
    ``SPLIT_IGNORE_IP_ADDRESSES`` setting.
    """
    ignore_ip_addresses = current_app.config['SPLIT_IGNORE_IP_ADDRESSES']
    return request.remote_addr in ignore_ip_addresses
