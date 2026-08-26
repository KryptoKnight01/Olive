# Admin paper-execution monitoring

`GET /api/v1/admin/paper-executions` provides a read-only operational view of automatic paper
executions. The response includes aggregate fill, protection, reconciliation, and realized-P&L
metrics followed by the newest execution records.

Each record joins the authoritative signal intake, single-trade risk decision, and paper pipeline
run. The bounded `limit` parameter defaults to 50 and accepts 1 through 200 records.

This endpoint does not mutate orders, risk settings, strategies, kill switches, or live-trading
state. Authentication and role enforcement remain required before exposing the admin API beyond
the local staging boundary.
