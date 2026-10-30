# MASTER DEVELOPMENT PROMPT — INTELLIGENT RESTAURANT DELIVERY ROUTE OPTIMISATION PLATFORM

## 1. YOUR ROLE AND OBJECTIVE

You are a principal software architect, full-stack engineer, mathematical optimisation specialist, logistics systems designer, UX/UI engineer, database architect, DevOps engineer and senior quality assurance engineer.

You have extensive experience with:

- Python, TypeScript, React, Next.js and FastAPI.
- Operations research, combinatorial optimisation and Google OR-Tools.
- Vehicle Routing Problems (VRP), Vehicle Routing Problems with Time Windows (VRPTW) and dynamic vehicle routing.
- Geospatial systems, road networks, road restrictions, distance matrices and traffic-aware routing.
- Real-time event-driven applications, database transactions and distributed systems.
- Building secure, maintainable, production-ready applications.

Your task is to **design, build, test and document a complete intelligent restaurant delivery dispatch and route optimisation web application**.

The system must automatically determine which delivery orders should be grouped, which driver should deliver them, their optimal stop sequence and when each driver should depart.

The application must work under continuously changing real-world restaurant conditions.

Do not merely design a theoretical route optimiser. Build an operational restaurant dispatch platform that eliminates the need for experienced employees to manually group deliveries by recognising street names, postcode areas and driving directions.

**Primary objective: deliver customer orders as quickly and punctually as reasonably possible while minimising inefficient journeys, excessive food waiting times and unnecessary driver usage.**

Implement a functional application, not a static prototype, presentation, mock dashboard or collection of disconnected code examples.

---

## 2. BUSINESS CONTEXT

A takeaway restaurant accepts delivery orders throughout the day.

The restaurant hires a variable number of delivery drivers depending on the day, expected demand and staffing availability.

For example:

- Monday may have 3 drivers.
- Friday may have 8 drivers.
- Saturday may have 12 drivers.
- During quieter periods, only 1 or 2 drivers may be available.
- Some employees normally work as waiters but can temporarily perform deliveries when authorised.

Not every driver is simultaneously available. Some may be at the restaurant, delivering orders, returning, taking breaks or finishing their shifts.

The restaurant receives deliveries at unpredictable times. Orders have different preparation times and requested delivery deadlines.

Some customers order food for immediate delivery. Others order in advance and request delivery at a particular time.

Currently, experienced restaurant employees manually group deliveries according to:

1. Geographical proximity.
2. Knowledge of street names and neighbourhoods.
3. Which roads drivers typically use.
4. Whether a delivery lies along another delivery's route.
5. The number of drivers available.
6. How urgently each delivery needs to leave.
7. How many deliveries a driver can reasonably take.

This creates a bottleneck when knowledgeable employees are unavailable.

The application must replicate and significantly improve this decision-making using real road-network information, journey times, delivery deadlines, food preparation readiness, driver availability and optimisation algorithms.

### Essential business principle

**Do not group deliveries solely according to distance, postcode or neighbourhood.**

Two addresses can be geographically close but require a long detour because of one-way systems, rivers, restricted turns or disconnected roads.

Conversely, two deliveries can be several miles apart and belong to different postcode districts but still be efficient to group if one is naturally encountered on the road to the other.

The application must discover these opportunities automatically.

---

## 3. MANDATORY TECHNOLOGY STACK

Use the following default architecture unless a clearly documented technical reason justifies changing it.

### Frontend
- Next.js with React and TypeScript.
- Tailwind CSS for styling.
- Accessible, reusable component library such as shadcn/ui.
- TanStack Query for server-state management.
- React Hook Form with Zod for form validation.
- Responsive desktop, tablet and mobile interfaces.
- Progressive Web App capabilities for the driver interface.

### Backend
- Python with FastAPI.
- Pydantic for request and response validation.
- SQLAlchemy 2.x for database access.
- Alembic for database migrations.
- OpenAPI specifications and automatically generated API documentation.
- WebSockets for real-time updates.

### Optimisation
- Google OR-Tools as the primary optimisation engine.
- Use VRPTW modelling, capacity constraints, vehicle availability, service durations and appropriate objective functions.
- Use dynamic reoptimisation for changing delivery and driver conditions.
- Implement bounded solver execution times and deterministic fallback strategies.

### Mapping and navigation
- Google Maps Platform as the preferred production mapping and routing provider.
- Google Routes API for routes and travel-time matrices.
- An appropriate address search/geocoding provider for resolving addresses.
- Google Maps JavaScript API for displaying routes and driver locations.

The application must support an interchangeable routing-provider interface so that alternative providers, such as GraphHopper, can be configured without rewriting the optimisation engine.

Respect the actual capabilities, quotas, service terms, geographic restrictions, attribution requirements, permitted storage duration and licensing restrictions of the selected provider.

Do not combine map data from incompatible providers in ways prohibited by their licences.

### Database
- PostgreSQL.
- PostGIS for geospatial operations where appropriate.
- Indexed, relational data structures with appropriate foreign keys and constraints.

### Background processing
- Redis.
- Celery workers for computationally expensive optimisation and other asynchronous tasks.

### Deployment
- Docker and Docker Compose.
- Environment-based configuration.
- Separate development, testing and production settings.
- Secure management of API keys and secrets.

### Testing
- pytest for Python.
- Vitest and React Testing Library for frontend components.
- Playwright for end-to-end tests.

Follow current stable, compatible package versions. Verify actual package APIs and avoid deprecated or imaginary functions.

Do not introduce additional services or microservices unless they provide a clear architectural benefit.

---

## 4. CORE APPLICATION REQUIREMENTS

### 4.1 Configurable restaurant starting location

