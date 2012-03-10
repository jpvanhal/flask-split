from datetime import datetime
from math import sqrt
from random import random

from flask import current_app


def get_redis():
    return current_app.extensions['split'].redis


class Alternative(object):
    def __init__(self, name, experiment_name):
        self.redis = get_redis()
        self.experiment_name = experiment_name
        if isinstance(name, tuple):
            self.name, self.weight = name
        else:
            self.name = name
            self.weight = 1

    def _get_participant_count(self):
        return int(self.redis.hget(self.key, 'participant_count') or 0)

    def _set_participant_count(self, count):
        self.redis.hset(self.key, 'participant_count', int(count))

    participant_count = property(
        _get_participant_count,
        _set_participant_count
    )

    def _get_completed_count(self):
        return int(self.redis.hget(self.key, 'completed_count') or 0)

    def _set_completed_count(self, count):
        self.redis.hset(self.key, 'completed_count', int(count))

    completed_count = property(
        _get_completed_count,
        _set_completed_count
    )

    def increment_participation(self):
        self.redis.hincrby(self.key, 'participant_count', 1)

    def increment_completion(self):
        self.redis.hincrby(self.key, 'completed_count', 1)

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
        self.redis.hsetnx(self.key, 'participant_count', 0)
        self.redis.hsetnx(self.key, 'completed_count', 0)

    def reset(self):
        self.redis.hmset(self.key, {
            'participant_count': 0,
            'completed_count': 0
        })

    def delete(self):
        self.redis.delete(self.key)

    @property
    def key(self):
        return '%s:%s' % (self.experiment_name, self.name)

    @property
    def z_score(self):
        control = self.experiment.control
        alternative = self

        if control.name == alternative.name:
            return None

        # the CTR within the experiment split
        ctr_e = alternative.conversion_rate
        # the CTR within the control split
        ctr_c = control.conversion_rate

        # the number of impressions within the experiment split
        e = alternative.participant_count
        # the number of impressions within the control split
        c = control.participant_count

        if ctr_c == 0:
            return 0

        standard_deviation = sqrt((ctr_e / ctr_c ** 3) * ((e * ctr_e) + (c * ctr_c) - (ctr_c * ctr_e) * (c + e)) / (c * e))

        return ((ctr_e / ctr_c) - 1) / standard_deviation

    @property
    def confidence_level(self):
        z = self.z_score
        if z is None:
            return 'N/A'
        z = abs(round(z, 3))
        if z == 0:
            return 'no change'
        elif z < 1.96:
            return 'no confidence'
        elif z < 2.57:
            return '95% confidence'
        elif z < 3.29:
            return '99% confidence'
        else:
            return '99.9% confidence'


class Experiment(object):
    def __init__(self, name, *alternative_names):
        self.redis = get_redis()
        self.name = name
        self.alternatives = [
            Alternative(alternative, name)
            for alternative in alternative_names
        ]

    @property
    def control(self):
        return self.alternatives[0]

    def _get_winner(self):
        winner = self.redis.hget('experiment_winner', self.name)
        if winner:
            return Alternative(winner, self.name)

    def _set_winner(self, winner_name):
        self.redis.hset('experiment_winner', self.name, winner_name)

    winner = property(
        _get_winner,
        _set_winner
    )

    def reset_winner(self):
        self.redis.hdel('experiment_winner', self.name)

    @property
    def start_time(self):
        t = self.redis.hget('experiment_start_times', self.name)
        if t:
            return datetime.strptime(t, '%Y-%m-%dT%H:%M:%S')

    @property
    def total_participants(self):
        return sum(a.participant_count for a in self.alternatives)

    @property
    def total_completed(self):
        return sum(a.completed_count for a in self.alternatives)

    @property
    def alternative_names(self):
        return [alternative.name for alternative in self.alternatives]

    def next_alternative(self):
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
        return int(self.redis.get('%s:version' % self.name) or 0)

    def increment_version(self):
        self.redis.incr('%s:version' % self.name)

    @property
    def key(self):
        if self.version > 0:
            return "%s:%s" % (self.name, self.version)
        else:
            return self.name

    def reset(self):
        for alternative in self.alternatives:
            alternative.reset()
        self.reset_winner()
        self.increment_version()

    def delete(self):
        for alternative in self.alternatives:
            alternative.delete()
        self.reset_winner()
        self.redis.srem('experiments', self.name)
        self.redis.delete(self.name)
        self.increment_version()

    @property
    def is_new_record(self):
        return self.name not in self.redis

    def save(self):
        if self.is_new_record:
            start_time = self._get_time().isoformat()[:19]
            self.redis.sadd('experiments', self.name)
            self.redis.hset('experiment_start_times', self.name, start_time)
            for alternative in reversed(self.alternatives):
                self.redis.lpush(self.name, alternative.name)

    @classmethod
    def load_alternatives_for(cls, name):
        return get_redis().lrange(name, 0, -1)

    @classmethod
    def all(cls):
        return [cls.find(e) for e in get_redis().smembers('experiments')]

    @classmethod
    def find(cls, name):
        if name in get_redis():
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
            print 'Creating experiment'
            experiment = cls(name, *alternatives)
            experiment.save()
        return experiment

    def _get_time(self):
        return datetime.now()
