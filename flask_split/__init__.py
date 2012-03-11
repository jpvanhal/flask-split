# -*- coding: utf-8 -*-
"""
    flask.ext.split
    ~~~~~~~~~~~~~~~

    A/B testing for your Flask application.

    :copyright: (c) 2012 by Janne Vanhala.
    :license: MIT, see LICENSE for more details.
"""

import re

from flask import current_app, request, session
from redis import ConnectionError

from .models import Alternative, Experiment
from .views import split


try:
    __version__ = __import__('pkg_resources')\
        .get_distribution('flask_split').version
except Exception:
    __version__ = 'unknown'


class Split(object):
    def __init__(self, app=None):
        if app:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('SPLIT_ALLOW_MULTIPLE_EXPERIMENTS', False)
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

        app.extensions['split'] = self
        app.register_blueprint(split, url_prefix='/split')
        app.jinja_env.globals.update({
            'ab_test': self.ab_test,
            'finished': self.finished
        })

    def ab_test(self, experiment_name, *alternatives):
        try:
            experiment = Experiment.find_or_create(
                experiment_name, *alternatives)
            if experiment.winner:
                return experiment.winner.name
            else:
                forced_alternative = self.override(
                    experiment.name, experiment.alternative_names)
                if forced_alternative:
                    return forced_alternative
                self.clean_old_versions(experiment)
                if (self.exclude_visitor() or
                        self.not_allowed_to_test(experiment.key)):
                    self.begin_experiment(experiment)

                alternative_name = self.ab_user.get(experiment.key)
                if alternative_name:
                    return alternative_name
                alternative = experiment.next_alternative()
                alternative.increment_participation()
                self.begin_experiment(experiment, alternative.name)
                return alternative.name
        except ConnectionError, e:
            if not current_app.config['SPLIT_DB_FAILOVER']:
                raise
            self.handle_db_error(e)
            control = alternatives[0]
            return control[0] if isinstance(control, tuple) else control

    def finished(self, experiment_name, reset=True):
        if self.exclude_visitor():
            return
        try:
            experiment = Experiment.find(experiment_name)
            if not experiment:
                return
            alternative_name = self.ab_user.get(experiment.key)
            if alternative_name:
                alternative = Alternative(alternative_name, experiment_name)
                alternative.increment_completion()
                if reset:
                    self.ab_user.pop(experiment_name, None)
                    session.modified = True
        except ConnectionError, e:
            if not current_app.config['SPLIT_DB_FAILOVER']:
                raise
            self.handle_db_error(e)

    def handle_db_error(self, error):
        """
        Called when a connection error occurs with Redis.  By default, does
        not do anything.  Use :meth:`db_error_handler` to override this.
        """

    def db_error_handler(self, f):
        """
        A decorator that can be used to override :meth:`handle_db_error`.
        The decorated function is passed a :class:`redis.ConnectionError`
        object.

        Example::

            @split.on_db_error
            def on_db_error(e):
                log.error(e.message)

        """
        self.handle_db_error = f
        return f

    def override(self, experiment_name, alternatives):
        if request.args.get(experiment_name) in alternatives:
            return request.args.get(experiment_name)

    def begin_experiment(self, experiment, alternative_name=None):
        if not alternative_name:
            alternative_name = experiment.control.name
        self.ab_user[experiment.key] = alternative_name
        session.modified = True

    @property
    def ab_user(self):
        if 'split' not in session:
            session['split'] = {}
        return session['split']

    def exclude_visitor(self):
        return self.is_robot() or self.is_ignored_ip_address()

    def not_allowed_to_test(self, experiment_key):
        return (
            not current_app.config['SPLIT_ALLOW_MULTIPLE_EXPERIMENTS'] and
            self.doing_other_tests(experiment_key)
        )

    def doing_other_tests(self, experiment_key):
        for key in self.ab_user.iterkeys():
            if key != experiment_key:
                return True
        return False

    def clean_old_versions(self, experiment):
        for old_key in self.old_versions(experiment):
            del self.ab_user[old_key]
        session.modified = True

    def old_versions(self, experiment):
        if experiment.version > 0:
            return [
                key for key in self.ab_user.iterkeys()
                if key.startswith(experiment.name) and key != experiment.key
            ]
        else:
            return []

    def is_robot(self):
        robot_regex = current_app.config['SPLIT_ROBOT_REGEX']
        user_agent = request.headers.get('User-Agent', '')
        return re.search(robot_regex, user_agent, flags=re.VERBOSE)

    def is_ignored_ip_address(self):
        ignore_ip_addresses = current_app.config['SPLIT_IGNORE_IP_ADDRESSES']
        return request.remote_addr in ignore_ip_addresses
