# Operator guide

1. Start the demo and sign in as `manager` with your configured `DEMO_PASSWORD`.
2. Review Orders. The seed creates four ready orders and two drivers relative to seed time. If data is old, release any reserved trip, then delay/mark ready or add fresh orders; the seed never overwrites existing data.
3. Add orders with a simulated node. Street labels do not change demo travel times. Scheduled inputs require a timestamp such as `2026-10-30T19:30:00+00:00`; choose the intended offset at clock changes.
4. Drivers shows today’s availability. Only an administrator can add staff, change availability or release a waiter. Driver count is not hardcoded.
5. Generate routes. Review lateness, sequence, departure/return and provisional status. Commit one ready trip, then regenerate for the next. Any business change invalidates old proposals.
6. Confirm collection and departure when loading completes. The server rechecks the route before departure. If a reserved route is no longer feasible, release it, fix the orders/staff constraints and regenerate.
7. Complete each stop in order, or record a failed attempt. Confirm physical return; the ETA never does this automatically.
8. Analytics uses actual recorded timestamps. CSV export contains no address/name/phone columns.

# Driver guide

Sign in as `driver1` or `driver2` in the demo. Only your active trip and its order details appear. Confirm collection, open external Google Maps navigation if desired, record delivered/failed, then confirm return. Demo navigation coordinates are illustrative; do not perform real deliveries from demo routes.

Wait for the server's confirmation after each action. On connection errors the UI retains last loaded data and shows an error; it does not claim an offline delivery was saved. Refresh and retry the same lifecycle action when connectivity returns.

# Production provider setup

Create a Google Cloud project with billing and Routes API enabled. Put a restricted server key in `GOOGLE_MAPS_API_KEY`; never use a frontend key for this backend. Review current provider terms, quota limits and prices before enabling. Set the restaurant's verified coordinates in Settings, select Google, and use externally verified coordinates for orders. The adapter requests DRIVE / TRAFFIC_UNAWARE. It does not claim live traffic, closures or geocoding. There is no live-provider integration test until credentials are supplied.

Reference endpoints used by the adapter:
- https://developers.google.com/maps/documentation/routes/compute_route_matrix
- https://developers.google.com/maps/documentation/routes/reference/rest/v2/TopLevel/computeRouteMatrix

Production rollout remains gated on the items in STATUS.md, particularly actual routing validation, database concurrency, browser QA and security/retention work.

# Backups and recovery

For PostgreSQL, run `docker compose exec -T db pg_dump -U dispatch -Fc dispatch > dispatch.dump`. Store encrypted backups outside the application host with limited retention/access. Rehearse restore to an isolated database with `pg_restore` before relying on backups. Restore the database and secrets together, inspect open trips, and reconcile drivers/orders with staff before resuming dispatch. Never automatically assume restored active drivers have returned.

For local SQLite tests/demos, stop the API before copying the database. Do not use a disposable test database as an operational store. `docker compose down -v` deletes all development database data; do not use it on a live instance.

# Writable development environment

The GitHub connector successfully writes this branch, but terminal Git here lacks credentials. On your own development computer, clone the repository, check out `development/delivery-optimiser`, and authenticate terminal Git through GitHub CLI (`gh auth login`, then `gh auth setup-git`) or an SSH key authorised on your GitHub account. Open that checkout in your coding environment. Use `git push -u origin development/delivery-optimiser`; never put access tokens in source files or prompts. Repository access through a chat connector does not automatically authenticate terminal Git.
