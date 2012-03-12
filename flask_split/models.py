# -*- coding: utf-8 -*-
"""
    flask.ext.split.models
    ~~~~~~~~~~~~~~~~~~~~~~

    This module provides the models for experiments and alternatives.

    :copyright: (c) 2012 by Janne Vanhala.
    :license: MIT, see LICENSE for more details.
"""

from datetime import datetime
from math import sqrt
from random import random

from redis import Redis


redis = Redis()


class Alternative(object):
    def __init__(self, name, experiment_name):
        self.experiment_name = experiment_name
        if isinstance(name, tuple):
            self.name, self.weight = name
        else:
            self.name = name
            self.weight = 1

    def _get_participant_count(self):
        return int(redis.hget(self.key, 'participant_count') or 0)

    def _set_participant_count(self, count):
        redis.hset(self.key, 'participant_count', int(count))

    participant_count = property(
        _get_participant_count,
        _set_participant_count
    )

    def _get_completed_count(self):
        return int(redis.hget(self.key, 'completed_count') or 0)

    def _set_completed_count(self, count):
        redis.hset(self.key, 'completed_count', int(count))

    completed_count = property(
        _get_completed_count,
        _set_completed_count
    )

    def increment_participation(self):
        redis.hincrby(self.key, 'participant_count', 1)

    def increment_completion(self):
        redis.hincrby(self.key, 'completed_count', 1)

    @property
    def is_control(self):
        return self.experiment.control.name == self.name

    @property
    def conversion_rate(self):
        if self.participant_count == 0:
            return 0
        return float(self.completed_count) / float(self.participant_count)

    @property
    def experiment(self):
        return Experiment.find(self.experiment_name)

    def save(self):
        redis.hsetnx(self.key, 'participant_count', 0)
        redis.hsetnx(self.key, 'completed_count', 0)

    def reset(self):
        redis.hmset(self.key, {
            'participant_count': 0,
            'completed_count': 0
        })

    def delete(self):
        redis.delete(self.key)

    @property
    def key(self):
        return '%s:%s' % (self.experiment_name, self.name)

    @property
    def z_score(self):
        control = self.experiment.control
        alternative = self

        if control.name == alternative.name:
            return None

        cr = alternative.conversion_rate
        crc = control.conversion_rate

        n = alternative.participant_count
        nc = control.participant_count

        if n == 0 or nc == 0:
            return None

        mean = cr - crc
        var_cr = cr * (1 - cr) / float(n)
        var_crc = crc * (1 - crc) / float(nc)

        if var_cr + var_crc == 0:
            return None

        return mean / sqrt(var_cr + var_crc)

    @property
    def confidence_level(self):
        z = self.z_score
        if z is None:
            return 'N/A'
        z = abs(round(z, 3))
        if z == 0:
            return 'no change'
        elif z < 1.64:
            return 'no confidence'
        elif z < 1.96:
            return '90% confidence'
        elif z < 2.57:
            return '95% confidence'
        elif z < 3.29:
            return '99% confidence'
        else:
            return '99.9% confidence'


class Experiment(object):
    def __init__(self, name, *alternative_names):
        self.name = name
        self.alternatives = [
            Alternative(alternative, name)
            for alternative in alternative_names
        ]

    @property
    def control(self):
        return self.alternatives[0]

    def _get_winner(self):
        winner = redis.hget('experiment_winner', self.name)
        if winner:
            return Alternative(winner, self.name)

    def _set_winner(self, winner_name):
        redis.hset('experiment_winner', self.name, winner_name)

    winner = property(
        _get_winner,
        _set_winner
    )

    def reset_winner(self):
        """Reset the winner of this experiment."""
        redis.hdel('experiment_winner', self.name)

    @property
    def start_time(self):
        """The start time of this experiment."""
        t = redis.hget('experiment_start_times', self.name)
        if t:
            return datetime.strptime(t, '%Y-%m-%dT%H:%M:%S')

    @property
    def total_participants(self):
        """The total number of participants in this experiment."""
        return sum(a.participant_count for a in self.alternatives)

    @property
    def total_completed(self):
        """The total number of users who completed this experiment."""
        return sum(a.completed_count for a in self.alternatives)

    @property
    def alternative_names(self):
        """A list of alternative names. in this experiment."""
        return [alternative.name for alternative in self.alternatives]

    def next_alternative(self):
        """Return the winner of the experiment if set, or a random
        alternative."""
        return self.winner or self.random_alternative()

    def random_alternative(self):
        total = sum(alternative.weight for alternative in self.alternatives)
        point = random() * total
        for alternative in self.alternatives:
            if alternative.weight >= point:
                return alternative
            point -= alternative.weight

    @property
    def version(self):
        return int(redis.get('%s:version' % self.name) or 0)

    def increment_version(self):
        redis.incr('%s:version' % self.name)

    @property
    def key(self):
        if self.version > 0:
            return "%s:%s" % (self.name, self.version)
        else:
            return self.name

    def reset(self):
        """Delete all data for this experiment."""
        for alternative in self.alternatives:
            alternative.reset()
        self.reset_winner()
        self.increment_version()

    def delete(self):
        """Delete this experiment and all its data."""
        for alternative in self.alternatives:
            alternative.delete()
        self.reset_winner()
        redis.srem('experiments', self.name)
        redis.delete(self.name)
        self.increment_version()

    @property
    def is_new_record(self):
        return self.name not in redis

    def save(self):
        if self.is_new_record:
            start_time = self._get_time().isoformat()[:19]
            redis.sadd('experiments', self.name)
            redis.hset('experiment_start_times', self.name, start_time)
            for alternative in reversed(self.alternatives):
                redis.lpush(self.name, alternative.name)

    @classmethod
    def load_alternatives_for(cls, name):
        return redis.lrange(name, 0, -1)

    @classmethod
    def all(cls):
        return [cls.find(e) for e in redis.smembers('experiments')]

    @classmethod
    def find(cls, name):
        if name in redis:
            return cls(name, *cls.load_alternatives_for(name))

    @classmethod
    def find_or_create(cls, key, *alternatives):
        name = key.split(':')[0]

        if len(alternatives) < 2:
            raise TypeError('You must declare at least 2 alternatives.')

        experiment = cls.find(name)
        if experiment:
            alts = [a[0] if isinstance(a, tuple) else a for a in alternatives]
            if [a.name for a in experiment.alternatives] != alts:
                experiment.reset()
                for alternative in experiment.alternatives:
                    alternative.delete()
                experiment = cls(name, *alternatives)
                experiment.save()
        else:
            experiment = cls(name, *alternatives)
            experiment.save()
        return experiment

    def _get_time(self):
        return datetime.now()
