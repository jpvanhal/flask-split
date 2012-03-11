# -*- coding: utf-8 -*-

from __future__ import with_statement

from flask import session
from flask_split import ab_test, finished
from flask_split.core import _get_session
from flask_split.models import Alternative, Experiment
from flexmock import flexmock
from pytest import raises
from redis import ConnectionError, Redis

from . import TestCase


class TestExtension(TestCase):

    def test_ab_test_assigns_random_alternative_to_a_new_user(self):
        ab_test('link_color', 'blue', 'red')
        assert _get_session()['link_color'] in ['red', 'blue']

    def test_ab_test_increments_participation_counter_for_new_user(self):
        Experiment.find_or_create('link_color', 'blue', 'red')

        previous_red_count = Alternative('red', 'link_color').participant_count
        previous_blue_count = Alternative('blue', 'link_color').participant_count

        ab_test('link_color', 'blue', 'red')

        new_red_count = Alternative('red', 'link_color').participant_count
        new_blue_count = Alternative('blue', 'link_color').participant_count

        assert (new_red_count + new_blue_count ==
            previous_red_count + previous_blue_count + 1)

    def test_ab_test_returns_the_given_alternative_for_an_existing_user(self):
        Experiment.find_or_create('link_color', 'blue', 'red')
        alternative = ab_test('link_color', 'blue', 'red')
        repeat_alternative = ab_test('link_color', 'blue', 'red')
        assert alternative == repeat_alternative

    def test_ab_test_always_returns_the_winner_if_one_is_present(self):
        experiment = Experiment.find_or_create('link_color', 'blue', 'red')
        experiment.winner = "orange"

        assert ab_test('link_color', 'blue', 'red') == 'orange'

    def test_ab_test_allows_the_share_of_visitors_see_an_alternative(self):
        ab_test('link_color', ('blue', 0.8), ('red', 20))
        assert _get_session()['link_color'] in ['red', 'blue']

    def test_ab_test_only_lets_user_participate_in_one_experiment(self):
        ab_test('link_color', 'blue', 'red')
        ab_test('button_size', 'small', 'big')
        assert _get_session()['button_size'] == 'small'
        big = Alternative('big', 'button_size')
        assert big.participant_count == 0
        small = Alternative('small', 'button_size')
        assert small.participant_count == 0

    def test_lets_user_participate_in_many_experiments_with_allow_multiple_experiments_option(self):
        self.app.config['SPLIT_ALLOW_MULTIPLE_EXPERIMENTS'] = True
        link_color = ab_test('link_color', 'blue', 'red')
        button_size = ab_test('button_size', 'small', 'big')
        assert _get_session()['button_size'] == button_size
        button_size_alt = Alternative(button_size, 'button_size')
        assert button_size_alt.participant_count == 1

    def test_finished_increments_completed_alternative_counter(self):
        Experiment.find_or_create('link_color', 'blue', 'red')
        alternative_name = ab_test('link_color', 'blue', 'red')
        previous_completion_count = Alternative(alternative_name, 'link_color').completed_count
        finished('link_color')
        new_completion_count = Alternative(alternative_name, 'link_color').completed_count
        assert new_completion_count == previous_completion_count + 1

    def test_finished_clears_out_the_users_participation_from_their_session(self):
        Experiment.find_or_create('link_color', 'blue', 'red')
        alternative_name = ab_test('link_color', 'blue', 'red')

        assert session['split'] == {"link_color": alternative_name}
        finished('link_color')
        assert session['split'] == {}

    def test_finished_does_not_clear_out_the_users_session_if_reset_is_false(self):
        Experiment.find_or_create('link_color', 'blue', 'red')
        alternative_name = ab_test('link_color', 'blue', 'red')

        assert session['split'] == {"link_color": alternative_name}
        finished('link_color', reset=False)
        assert session['split'] == {"link_color": alternative_name}

    def test_finished_does_nothing_if_experiment_was_not_started_by_the_user(self):
        session['split'] = None
        finished('some_experiment_not_started_by_the_user')

    def test_conversions_return_conversion_rates_for_alternatives(self):
        Experiment.find_or_create('link_color', 'blue', 'red')
        alternative_name = ab_test('link_color', 'blue', 'red')

        previous_convertion_rate = Alternative(alternative_name, 'link_color').conversion_rate
        assert previous_convertion_rate == 0.0

        finished('link_color')

        new_convertion_rate = Alternative(alternative_name, 'link_color').conversion_rate
        assert new_convertion_rate == 1.0