The system must support any valid restaurant address or geographical location.

On initial setup, an administrator can:

- Enter the restaurant's full address and UK postcode.
- Use address autocomplete.
- Select or adjust the location on a map.
- Save verified latitude and longitude coordinates.
- Configure a default delivery area.
- Configure restaurant opening hours.
- Configure default delivery preparation and handling times.
- Configure delivery service policies.

The restaurant must not be hardcoded to a particular city or postcode.

Design the database and domain model so multiple restaurants or branches can be supported later.

A driver should normally begin and end a delivery trip at the restaurant, but configurable alternative starts and ends must also be possible.

Support situations where a driver starts from another known position, where an authorised driver may begin at a different depot, or where a driver does not need to return after their final delivery.

### 4.2 Delivery order management

Every delivery order must include the following information.

**Required fields**

- Unique internal order ID.
- Customer delivery address.
- Validated geographical coordinates.
- Time the order was received.
- Delivery type: ASAP or scheduled.
- Requested delivery time or time window.
- Order preparation status.
- Estimated food-ready time.
- Order status.

**Optional and configurable fields**

- External order reference.
- Customer name.
- Customer telephone number.
- Order source, such as telephone, website, Uber Eats, Deliveroo or Just Eat.
- Number of bags or capacity units.
- Special delivery instructions.
- Priority or business urgency.
- Estimated handover/service duration.
- Kitchen preparation estimate.
- Food freshness constraints.
- Delivery notes.
- Customer access restrictions or special requirements.

Store the order-received time separately from the food-ready time and the promised delivery time.

These are different concepts and must not be confused.

An order should move through an appropriate status lifecycle:

Received → Preparing → Ready → Assigned → Collected → Out for Delivery → Delivered.

Also support Cancelled and Failed Delivery with valid transition rules.

Prevent accidental duplicate orders and invalid status transitions.

### 4.3 ASAP and scheduled deliveries

The application must distinguish immediate deliveries from scheduled deliveries.

**ASAP deliveries**

For immediate deliveries:

- Estimate the earliest feasible delivery time.
- Use the restaurant's configurable delivery promise or actual promised deadline.
- Consider the order age and food-ready time.
- Prioritise orders approaching or exceeding their deadlines.
- Prevent food sitting unnecessarily after preparation.
- Avoid excessive batching merely to reduce driver mileage.

**Scheduled deliveries**

For scheduled orders:

- Store the requested delivery time.
- Support a configurable permitted arrival window.
- Prevent the optimizer from planning delivery earlier than the allowed earliest arrival.
- Aim to deliver within the promised time window.
- Account for preparation time, pickup time, driving time and unloading time.
- Plan a suitable driver departure time.
- Avoid preparing or dispatching an order unnecessarily early.

For example, if a customer has requested delivery at 19:30 and the allowed delivery window is 19:25–19:35, calculate an appropriate departure and delivery sequence.

If the order cannot reasonably be delivered within that window, show an explicit warning.

Never silently change a scheduled deadline to make a route appear feasible.

### 4.4 Food preparation and freshness

The optimisation engine must account for kitchen readiness.

An order cannot be picked up before it is ready.

Each order should support:

- Estimated ready time.
- Actual ready time.
- Preparation status.
- Pickup time.
- Maximum preferred food-holding time before collection.
- Maximum preferred time between collection and delivery.

Treat kitchen preparation estimates as estimates rather than guaranteed facts.

If preparation is delayed, update the dispatch plan.

Support configurable freshness warnings for food that has waited too long.

Avoid grouping orders if the resulting route causes an unacceptable delivery delay for an order that was ready significantly earlier.

Hard food-handling requirements must remain hard constraints. Softer quality targets may be represented as optimisation penalties.

---

## 5. DRIVER AND STAFF MANAGEMENT

### 5.1 Dynamic driver availability

The number of drivers working and the number currently available must be independent values.

Provide a daily staffing interface where authorised users can:

- Add drivers to a shift.
- Remove drivers from future assignments.
- Mark drivers as available.
- Mark drivers as unavailable.
- Record breaks.
- Record expected shift end times.
- View drivers who are currently on a delivery.
- View drivers expected to return.
- Temporarily pause dispatch eligibility.
- Set driver-specific vehicle capacities.

Use driver states such as:

OFF_DUTY, AVAILABLE, RESERVED, LOADING, ON_DELIVERY, RETURNING, ON_BREAK and UNAVAILABLE.

Create clearly defined, validated transitions.

A driver cannot be assigned to two overlapping active trips.

### 5.2 Drivers currently on the road

The system must distinguish:

1. Drivers physically available at the restaurant.
2. Drivers on delivery trips.
3. Drivers returning to the restaurant.
4. Drivers expected to become available in the future.

For drivers on delivery trips, show:

- Currently assigned route.
- Remaining stops.
- Current trip status.
- Estimated completion time.
- Estimated return time.
- Last confirmed location, if available.
- Whether their availability estimate is verified or predicted.

The system may provisionally plan future deliveries for a returning driver, but must not mark that driver physically available until their return is confirmed.

Do not assume a driver has returned solely because the estimated return time has passed.

### 5.3 Waiters who can become drivers

Some waiters can also perform deliveries.

Implement a staff capability model rather than treating every employee as either permanently a waiter or permanently a driver.

A waiter may have:

- Normal role: waiter.
- Additional capability: delivery driver.
- Currently working in restaurant: true.
- Available for delivery: false.
- Authorised to leave restaurant: false.

An authorised manager can release an eligible waiter for deliveries.

Only after this change may the optimiser assign deliveries to them.

Support:

- Temporary delivery availability.
- Configurable return-by time.
- Maximum allowed trip duration.
- Staff role restrictions.
- Returning to waiter duties after the trip.
- Warnings when using a waiter would leave insufficient restaurant staff.

