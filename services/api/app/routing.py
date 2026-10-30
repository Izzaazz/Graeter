"""No synthetic fallback in production. Demo uses shortest paths on a directed graph."""
import heapq
import os
import time
from dataclasses import dataclass
import httpx
from .domain import Location


class RoutingError(Exception):
    pass


@dataclass
class Matrix:
    seconds: list[list[int | None]]
    metres: list[list[int | None]]
    source: str

    def validate(self, n):
        for matrix in (self.seconds, self.metres):
            if len(matrix) != n or any(len(row) != n for row in matrix):
                raise RoutingError('Incomplete routing matrix')
            if any(v is not None and (not isinstance(v, int) or v < 0) for row in matrix for v in row):
                raise RoutingError('Invalid routing cost')
        for i in range(n):
            for j in range(n):
                if (self.seconds[i][j] is None) != (self.metres[i][j] is None):
                    raise RoutingError('Mismatched reachability')
        return self


NODES = {
    'depot': (52.136, -.467), 'north': (52.144, -.467),
    'far_north': (52.154, -.467), 'east': (52.136, -.449),
    'far_east': (52.136, -.430), 'south': (52.124, -.460),
}
EDGES = {
    'depot': {'north': 240, 'east': 300, 'south': 360},
    'north': {'far_north': 240, 'depot': 420},
    'far_north': {'north': 420, 'east': 600},
    'east': {'far_east': 240, 'depot': 420},
    'far_east': {'east': 360, 'south': 540},
    'south': {'depot': 300, 'east': 240},
}


class DemoProvider:
    def matrix(self, locations):
        if any(p.node not in NODES for p in locations):
            raise RoutingError('Demo mode requires a named simulated road node; real addresses require production routing')
        result = []
        for p in locations:
            costs, queue = {p.node: 0}, [(0, p.node)]
            while queue:
                cost, node = heapq.heappop(queue)
                if cost != costs[node]:
                    continue
                for target, edge in EDGES[node].items():
                    new = cost + edge
                    if new < costs.get(target, float('inf')):
                        costs[target] = new
                        heapq.heappush(queue, (new, target))
            result.append([costs.get(q.node) for q in locations])
        return Matrix(result, [[v * 7 if v is not None else None for v in row] for row in result],
                      'SIMULATED directed road graph • no live traffic').validate(len(locations))


class GoogleProvider:
    def __init__(self):
        self.key = os.getenv('GOOGLE_MAPS_API_KEY')
        if not self.key:
            raise RoutingError('GOOGLE_MAPS_API_KEY is required for production routing')

    def matrix(self, locations):
        # Batches of 10x10 remain below the Routes API 625-element limit.
        n = len(locations)
        seconds = [[None] * n for _ in range(n)]
        metres = [[None] * n for _ in range(n)]
        def waypoint(p):
            return {'waypoint': {'location': {'latLng': {'latitude': p.lat, 'longitude': p.lng}}}}
        with httpx.Client(timeout=15) as client:
            for a in range(0, n, 10):
                for b in range(0, n, 10):
                    body = {'origins': [waypoint(p) for p in locations[a:a+10]],
                            'destinations': [waypoint(p) for p in locations[b:b+10]],
                            'travelMode': 'DRIVE', 'routingPreference': 'TRAFFIC_UNAWARE'}
                    response = None
                    for attempt in range(3):
                        try:
                            response = client.post('https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix',
                                json=body, headers={'X-Goog-Api-Key': self.key,
                                'X-Goog-FieldMask': 'originIndex,destinationIndex,status,condition,duration,distanceMeters'})
                        except httpx.HTTPError:
                            if attempt == 2:
                                raise RoutingError('Routing provider unavailable') from None
                            time.sleep(.2 * 2**attempt)
                            continue
                        if response.status_code not in (429, 500, 502, 503, 504):
                            break
                        time.sleep(.2 * 2**attempt)
                    if response is None or response.status_code != 200:
                        raise RoutingError('Routing provider rejected request; check credentials, quota and billing')
                    try:
                        elements = response.json()
                        seen = set()
                        for e in elements:
                            i, j = e['originIndex'], e['destinationIndex']
                            if not (0 <= i < min(10,n-a) and 0 <= j < min(10,n-b)) or (i,j) in seen:
                                raise ValueError()
                            seen.add((i,j))
                            if e.get('status', {}).get('code', 0) != 0:
                                raise RoutingError('Provider returned an element error')
                            if e.get('condition') == 'ROUTE_NOT_FOUND':
                                continue
                            if e.get('condition') != 'ROUTE_EXISTS':
                                raise ValueError()
                            seconds[a+i][b+j] = int(float(e['duration'].removesuffix('s')) + .999)
                            metres[a+i][b+j] = e['distanceMeters']
                        if len(seen) != min(10,n-a)*min(10,n-b):
                            raise ValueError()
                    except (KeyError, TypeError, ValueError):
                        raise RoutingError('Incomplete or malformed provider matrix') from None
        return Matrix(seconds, metres, 'Google Routes • traffic unaware').validate(n)


def provider(name):
    return DemoProvider() if name == 'demo' else GoogleProvider()
