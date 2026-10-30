"""Explicit demo seed; refuses to overwrite existing data."""
import os
from datetime import timedelta
from .db import factory, Revision, Config, User, OrderRow, DriverRow
from .domain import Settings, Order, Driver, Location, utcnow
from .routing import NODES
from .security import password_hash, secret


def seed(Session):
    secret()
    password=os.environ.get('DEMO_PASSWORD','')
    if len(password)<12:raise RuntimeError('DEMO_PASSWORD must contain at least 12 characters')
    now=utcnow()
    with Session.begin() as s:
        if s.get(Revision,1):return False
        s.add(Revision(id=1,value=0));s.add(Config(id=1,data=Settings().model_dump(mode='json')))
        for uid,role,did in [('manager','admin',None),('dispatcher','dispatcher',None),('driver1','driver','d1'),('driver2','driver','d2')]:
            s.add(User(id=uid,password=password_hash(password),role=role,driver_id=did))
        for i in range(1,3):
            d=Driver(id=f'd{i}',name=f'Driver {i}',available_at=now,shift_end=now+timedelta(hours=8))
            s.add(DriverRow(id=d.id,data=d.model_dump(mode='json')))
        for i,node in enumerate(['north','far_north','east','far_east']):
            lat,lng=NODES[node]
            o=Order(id=str(104+i),location=Location(address='Demo '+node.replace('_',' '),lat=lat,lng=lng,node=node),
                    received_at=now-timedelta(minutes=15),ready_at=now,actual_ready_at=now,
                    earliest=now,deadline=now+timedelta(minutes=25),status='READY')
            s.add(OrderRow(id=o.id,data=o.model_dump(mode='json')))
    return True

if __name__=='__main__':
    _,Session=factory();print('Seeded demo' if seed(Session) else 'Existing data preserved')
