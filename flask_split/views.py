import os

from flask import Blueprint, redirect, render_template, request, url_for

from .models import Alternative, Experiment


root = os.path.abspath(os.path.dirname(__file__))
split = Blueprint('split', 'flask.ext.split',
    template_folder=os.path.join(root, 'templates'),
    static_folder=os.path.join(root, 'static')
)


@split.context_processor
def inject_version():
    from . import __version__
    return dict(version=__version__)


@split.route('/')
def index():
    return render_template('split/index.html',
        experiments=Experiment.all()
    )


@split.route('/<experiment>', methods=['POST'])
def set_experiment_winner(experiment):
    experiment = Experiment.find(experiment)
    if experiment:
        alternative = Alternative(request.form.get('alternative'), experiment.name)
        if alternative.name in experiment.alternative_names:
            experiment.winner = alternative.name
    return redirect(url_for('.index'))


@split.route('/<experiment>/reset', methods=['POST'])
def reset_experiment(experiment):
    experiment = Experiment.find(experiment)
    if experiment:
        experiment.reset()
    return redirect(url_for('.index'))


@split.route('/<experiment>/delete', methods=['POST'])
def delete_experiment(experiment):
    experiment = Experiment.find(experiment)
    if experiment:
        experiment.delete()
    return redirect(url_for('.index'))
