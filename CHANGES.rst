Changelog
---------

Here you can see the full list of changes between each Flask-Split release.

0.1.2 (2012-03-15)
^^^^^^^^^^^^^^^^^^

- Fixed default value for ``SPLIT_DB_FAILOVER`` not being set.

0.1.1 (2012-03-12)
^^^^^^^^^^^^^^^^^^

- Fixed user's participation to an experiment not clearing out from their
  session, when experiment version was greater than 0.
- Fixed :exc:`ZeroDivisionError` in altenative's z-score calculation.
- Fixed conversion rate difference to control rendering.
- More sensible rounding of percentage values in the dashboard.
- Added 90% confidence level.
- Removed a debug print from :meth:`Experiment.find_or_create`.

0.1.0 (2012-03-11)
^^^^^^^^^^^^^^^^^^

- Initial public release
