"""Provider-independent, UTC-only dispatch contracts."""
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, model_validator


def utcnow():
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    model_config = {'extra': 'forbid'}


class Location(StrictModel):
    address: str = Field(min_length=3, max_length=300)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    node: str | None = None


class Settings(StrictModel):
    name: str = 'New Bombay • Demo'
    depot: Location = Location(address='Simulated restaurant', lat=52.136, lng=-0.467, node='depot')
    loading_seconds: int = Field(default=60, ge=0, le=900)
    max_batch_wait: int = Field(default=300, ge=0, le=1800)
    max_hold: int = Field(default=1200, ge=60, le=7200)
    max_transit: int = Field(default=2400, ge=60, le=7200)
    max_orders: int = Field(default=4, ge=1, le=8)
    solver_seconds: float = Field(default=2, ge=.1, le=10)
    horizon_seconds: int = Field(default=7200, ge=300, le=14400)
    provider: Literal['demo', 'google'] = 'demo'


class Order(StrictModel):
    id: str = Field(min_length=1, max_length=80)
    location: Location
    received_at: datetime
    ready_at: datetime
    earliest: datetime
    deadline: datetime
    actual_ready_at: datetime | None = None
    kind: Literal['ASAP', 'SCHEDULED'] = 'ASAP'
    status: Literal['RECEIVED','PREPARING','READY','ASSIGNED','OUT_FOR_DELIVERY','DELIVERED','FAILED','CANCELLED'] = 'PREPARING'
    units: int = Field(default=1, ge=1, le=100)
    service_seconds: int = Field(default=90, ge=0, le=1800)
    priority: int = Field(default=1, ge=1, le=5)
    instructions: str = Field(default='', max_length=500)
    picked_up_at: datetime | None = None
    delivered_at: datetime | None = None

    @model_validator(mode='after')
    def dates(self):
        for field in ['received_at','ready_at','earliest','deadline','actual_ready_at','picked_up_at','delivered_at']:
            value = getattr(self, field)
            if value is not None:
                if value.tzinfo is None or value.utcoffset() is None:
                    raise ValueError('Times must include a UTC offset; ambiguous local times are not accepted')
                setattr(self, field, value.astimezone(timezone.utc))
        if self.earliest > self.deadline or self.ready_at < self.received_at:
            raise ValueError('Invalid delivery window or readiness time')
        if self.status == 'READY' and self.actual_ready_at is None:
            raise ValueError('Ready orders require an actual readiness timestamp')
        return self


class Driver(StrictModel):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=100)
    state: Literal['OFF_DUTY','AVAILABLE','RESERVED','ON_DELIVERY','RETURNING','ON_BREAK','UNAVAILABLE'] = 'AVAILABLE'
    capacity: int = Field(default=4, ge=1, le=100)
    max_orders: int = Field(default=4, ge=1, le=8)
    max_trip_seconds: int = Field(default=3600, ge=60, le=14400)
    available_at: datetime
    shift_end: datetime
    waiter: bool = False
    authorised: bool = False
    return_by: datetime | None = None

    @model_validator(mode='after')
    def dates(self):
        for f in ['available_at','shift_end','return_by']:
            v = getattr(self, f)
            if v is not None:
                if v.tzinfo is None or v.utcoffset() is None:
                    raise ValueError('Driver times require UTC offsets')
                setattr(self, f, v.astimezone(timezone.utc))
        if self.waiter and self.authorised and not self.return_by:
            raise ValueError('Released waiters require a return-by time')
        return self


class Stop(StrictModel):
    order_id: str
    arrival: datetime
    late_seconds: int


class Route(StrictModel):
    driver_id: str
    order_ids: list[str]
    departure: datetime
    returns_at: datetime
    travel_seconds: int
    distance_metres: int
    stops: list[Stop]
    executable: bool
    warnings: list[str] = []


class Plan(StrictModel):
    id: str
    revision: int
    created_at: datetime
    provider: str
    routes: list[Route]
    unassigned: dict[str,str]
    solver: str
    warnings: list[str] = []
