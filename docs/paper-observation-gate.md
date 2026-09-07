# Paper observation gate

Olive tracks the defined validation period required before a formal live-readiness review. The gate
is evidence-only: it does not contain a control that can arm live routing or submit venue orders.

The default evidence requirements are 30 elapsed days and at least 20 paper executions for every
observed strategy version. Both values are configurable in staging:

- `OLIVE_PAPER_OBSERVATION_DAYS`
- `OLIVE_PAPER_OBSERVATION_MIN_TRADES`

`GET /api/v1/admin/paper-executions` returns the gate status, elapsed period, sample coverage, and
remaining blockers. `READY_FOR_REVIEW` means that the duration and sample requirements are met,
all observed strategies are green, and every paper execution is filled, protected, and reconciled.
It is an invitation to perform the separate formal readiness review, not approval for live capital.
