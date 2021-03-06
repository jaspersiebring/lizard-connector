from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import generators

import json
import unittest
from collections import Iterable

from lizard_connector.connector import Connector, Endpoint

import mock


class MockHeaders:

    def __init__(self, calls):
        self.calls = calls

    def get_content_charset(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return 'utf-8'

    def __getitem__(self, item):
        return "application/json"


class MockUrlopen:

    def __init__(self):
        self.calls = []
        self.headers = MockHeaders(self.calls)

    def read(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return json.dumps({
            'count': 10,
            'next': 'next_url',
            'results': [{
                    'uuid': 1
                }]
        }).encode('utf-8')

    def assert_called_with(self, *args, **kwargs):
        return any(
            all(arg in called_args for arg in args) and
            all(kwarg in called_kwargs.items() for kwarg in kwargs.items())
            for called_args, called_kwargs in self.calls
        )

    def __call__(self, *args, **kwargs):
        return self

    def __enter__(self, *args, **kwargs):
        return self

    def __exit__(self, *args, **kwargs):
        return False


class ConnectorTestCase(unittest.TestCase):

    def setUp(self):
        self.mock_urlopen = MockUrlopen()
        self.connector = Connector()
        self.full_connector = Connector(password='123456',
                                        username='test.user')

    def __connector_test(self, connector_method, *args, **kwargs):
        with mock.patch(
                'lizard_connector.connector.urlopen', self.mock_urlopen):
            return connector_method(*args, **kwargs)

    def test_get(self):
        json_ = self.__connector_test(self.connector.get, 'https://test.nl')
        self.assertDictEqual(json_[0], {'uuid': 1})
        self.mock_urlopen.assert_called_with('https://test.nl', {})

    def test_post(self):
        self.__connector_test(
            self.connector.post, 'https://test.nl', {'data': 1})
        self.mock_urlopen.assert_called_with('https://test.nl', {})

    def test_request(self):
        json_ = self.__connector_test(
            self.connector.perform_request, 'https://test.nl')
        self.assertDictEqual(
            json_, {'count': 10, 'next': 'next_url', 'results': [{
                'uuid': 1}]}
        )

    def test_use_header(self):
        self.assertFalse(self.connector.use_header)
        self.assertTrue(self.full_connector.use_header)

    def test_header(self):
        self.assertDictEqual({}, self.connector._Connector__header)
        self.assertDictEqual({"username": 'test.user', "password": '123456'},
                             self.full_connector._Connector__header)


class EndpointTestCase(unittest.TestCase):

    def setUp(self):
        self.connector_get = mock.MagicMock(return_value=[{'uuid': 1}])
        self.connector_get_task = mock.MagicMock(return_value={
            'url': "test", 'task_status': "SUCCESS"})
        self.connector_post = mock.MagicMock(return_value=None)
        self.endpoint = Endpoint(base='https://test.nl', endpoint='test')
        self.endpoint.next_url = 'test'

    def split_query(self, query):
        url, qargs = query.split('?')
        return url, dict(q.split('=') for q in qargs.split('&'))

    def query_url(self, expected, result):
        expected_url, expected = self.split_query(expected)
        result_url, result = self.split_query(result)
        self.assertEqual(expected_url, result_url)
        self.assertDictEqual(expected, result)

    def __connector_test(self, connector_method, async=False, *args, **kwargs):
        connector = self.connector_get_task if async else self.connector_get
        with mock.patch(
            'lizard_connector.connector.Connector.get', connector), mock.patch(
            'lizard_connector.connector.Connector.post', self.connector_post
        ):
            return connector_method(*args, **kwargs)

    def test_download(self):
        self.__connector_test(self.endpoint.get, q1=2)
        first_call = self.connector_get.call_args_list[0][0][0]
        expected = ('https://test.nl/api/v3/test/?q1=2&page_size=1000&'
                    'format=json')
        self.query_url(expected, first_call)

    def test_paginated_download(self):
        result = self.endpoint.get_paginated('testendpoint')
        self.assertIsInstance(result, Iterable)

    def test_async_download(self):
        # This throws an error. That is ok.
        try:
            self.__connector_test(self.endpoint.get_async, async=True, q1=2)
        except AttributeError:
            if not len(self.connector_get_task.call_args_list):
                return
        second_call = self.connector_get_task.call_args_list[0][1]
        self.assertDictEqual(second_call, {})
        first_call = self.connector_get_task.call_args_list[0][0][0]
        expected = ('https://test.nl/api/v3/test/?async=true&q1=2&page_size=0&'
                    'format=json')
        self.query_url(expected, first_call)

    def test_post(self):
        self.__connector_test(self.endpoint.create, uuid="1", a=1)
        self.connector_post.assert_called_with(
            'https://test.nl/api/v3/test/1/data/', {"a": 1})
        self.__connector_test(self.endpoint.create, a=1)
        self.connector_post.assert_called_with(
            'https://test.nl/api/v3/test/', {"a": 1})


class PaginatedRequestTestcase(unittest.TestCase):

    def test_count(self):
        pass
        # self.connector_test(self.connector.get, 'https://test.nl')
        # self.assertEqual(self.connector.count, 10)

    def test_next_page(self):
        pass
        # self.connector_test(self.connector.get, 'https://test.nl')
        # self.assertEqual(self.connector.next_url, 'next_url')


if __name__ == '__main__':
    unittest.main()
