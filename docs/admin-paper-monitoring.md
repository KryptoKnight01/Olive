# Admin paper-execution monitoring

`GET /api/v1/admin/paper-executions` provides a read-only operational view of automatic paper
executions. The response includes aggregate fill, protection, reconciliation, and realized-P&L
metrics followed by the newest execution records.

The response also groups the complete observation history by strategy code and version. Each
strategy summary reports execution, fill, protection, reconciliation, realized-P&L, and latest
activity metrics so operators can compare concurrent TradingView strategies without mixing their
results.

Each record joins the authoritative signal intake, single-trade risk decision, and paper pipeline
run. The bounded `limit` parameter defaults to 50 and accepts 1 through 200 records.

This endpoint does not mutate orders, risk settings, strategies, kill switches, or live-trading
state. Authentication and role enforcement remain required before exposing the admin API beyond
the local staging boundary.
