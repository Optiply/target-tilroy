# target-tilroy

A [Singer](https://singer.io) target for Tilroy that loads BuyOrders into Tilroy's Purchase API, built with the Hotglue target SDK.

## Installation

### Install from source

```bash
git clone https://github.com/your-username/target-tilroy.git
cd target-tilroy

```

## Configuration

Create a `config.json` file in the `secrets` folder with your Tilroy API configuration:

```json
{
  "api_url": "https://api.tilroy.com",
  "tilroy_api_key": "your-tilroy-api-key-here",
  "x_api_key": "your-x-api-key-here",
  "warehouse_id": 500134
}
```

### Configuration Parameters

| Parameter        | Type    | Required | Description                                               |
| ---------------- | ------- | -------- | --------------------------------------------------------- |
| `api_url`        | string  | No       | Base URL for Tilroy API (default: https://api.tilroy.com) |
| `tilroy_api_key` | string  | Yes      | `Tilroy-Api-Key` header value                             |
| `x_api_key`      | string  | Yes      | `x-api-key` header value                                  |
| `warehouse_id`   | integer | Yes      | Warehouse number for purchase order lines                 |

## Usage

### Basic Usage

```bash
# Read from stdin and write to Tilroy
poetry run target-tilroy --config secrets/config.json
```

### With State File

```bash
# Use a state file to track sync progress
poetry run target-tilroy --config secrets/config.json --state state.json
```

### Test with Sample Data

```bash
# Test with the provided sample data
cat payloads/sample_purchase_orders.json | target-tilroy --config secrets/config.json
```

```bash
# For Windows command
Get-Content payloads/data_fixed.singer | poetry run target-tilroy --config secrets/config.json

```

## Architecture

The target uses the Hotglue target SDK so individual BuyOrder failures are written to target state instead of hard-failing the whole export.

- **TilroySink**: Base Hotglue sink class that handles authentication and base URL configuration while keeping the Hotglue SDK's default request/error behavior.
- **PurchaseOrderSink**: Sink class that defines the purchase order import endpoint and transformation logic.
- **TargetTilroy**: Main `TargetHotglue` class that registers supported sinks.

The target keeps the Hotglue SDK default behavior for API failures: transient/server errors use the SDK retry/backoff handling, then failed BuyOrders are written to target state and processing continues with subsequent BuyOrders.

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/your-username/target-tilroy.git
cd target-tilroy

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


```

### Project Structure

```
target-tilroy/
├── target_tilroy/
│   ├── __init__.py
│   ├── target.py              # Main target implementation
│   ├── client.py              # Base Tilroy API client
│   └── sinks.py               # Sink implementations
├── payloads/
│   ├── README.md
│   └── sample_purchase_orders.json  # Sample Singer data
├── secrets/
│   └── config.json            # Configuration file (not in git)
├── pyproject.toml            # Poetry configuration
├── README.md                 # This file
└── .gitignore
```

## Supported Python Versions

This target supports Python 3.9, 3.10, and 3.11.

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## Support

For issues and questions, please open an issue on GitHub or contact the maintainers.