Do not automatically send waiters out merely because they technically have driving capability.

### 5.4 Driver-specific constraints

Support individually configurable:

- Maximum orders per trip.
- Maximum bags or load units.
- Preferred maximum route duration.
- Shift end time.
- Scheduled breaks.
- Travel mode and vehicle type where supported.
- Optional delivery area restrictions.
- Whether returning to the restaurant is required.

Provide sensible defaults that administrators can change.

A driver's trip may contain multiple deliveries, but the number must be determined by actual constraints and route efficiency, not a universally hardcoded number.

---

## 6. REAL-WORLD ROAD-NETWORK ROUTING

This is a fundamental requirement.

### 6.1 Do not use straight-line distance as the actual driving cost

Do not use Euclidean distance, latitude/longitude differences or Haversine distance as the final basis for assigning delivery routes.

Those calculations may be used for preliminary candidate filtering, but the final optimisation must use journey-time estimates produced by a real road-routing engine.

### 6.2 Road restrictions

When supported by the chosen provider and its underlying map data, account for:

- One-way roads.
- Prohibited turns.
- Roundabouts.
- Road directions.
- Access restrictions.
- Restricted roads.
- Motorways and motorway access points.
- Bridges and tunnels.
- Disconnected roads.
- Applicable road closures.
- Legal vehicle access.
- Driving time and distance.
- Traffic conditions.
- Different departure times.

The system must avoid creating illegal or physically impossible routes.

Do not claim that every temporary road closure or road restriction is available unless the configured provider actually supports it.

### 6.3 Direction-dependent travel times

The time from address A to address B may differ from the time from B to A.

Use a directed, potentially asymmetric travel-time matrix.

For instance:

A → B: 4 minutes.

B → A: 9 minutes.

This may occur because of one-way roads and turn restrictions.

The optimiser must preserve this distinction.

### 6.4 Traffic awareness

Where traffic-aware routing is available:

- Obtain travel-time estimates appropriate to planned departure times.
- Reflect changing traffic where feasible.
- Update ETAs before dispatch.
- Recalculate affected routes when material changes occur.
- Avoid excessive API requests.
- Show when an estimate was last updated.

Prefer reliable provider-supported traffic modelling rather than inventing traffic values.

Account for the distinction between live traffic, predicted traffic and historical or free-flow estimates.

When traffic data is unavailable, display that limitation.

### 6.5 Along-the-route delivery grouping

The optimiser must identify when a delivery is a natural intermediate stop along another delivery's route.

Example:

- Delivery A is 15 minutes from the restaurant.
- Delivery B is 9 minutes from the restaurant.
- Delivery B lies close to the road normally taken to reach Delivery A.
- The additional journey time for visiting B before A is only 2 minutes.

The system should consider grouping B and A even if they belong to different neighbourhoods or postcode districts.

Evaluate incremental route cost, delivery deadlines, service time and order freshness.

Do not merely use an arbitrary straight-line radius or postcode prefix.

Conversely, reject grouping when apparently nearby destinations require significant detours.

### 6.6 Travel-time matrix construction

Build a dedicated module responsible for:

- Obtaining travel-time matrices.
- Obtaining road distance matrices.
- Handling asymmetric routes.
- Respecting provider request-size limits.
- Batching matrix requests correctly.
- Handling API quota exhaustion.
- Retrying transient failures with backoff.
- Recording the source and freshness of estimates.
- Supporting provider-specific permitted caching.
- Distinguishing unavailable routes from API errors.

The optimisation engine must receive a validated matrix rather than making direct map API calls itself.

Do not substitute fabricated road times if the provider fails.

Use a clearly labelled demo provider for local development and automated testing, without misrepresenting simulated data as live route information.

---

## 7. ADVANCED DELIVERY OPTIMISATION ENGINE

### 7.1 Problem formulation

Model the dispatch problem as a dynamic, multi-vehicle routing and scheduling problem with time windows.

Account for:

- Variable fleet size.
- Different driver availability times.
- Multiple delivery destinations.
- Food-ready times.
- ASAP delivery deadlines.
- Scheduled delivery windows.
- Vehicle capacities.
- Driver shift restrictions.
- Stop service times.
- Return-to-restaurant requirements.
- Travel-time matrices.
- Driver eligibility.
- Existing assignments.
- New orders arriving during active operations.

Use Google OR-Tools as the main solver.

Recognise that this is more complex than a basic shortest-path problem or the Travelling Salesperson Problem.

Implement a practical rolling-horizon optimisation approach and explicitly document the modelling assumptions.

### 7.2 Optimisation priorities

Use a configurable, carefully designed objective system.

Default priority order:

1. Preserve safety, legality, order readiness, capacities, staff eligibility and other hard constraints.
2. Avoid leaving deliverable orders unassigned when feasible resources are available.
3. Minimise missed promised delivery deadlines.
4. Minimise the severity and number of late deliveries.
5. Minimise excessive food holding and in-transit times.
6. Minimise unnecessary customer waiting time.
7. Minimise total travel time.
8. Minimise unnecessary travel distance.
9. Reduce unnecessary vehicle trips and driver operating time.
10. Prefer sensible driver workload distribution when higher-priority service objectives are comparable.

Do not simply optimise total mileage.

Use lexicographic optimisation or appropriately scaled penalties where practical. Document the weighting system and demonstrate that lower-priority fuel savings cannot override critical service constraints.

Hard constraints must never be violated silently.

When there is no completely feasible plan, return the best practical alternative together with explicit violations, warnings and unassigned orders.

### 7.3 Automatic delivery grouping

The system must determine automatically:

