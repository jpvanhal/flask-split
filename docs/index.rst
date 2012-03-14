Flask-Split
===========

Flask-Split is a Flask extension for `A/B testing`_ your web application. It
is a port of Andrew Nesbitt's excellent `Split`_ A/B testing framework to
Python and Flask.

.. _A/B testing: http://en.wikipedia.org/wiki/A/B_testing
.. _Split: https://github.com/andrew/split


Installation
------------

The easiest way to install Flask-Split is with pip::

    pip install Flask-Split

You will also need Redis as Flask-Split uses it as a datastore.  Flask-Split
only supports Redis 2.0 or greater.

In case you are on OS X, the easiest way to install Redis is with Homebrew::

    brew install redis

If you are on Ubuntu or other Debian-based Linux, you can install Redis with
APT::

    sudo apt-get install redis-server


Quickstart
----------

In order to start using Flask-Split, you need to first register the Flask-Split
blueprint to your Flask application::

    from flask import Flask
    from flask.ext.split import split

    app = Flask(__name__)
    app.register_blueprint(split)

After that you can start A/B testing your application.

Defining an A/B test
^^^^^^^^^^^^^^^^^^^^

You can define experiments with the :func:`ab_test` function in a view or a
template.  For example, in a template you can define an experiment like so:

.. sourcecode:: html+jinja

   <button type="submit">
     {{ ab_test('signup_btn_text', 'Register', 'Sign up') }}
   </button>

This will set up a new experiment called `signup_btn_text` with two
alternatives: `Register` and `Sign up`.  The first alternative is the control.
It should be the original text that was already on the page and the text you
test new alternative against.  You should not add only new alternatives as then
you won't be able to tell if you have improved over the original or not.

Tracking conversions
^^^^^^^^^^^^^^^^^^^^

To measure how the alternative has imcpacted the conversion rate of your
experiment you need to mark a visitor reaching the conversion point.  You can
do this with the :func:`finished` function::

    finished('signup_btn_text')

You should place this in a view, for example after a user has completed the
sign up process.

Configuration
-------------

The following configuration values exist for Flask-Split.  Flask-Split loads
these values from your main Flask config which can be populated in various
ways.

A list of configuration keys currently understood by the extension:

``SPLIT_ALLOW_MULTIPLE_EXPERIMENTS``
    If set to `True` Flask-Split will allow users to participate in multiple
    experiments.

    If set to `False` Flask-Split will avoid users participating in multiple
    experiments at once.  This means you are less likely to skew results by
    adding in more  variation to your tests.

    Defaults to `False`.

``SPLIT_IGNORE_IP_ADDRESSES``
    Specifies a list of IP addresses to ignore visits from.  You may wish to
    use this to prevent yourself or people from your office from skewing the
    results.

    Defaults to ``[]``, i.e. no IP addresses are ignored by default.

``SPLIT_ROBOT_REGEX``
    Flask-Split ignores visitors that appear to be robots or spider in order to
    avoid them from skeweing any results. Flask-Split detects robots and
    spiders by comparing the user agent of each request with the regular
    expression in this setting.

    Defaults to::

        r"""
        (?:i)\b(
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
        """

``SPLIT_DB_FAILOVER``
    If set to `True` Flask-Split will not let :meth:`ab_test` or
    :meth:`finished` to crash in case of a Redis connection error.  In that
    case :meth:`ab_test` always delivers the first alternative i.e. the
    control.

    Defaults to `True`.


Web Interface
-------------

Flask-Split comes with a web frontend to get an overview of how your
experiments are doing. You can find the web interface from the address
``/split/``.

If you would like to restrict the access to the web interface, you can take
advantage of blueprint's hooks::

    from flask import abort
    from flask.ext.split import split

    @split.before_request
    def require_login():
        if not user_logged_in():
            abort(401)


API reference
-------------

.. module:: flask.ext.split

This part of the documentation covers all the public classes and functions
in Flask-Split.

.. autofunction:: ab_test
.. autofunction:: finished


.. include:: ../CHANGES.rst


License
-------

.. include:: ../LICENSE

