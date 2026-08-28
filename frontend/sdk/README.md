# Sentinel AI Browser SDK

Dependency-free JavaScript SDK that automatically captures frontend errors, unhandled promise rejections, and HTTP failures — then batches and ships them to your Sentinel AI backend.

## Quick Start

Add the following snippet before the closing `</body>` tag (or in your `<head>` with `defer`):

```html
<script src="https://your-cdn.example.com/sentinelai-browser.js"></script>
<script>
  SentinelAI.init({
    apiKey:       "your-project-api-key",
    endpoint:     "https://api.your-sentinelai.example.com",
    serviceName:  "my-frontend-app",
    environment:  "production",
    appVersion:   "1.2.3"
  });
</script>
```

## What It Captures Automatically

| Signal | How |
|---|---|
| **Unhandled errors** | `window.onerror` |
| **Unhandled rejections** | `unhandledrejection` listener |
| **HTTP ≥ 500 failures** | `fetch()` monkey-patch |
| **Network errors** | `fetch()` catch |
| **Distributed traces** | Injects `x-trace-id` header on every outgoing `fetch` |

## Manual Capture

```js
// Log a custom event
SentinelAI.log("WARN", "Cart abandoned after 30 s", { userId: "u-123" });

// Capture a caught exception
try { riskyOp(); } catch (e) { SentinelAI.captureException(e); }

// Force flush (e.g. before SPA navigation)
SentinelAI.flush();
```

## Flush Behaviour

- Events are buffered and flushed every **5 seconds** or when the buffer exceeds **50 items**.
- On `visibilitychange` (tab hidden) and `beforeunload`, the SDK uses `navigator.sendBeacon` for reliable delivery.
- All flushes are non-blocking and best-effort.

## Payload Format

The SDK posts to `POST {endpoint}/api/v1/sdk/ingest` with header `X-API-Key`, matching the backend `IngestPayloadSchema`:

```json
{
  "api_key": "...",
  "service_name": "my-frontend-app",
  "environment": "production",
  "logs": [],
  "exceptions": [],
  "traces": [],
  "metrics": [],
  "deployments": []
}
```