- Which orders belong on the same trip.
- How many orders each driver should take.
- Which order should be delivered first.
- When each trip should start.
- Whether a delivery should wait for another order.
- Whether a currently available driver should leave immediately.
- Whether a returning driver can reasonably handle a future order.
- Whether another available driver would produce a better outcome.

A route with 4 deliveries may be better than four separate routes, but only when deadlines, travel times, service durations and food quality permit.

Similarly, a single urgent delivery must be dispatched independently when necessary.

### 7.4 Intelligent departure timing

The system must optimise departure timing, not only route sequence.

For example:

- Driver A is available now.
- Order 1 is ready now.
- Order 2 will be ready in 4 minutes.
- Both orders are on a highly compatible route.
- Waiting 4 minutes may save an entire additional journey.

The optimiser should compare waiting against the consequences for customer delivery times and food freshness.

If waiting would cause Order 1 to become late, recommend immediate dispatch instead.

Implement configurable maximum batching waits and departure deadlines.

Distinguish a route that is ready to dispatch immediately from a provisional route awaiting food or driver availability.

### 7.5 Driver allocation

Select drivers according to availability and feasibility.

The system must not always allocate orders to the first available driver.

Consider whether:

- Another driver has a more suitable availability time.
- One driver's shift ends too soon.
- A waiter has a restricted return time.
- One driver has a lower capacity.
- An available driver should be reserved for an urgent order when doing so is justified by current known demand.

Never justify delaying current orders based on speculative future orders unless the policy explicitly permits it and the resulting risk is bounded.

### 7.6 Multi-trip operations

A driver should be able to perform multiple successive delivery trips during one shift.

After returning to the restaurant, they become eligible for new assignments.

Track trips separately from drivers and shifts.

Support a rolling planning horizon where future trips can be proposed.

Avoid incorrectly assuming that a single driver's entire shift is one continuous route containing every delivery of the evening.

The optimiser should focus on immediately executable assignments and feasible near-term plans, while allowing later reoptimisation.

### 7.7 Route freezing and operational stability

Once a driver has accepted or started a trip, the application must protect active commitments.

Default rules:

- Delivered stops can never be changed.
- Collected orders remain associated with the driver unless an explicit controlled exception is supported.
- Active trips must not have their stops reassigned automatically.
- Uncollected orders may be reassigned when safe and authorised.
- Proposed routes may be recalculated freely.
- Confirmed but not yet departed routes require explicit rules for modification.

Route recalculation must not cause continual rearrangement of assignments that confuses staff.

Introduce route versions and appropriate assignment locking.

### 7.8 Infeasible orders and exceptional scenarios

Explicitly handle:

- No drivers available.
- All drivers currently out.
- A delivery deadline that is already impossible.
- Food not ready.
- An invalid delivery address.
- An unreachable destination.
- An order exceeding every available vehicle's capacity.
- Driver ending shift.
- Driver delayed.
- Driver suddenly becoming unavailable.
- An order being cancelled after assignment.
- An order being cancelled while the driver is already on the road.
- Provider API errors.
- Solver timeout.
- New urgent orders arriving.
- Scheduled orders conflicting with ASAP deliveries.

Never silently discard deliveries.

Display the reason an order could not be assigned, plus an actionable recommendation.

### 7.9 Optimisation performance

Optimisation must be fast enough for restaurant operations.

Implement:

- Configurable solver execution time limits.
- Warm-starting from an existing route plan where practical.
- Reuse of valid route information.
- Candidate filtering using safe lower bounds or preliminary estimates.
- Efficient matrix batching.
- Background optimisation jobs.
- Timeouts and cancellation handling.
- A deterministic fallback heuristic for cases where the main solver fails or times out.

The fallback must also respect hard constraints.

Measure optimisation quality and time.

Do not promise mathematically optimal solutions when only feasible or heuristic solutions have been found.

---

## 8. CONTINUOUS REAL-TIME REOPTIMISATION

The application must respond intelligently to operational events.

Events should include:

- New delivery received.
- Food marked ready.
- Food preparation delayed.
- Driver becomes available.
- Driver starts a route.
- Driver completes a delivery.
- Driver returns.
- Driver begins a break.
- Driver becomes unavailable.
- Existing order cancelled.
- Delivery deadline changed.
- Relevant travel-time estimates materially changed.

Implement a rolling-horizon optimisation service.

Use event-driven triggers with debouncing and configurable periodic refreshes to prevent excessive calculations.

Do not blindly rerun a costly full optimisation after every tiny change.

Separate:

1. Calculating an optimisation proposal.
2. Reviewing the proposal.
3. Committing assignments.
4. Dispatching a trip.
5. Executing and completing the trip.

Provide both automatic and human-confirmed dispatch modes.

Use database transactions, idempotency and optimistic concurrency control to prevent two dispatchers or background tasks from assigning the same order twice.

---

## 9. DISPATCH DASHBOARD AND USER EXPERIENCE

Create a professional, highly usable restaurant operations dashboard.

It should be designed for employees working under time pressure, not technical users.

Use clear, high-contrast typography, large interactive controls, easily readable order numbers and responsive layouts.

### 9.1 Main dashboard

Display key metrics such as:

- Active delivery orders.
- Orders awaiting preparation.
- Orders ready for dispatch.
- Orders assigned to drivers.
- Drivers available now.
- Drivers currently on delivery.
- Drivers expected back.
- Orders approaching deadlines.
- Late or at-risk orders.
- Next recommended dispatch.

Use meaningful colour indicators accompanied by readable text and icons.

Do not rely on colour alone to communicate urgency.

### 9.2 Interactive map

Display:

