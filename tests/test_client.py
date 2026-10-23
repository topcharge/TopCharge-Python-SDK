import json
import unittest

from topcharge_sdk import TopChargeApiError, TopChargeClient
from topcharge_sdk.client import HttpResponse


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def request(self, method, url, headers, body, timeout):
        self.requests.append({"method": method, "url": url, "headers": dict(headers), "body": body})
        return self.responses.pop(0)


class TopChargeClientTests(unittest.TestCase):
    def setUp(self):
        self.transport = FakeTransport([
            HttpResponse(200, '{"availableBalance":"140000.0000"}'),
            HttpResponse(201, '{"paymentId":"pay_123"}'),
            HttpResponse(401, '{"ok":false,"err":{"message":"invalid API credentials"}}'),
        ])
        self.client = TopChargeClient("mch_test_example", "sk_test_example", base_url="https://api.example.test/", transport=self.transport)

    def test_requests_and_api_errors(self):
        self.assertEqual(self.client.account.get_balance()["availableBalance"], "140000.0000")
        self.assertEqual(self.client.payments.create("25000", description="Invoice #1001")["paymentId"], "pay_123")

        self.assertEqual(self.transport.requests[0]["url"], "https://api.example.test/api/v1/account/balance/")
        self.assertEqual(self.transport.requests[0]["headers"]["x-api-key"], "mch_test_example")
        self.assertEqual(self.transport.requests[0]["headers"]["x-api-secret"], "sk_test_example")
        self.assertEqual(json.loads(self.transport.requests[1]["body"]), {"paymentAmount": "25000", "description": "Invoice #1001"})

        with self.assertRaisesRegex(TopChargeApiError, "invalid API credentials") as context:
            self.client.account.verify_credentials()
        self.assertEqual(context.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
