"""Bounded feasible-route generation + OR-Tools set packing for rolling-horizon VRPTW.
One proposed trip per driver per cycle. Not a global optimality guarantee.
"""
from datetime import timedelta
from itertools import permutations
from time import monotonic
from uuid import uuid4
from ortools.sat.python import cp_model
from .domain import Order, Driver, Settings, Route, Stop, Plan
from .routing import Matrix


def evaluate(sequence, driver, orders, matrix, index, settings, now):
    if not sequence or driver.state not in ('AVAILABLE','RETURNING') or (driver.waiter and not driver.authorised):
        return None
    if len(sequence) > min(driver.max_orders, settings.max_orders) or sum(orders[x].units for x in sequence) > driver.capacity:
        return None
    ready = [orders[x].actual_ready_at or orders[x].ready_at for x in sequence]
    departure = max(now, driver.available_at, max(ready)) + timedelta(seconds=settings.loading_seconds)
    # Delay at depot rather than delivering a scheduled order early. Later stops may wait.
    first = orders[sequence[0]]
    outbound = matrix.seconds[0][index[first.id]]
    if outbound is None:
        return None
    departure = max(departure, first.earliest - timedelta(seconds=outbound))
    if (departure - now).total_seconds() > settings.horizon_seconds:
        return None
    if any((departure - r).total_seconds() > settings.max_hold for r in ready):
        return None
    if len(sequence) > 1 and (max(ready)-min(ready)).total_seconds() > settings.max_batch_wait:
        return None
    current, position, travel, distance, stops = departure, 0, 0, 0, []
    for oid in sequence:
        order, target = orders[oid], index[oid]
        duration = matrix.seconds[position][target]
        if duration is None:
            return None
        current = max(current + timedelta(seconds=duration), order.earliest)
        if (current-departure).total_seconds() > settings.max_transit:
            return None
        late = max(0, int((current-order.deadline).total_seconds()))
        stops.append(Stop(order_id=oid, arrival=current, late_seconds=late))
        current += timedelta(seconds=order.service_seconds)
        travel += duration
        distance += matrix.metres[position][target]
        position = target
    back = matrix.seconds[position][0]
    if back is None:
        return None
    current += timedelta(seconds=back)
    travel += back
    distance += matrix.metres[position][0]
    end = min(driver.shift_end, driver.return_by or driver.shift_end)
    if current > end or (current-departure).total_seconds() > driver.max_trip_seconds:
        return None
    warnings = [f'{s.order_id}: {s.late_seconds//60} min late' for s in stops if s.late_seconds]
    executable = driver.state == 'AVAILABLE' and driver.available_at <= now and all(
        orders[x].status == 'READY' and orders[x].actual_ready_at <= now for x in sequence)
    # Loading is allowed; any deliberate future wait makes the proposal provisional.
    executable = executable and departure <= now + timedelta(seconds=settings.loading_seconds)
    return Route(driver_id=driver.id, order_ids=list(sequence), departure=departure, returns_at=current,
                 travel_seconds=travel, distance_metres=distance, stops=stops, executable=executable, warnings=warnings)


def optimise(orders: list[Order], drivers: list[Driver], settings: Settings, matrix: Matrix, now, revision=0,
             force_fallback=False):
    matrix.validate(len(orders)+1)
    eligible = {o.id:o for o in orders if o.status in ('RECEIVED','PREPARING','READY')}
    index = {o.id:i+1 for i,o in enumerate(orders)}
    candidates, warnings = [], []
    capped = False
    for driver in sorted(drivers, key=lambda d:d.id):
        # Bound factorial growth. Urgency-first candidate pool; unselected orders remain visible.
        pool = sorted(eligible, key=lambda x:(eligible[x].deadline, -eligible[x].priority, x))[:12]
        count = 0
        driver_start = monotonic()
        driver_capped = False
        for size in range(1, min(len(pool),driver.max_orders,settings.max_orders)+1):
            for sequence in permutations(pool, size):
                count += 1
                if count > 4000 or monotonic()-driver_start > settings.solver_seconds/max(1,len(drivers)):
                    capped = True
                    driver_capped = True
                    break
                route = evaluate(sequence,driver,eligible,matrix,index,settings,now)
                if route:
                    candidates.append(route)
            if driver_capped:
                break
    if capped or len(eligible) > 12:
        warnings.append('Candidate search bounded; some feasible alternatives may be unexplored')
    chosen = []
    solver_name = 'OR-Tools CP-SAT feasible-route VRPTW'
    def cost(r):
        return (sum(s.late_seconds for s in r.stops)*1000 + r.travel_seconds
                + sum(int((s.arrival-now).total_seconds()) * eligible[s.order_id].priority for s in r.stops)
                + int((r.departure-now).total_seconds()))
    if candidates and not force_fallback:
        model = cp_model.CpModel()
        picks = [model.NewBoolVar(f'r{i}') for i in range(len(candidates))]
        for oid in eligible:
            model.Add(sum(picks[i] for i,r in enumerate(candidates) if oid in r.order_ids) <= 1)
        for driver in drivers:
            model.Add(sum(picks[i] for i,r in enumerate(candidates) if r.driver_id == driver.id) <= 1)
        # An additional assigned order dominates all candidate travel/lateness costs.
        bound = sum(cost(r) for r in candidates)+1
        model.Maximize(sum(picks[i]*(len(r.order_ids)*bound-cost(r)) for i,r in enumerate(candidates)))
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = settings.solver_seconds
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = 0
        status = solver.Solve(model)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            chosen = [r for i,r in enumerate(candidates) if solver.Value(picks[i])]
        else:
            force_fallback = True
    if force_fallback:
        solver_name = 'Deterministic feasible-route greedy fallback'
        used_orders, used_drivers = set(), set()
        for route in sorted(candidates,key=lambda r:(-len(r.order_ids),cost(r),r.driver_id,r.order_ids)):
            if route.driver_id not in used_drivers and not used_orders.intersection(route.order_ids):
                chosen.append(route)
                used_orders.update(route.order_ids)
                used_drivers.add(route.driver_id)
        warnings.append('Fallback used; review recommendations')
    assigned = {x for route in chosen for x in route.order_ids}
    unassigned = {x: 'No selected feasible trip: review driver availability, capacity, readiness, freshness and shift limits'
                  for x in eligible if x not in assigned}
    return Plan(id=str(uuid4()), revision=revision, created_at=now, provider=matrix.source, routes=chosen,
                unassigned=unassigned, solver=solver_name, warnings=warnings)
