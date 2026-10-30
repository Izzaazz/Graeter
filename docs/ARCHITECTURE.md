# Architecture and implementation plan

## Repository and access assessment

The connected repository was `Izzaazz/Graeter`, initially a single nine-byte README on `main`, commit `9fc5064`. No application or AGENTS.md existed. The original README title is retained. Work is isolated to `development/delivery-optimiser`.

Read/clone, local editing, execution and tests are available. Creating the remote development branch succeeded through the GitHub connector. Terminal HTTPS push failed because terminal Git has no credentials. Changes are therefore committed to the remote branch through the connector's Git database operations, with an expected-head check. No main-branch update is authorised or performed.

## Selected architecture

- Next.js/React/TypeScript, Tailwind, TanStack Query; React Hook Form/Zod for login.
- Same-origin Next.js HTTP proxy to FastAPI. HttpOnly session cookie, server-side roles.
- Independent Pydantic domain contracts; provider-specific payloads confined to `routing.py`.
- SQLAlchemy with PostgreSQL in Compose, SQLite for portable execution and tests.
- Alembic initial schema; relational user/driver/order/trip/stop keys, active-driver and order-assignment uniqueness. Domain attributes are currently JSON payloads. Full analytical normalization is deferred.
- OR-Tools CP-SAT selects non-overlapping feasible routes for a bounded rolling-horizon VRPTW. The solver does not call routing APIs.
- Redis/Celery queued planner is available as a task; the dashboard currently uses synchronous bounded planning. It does not automatically schedule the worker.

## Implementation sequence and current status

1. Repository/access inspection and assumptions: completed.
2. Domain and simulated directed road provider: implemented and tested.
3. Feasible-route construction and OR-Tools selection: implemented and tested.
4. Persistence, authentication and transactional dispatch: implemented; SQLite tests pass.
5. Dashboard and mobile trip workflow: built/typechecked; live HTTP proxy smoke tested.
6. Google matrix adapter and Compose: implemented, not live-provider or Docker verified.
7. Production hardening, richer maps, automated planning and remaining acceptance items: pending. See STATUS.md.

## Decisions and assumptions

One restaurant per database in this release. Drivers start and return at its depot. Explicit UTC offsets are mandatory; local ambiguous DST values are rejected. UI displays Europe/London. Estimated driver return never changes confirmed driver state. Waiters require administrator release and a return-by time. Returning drivers can appear only in provisional proposals.

Readiness, load, orders-per-trip, maximum hold/transit time, shift/return-by and route duration are hard limits. Deadlines are soft: missed deadlines are shown explicitly. Food-readiness estimates produce provisional routes; only confirmed ready orders can be committed. There is no automatic dispatch.

## Solver strategy and limitations

Generate up to 4,000 ordered candidates per driver from the 12 earliest-deadline eligible orders. A shared generation budget is apportioned among drivers. Validate each route using directed provider costs, depot loading, scheduled earliest arrivals, preparation and freshness, capacity, shift and return limits. A driver has at most one proposed next trip per solve; subsequent trips are replanned after physical return.

OR-Tools CP-SAT performs weighted set packing over these feasible routes. Maximise assigned order count first: the assignment reward exceeds the sum of all candidate costs. Secondary cost is 1000 × lateness seconds, plus total driving time, priority-weighted arrival wait and departure wait. This secondary objective is weighted, not fully lexicographic. It does not guarantee minimum number of late orders. Feasible route alternatives omitted by the candidate bound may be better; never claim a globally optimal plan. On solver timeout without a feasible result, use deterministic greedy selection from the same validated candidates. Missing provider data never invokes synthetic routing in production.

One candidate can contain separate order records for the same physical address; the inter-order road cost is zero, but each order currently incurs its own handover time. This is conservative and not a fully coalesced shared-stop model.

API guardrail: at most 100 pending orders and 30 drivers per request. Deployment sizing and provider-call time need further load testing. Google calls can outlast the solver bound; the bound applies to optimisation, not end-to-end request time.

## Concurrency and lifecycle

A global monotonic database revision serialises business mutations using `UPDATE ... WHERE value = expected`. Plans retain their snapshot revision. Commit checks the revision, 120-second expiry, actual readiness and driver state, revalidates with fresh provider data and then writes trip/stops atomically. Database unique constraints provide a second defence against overlap. After committing one route, regenerate the plan before committing another.

Commit idempotency keys are scoped to a user and bound to plan/route. Departure, matching stop outcomes and return retries are idempotent. Active trips are frozen. Reserved trips can be explicitly released by staff before collection; orders return to the ready queue. Collected trips cannot be released. Completion requires the planned stop order and the scheduled window's lower bound. Actual timestamps drive analytics.

A global revision is intentionally conservative: unrelated changes can invalidate a plan. Provider revalidation currently holds the commit transaction open; production scaling should move this outside a short final lock with a second revision check.

## Main contracts

`/auth/login`, `/auth/me`, `/auth/logout`; `/state`; `/settings`; `/orders`; `/drivers`; `/plans`; `/plans/{id}/commit`; `/trips/{id}/depart`, `/release`, `/return`; `/trips/{id}/stops/{order}/complete`; `/analytics`, `/analytics/export`; `/health`; `/events`. See generated `/docs` for exact schemas. The WebSocket emits revision numbers only; the dashboard currently polls.

## Security boundary

Scrypt passwords; expiring HMAC sessions; strict SameSite cookies; origin checks; driver ownership enforced server-side; driver state responses exclude other drivers' orders. No customer payloads in audit events. Production requires HTTPS origin and secure cookies. Secrets are server-side environment variables. Current per-process login rate limiting, session revocation, audit retention, tenant isolation, deletion policy, production database privileges and security review need further work before public deployment.
