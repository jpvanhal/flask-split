# -*- coding: utf-8 -*-
"""
    flask_split.views
    ~~~~~~~~~~~~~~~~~

    This module provides the views for Flask-Split's web interface.

    :copyright: (c) 2012-2015 by Janne Vanhala.
    :license: MIT, see LICENSE for more details.
"""

import os

from flask import Blueprint, redirect, render_template, request, url_for

from .models import Alternative, Experiment
from .utils import _get_redis_connection


root = os.path.abspath(os.path.dirname(__file__))
split = Blueprint('split', 'flask_split',
    template_folder=os.path.join(root, 'templates'),
    static_folder=os.path.join(root, 'static'),
    url_prefix='/split'
)


@split.context_processor
def inject_version():
    from . import __version__
    return dict(version=__version__)


@split.route('/')
def index():
    """Render a dashboard that lists all active experiments."""
    redis = _get_redis_connection()
    return render_template('split/index.html',
        experiments=Experiment.all(redis)
    )


@split.route('/<experiment>', methods=['POST'])
def set_experiment_winner(experiment):
    """Mark an alternative as the winner of the experiment."""
    redis = _get_redis_connection()
    experiment = Experiment.find(redis, experiment)
    if experiment:
        alternative_name = request.form.get('alternative')
        alternative = Alternative(redis, alternative_name, experiment.name)
        if alternative.name in experiment.alternative_names:
            experiment.winner = alternative.name
    return redirect(url_for('.index'))


@split.route('/<experiment>/reset', methods=['POST'])
def reset_experiment(experiment):
    """Delete all data for an experiment."""
    redis = _get_redis_connection()
    experiment = Experiment.find(redis, experiment)
    if experiment:
        experiment.reset()
    return redirect(url_for('.index'))


@split.route('/<experiment>/delete', methods=['POST'])
def delete_experiment(experiment):
    """Delete an experiment and all its data."""
    redis = _get_redis_connection()
    experiment = Experiment.find(redis, experiment)
    if experiment:
        experiment.delete()
    return redirect(url_for('.index'))
