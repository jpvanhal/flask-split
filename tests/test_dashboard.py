# -*- coding: utf-8 -*-

from datetime import datetime

from flask_split.models import Alternative, Experiment
from flexmock import flexmock

from . import assert_redirects, TestCase


class TestDashboard(TestCase):
    def test_responds_to_index(self):
        response = self.client.get('/split/')
        assert response.status_code == 200

    def test_reset_an_experiment(self):
        Experiment.find_or_create('link_color', 'blue', 'red')

        red = Alternative('red', 'link_color')
        blue = Alternative('blue', 'link_color')
        red.participant_count = 5
        blue.participant_count = 6

        response = self.client.post('/split/link_color/reset')
        assert_redirects(response, '/split/')

        new_red_count = Alternative('red', 'link_color').participant_count
        new_blue_count = Alternative('blue', 'link_color').participant_count

        assert new_blue_count == 0
        assert new_red_count == 0

    def test_reset_a_non_existing_experiment(self):
        response = self.client.post('/split/foobar/reset')
        assert_redirects(response, '/split/')

    def test_delete_an_experiment(self):
        Experiment.find_or_create('link_color', 'blue', 'red')
        response = self.client.post('/split/link_color/delete')
        assert_redirects(response, '/split/')
        assert Experiment.find('link_color') is None

    def test_delete_a_non_existing_experiment(self):
        response = self.client.post('/split/foobar/delete')
        assert_redirects(response, '/split/')

    def test_mark_an_alternative_as_the_winner(self):
        experiment = Experiment.find_or_create('link_color', 'blue', 'red')
        assert experiment.winner is None

        response = self.client.post('/split/link_color', data={'alternative': 'red'})
        assert_redirects(response, '/split/')

        assert experiment.winner.name == 'red'

    def test_mark_a_non_existing_alternative_as_the_winner(self):
        experiment = Experiment.find_or_create('link_color', 'blue', 'red')
        assert experiment.winner is None

        response = self.client.post('/split/link_color', data={'alternative': 'foobar'})
        assert_redirects(response, '/split/')

        assert experiment.winner is None

    def test_mark_an_alternative_as_the_winner_for_non_existing_experiment(self):
        response = self.client.post('/split/foobar', data={'alternative': 'red'})
        assert_redirects(response, '/split/')

    def test_displays_the_start_date(self):
        experiment_start_time = datetime(2011, 7, 7)
        flexmock(Experiment).should_receive('_get_time').and_return(experiment_start_time)
        Experiment.find_or_create('link_color', 'blue', 'red')
        response = self.client.get('/split/')
        assert '2011-07-07' in response.data
