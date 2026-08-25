# Olive Mobile

This mobile client boundary is intentionally monitoring-first. It consumes the authenticated
mobile snapshot and control contracts implemented in `olive.operations`. Strategy pause and
emergency halt require MFA and authorized roles; complex configuration remains in the web app.

Native iOS/Android packaging and store distribution require deployment credentials and are
environment-specific release activities, not part of the automated repository acceptance test.
