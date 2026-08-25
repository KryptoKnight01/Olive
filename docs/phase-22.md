# Phase 22 — Kill Switch Framework

Kill switches support global, strategy, asset, asset-class, account, and venue scopes with pause-entry, cancel-order, close-position, and emergency-halt actions. Pausing is distinct from liquidation. Scoped active states deny new entries deterministically; global emergency halt requires an administrator.

Migration `20260825_0023` stores active states and reasons. Tests cover authorization, scoped entry blocking, emergency-halt restrictions, configuration dual approval, immutability, and audit reconstruction.

Phase 23 introduces strategy performance monitoring.
