# Phase 26 — Shadow Live Mode

Shadow mode processes a live-like signal and calculates a hypothetical venue fill without
transmitting an order. Every result is marked `SHADOW_ONLY` and `sent_to_venue` is always
false, providing measurable execution evidence without capital exposure.
