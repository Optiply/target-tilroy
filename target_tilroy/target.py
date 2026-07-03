"""Tilroy target class."""

from __future__ import annotations

from typing import Any

from singer_sdk import typing as th
from target_hotglue.target import TargetHotglue

from target_tilroy.sinks import PurchaseOrderSink


class TargetTilroy(TargetHotglue):
    """Singer target for Tilroy Purchase API using target-hotglue state handling."""

    name = "target-tilroy"
    MAX_PARALLELISM = 1
    SINK_TYPES = [PurchaseOrderSink]

    config_jsonschema = th.PropertiesList(
        th.Property(
            "api_url",
            th.StringType,
            default="https://api.tilroy.com",
            description="API URL for Tilroy API",
        ),
        th.Property(
            "tilroy_api_key",
            th.StringType,
            required=True,
            description="Tilroy-Api-Key header value",
        ),
        th.Property(
            "x_api_key",
            th.StringType,
            required=True,
            description="x-api-key header value",
        ),
        th.Property(
            "warehouse_id",
            th.IntegerType,
            required=True,
            description="Warehouse number for purchase order lines",
        ),
    ).to_dict()

    def get_sink_class(self, stream_name: str) -> Any:
        """Return sink class for a Singer stream."""
        if stream_name == "BuyOrders":
            return PurchaseOrderSink
        self.logger.warning(f"Unknown stream: {stream_name}")
        return None


def cli() -> None:
    """CLI entry point for target-tilroy."""
    TargetTilroy.cli()


if __name__ == "__main__":
    cli()
