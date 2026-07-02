"""Tilroy target sink base class."""

from __future__ import annotations

import ast
import json
import logging
from typing import Any

import requests
from singer_sdk.plugin_base import PluginBase
from target_hotglue.client import HotglueSink

logger = logging.getLogger(__name__)


class TilroySink(HotglueSink):
    """Base sink for Tilroy API requests."""

    # Match target-hotglue's default REST timeout.
    timeout = 300

    def __init__(
        self,
        target: PluginBase,
        stream_name: str,
        schema: dict,
        key_properties: list[str] | None,
    ) -> None:
        """Initialize the sink and configure Tilroy headers."""
        super().__init__(target, stream_name, schema, key_properties)
        self.http_headers = self._build_http_headers()

    @property
    def unified_schema(self) -> Any:
        """Return no pydantic schema; this target uses legacy BuyOrders directly."""
        return None

    @property
    def base_url(self) -> str:
        """Return the API base URL for Tilroy API."""
        return self._target.config.get("api_url", "https://api.tilroy.com").rstrip("/")

    def _build_http_headers(self) -> dict[str, str]:
        """Return the HTTP headers needed for Tilroy authentication."""
        headers: dict[str, str] = {}

        if hasattr(self._target, "config"):
            if self._target.config.get("tilroy_api_key"):
                headers["Tilroy-Api-Key"] = self._target.config["tilroy_api_key"]
            if self._target.config.get("x_api_key"):
                headers["X-Api-Key"] = self._target.config["x_api_key"]

        return headers

    def parse_objs(self, obj: Any) -> Any:
        """Parse objects that may arrive as JSON or Python-literal strings."""
        if not isinstance(obj, str):
            return obj

        try:
            return ast.literal_eval(obj)
        except (ValueError, SyntaxError):
            return json.loads(obj)

    def _request(
        self,
        http_method: str,
        endpoint: str | None,
        params: dict | None = None,
        request_data: dict | None = None,
        headers: dict | None = None,
        verify: bool = True,
    ) -> Any:
        """Make a Tilroy API request without retrying failed BuyOrder POSTs."""
        url = self.url(endpoint)
        request_headers = self.default_headers.copy()
        request_headers.update({"Content-Type": "application/json"})
        if headers:
            request_headers.update(headers)

        self.logger.info(f"Making API request to: {url}")
        self.logger.info(f"Request method: {http_method}")
        if request_data is not None:
            self.logger.info(f"Request payload: {request_data}")

        response = requests.request(
            method=http_method,
            url=url,
            params=params,
            headers=request_headers,
            json=request_data,
            timeout=self.timeout,
            verify=verify,
        )

        self.logger.info(f"Response status: {response.status_code}")
        if response.status_code >= 400:
            self.logger.error(f"API error response: {response.text}")
            # Do not use target-hotglue's default 5xx backoff for Tilroy BuyOrder
            # POSTs. Tilroy can create a partial/empty BO before returning 5xx, so
            # retries can create duplicates. The sink catches this and stores a
            # failed bookmark in target state, then continues to the next BO.
            raise requests.exceptions.HTTPError(
                self.response_error_message(response), response=response
            )

        return response

    def request_api(
        self,
        http_method: str,
        endpoint: str | None = None,
        params: dict | None = None,
        request_data: dict | None = None,
        headers: dict | None = None,
        verify: bool = True,
    ) -> Any:
        """Request Tilroy's REST API."""
        return self._request(
            http_method, endpoint, params, request_data, headers, verify
        )
