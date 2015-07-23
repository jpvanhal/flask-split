Changelog
---------

Here you can see the full list of changes between each Flask-Split release.

0.3.0 (2015-07-23)
^^^^^^^^^^^^^^^^^^

- Fixed #3: `TypeError: set([]) is not JSON serializable` when tracking a
  conversion in Flask 0.10. Thanks Kacper Wikieł and Nick Woodhams.
- Dropped support for Python 2.5.

0.2.0 (2012-06-03)
^^^^^^^^^^^^^^^^^^

- Added ``REDIS_URL`` configuration variable for configuring the Redis
  connection.
- Fixed properly :func:`finished` incrementing alternative's completion count
  multiple times, when the test is not reset after it has been finished.  The
  fix for this issue in the previous release did not work, when the version of
  the test was greater than 0.

0.1.3 (2012-05-30)
^^^^^^^^^^^^^^^^^^

- Fixed :func:`finished` incrementing alternative's completion count multiple
  times, when the test is not reset after it has been finished.

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
