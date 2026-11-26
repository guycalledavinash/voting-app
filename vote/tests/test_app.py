import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as vote_app


class VotingAppTestCase(unittest.TestCase):
    def setUp(self):
        vote_app.app.config.update(TESTING=True)
        self.client = vote_app.app.test_client()

    def test_homepage_returns_ok(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_voter_cookie_is_httponly_and_same_site_lax(self):
        response = self.client.get('/')
        cookie = response.headers['Set-Cookie']
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=Lax', cookie)

    def test_valid_vote_is_stored_as_json(self):
        redis = mock.Mock()
        self.client.set_cookie('voter_id', 'test-voter')
        with mock.patch.object(vote_app, 'get_redis', return_value=redis):
            response = self.client.post('/', data={'vote': 'a'})

        self.assertEqual(response.status_code, 200)
        redis.rpush.assert_called_once()
        key, data = redis.rpush.call_args.args
        self.assertEqual(key, 'votes')
        stored_vote = json.loads(data)
        self.assertEqual(stored_vote['vote'], 'a')
        self.assertEqual(stored_vote['voter_id'], 'test-voter')

    def test_invalid_or_missing_vote_returns_bad_request_without_redis_write(self):
        for data in ({'vote': 'invalid'}, {}):
            with self.subTest(data=data), mock.patch.object(vote_app, 'get_redis') as get_redis:
                response = self.client.post('/', data=data)
                self.assertEqual(response.status_code, 400)
                get_redis.assert_not_called()

    def test_health_returns_ok_without_contacting_redis(self):
        with mock.patch.object(vote_app, 'Redis') as redis:
            response = self.client.get('/health')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': 'ok'})
        redis.assert_not_called()

    def test_malicious_option_names_are_serialized_and_not_rendered_as_markup(self):
        option_a = 'Bad "label" <script>alert(1)</script>'
        option_b = '<img src=x onerror=alert(2)>'
        redis = mock.Mock()
        with mock.patch.object(vote_app, 'option_a', option_a), \
             mock.patch.object(vote_app, 'option_b', option_b), \
             mock.patch.object(vote_app, 'get_redis', return_value=redis):
            response = self.client.post('/', data={'vote': 'a'})

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('const optionA = ', body)
        self.assertIn('\\u003cscript\\u003ealert(1)\\u003c/script\\u003e', body)
        self.assertIn('\\u003cimg src=x onerror=alert(2)\\u003e', body)
        self.assertNotIn('<script>alert(1)</script>', body)
        self.assertNotIn('<img src=x onerror=alert(2)>', body)
        self.assertIn(".text(optionA).append(checkIcon)", body)
        self.assertNotIn('.html(optionA + checkIcon)', body)


if __name__ == '__main__':
    unittest.main()

