# TradingView paper alerts

TradingView cannot attach Olive's custom HMAC headers. Olive therefore exposes a separate
`POST /api/v1/signals/tradingview-alert` bridge that is disabled unless a dedicated secret is
configured. It runs only in `paper` or `staging`, removes the secret before persistence, and then
routes the sanitized signal through the existing HMAC authentication, replay protection,
validation, risk and automatic paper-execution services.

Set a unique value of at least 32 characters in the private staging environment:

```text
OLIVE_TRADINGVIEW_WEBHOOK_SECRET=replace-with-a-random-secret
```

The TradingView alert body must be valid JSON and include `webhook_secret`. A stable text signal
identifier is accepted and converted deterministically to Olive's UUID format. When `expiry` is
omitted, `expiry_seconds` is added to the supplied timestamp.

```json
{
  "webhook_secret": "replace-with-the-private-staging-secret",
  "schema_version": "1.0",
  "signal_id": "OLC-BTCUSD-{{timenow}}-long",
  "strategy_id": "OLC",
  "strategy_version": "1.0.0",
  "configuration_version": "smoke-1",
  "environment": "staging",
  "timestamp": "{{timenow}}",
  "expiry_seconds": 300,
  "venue": "COINBASE",
  "instrument": "BTC-USD",
  "direction": "LONG",
  "entry_price": "{{close}}",
  "reference_price": "{{close}}",
  "stop": "64000.00",
  "targets": ["67000.00", "68000.00"],
  "expected_rr": "2.0",
  "timeframe": "{{interval}}",
  "setup_score": "82.5",
  "regime": "NORMAL",
  "metadata": {"confidence": "0.75"}
}
```

The bridge must not be exposed directly from a personal workstation. Put a TLS-terminating,
rate-limited tunnel or reverse proxy in front of the API and expose only the bridge route. Never
place the HMAC secret or admin API key in TradingView.

## Temporary paper-testing tunnel

With staging already running, start the Docker-based testing tunnel:

```powershell
.\scripts\tradingview-tunnel-up.ps1
```

The command prints the complete HTTPS webhook URL. The tunnel first passes through a restricted
Nginx ingress that accepts only `POST /api/v1/signals/tradingview-alert`, limits request size and
rate, and returns `404` for every other route. The admin dashboard remains localhost-only.

This uses a Cloudflare Quick Tunnel for testing. Its random `trycloudflare.com` URL changes whenever
the tunnel restarts. Stop the public tunnel without stopping Olive staging by running:

```powershell
.\scripts\tradingview-tunnel-down.ps1
```

For continuous alerts, replace the Quick Tunnel with a named, account-managed tunnel and a stable
hostname after the paper-alert flow has been verified.
