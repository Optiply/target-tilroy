"""Purchase Order Sink for Tilroy API."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from target_tilroy.client import TilroySink

logger = logging.getLogger(__name__)


class PurchaseOrderSink(TilroySink):
    """Sink for Purchase Orders to Tilroy API."""

    name = "BuyOrders"
    endpoint = "/purchaseapi/production/import/purchaseorders"

    def preprocess_record(self, record: dict, context: dict) -> Optional[dict]:
        """Prepare Tilroy purchase order payload before sending to API."""
        order_date = record.get("transaction_date")
        if isinstance(order_date, datetime):
            order_date = order_date.strftime("%Y-%m-%d")
        elif isinstance(order_date, str) and "T" in order_date:
            order_date = order_date.split("T")[0]

        # requestedDeliveryDate from BuyOrder created_at (keep ISO date-time like data.singer)
        requested_delivery_date = record.get("created_at")
        if isinstance(requested_delivery_date, datetime):
            requested_delivery_date = requested_delivery_date.strftime(
                "%Y-%m-%dT%H:%M:%S.000000Z"
            )

        payload = {
            "orderDate": order_date,
        }
        if record.get("id") is not None:
            payload["supplierReference"] = str(record["id"])

        if requested_delivery_date:
            payload["requestedDeliveryDate"] = requested_delivery_date

        # supplier.tilroyId from supplier_remoteId; API requires string
        if record.get("supplier_remoteId") is not None:
            payload["supplier"] = {"tilroyId": str(record["supplier_remoteId"])}
        else:
            self.logger.info(
                f"Skipping order {record.get('id')} because supplier_remoteId is missing"
            )
            return None

        # lines from line_items (fallback to "items" for backward compat)
        items = record.get("line_items", [])
        if not items:
            items = record.get("items", [])

        if isinstance(items, str):
            items = self.parse_objs(items)

        if not items:
            self.logger.info(f"Skipping order {record.get('id')} with no line items")
            return None

        payload["lines"] = []
        order_delivery_date = payload.get("requestedDeliveryDate")
        for item in items:
            transformed_item = {
                "status": "open",
                "sku": {"tilroyId": str(item.get("product_remoteId"))},
                "qty": {"ordered": item.get("quantity")},
                "warehouse": {"number": int(self.config.get("warehouse_id"))},
            }
            line_delivery = item.get("delivery_date") or order_delivery_date
            if line_delivery:
                transformed_item["requestedDeliveryDate"] = line_delivery

            payload["lines"].append(transformed_item)

        return payload

    def process_record(self, record: dict, context: dict) -> None:
        """Process a preprocessed record, preserving legacy skip behavior."""
        if not record:
            return
        super().process_record(record, context)

    def upsert_record(
        self, record: dict, context: dict
    ) -> tuple[Optional[str], bool, dict]:
        """Send purchase order to Tilroy API and return target-hotglue state info."""
        if not record:
            return None, False, {"error": "Empty purchase order payload"}

        order_id = record.get("supplierReference", "unknown")

        try:
            response = self.request_api(
                "POST",
                endpoint=self.endpoint,
                request_data=record,
            )

            response_data = response.json() if response.text else {}
            remote_id = response_data.get("supplierReference") or response_data.get(
                "id"
            )
            if not remote_id:
                remote_id = order_id

            self.logger.info(f"{self.name} created in Tilroy with ID: {remote_id}")
            return str(remote_id), response.ok, {}

        except Exception as exc:
            self.logger.error(f"API request failed for BuyOrder {order_id}: {exc}")
            response = getattr(exc, "response", None)

            if response is not None:
                status_code = response.status_code
                api_error_response = response.text
                if status_code == 504:
                    error_message = (
                        f"Timeout 504 - BO {order_id} - Please Check BO in Tilroy API"
                    )
                else:
                    error_message = f"HTTP {status_code} - BO {order_id}: {api_error_response or exc}"
            else:
                status_code = None
                api_error_response = None
                error_message = f"BO {order_id}: {exc}"

            state_updates: dict = {
                "error": error_message,
                "error_type": type(exc).__name__,
            }

            if response is not None:
                state_updates["status_code"] = status_code
                state_updates["api_error_response"] = api_error_response
                self.logger.error(f"Error response: {api_error_response}")

            # Do not re-raise: target-hotglue will mark this record as failed in
            # target state and continue processing subsequent BuyOrders.
            return None, False, state_updates

    def clean_up(self) -> None:
        """Clean up resources."""
        # No cleanup needed for this sink.
