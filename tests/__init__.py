from flask import Flask
from flask_split import Split


class TestCase(object):
    def setup_method(self, method):
        self.app = Flask(__name__)
        self.app.debug = True
        self.app.secret_key = 'very secret'
        self.split = Split(self.app)
        self.split.redis.flushall()
        self._ctx = self.make_test_request_context()
        self._ctx.push()
        self.client = self.app.test_client()

    def teardown_method(self, method):
        self._ctx.pop()

    def make_test_request_context(self):
        return self.app.test_request_context()


def assert_redirects(response, location):
    """
    Checks if response is an HTTP redirect to the
    given location.

    :param response: Flask response
    :param location: relative URL (i.e. without **http://localhost**)
    """
    assert response.status_code in (301, 302)
    assert response.location == 'http://localhost' + location