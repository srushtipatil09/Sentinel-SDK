# Sentinel AI Python SDK

Official Python SDK for **Sentinel AI** — Autonomous AI Observability & Root Cause Analysis Platform.

## Installation

```bash
pip install sentinelai-telemetry-sdk
```

## Quickstart

```python
from backend.sdk.client import SentinelAISDKClient

# 1. Initialize client with your Sentinel AI project API Key
client = SentinelAISDKClient(
    api_key="stl_live_your_api_key_here",
    service_name="checkout-service",
    environment="production"
)

# 2. Capture logs, metrics, traces, exceptions, or deployment markers
client.capture_log("INFO", "Order processed successfully", attributes={"order_id": "9941"})
client.capture_metric("checkout_latency_ms", 124.5, metric_type="gauge")

# 3. Flush buffered telemetry batch to Sentinel AI backend
client.flush()
```

## Supported Telemetry Signals

- **Logs**: `client.capture_log(level, message, attributes)`
- **Exceptions**: `client.capture_exception(exception, handled)`
- **Traces**: `client.capture_trace(trace_id, span_id, operation_name, duration_ms)`
- **Metrics**: `client.capture_metric(name, value, metric_type, unit, tags)`
- **Deployments**: `client.capture_deployment(version, commit_hash, commit_message, author)`

## License

MIT License