- Restaurant location.
- Delivery destinations.
- Assigned route paths.
- Driver-specific route colours.
- Numbered delivery stops.
- Estimated departure and arrival times.
- Available current driver positions where authorised GPS information exists.
- Selected route information.
- Warning indicators for problematic deliveries.

Allow map filtering by driver, route and order status.

Ensure the displayed route follows actual provider-supplied road geometry rather than drawing straight lines between destinations.

### 9.3 Orders panel

Provide a searchable, sortable table showing:

- Order number.
- Delivery address.
- Time received.
- Food readiness.
- Due time.
- Time remaining.
- Assigned driver.
- Planned departure.
- Predicted delivery time.
- Delivery status.
- Urgency.

Support quick entry and editing.

Highlight important orders prominently.

### 9.4 Recommended dispatch panel

For each recommended trip, show:

- Driver name.
- Number of orders.
- Order IDs.
- Addresses.
- Recommended delivery sequence.
- Proposed departure time.
- Total driving time.
- Estimated complete-trip duration.
- Estimated return time.
- Route distance.
- Expected delivery time at each stop.
- Deadline compliance.
- Reasons for warnings.

Include an understandable explanation of the route recommendation.

For example:

"Orders 104 and 109 share an efficient outbound route. Delivering 109 first adds approximately 2 minutes and both orders remain within their delivery windows."

The explanation must be based on actual optimisation outputs, not invented claims.

### 9.5 Dispatcher actions

Support:

- Generate recommended routes.
- Preview proposed assignments.
- Accept a route.
- Dispatch a route.
- Reoptimise pending orders.
- Select another eligible driver.
- Manually group or ungroup orders.
- Change stop order.
- Mark an order urgent.
- Mark a driver unavailable.
- Add an emergency driver.
- Release an eligible waiter for delivery.
- View warnings and assignment conflicts.

Any manual adjustment must be revalidated against hard constraints.

Provide a warning before accepting an adjustment that worsens delivery deadlines or freshness targets.

### 9.6 Interface polish

Aim for a high-quality modern SaaS-style user interface.

Include:

- Consistent spacing and visual hierarchy.
- Clear responsive navigation.
- Dark and light themes where practical.
- Fast loading.
- Helpful empty states.
- Skeleton loaders.
- Clear confirmation dialogs.
- Toast notifications.
- Keyboard accessibility.
- Useful status indicators.
- Well-designed order and driver cards.

Prioritise operational clarity over decorative animation.

---

## 10. DRIVER MOBILE INTERFACE

Create a mobile-friendly PWA for delivery drivers.

Drivers must be able to:

- Log in securely.
- View their assigned trip.
- Accept an assigned trip.
- See the ordered list of deliveries.
- See customer addresses and permitted instructions.
- Confirm collection from the restaurant.
- Open navigation to the next stop.
- Mark individual orders delivered.
- Mark failed delivery attempts.
- Record return to the restaurant.
- Report delays.
- View their next assignment.

Offer a navigation link to a supported external navigation application.

Do not claim to provide full turn-by-turn navigation unless it has actually been implemented.

Support optional location sharing while on duty, with clear consent and privacy controls.

Do not require continuous GPS tracking for the core dispatch system to function.

For interrupted network connectivity, preserve safe local UI state and use idempotent synchronisation where appropriate. Never claim a delivery has been successfully recorded on the server before receiving confirmation.

---

## 11. DATABASE DESIGN

Design a normalised PostgreSQL schema.

At minimum, consider the following entities:

### Restaurant
- ID.
- Name.
- Address.
- Coordinates.
- Time zone.
- Opening hours.
- Configuration settings.

### User
- ID.
- Name.
- Role.
- Authentication credentials or identity reference.
- Active status.

### StaffMember
- ID.
- User ID.
- Employment role.
- Delivery eligibility.
- Staff availability.

### Driver
- ID.
- Staff member reference.
- Current state.
- Capacity.
- Driver restrictions.

### DriverShift
- ID.
- Driver ID.
- Shift start.
- Shift end.
- Breaks.
- Actual clock-in and clock-out times.

### DeliveryOrder
- ID.
- Restaurant ID.
- External order reference.
- Customer address and coordinates.
- Received time.
- Delivery type.
- Requested time window.
- Promised deadline.
- Estimated and actual ready times.
- Capacity requirements.
- Status.
- Priority.

### DeliveryTrip
- ID.
- Driver ID.
- Restaurant ID.
- Start location.
- End location.
- Planned departure.
- Actual departure.
- Expected return.
- Actual completion.
- Trip status.
- Route version.

### DeliveryStop
- ID.
- Trip ID.
- Sequence number.
- Geographic location.
- Estimated arrival.
- Actual arrival.
- Estimated service duration.
- Stop status.

Support multiple order IDs at one physical stop where appropriate.

### TripOrderAssignment
Associate orders with trips and stops without permitting invalid overlapping active assignments.

### OptimisationRun
- ID.
- Trigger.
- Start time.
- Completion time.
- Solver status.
- Objective metrics.
- Algorithm configuration.
- Result version.

### OptimisationProposal
Store proposed assignments separately from committed trips.

### AuditEvent
Track significant order, route, driver and administrative changes.

Add entities for address validation, staff capabilities, notifications and provider metadata as required.

Use:

- Appropriate indexes.
- Database constraints.
- Foreign keys.
- Unique constraints.
- Transactions.
- Schema migrations.
- UTC storage for timestamps.
- Explicit local time-zone conversion.

Support Europe/London time correctly, including British Summer Time and daylight-saving transitions.

Avoid storing important operational state exclusively in the browser or process memory.

Apply suitable safeguards when storing customer and location information.

---

## 12. API DESIGN

Design a documented, versioned REST API under `/api/v1`.

Include appropriate endpoints for:

