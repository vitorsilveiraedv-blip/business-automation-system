import json
from urllib.error import HTTPError, URLError
from unittest.mock import Mock, call, patch

import pytest

from business_automation.integrations import WebhookClient, WebhookDeliveryError
from business_automation.processor import ProcessedOrder


@pytest.fixture
def order():
    return ProcessedOrder(
        order_id="ORD-1001",
        customer_email="customer@example.com",
        amount="125.50",
        currency="USD",
        status="paid",
    )


def response(status=201):
    result = Mock()
    result.status = status
    result.__enter__ = Mock(return_value=result)
    result.__exit__ = Mock(return_value=False)
    return result


def test_webhook_posts_order_as_json(order):
    with patch("business_automation.integrations.urlopen", return_value=response()) as mocked:
        client = WebhookClient("https://example.com/orders")
        assert client.send_order(order) == 201

    request = mocked.call_args.args[0]
    assert request.method == "POST"
    assert request.get_header("Content-type") == "application/json"
    assert json.loads(request.data) == {
        "order_id": "ORD-1001",
        "customer_email": "customer@example.com",
        "amount": "125.50",
        "currency": "USD",
        "status": "paid",
    }
    assert mocked.call_args.kwargs["timeout"] == 5.0


def test_webhook_retries_temporary_server_error(order):
    temporary_error = HTTPError(
        "https://example.com/orders", 503, "Unavailable", {}, None
    )
    with (
        patch("business_automation.integrations.urlopen",
              side_effect=[temporary_error, response()]) as mocked,
        patch("business_automation.integrations.time.sleep") as sleep,
    ):
        client = WebhookClient(
            "https://example.com/orders", max_retries=1, backoff_seconds=0.1
        )
        assert client.send_order(order) == 201

    assert mocked.call_count == 2
    sleep.assert_called_once_with(0.1)


def test_webhook_does_not_retry_client_error(order):
    error = HTTPError("https://example.com/orders", 400, "Bad Request", {}, None)
    with patch("business_automation.integrations.urlopen", side_effect=error) as mocked:
        client = WebhookClient("https://example.com/orders", max_retries=3)
        with pytest.raises(WebhookDeliveryError, match="HTTP 400"):
            client.send_order(order)

    mocked.assert_called_once()


def test_webhook_retries_network_error_then_fails(order):
    with (
        patch("business_automation.integrations.urlopen",
              side_effect=URLError("connection refused")) as mocked,
        patch("business_automation.integrations.time.sleep"),
    ):
        client = WebhookClient("https://example.com/orders", max_retries=1)
        with pytest.raises(WebhookDeliveryError, match="after 2 attempt"):
            client.send_order(order)

    assert mocked.call_count == 2


@pytest.mark.parametrize("endpoint", ["", "ftp://example.com", "not-a-url"])
def test_webhook_rejects_invalid_endpoint(endpoint):
    with pytest.raises(ValueError, match="HTTP or HTTPS"):
        WebhookClient(endpoint)


def test_webhook_rejects_invalid_retry_settings():
    with pytest.raises(ValueError, match="max_retries"):
        WebhookClient("https://example.com", max_retries=-1)
