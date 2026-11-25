"""Optional JSON webhook integration for accepted orders."""

from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from business_automation.processor import ProcessedOrder

logger = logging.getLogger(__name__)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class WebhookDeliveryError(RuntimeError):
    """Raised when an order cannot be delivered to the configured webhook."""


class WebhookClient:
    """Deliver orders to an HTTP endpoint with bounded retries."""

    def __init__(
        self,
        endpoint: str,
        *,
        timeout: float = 5.0,
        max_retries: int = 2,
        backoff_seconds: float = 0.5,
    ) -> None:
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Webhook endpoint must be a valid HTTP or HTTPS URL")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if backoff_seconds < 0:
            raise ValueError("backoff_seconds cannot be negative")

        self.endpoint = endpoint
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds

    def send_order(self, order: ProcessedOrder) -> int:
        """POST one order as JSON and return the HTTP response status."""
        payload: dict[str, Any] = {
            "order_id": order.order_id,
            "customer_email": order.customer_email,
            "amount": order.amount,
            "currency": order.currency,
            "status": order.status,
        }
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            self.endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "business-automation-system/1.0",
            },
            method="POST",
        )

        for attempt in range(self.max_retries + 1):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    status = response.status
                if not 200 <= status < 300:
                    raise WebhookDeliveryError(
                        f"Webhook returned unexpected HTTP status {status}"
                    )
                logger.info("Delivered order %s (HTTP %s)", order.order_id, status)
                return status
            except HTTPError as error:
                if error.code not in RETRYABLE_STATUS_CODES:
                    raise WebhookDeliveryError(
                        f"Webhook rejected order {order.order_id} with HTTP {error.code}"
                    ) from error
                last_error: Exception = error
            except URLError as error:
                last_error = error

            if attempt >= self.max_retries:
                raise WebhookDeliveryError(
                    f"Could not deliver order {order.order_id} after "
                    f"{attempt + 1} attempt(s): {last_error}"
                ) from last_error

            delay = self.backoff_seconds * (2 ** attempt)
            logger.warning(
                "Temporary webhook failure for order %s; retrying in %.2fs",
                order.order_id,
                delay,
            )
            time.sleep(delay)

        raise WebhookDeliveryError(f"Could not deliver order {order.order_id}")
