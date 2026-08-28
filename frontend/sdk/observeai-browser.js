/**
 * SentinelAI Browser SDK — dependency-free auto-capture for frontend observability.
 *
 * Usage:
 *   SentinelAI.init({ apiKey, endpoint, serviceName, environment, appVersion });
 *
 * Captures:
 *   - Unhandled errors (window.onerror)
 *   - Unhandled promise rejections
 *   - fetch() failures (HTTP ≥ 500 or network error) & duration tracing
 *   - Injects x-trace-id header on outgoing fetch requests
 *
 * Batches events and flushes via POST <endpoint>/api/v1/sdk/ingest
 * using sendBeacon on page unload and async fetch otherwise.
 */
(function (root) {
  "use strict";

  var SentinelAI = root.SentinelAI || {};
  var _config = {};
  var _buffer = { logs: [], exceptions: [], traces: [], metrics: [], deployments: [] };
  var _flushInterval = null;
  var _originalFetch = null;
  var FLUSH_INTERVAL_MS = 5000;
  var MAX_BUFFER_SIZE = 50;

  // ── Helpers ────────────────────────────────────────────────────────
  function _uuid() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    });
  }

  function _isoNow() {
    return new Date().toISOString();
  }

  // ── Payload builder ────────────────────────────────────────────────
  function _buildPayload() {
    return {
      api_key: _config.apiKey || "",
      service_name: _config.serviceName || "browser-frontend",
      environment: _config.environment || "production",
      logs: _buffer.logs.splice(0),
      exceptions: _buffer.exceptions.splice(0),
      traces: _buffer.traces.splice(0),
      metrics: _buffer.metrics.splice(0),
      deployments: _buffer.deployments.splice(0),
    };
  }

  // ── Flush ──────────────────────────────────────────────────────────
  function _flush(useBeacon) {
    if (
      _buffer.logs.length === 0 &&
      _buffer.exceptions.length === 0 &&
      _buffer.traces.length === 0 &&
      _buffer.metrics.length === 0 &&
      _buffer.deployments.length === 0
    ) {
      return;
    }

    var payload = _buildPayload();
    var url = (_config.endpoint || "").replace(/\/+$/, "") + "/api/v1/sdk/ingest";
    var body = JSON.stringify(payload);

    if (useBeacon && navigator && typeof navigator.sendBeacon === "function") {
      var blob = new Blob([body], { type: "application/json" });
      navigator.sendBeacon(url, blob);
      return;
    }

    if (_originalFetch) {
      _originalFetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": _config.apiKey || "" },
        body: body,
        keepalive: true,
      }).catch(function () {
        /* swallow — best effort */
      });
    }
  }

  function _maybeFlush() {
    var total =
      _buffer.logs.length +
      _buffer.exceptions.length +
      _buffer.traces.length +
      _buffer.metrics.length;
    if (total >= MAX_BUFFER_SIZE) {
      _flush(false);
    }
  }

  // ── Error hooks ────────────────────────────────────────────────────
  function _hookErrors() {
    root.onerror = function (message, source, lineno, colno, error) {
      _buffer.exceptions.push({
        exception_type: (error && error.name) || "Error",
        message: String(message),
        stacktrace: (error && error.stack) || "",
        file_name: source || "",
        line_number: lineno || 0,
        handled: false,
        timestamp: _isoNow(),
      });
      _maybeFlush();
    };

    root.addEventListener("unhandledrejection", function (event) {
      var reason = event.reason || {};
      _buffer.exceptions.push({
        exception_type: (reason && reason.name) || "UnhandledPromiseRejection",
        message: String(reason.message || reason),
        stacktrace: (reason && reason.stack) || "",
        handled: false,
        timestamp: _isoNow(),
      });
      _maybeFlush();
    });
  }

  // ── Fetch monkey-patch ─────────────────────────────────────────────
  function _hookFetch() {
    if (typeof root.fetch !== "function") return;
    _originalFetch = root.fetch;

    root.fetch = function (input, init) {
      var traceId = _uuid();
      init = init || {};
      init.headers = init.headers || {};

      // Inject trace header on outgoing requests
      if (typeof init.headers.set === "function") {
        init.headers.set("x-trace-id", traceId);
      } else {
        init.headers["x-trace-id"] = traceId;
      }

      var url = typeof input === "string" ? input : (input && input.url) || "";
      var method = (init.method || "GET").toUpperCase();
      var startMs = Date.now();

      return _originalFetch.call(root, input, init).then(
        function (response) {
          var durationMs = Date.now() - startMs;
          var statusCode = response.status;

          if (statusCode >= 500) {
            _buffer.traces.push({
              trace_id: traceId,
              operation_name: method + " " + url,
              duration_ms: durationMs,
              status_code: statusCode,
              timestamp: _isoNow(),
            });
            _buffer.exceptions.push({
              exception_type: "HttpServerError",
              message: method + " " + url + " returned " + statusCode,
              handled: false,
              timestamp: _isoNow(),
              trace_id: traceId,
            });
          }
          _maybeFlush();
          return response;
        },
        function (error) {
          var durationMs = Date.now() - startMs;
          _buffer.traces.push({
            trace_id: traceId,
            operation_name: method + " " + url,
            duration_ms: durationMs,
            status_code: 0,
            timestamp: _isoNow(),
          });
          _buffer.exceptions.push({
            exception_type: "NetworkError",
            message: method + " " + url + " failed: " + String(error.message || error),
            handled: false,
            timestamp: _isoNow(),
            trace_id: traceId,
          });
          _maybeFlush();
          throw error;
        }
      );
    };
  }

  // ── Lifecycle hooks ────────────────────────────────────────────────
  function _hookLifecycle() {
    var flushOnExit = function () {
      _flush(true);
    };
    if (typeof document !== "undefined") {
      document.addEventListener("visibilitychange", function () {
        if (document.visibilityState === "hidden") flushOnExit();
      });
    }
    root.addEventListener("beforeunload", flushOnExit);
  }

  // ── Public API ─────────────────────────────────────────────────────
  SentinelAI.init = function (config) {
    _config = config || {};
    _hookErrors();
    _hookFetch();
    _hookLifecycle();
    _flushInterval = setInterval(function () {
      _flush(false);
    }, FLUSH_INTERVAL_MS);
  };

  /** Manually capture a log entry. */
  SentinelAI.log = function (level, message, attrs) {
    _buffer.logs.push({
      level: level || "INFO",
      message: message || "",
      attributes: attrs || {},
      timestamp: _isoNow(),
    });
    _maybeFlush();
  };

  /** Manually capture an exception. */
  SentinelAI.captureException = function (error) {
    _buffer.exceptions.push({
      exception_type: (error && error.name) || "Error",
      message: String((error && error.message) || error),
      stacktrace: (error && error.stack) || "",
      handled: true,
      timestamp: _isoNow(),
    });
    _maybeFlush();
  };

  /** Force an immediate flush. */
  SentinelAI.flush = function () {
    _flush(false);
  };

  root.SentinelAI = SentinelAI;
})(typeof window !== "undefined" ? window : globalThis);
