"""Preserve response types without changing the standard request marshaller."""
import unittest
from datetime import datetime
from xmlrpc.client import Binary, dumps, loads

from tactic_stream.server.xmlrpc_response import encode_response


class XmlrpcResponseTests(unittest.TestCase):
    def test_ordinary_response_matches_standard_encoding(self):
        value = {'rows': [False, True, None, -(2**31), 2**31 - 1, '<&Привет',
                          b'\x00\xff', Binary(b'\x00'), datetime(2026, 10, 14, 0, 30)]}
        self.assertEqual(encode_response(value), dumps((value,), methodresponse=True, allow_none=True).encode('utf-8'))

    def test_nested_integer_boundaries_round_trip_without_global_patch(self):
        values = [-(2**63)-1, -(2**63), -(2**31)-1, -(2**31),
                  2**31-1, 2**31, 2**63-1, 2**63, 10**100]
        value = {'result': {'rows': [[number] for number in values], 'flag': True}}
        decoded, _method = loads(encode_response(value))
        self.assertEqual(decoded[0], value)
        self.assertIs(decoded[0]['result']['flag'], True)
        for row in decoded[0]['result']['rows']:
            self.assertIs(type(row[0]), int)
        with self.assertRaises(OverflowError):
            dumps((2**31,))


if __name__ == '__main__':
    unittest.main()