class TestExtensionWhenUserIsARobot(TestCase):
    def make_test_request_context(self):
        return self.app.test_request_context(
            headers={
                'User-Agent': 'Googlebot/2.1 (+http://www.google.com/bot.html)'
            }
        )

    def test_ab_test_return_the_control(self):
        experiment = Experiment.find_or_create('link_color', 'blue', 'red')
        alternative = ab_test('link_color', 'blue', 'red')
        assert alternative == experiment.control.name

    def test_ab_test_does_not_increment_the_participation_count(self):
        Experiment.find_or_create('link_color', 'blue', 'red')

        previous_red_count = Alternative('red', 'link_color').participant_count
        previous_blue_count = Alternative('blue', 'link_color').participant_count

        ab_test('link_color', 'blue', 'red')

        new_red_count = Alternative('red', 'link_color').participant_count
        new_blue_count = Alternative('blue', 'link_color').participant_count

        assert (new_red_count + new_blue_count ==
            previous_red_count + previous_blue_count)

    def test_finished_does_not_increment_the_completed_count(self):
        Experiment.find_or_create('link_color', 'blue', 'red')
        alternative_name = ab_test('link_color', 'blue', 'red')

        previous_completion_count = Alternative(alternative_name, 'link_color').completed_count

        finished('link_color')

        new_completion_count = Alternative(alternative_name, 'link_color').completed_count

        assert new_completion_count == previous_completion_count


class TestExtensionWhenIPAddressIsIgnored(TestCase):
    def setup_method(self, method):
        super(TestExtensionWhenIPAddressIsIgnored, self).setup_method(method)
        self.app.config['SPLIT_IGNORE_IP_ADDRESSES'] = ['81.19.48.130']

    def make_test_request_context(self):
        return self.app.test_request_context(environ_overrides={
            'REMOTE_ADDR': '81.19.48.130'
        })

    def test_ab_test_return_the_control(self):
        experiment = Experiment.find_or_create('link_color', 'blue', 'red')
        alternative = ab_test('link_color', 'blue', 'red')
        assert alternative == experiment.control.name

    def test_ab_test_does_not_increment_the_participation_count(self):
        Experiment.find_or_create('link_color', 'blue', 'red')

        previous_red_count = Alternative('red', 'link_color').participant_count
        previous_blue_count = Alternative('blue', 'link_color').participant_count

        ab_test('link_color', 'blue', 'red')

        new_red_count = Alternative('red', 'link_color').participant_count
        new_blue_count = Alternative('blue', 'link_color').participant_count

        assert (new_red_count + new_blue_count ==
            previous_red_count + previous_blue_count)

    def test_finished_does_not_increment_the_completed_count(self):
        Experiment.find_or_create('link_color', 'blue', 'red')
        alternative_name = ab_test('link_color', 'blue', 'red')

        previous_completion_count = Alternative(alternative_name, 'link_color').completed_count

        finished('link_color')

        new_completion_count = Alternative(alternative_name, 'link_color').completed_count

        assert new_completion_count == previous_completion_count