### Restaurant configuration
- Retrieve restaurant settings.
- Update restaurant configuration.
- Set and validate the restaurant location.

### Orders
- Create an order.
- List and filter orders.
- Retrieve an order.
- Update permitted order details.
- Change order status.
- Cancel an order.
- Retrieve order history.

### Drivers and staff
- List drivers.
- Manage shifts.
- Update availability.
- View active trips.
- Authorise waiter-to-driver availability.
- Report driver return.

### Optimisation
- Request an optimisation proposal.
- Poll optimisation job status.
- Retrieve proposed routes.
- Compare existing and proposed plans.
- Commit a proposal.
- Retrieve optimisation warnings and metrics.

### Dispatch
- Assign a trip.
- Confirm dispatch.
- Retrieve trips.
- Record order pickup.
- Record stop completion.
- Record failed delivery.
- Record trip completion.
- Record driver return.
- Apply validated manual overrides.

### Analytics
- Daily delivery performance.
- Driver utilisation.
- On-time delivery percentage.
- Average food waiting time.
- Average delivery duration.
- Optimisation performance.

Implement real-time WebSocket events for order changes, driver changes, route proposals and dispatch status.

Use predictable DTOs, appropriate HTTP status codes, validation, pagination and machine-readable errors.

Add idempotency keys to operations where retries could otherwise create duplicates.

Publish OpenAPI documentation with example requests and responses.

---

## 13. SECURITY AND PRIVACY

Implement appropriate protection for a real restaurant handling customer information.

Requirements:

- Secure authentication.
- Role-based authorisation.
- Admin, dispatcher, waiter and driver permissions.
- Server-side validation for all sensitive operations.
- Strong password hashing when using local passwords.
- Secure session or token handling.
- HTTPS in production.
- Restricted API key usage.
- No secrets committed to source control.
- Rate limiting.
- Audit logging.
- Safe handling of external API failures.
- Protection against injection and common web vulnerabilities.
- Appropriate cross-origin and CSRF controls for the selected authentication architecture.

Follow UK GDPR principles where personal data is processed.

Customer addresses and phone numbers must not be unnecessarily exposed.

Drivers should see only the customer information needed for their assigned deliveries.

Implement configurable data retention and deletion or anonymisation policies.

Employee location tracking should be optional, transparent and limited to legitimate operational needs.

Do not retain historical GPS data indefinitely by default.

---

## 14. CONFIGURATION AND BUSINESS RULES

Make operational assumptions configurable instead of hardcoding them.

Include settings for:

- Default ASAP delivery promise.
- Scheduled delivery tolerance.
- Average preparation time.
- Average time spent at each customer.
- Maximum preferred food holding time.
- Maximum preferred in-transit time.
- Maximum batching wait.
- Maximum orders per trip.
- Driver capacity.
- Maximum trip duration.
- Driver shift restrictions.
- Optimisation refresh interval.
- Solver time limit.
- Lateness penalty.
- Travel-time weighting.
- Travel-distance weighting.
- Driver utilisation weighting.
- Manual approval versus automatic dispatch.
- Traffic-data refresh policy.
- Estimated driver loading time.
- Optional navigation and tracking integrations.

Provide conservative, documented defaults.

Make it clear which requirements are hard constraints and which are optimisation preferences.

Avoid exposing unnecessary low-level solver parameters to ordinary dispatch staff.

---

## 15. ANALYTICS AND PERFORMANCE MEASUREMENT

Create an analytics section that enables the restaurant to evaluate whether the system is actually improving dispatch operations.

Track:

1. Total daily delivery orders.
2. Percentage delivered on time.
3. Average minutes early or late.
4. Average customer wait after ordering.
5. Average time between food readiness and dispatch.
6. Average collection-to-delivery time.
7. Driver utilisation.
8. Average orders per trip.
9. Average journey time per order.
10. Total driver travel distance.
11. Percentage of orders requiring manual reassignment.
12. Number of solver failures or fallback runs.
13. Estimated time saved against a documented baseline.
14. Delivery deadline violations.
15. Scheduled-order punctuality.

Use real recorded timestamps for actual performance.

Do not present model estimates as proven operational savings.

If comparing against manual dispatch, implement an explicit historical baseline or controlled comparison rather than making unsupported claims.

Provide useful date filters and export functionality.

---

## 16. IMPORTANT EXAMPLE SCENARIOS

Create automated tests and demonstration data for the following scenarios.

### Scenario A — Standard grouping

There are 2 available drivers and 4 ready orders.

Two orders have highly compatible driving routes.

Two others lie in a different part of town.

Expected behaviour: produce efficient driver assignments while respecting deadlines and route capacities.

### Scenario B — Delivery along an existing route

Order A is farther away.

Order B lies naturally along the driving route to Order A but belongs to a different postcode district.

Expected behaviour: detect that grouping A and B produces a small incremental detour and consider grouping them.

Do not reject grouping merely because the postcodes differ.

### Scenario C — Nearby addresses with one-way restrictions

Two deliveries appear extremely close on a map.

However, one-way roads make travel between them slow in one direction.

Expected behaviour: use the asymmetric road matrix and select a valid stop order.

### Scenario D — Driver shortage

There are 8 outstanding deliveries but only 2 drivers.

One driver is available while the other is returning in approximately 10 minutes.

Expected behaviour: distinguish executable dispatches from provisional future assignments, minimise lateness and avoid double-booking.

### Scenario E — Scheduled order

A customer requests delivery at 19:30.

Another ASAP delivery lies on a compatible route.

Expected behaviour: determine whether grouping is feasible without delivering the scheduled order too early or delaying the ASAP order excessively.

### Scenario F — Waiter temporarily available

The restaurant has 3 active drivers, all unavailable.

