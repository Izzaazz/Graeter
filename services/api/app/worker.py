"""Queueable planning, never automatic commitment."""
import os
from celery import Celery
from sqlalchemy import select
from .db import factory,Config,OrderRow,DriverRow,Revision,Proposal,Conflict
from .domain import Settings,Order,Driver,utcnow
from .routing import provider
from .optimisation import optimise
worker=Celery('dispatch',broker=os.getenv('REDIS_URL','redis://localhost:6379/0'))
worker.conf.update(task_soft_time_limit=55,task_time_limit=60,worker_prefetch_multiplier=1)
@worker.task(name='dispatch.plan')
def generate_plan():
    _,Session=factory()
    with Session() as s:
        settings=Settings.model_validate(s.get(Config,1).data)
        orders=[Order.model_validate(r.data) for r in s.scalars(select(OrderRow)) if r.data['status'] in ('RECEIVED','PREPARING','READY')]
        drivers=[Driver.model_validate(r.data) for r in s.scalars(select(DriverRow))]
        rev=s.get(Revision,1).value
    matrix=provider(settings.provider).matrix([settings.depot]+[o.location for o in orders])
    plan=optimise(orders,drivers,settings,matrix,utcnow(),rev)
    with Session.begin() as s:
        if s.get(Revision,1).value!=rev:raise Conflict('Snapshot changed during queued optimisation')
        s.add(Proposal(id=plan.id,data=plan.model_dump(mode='json')))
    return plan.id