class TestVersionedExperiments(TestCase):
    def test_uses_version_zero_if_no_version_is_present(self):
        experiment = Experiment.find_or_create('link_color', 'blue', 'red')
        alternative_name = ab_test('link_color', 'blue', 'red')
        assert experiment.version == 0
        assert session['split'] == {'link_color': alternative_name}

    def test_saves_the_version_of_the_experiment_to_the_session(self):
        experiment = Experiment.find_or_create('link_color', 'blue', 'red')
        experiment.reset()
        assert experiment.version == 1
        alternative_name = ab_test('link_color', 'blue', 'red')
        assert session['split'] == {'link_color:1': alternative_name}

    def test_loads_the_experiment_even_if_the_version_is_not_0(self):
        experiment = Experiment.find_or_create('link_color', 'blue', 'red')
        experiment.reset()
        assert experiment.version == 1
        alternative_name = ab_test('link_color', 'blue', 'red')
        assert session['split'] == {'link_color:1': alternative_name}
        return_alternative_name = ab_test('link_color', 'blue', 'red')
        assert return_alternative_name == alternative_name

    def test_resets_the_session_of_a_user_on_an_older_version_of_the_experiment(self):
        experiment = Experiment.find_or_create('link_color', 'blue', 'red')
        alternative_name = ab_test('link_color', 'blue', 'red')
        assert session['split'] == {'link_color': alternative_name}
        alternative = Alternative(alternative_name, 'link_color')
        assert alternative.participant_count == 1

        experiment.reset()
        assert experiment.version == 1
        alternative = Alternative(alternative_name, 'link_color')
        assert alternative.participant_count == 0

        new_alternative_name = ab_test('link_color', 'blue', 'red')
        assert session['split']['link_color:1'] == new_alternative_name
        new_alternative = Alternative(new_alternative_name, 'link_color')
        assert new_alternative.participant_count == 1

    def test_cleans_up_old_versions_of_experiments_from_the_session(self):
        experiment = Experiment.find_or_create('link_color', 'blue', 'red')
        alternative_name = ab_test('link_color', 'blue', 'red')
        assert session['split'] == {'link_color': alternative_name}
        alternative = Alternative(alternative_name, 'link_color')
        assert alternative.participant_count == 1

        experiment.reset()
        assert experiment.version == 1
        alternative = Alternative(alternative_name, 'link_color')
        assert alternative.participant_count == 0

        new_alternative_name = ab_test('link_color', 'blue', 'red')
        assert session['split'] == {'link_color:1': new_alternative_name}

    def test_only_counts_completion_of_users_on_the_current_version(self):
        experiment = Experiment.find_or_create('link_color', 'blue', 'red')
        alternative_name = ab_test('link_color', 'blue', 'red')
        assert session['split'] == {'link_color': alternative_name}
        alternative = Alternative(alternative_name, 'link_color')

        experiment.reset()
        assert experiment.version == 1

        finished('link_color')
        alternative = Alternative(alternative_name, 'link_color')
        assert alternative.completed_count == 0


class TestExtensionWhenRedisNotAvailable(TestCase):
    def test_ab_test_raises_an_exception_when_db_failover_is_off(self):
        self.app.config['SPLIT_DB_FAILOVER'] = False
        flexmock(Redis).should_receive('execute_command').and_raise(ConnectionError)
        with raises(ConnectionError):
            ab_test('link_color', 'blue', 'red')

    def test_finished_raises_an_exception_when_db_failover_is_off(self):
        self.app.config['SPLIT_DB_FAILOVER'] = False
        flexmock(Redis).should_receive('execute_command').and_raise(ConnectionError)
        with raises(ConnectionError):
            finished('link_color')

    def test_ab_test_does_not_raise_an_exception_when_db_failover_is_on(self):
        self.app.config['SPLIT_DB_FAILOVER'] = True
        flexmock(Redis).should_receive('execute_command').and_raise(ConnectionError)
        ab_test('link_color', 'blue', 'red')

    def test_ab_test_always_uses_first_alternative_when_db_failover_is_on(self):
        self.app.config['SPLIT_DB_FAILOVER'] = True
        flexmock(Redis).should_receive('execute_command').and_raise(ConnectionError)
        assert ab_test('link_color', 'blue', 'red') == 'blue'
        assert ab_test('link_color', ('blue', 0.01), ('red', 0.2)) == 'blue'
        assert ab_test('link_color', ('blue', 0.8), ('red', 20)) == 'blue'

    def test_finished_does_not_raise_an_exception_when_db_failover_is_on(self):
        self.app.config['SPLIT_DB_FAILOVER'] = True
        flexmock(Redis).should_receive('execute_command').and_raise(ConnectionError)
        finished('link_color')
