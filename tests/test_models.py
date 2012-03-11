# -*- coding: utf-8 -*-

from datetime import datetime

from flask_split.models import Alternative, Experiment, redis
from flexmock import flexmock

from . import TestCase


class TestAlternative(TestCase):
    def test_has_name(self):
        alternative = Alternative('Basket', 'basket_text')
        assert alternative.name == 'Basket'

    def test_has_default_participation_count_of_0(self):
        alternative = Alternative('Basket', 'basket_text')
        assert alternative.participant_count == 0

    def test_has_default_completed_count_of_0(self):
        alternative = Alternative('Basket', 'basket_text')
        assert alternative.completed_count == 0

    def test_belong_to_an_experiment(self):
        experiment = Experiment('basket_text', 'Basket', 'Cart')
        experiment.save()
        alternative = Alternative('Basket', 'basket_text')
        assert alternative.experiment.name == experiment.name

    def test_saves_to_redis(self):
        alternative = Alternative('Basket', 'basket_text')
        alternative.save()
        assert 'basket_text:Basket' in redis

    def test_increment_participation_count(self):
        experiment = Experiment('basket_text', 'Basket', "Cart")
        experiment.save()
        alternative = Alternative('Basket', 'basket_text')
        old_participant_count = alternative.participant_count
        alternative.increment_participation()
        assert alternative.participant_count == old_participant_count + 1
        assert Alternative('Basket', 'basket_text').participant_count == old_participant_count + 1

    def test_increment_completed_count(self):
        experiment = Experiment('basket_text', 'Basket', "Cart")
        experiment.save()
        alternative = Alternative('Basket', 'basket_text')
        old_completed_count = alternative.participant_count
        alternative.increment_completion()
        assert alternative.completed_count == old_completed_count + 1
        assert Alternative('Basket', 'basket_text').completed_count == old_completed_count + 1

    def test_can_be_reset(self):
        alternative = Alternative('Basket', 'basket_text')
        alternative.participant_count = 10
        alternative.completed_count = 4
        alternative.reset()
        assert alternative.participant_count == 0
        assert alternative.completed_count == 0

    def test_know_if_it_is_the_control_of_an_experiment(self):
        experiment = Experiment('basket_text', 'Basket', 'Cart')
        experiment.save()
        alternative = Alternative('Basket', 'basket_text')
        assert alternative.is_control
        alternative = Alternative('Cart', 'basket_text')
        assert not alternative.is_control

    def test_conversion_rate_is_0_if_there_are_no_conversions(self):
        alternative = Alternative('Basket', 'basket_text')
        assert alternative.completed_count == 0
        assert alternative.conversion_rate == 0

    def test_conversion_rate_does_something(self):
        alternative = Alternative('Basket', 'basket_text')
        alternative.participant_count = 10
        alternative.completed_count = 4
        assert alternative.conversion_rate == 0.4

    def test_z_score_is_zero_when_the_control_has_no_conversions(self):
        experiment = Experiment('link_color', 'blue', 'red')
        experiment.save()
        alternative = Alternative('red', 'link_color')
        assert alternative.z_score == 0

    def test_z_score_is_none_for_the_control(self):
        experiment = Experiment.find_or_create('link_color', 'blue', 'red')
        assert experiment.control.z_score is None