A waiter can be released for a maximum of 20 minutes.

Expected behaviour: only consider that waiter after authorisation and restrict trips according to their return deadline.

### Scenario G — New urgent order

A proposed route has been generated.

A new urgent order arrives before dispatch.

Expected behaviour: recalculate eligible proposed trips without changing already completed or frozen work.

### Scenario H — Food preparation delay

Two orders are grouped provisionally.

One order's preparation is delayed by 15 minutes.

Expected behaviour: determine whether the ready order should depart independently rather than becoming late.

### Scenario I — No feasible solution

There are no available or returning eligible drivers within the required horizon, and several deadlines are impossible.

Expected behaviour: report the infeasibility transparently and show the affected orders rather than inventing an apparently valid route.

### Scenario J — Driver becomes unavailable

A driver becomes unavailable after a provisional assignment is calculated but before it is committed.

Expected behaviour: reject stale or conflicting commitments and generate a new feasible plan.

### Scenario K — Multiple orders at one address

Two customers or orders have the same delivery building and compatible time windows.

Expected behaviour: consider a shared physical stop while preserving separate order completion records.

### Scenario L — Provider API failure

The routing provider times out or returns a partially incomplete matrix.

Expected behaviour: handle the failure safely, preserve existing valid assignments and avoid dispatching routes using fabricated road data.

### Scenario M — Concurrent dispatchers

Two employees attempt to commit overlapping assignments at the same time.

Expected behaviour: prevent duplicate order assignment through transactional concurrency control.

### Scenario N — Time-zone transition

A scheduled delivery crosses a British Summer Time clock change.

Expected behaviour: preserve the intended real-world delivery time and handle ambiguous local timestamps explicitly.

### Scenario O — Mixed driver capacities

Three drivers have different load capacities and trip limits.

Expected behaviour: assign orders to appropriate drivers without exceeding individual constraints.

Each scenario must include deterministic test fixtures and assertions, not just a written description.

---

## 17. DEMONSTRATION MODE

The completed repository must be usable for development and evaluation without immediately purchasing or configuring a commercial routing API.

Implement a clearly labelled demo mode with:

- A sample restaurant.
- Example orders.
- Example drivers.
- Realistic shifts and statuses.
- Scheduled and ASAP orders.
- Different delivery deadlines.
- A deterministic simulated travel-time provider.
- Example road-network asymmetry.
- Example route recommendations.

Where possible, construct a small directed test road graph that demonstrates one-way streets and route-based grouping.

Do not present synthetic travel estimates as current live road conditions.

A production mode must support actual routing providers using configured credentials.

Provide a simple way to switch between demonstration and production providers.

---

## 18. RELIABILITY AND DEPLOYMENT

Implement production-conscious engineering practices.

Requirements:

- Docker Compose development environment.
- Health-check endpoints.
- Database migrations.
- Structured logging.
- Appropriate monitoring hooks.
- Background worker health checks.
- Graceful API and solver timeouts.
- Retry handling for transient failures.
- Safe handling of duplicate events.
- Backup and recovery documentation.
- Environment variable validation.
- Separate database credentials.
- Restricted production permissions.
- API usage and quota monitoring.
- Error reporting without leaking sensitive information.

The system must continue displaying the last confirmed dispatch state if optimisation services are temporarily unavailable.

Never automatically commit a partial or corrupted solver result.

---

## 19. PROJECT STRUCTURE

Use a clean, maintainable monorepo.

Suggested structure:

```text
restaurant-delivery-optimiser/
├── apps/
│   └── web/
│       ├── app/
│       ├── components/
│       ├── features/
│       ├── hooks/
│       ├── lib/
│       ├── types/
│       └── tests/
├── services/
│   └── api/
│       ├── app/
│       │   ├── api/
│       │   ├── core/
│       │   ├── db/
│       │   ├── models/
│       │   ├── schemas/
│       │   ├── services/
│       │   ├── routing/
│       │   │   ├── providers/
│       │   │   └── matrices/
│       │   ├── optimisation/
│       │   │   ├── solver/
│       │   │   ├── constraints/
│       │   │   ├── objectives/
│       │   │   └── validation/
│       │   ├── dispatch/
│       │   ├── workers/
│       │   └── events/
│       ├── migrations/
│       └── tests/
├── packages/
│   └── api-contracts/
├── infra/
├── docs/
├── scripts/
├── docker-compose.yml
├── .env.example
└── README.md
```

Adapt this structure if necessary to fit the actual frameworks and development tools.

Do not create meaningless layers merely to imitate enterprise architecture.

Use clear dependency boundaries.

In particular:

- The optimisation engine must be independent of the UI.
- The road-routing provider must be interchangeable.
- Domain logic must not depend directly on external API response formats.
- The database model must not contain UI-specific assumptions.
- Dispatch decisions must be validated before persistence.
- Tests must be able to use an offline routing provider.

---

## 20. DEVELOPMENT PROCESS

Follow a disciplined implementation sequence.

### Phase 1 — Requirements and architectural design

Produce:

- Concise system requirements.
- Core user roles and user journeys.
- Important business assumptions.
- Domain model.
- System architecture.
- Database design.
- Component responsibilities.
- API contract outline.
- Optimisation strategy.
- External integration and quota considerations.
- Key technical risks.

Resolve ordinary implementation details using sensible, documented assumptions.

Ask for clarification only when a genuinely blocking business decision cannot be safely assumed.

### Phase 2 — Project foundations

Implement:

- Repository structure.
- Docker Compose.
- Database connection.
- Database migrations.
- Environment configuration.
- Authentication.
- Role-based authorisation.
- Base frontend application.
- API validation and error handling.

### Phase 3 — Operational business logic

