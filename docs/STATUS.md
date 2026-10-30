# Verification and remaining scope

This is a functional, tested first release, **not completion of the entire master specification** and not approved for live restaurant operation.

## Verified in this environment

- 28 Python tests: A–O scenario coverage, directed demo routing, along-route grouping, capacity, scheduled time, readiness delay, waiter release, returning-driver proposals, frozen work, explicit unassigned orders, provider failure, concurrent commits, stale plans, DST offsets, fallback, authentication/ownership, complete trip lifecycle, release and late return.
- Five additional mocked Google-provider checks are included in the 28 Python tests: asymmetric results, incomplete matrices, element errors, explicit unreachable routes and quota exhaustion. These do not replace live-provider validation.
- Four Vitest tests for London time formatting, navigation links, same-origin JSON calls and server rejection handling. These are utility tests, not UI component or browser interaction tests.
- Next.js production build and TypeScript validation.
- Alembic upgrade and demo seed on SQLite.
- Live HTTP smoke test of the Next.js page and proxy, login, planning, commit, departure, delivery completion, return and analytics using a disposable SQLite database.

## Implemented but not fully verified

- PostgreSQL/Redis/Celery Docker Compose environment: Docker is unavailable here; PostgreSQL concurrency and worker health must be tested on a Docker-capable machine.
- Google Routes matrix adapter: no API credentials; no live provider test. It uses explicitly labelled traffic-unaware DRIVE requests, rejects incomplete/error elements, retries transient failures and makes no synthetic substitution.
- Responsive interface and mobile trip controls: compilation passed; no browser-based visual, accessibility, component or Playwright end-to-end verification was available.
- WebSocket revision feed and queued Celery planning task: present but not integrated into dashboard event-driven reoptimisation.

## Acceptance gaps

- Address autocomplete, geocoding verification, delivery-area validation and provider road geometry/map display.
- Live/predicted traffic, departure-time-specific matrices, quota telemetry, permitted caching policies and alternate production providers.
- Multi-restaurant tenancy, alternative start/end depots, no-return last trips and richer shifts/break scheduling.
- Manual route grouping/reordering/reassignment UI, automatic dispatch and debounced event-driven background planning.
- Driver invitation/account management UI, password reset/revocation, delivery delay reports, complete PWA install/offline workflow. A manifest alone is not a complete PWA; no offline mutation claims are made.
- Data retention/anonymisation, complete role administration, production access logging/error monitoring, durable metrics, operational alerting, provider budgeting.
- Most requested analytics, date filters, historical baseline comparison and measured time savings.
- Fully normalised business columns and version-frozen schema migration definitions, PostgreSQL concurrency/load verification, production security review.
- Fully coalesced same-address stops; currently separate service times and completion records.
- Full schema validation on all frontend forms: backend Pydantic is authoritative; login uses Hook Form/Zod.

The complete original requirements are retained in `requirements.md`. Do not infer completion from a UI control, a Compose file, or passing unit tests. Add verified implementation incrementally on this branch before requesting a merge.