class TestExperiment(TestCase):
    def test_has_name(self):
        experiment = Experiment('basket_text', 'Basket', 'Cart')
        assert experiment.name == 'basket_text'

    def test_has_alternatives(self):
        experiment = Experiment('basket_text', 'Basket', 'Cart')
        assert len(experiment.alternatives) == 2

    def test_saves_to_redis(self):
        experiment = Experiment('basket_text', 'Basket', 'Cart')
        experiment.save()
        assert 'basket_text' in redis

    def test_saves_the_start_time_to_redis(self):
        experiment_start_time = datetime(2012, 3, 9, 22, 01, 34)
        flexmock(Experiment).should_receive('_get_time').and_return(experiment_start_time)
        experiment = Experiment('basket_text', 'Basket', 'Cart')
        experiment.save()
        assert Experiment.find('basket_text').start_time == experiment_start_time

    def test_handles_not_having_a_start_time(self):
        experiment_start_time = datetime(2012, 3, 9, 22, 01, 34)
        flexmock(Experiment).should_receive('_get_time').and_return(experiment_start_time)
        experiment = Experiment('basket_text', 'Basket', 'Cart')
        experiment.save()

        redis.hdel('experiment_start_times', experiment.name)

        assert Experiment.find('basket_text').start_time is None

    def test_does_not_create_duplicates_when_saving_multiple_times(self):
        experiment = Experiment('basket_text', 'Basket', 'Cart')
        experiment.save()
        experiment.save()
        assert 'basket_text' in redis
        assert redis.lrange('basket_text', 0, -1) == ['Basket', 'Cart']

    def test_deleting_should_delete_itself(self):
        experiment = Experiment('basket_text', 'Basket', 'Cart')
        experiment.save()

        experiment.delete()
        assert 'basket_text' not in redis

    def test_deleting_should_increment_the_version(self):
        experiment = Experiment.find_or_create('link_color', 'blue', 'red', 'green')
        assert experiment.version == 0
        experiment.delete()
        assert experiment.version == 1

    def test_is_new_record_knows_if_it_hasnt_been_saved_yet(self):
        experiment = Experiment('basket_text', 'Basket', 'Cart')
        assert experiment.is_new_record

    def test_is_new_record_knows_if_it_has_been_saved_yet(self):
        experiment = Experiment('basket_text', 'Basket', 'Cart')
        experiment.save()
        assert not experiment.is_new_record

    def test_find_returns_an_existing_experiment(self):
        experiment = Experiment('basket_text', 'Basket', 'Cart')
        experiment.save()
        assert Experiment.find('basket_text').name == 'basket_text'

    def test_handles_non_existing_experiment(self):
        assert Experiment.find('non_existent_experiment') is None

    def test_control_is_the_first_alternative(self):
        experiment = Experiment('basket_text', 'Basket', 'Cart')
        experiment.save()
        assert experiment.control.name == 'Basket'

    def test_have_no_winner_initially(self):
        experiment = Experiment.find_or_create('link_color', 'blue', 'red')
        assert experiment.winner is None

    def test_allow_you_to_specify_a_winner(self):
        experiment = Experiment.find_or_create('link_color', 'blue', 'red')
        experiment.winner = 'red'

        experiment = Experiment.find_or_create('link_color', 'blue', 'red')
        assert experiment.winner.name == 'red'

    def test_reset_should_reset_all_alternatives(self):
        experiment = Experiment.find_or_create('link_color', 'blue', 'red', 'green')
        green = Alternative('green', 'link_color')
        experiment.winner = 'green'

        assert experiment.next_alternative().name == 'green'
        green.increment_participation()

        experiment.reset()

        reset_green = Alternative('green', 'link_color')
        assert reset_green.participant_count == 0
        assert reset_green.completed_count == 0

    def test_reset_should_reset_the_winner(self):
        experiment = Experiment.find_or_create('link_color', 'blue', 'red', 'green')
        green = Alternative('green', 'link_color')
        experiment.winner = 'green'

        assert experiment.next_alternative().name == 'green'
        green.increment_participation()

        experiment.reset()

        assert experiment.winner is None

    def test_reset_should_increment_the_version(self):
        experiment = Experiment.find_or_create('link_color', 'blue', 'red', 'green')
        assert experiment.version == 0
        experiment.reset()
        assert experiment.version == 1

    def test_next_alternative_always_returns_the_winner_if_one_exists(self):
        experiment = Experiment.find_or_create('link_color', 'blue', 'red', 'green')
        green = Alternative('green', 'link_color')
        experiment.winner = 'green'

        assert experiment.next_alternative().name == 'green'
        green.increment_participation()

        experiment = Experiment.find_or_create('link_color', 'blue', 'red', 'green')
        assert experiment.next_alternative().name == 'green'

    def test_reset_an_experiment_if_it_is_loaded_with_different_alternatives(self):
        experiment = Experiment('link_color', 'blue', 'red', 'green')
        experiment.save()
        blue = Alternative('blue', 'link_color')
        blue.participant_count = 5
        blue.save()
        same_experiment = Experiment.find_or_create('link_color', 'blue', 'yellow', 'orange')
        assert [a.name for a in same_experiment.alternatives] == ['blue', 'yellow', 'orange']
        new_blue = Alternative('blue', 'link_color')
        assert new_blue.participant_count == 0