Implement:

- Restaurant settings.
- Delivery order lifecycle.
- Driver and staff management.
- Shift scheduling.
- Food readiness.
- Delivery deadlines.
- Driver availability tracking.
- Core REST APIs.

### Phase 4 — Road routing integration

Implement:

- Location validation.
- Geocoding.
- Routing-provider abstraction.
- Travel-time matrix generation.
- Road geometry retrieval.
- Directed road travel costs.
- API errors and rate-limit handling.
- Mock routing provider for tests.

### Phase 5 — Optimisation engine

Implement:

- VRPTW formulation.
- Vehicle capacities.
- Time windows.
- Driver availability.
- Pickup readiness.
- Delivery sequence optimisation.
- Departure-time planning.
- Dynamic driver allocation.
- Unassigned-order handling.
- Bounded solver execution.
- Fallback algorithm.

Build automated solver tests before connecting the optimiser to the live dashboard.

### Phase 6 — Dispatch orchestration

Implement:

- Optimisation proposals.
- Transactional route commitments.
- Route versioning.
- Driver trip execution.
- Stop completion.
- Driver return.
- Reoptimisation triggers.
- Stale assignment prevention.
- Real-time events.

### Phase 7 — Frontend and driver PWA

Implement the operational dashboard, interactive maps, order management, recommended routes, driver management and mobile trip interface.

Connect every visible control to actual implemented functionality.

### Phase 8 — Testing and hardening

Execute:

- Unit tests.
- Integration tests.
- Optimisation scenario tests.
- Database concurrency tests.
- API contract tests.
- Frontend component tests.
- End-to-end tests.
- Security and authorisation tests.
- Failure recovery tests.
- Performance tests using representative restaurant workloads.

### Phase 9 — Final verification and documentation

Provide:

- Complete source code.
- Working development environment.
- Database migration instructions.
- Demo data and seed script.
- Required environment variables.
- API key setup instructions.
- Routing-provider configuration.
- Full application startup commands.
- Test execution commands.
- Operator user guide.
- Driver user guide.
- Deployment instructions.
- Known limitations and future improvements.

---

## 21. ACCEPTANCE CRITERIA

The project is not complete unless the following can be demonstrated:

1. An administrator can configure a restaurant at an arbitrary valid address.

2. A dispatcher can enter orders containing real delivery addresses, arrival times, deadlines and readiness information.

3. A dispatcher can configure the drivers working today and update their current availability.

4. The optimiser can group deliveries using realistic road travel times rather than postcode matching or straight-line distance.

5. The optimiser can account for one-way roads where supported by the selected routing provider.

6. The optimiser can identify stops along the natural route toward another destination.

7. Different available-driver counts produce appropriate different assignments.

8. Scheduled deliveries are planned around their permitted delivery windows.

9. Food-ready times prevent premature collection.

10. Drivers already on committed trips cannot be double-booked.

11. Waiters can only receive deliveries when explicitly eligible and authorised.

12. A dispatcher can preview and commit recommended trips.

13. The application displays routes, stop sequences, estimated arrivals and operational warnings.

14. Drivers can complete an assigned trip from a mobile-friendly interface.

15. New orders and availability changes can trigger safe reoptimisation.

16. Orders that cannot be assigned are clearly identified.

17. External API failures do not result in fabricated live route information.

18. Multiple dispatchers cannot create conflicting active assignments.

19. Demo mode works without commercial API credentials.

20. Production routing can be enabled through documented configuration.

21. Automated tests cover all critical scenarios.

22. The application can be started locally using documented commands and genuinely works end to end.

---

## 22. QUALITY STANDARDS

Follow these non-negotiable engineering principles:

- No fabricated API endpoints or undocumented provider capabilities.
- No hardcoded restaurant location.
- No hardcoded number of drivers.
- No hardcoded assumption that every trip has the same number of stops.
- No reliance on postcodes alone for delivery grouping.
- No Haversine-only production route optimisation.
- No silent dropping of orders.
- No double-booking drivers.
- No automatic reassignment of frozen or completed deliveries.
- No exposing secrets in frontend code.
- No trusting frontend-supplied permissions.
- No fake successful API responses.
- No static mock dashboard presented as a completed application.
- No unsupported claim that a heuristic route is globally optimal.
- No untested route-commitment logic.

Use clear naming, strong typing, reusable components, separation of concerns, appropriate validation and comprehensive error handling.

Prefer a reliable, understandable solution to unnecessary architectural complexity.

---

## 23. INSTRUCTIONS FOR YOUR FINAL OUTPUT

Begin by briefly presenting the selected architecture and identifying any important assumptions.

Then implement the project phase by phase.

Do not stop after producing a requirements document or project plan.

Create actual application files and functional implementations.

If operating in a coding environment with filesystem and terminal access:

- Write files directly into the repository.
- Install the required dependencies.
- Run database migrations.
- Execute tests.
- Fix errors encountered.
- Start the application where the environment permits.
- Verify key user flows.
- Report actual verification results.

If execution is unavailable, provide complete implementable files and clearly identify what has not been tested.

Do not invent successful test results.

Do not use pseudocode in place of required functional code.

Do not leave important features as empty methods, disconnected UI placeholders or TODO-only implementations.

If the implementation exceeds the available context or execution budget, prioritise completing a coherent, tested end-to-end system and explicitly distinguish working functionality from remaining extensions.

**The final deliverable must be an intelligent restaurant delivery dispatch application that meaningfully reduces manual route planning, accounts for changing restaurant conditions and automatically recommends efficient, deadline-aware delivery assignments using real road-network information.**

The primary measure of success is whether restaurant employees with little or no local geographical knowledge can reliably use the application to dispatch deliveries quickly and sensibly.