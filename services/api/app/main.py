import asyncio
from contextlib import asynccontextmanager
import csv
import io
import logging
import os
import time
from datetime import timedelta
from uuid import uuid4
from fastapi import FastAPI, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from .db import (factory, Revision, Config, User, OrderRow, DriverRow, Proposal, Trip, StopRow, Audit, Idempotency, advance, Conflict)
from .domain import Order, Driver, Settings, Plan, utcnow
from .routing import provider, RoutingError, NODES
from .optimisation import optimise, evaluate
from .security import password_ok, token, subject, secret

log = logging.getLogger('dispatch')


def create_app(url=None):
    engine, Session = factory(url)
    @asynccontextmanager
    async def lifespan(app):
        secret()
        if os.getenv('APP_ENV')=='production' and not os.getenv('APP_ORIGIN','').startswith('https://'):
            raise RuntimeError('Production requires an HTTPS APP_ORIGIN')
        yield
    app = FastAPI(title='NB Dispatch API', version='0.1.0', lifespan=lifespan)
    app.state.Session = Session
    app.state.engine = engine
    attempts = {}

    @app.middleware('http')
    async def guard(request, call_next):
        if request.method not in ('GET','HEAD','OPTIONS'):
            origin = request.headers.get('origin')
            allowed = os.getenv('APP_ORIGIN','http://localhost:3000')
            if origin and origin != allowed:
                return JSONResponse({'detail':'Untrusted request origin'},status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.exception_handler(Conflict)
    async def conflict(_, exc): return JSONResponse({'detail':str(exc)},status_code=409)
    @app.exception_handler(IntegrityError)
    async def duplicate(_, exc): return JSONResponse({'detail':'Duplicate or conflicting record'},status_code=409)
    @app.exception_handler(RoutingError)
    async def routing_error(_, exc): return JSONResponse({'detail':str(exc)},status_code=503)

    def current(request: Request):
        uid = subject(request.cookies.get('session',''))
        with Session() as s:
            user = s.get(User, uid) if uid else None
            if not user: raise HTTPException(401,'Sign in required')
            return user
    def staff(user=Depends(current)):
        if user.role not in ('admin','dispatcher'): raise HTTPException(403,'Dispatcher access required')
        return user
    def admin(user=Depends(current)):
        if user.role != 'admin': raise HTTPException(403,'Administrator access required')
        return user
    def audit(s,user,action): s.add(Audit(actor=user.id,action=action,at=utcnow().isoformat()))
    def snapshot(s):
        settings = s.get(Config,1)
        if settings is None: raise HTTPException(503,'Run migrations and seed first')
        return (Settings.model_validate(settings.data),
                [Order.model_validate(r.data) for r in s.scalars(select(OrderRow))],
                [Driver.model_validate(r.data) for r in s.scalars(select(DriverRow))],s.get(Revision,1).value)
    def trip_access(s,tid,user):
        trip = s.get(Trip,tid)
        if trip is None: raise HTTPException(404,'Trip not found')
        if user.role == 'driver' and user.driver_id != trip.driver_id: raise HTTPException(403,'Not your trip')
        return trip
    def serialized_trip(s,trip):
        return {'id':trip.id,'driver_id':trip.driver_id,'status':trip.status,'route':trip.data,
                'stops':[{'order_id':st.order_id,'status':st.status,'sequence':st.sequence}
                         for st in s.scalars(select(StopRow).where(StopRow.trip_id==trip.id).order_by(StopRow.sequence))]}

    @app.get('/health')
    def health():
        with engine.connect() as c: c.execute(text('SELECT 1'))
        return {'status':'ok','version':'0.1.0'}

    class Login(BaseModel):
        username: str = Field(max_length=80)
        password: str = Field(max_length=200)
    @app.post('/auth/login')
    def login(body:Login,request:Request,response:Response):
        key = request.client.host if request.client else 'unknown'
        recent = [t for t in attempts.get(key,[]) if t>time.time()-60]
        attempts[key] = recent
        if len(recent)>=10: raise HTTPException(429,'Too many attempts; wait one minute')
        recent.append(time.time())
        with Session() as s:
            user = s.get(User,body.username)
            if not user or not password_ok(body.password,user.password): raise HTTPException(401,'Invalid credentials')
            response.set_cookie('session',token(user.id),httponly=True,samesite='strict',secure=os.getenv('APP_ENV')=='production',max_age=28800)
            return {'id':user.id,'role':user.role}
    @app.post('/auth/logout')
    def logout(response:Response):
        response.delete_cookie('session')
        return {'ok':True}
    @app.get('/auth/me')
    def me(user=Depends(current)): return {'id':user.id,'role':user.role,'driver_id':user.driver_id}

    @app.get('/state')
    def state(user=Depends(current)):
        with Session() as s:
            settings,orders,drivers,rev = snapshot(s)
            trips = list(s.scalars(select(Trip)))
            if user.role=='driver':
                trips = [t for t in trips if t.driver_id==user.driver_id and t.status not in ('COMPLETED','RELEASED')]
                ids = {st.order_id for t in trips for st in s.scalars(select(StopRow).where(StopRow.trip_id==t.id))}
                orders = [o for o in orders if o.id in ids]
                drivers = [d for d in drivers if d.id==user.driver_id]
            return {'settings':settings,'orders':orders,'drivers':drivers,'revision':rev,
                    'trips':[serialized_trip(s,t) for t in trips], 'demo_nodes':NODES if settings.provider=='demo' else {}}

    @app.put('/settings')
    def settings(body:Settings,revision:int,user=Depends(admin)):
        if body.provider=='google': provider('google')
        with Session.begin() as s:
            advance(s,revision)
            s.get(Config,1).data=body.model_dump(mode='json')
            audit(s,user,'settings.updated')
        return body

    @app.post('/orders',status_code=201)
    def add_order(body:Order,user=Depends(staff)):
        if body.status not in ('RECEIVED','PREPARING','READY'): raise HTTPException(422,'Invalid initial status')
        with Session.begin() as s:
            rev=s.get(Revision,1).value
            advance(s,rev)
            if body.actual_ready_at and body.actual_ready_at>utcnow(): raise HTTPException(422,'Readiness cannot be in the future')
            s.add(OrderRow(id=body.id,data=body.model_dump(mode='json')))
            audit(s,user,'order.created:'+body.id)
        return body

    @app.put('/orders/{oid}')
    def edit_order(oid:str,body:Order,revision:int,user=Depends(staff)):
        with Session.begin() as s:
            advance(s,revision)
            row=s.get(OrderRow,oid)
            if row is None: raise HTTPException(404,'Order not found')
            if body.id!=oid or row.data['status'] not in ('RECEIVED','PREPARING','READY'): raise Conflict('Only unassigned orders can be edited')
            if body.status not in ('RECEIVED','PREPARING','READY','CANCELLED'): raise HTTPException(422,'Invalid transition')
            if body.actual_ready_at and body.actual_ready_at>utcnow(): raise HTTPException(422,'Readiness cannot be in the future')
            row.data=body.model_dump(mode='json')
            audit(s,user,'order.updated:'+oid)
        return body

    @app.post('/drivers',status_code=201)
    def add_driver(body:Driver,user=Depends(admin)):
        if body.state not in ('AVAILABLE','OFF_DUTY','ON_BREAK','UNAVAILABLE'): raise HTTPException(422,'Invalid initial state')
        with Session.begin() as s:
            advance(s,s.get(Revision,1).value)
            s.add(DriverRow(id=body.id,data=body.model_dump(mode='json')))
            audit(s,user,'driver.created:'+body.id)
        return body

    @app.put('/drivers/{did}')
    def edit_driver(did:str,body:Driver,revision:int,user=Depends(admin)):
        with Session.begin() as s:
            advance(s,revision)
            row=s.get(DriverRow,did)
            if not row: raise HTTPException(404,'Driver not found')
            if body.id!=did or s.scalar(select(Trip).where(Trip.active_driver==did)): raise Conflict('Driver has an active trip')
            if body.state not in ('AVAILABLE','OFF_DUTY','ON_BREAK','UNAVAILABLE'): raise HTTPException(422,'Use trip actions to change delivery state')
            row.data=body.model_dump(mode='json')
            audit(s,user,'driver.updated:'+did)
        return body

    @app.post('/plans')
    def plan(user=Depends(staff)):
        with Session() as s: settings,orders,drivers,rev=snapshot(s)
        pending=[o for o in orders if o.status in ('RECEIVED','PREPARING','READY')]
        if len(pending)>100 or len(drivers)>30:
            raise HTTPException(422,'This release supports at most 100 pending orders and 30 drivers per planning run')
        matrix=provider(settings.provider).matrix([settings.depot]+[o.location for o in pending])
        result=optimise(pending,drivers,settings,matrix,utcnow(),rev)
        with Session.begin() as s:
            if s.get(Revision,1).value!=rev: raise Conflict('State changed while solving; regenerate')
            s.add(Proposal(id=result.id,data=result.model_dump(mode='json')))
            audit(s,user,'plan.generated:'+result.id)
        return result

    class Commit(BaseModel):
        route_index:int=Field(ge=0)
        idempotency_key:str=Field(min_length=8,max_length=80)
    @app.post('/plans/{pid}/commit')
    def commit(pid:str,body:Commit,user=Depends(staff)):
        key=user.id+':'+body.idempotency_key
        fingerprint=f'{pid}:{body.route_index}'
        with Session.begin() as s:
            existing=s.get(Idempotency,key)
            if existing:
                if existing.fingerprint!=fingerprint: raise Conflict('Idempotency key reused for another operation')
                return existing.result
            row=s.get(Proposal,pid)
            if not row: raise HTTPException(404,'Proposal not found')
            plan=Plan.model_validate(row.data)
            advance(s,plan.revision)
            if (utcnow()-plan.created_at).total_seconds()>120: raise Conflict('Proposal expired; regenerate')
            if body.route_index>=len(plan.routes): raise HTTPException(404,'Route not found')
            route=plan.routes[body.route_index]
            if not route.executable: raise Conflict('Provisional route: confirm driver return and food readiness, then regenerate')
            settings,orders,drivers,_=snapshot(s)
            by_id={o.id:o for o in orders}
            driver=next(d for d in drivers if d.id==route.driver_id)
            if driver.state!='AVAILABLE' or any(by_id[x].status!='READY' for x in route.order_ids): raise Conflict('Orders or driver unavailable')
            chosen={oid:by_id[oid] for oid in route.order_ids}
            matrix=provider(settings.provider).matrix([settings.depot]+[o.location for o in chosen.values()])
            refreshed=evaluate(route.order_ids,driver,chosen,matrix,{oid:i+1 for i,oid in enumerate(chosen)},settings,utcnow())
            if refreshed is None or not refreshed.executable:
                raise Conflict('Route no longer feasible; regenerate')
            route=refreshed
            tid=str(uuid4())
            s.add(Trip(id=tid,driver_id=driver.id,active_driver=driver.id,status='RESERVED',data=route.model_dump(mode='json')))
            s.flush()
            for i,oid in enumerate(route.order_ids):
                s.add(StopRow(trip_id=tid,order_id=oid,sequence=i,status='PENDING'))
                order=by_id[oid].model_copy(update={'status':'ASSIGNED'})
                s.get(OrderRow,oid).data=order.model_dump(mode='json')
            s.get(DriverRow,driver.id).data=driver.model_copy(update={'state':'RESERVED'}).model_dump(mode='json')
            result={'trip_id':tid}
            s.add(Idempotency(key=key,fingerprint=fingerprint,result=result))
            audit(s,user,'trip.committed:'+tid)
            return result

    @app.post('/trips/{tid}/release')
    def release(tid:str,user=Depends(staff)):
        with Session.begin() as s:
            trip=trip_access(s,tid,user)
            if trip.status=='RELEASED': return {'status':'RELEASED'}
            if trip.status!='RESERVED': raise Conflict('Only uncollected trips may be released')
            advance(s,s.get(Revision,1).value)
            for stop in s.scalars(select(StopRow).where(StopRow.trip_id==tid)):
                row=s.get(OrderRow,stop.order_id)
                row.data={**row.data,'status':'READY'}
                s.delete(stop)
            trip.status='RELEASED';trip.active_driver=None
            driver=s.get(DriverRow,trip.driver_id)
            driver.data={**driver.data,'state':'AVAILABLE'}
            audit(s,user,'trip.released:'+tid)
        return {'status':'RELEASED'}

    @app.post('/trips/{tid}/depart')
    def depart(tid:str,user=Depends(current)):
        with Session() as s:
            trip=trip_access(s,tid,user)
            if trip.status in ('ON_DELIVERY','RETURNING','COMPLETED'): return {'status':trip.status}
            settings,orders,drivers,rev=snapshot(s)
            route=trip.data
        selected={o.id:o for o in orders if o.id in route['order_ids']}
        driver=next(d for d in drivers if d.id==trip.driver_id).model_copy(update={'state':'AVAILABLE'})
        matrix=provider(settings.provider).matrix([settings.depot]+[o.location for o in selected.values()])
        now=utcnow()
        fresh=evaluate(route['order_ids'],driver,selected,matrix,{oid:i+1 for i,oid in enumerate(selected)},settings.model_copy(update={'loading_seconds':0}),now)
        if fresh is None: raise Conflict('Departure is no longer feasible; manager intervention required')
        with Session.begin() as s:
            advance(s,rev)
            trip=trip_access(s,tid,user)
            trip.status='ON_DELIVERY'
            trip.data={**fresh.model_dump(mode='json'),'actual_departure':now.isoformat()}
            for oid,order in selected.items():
                s.get(OrderRow,oid).data=order.model_copy(update={'status':'OUT_FOR_DELIVERY','picked_up_at':now}).model_dump(mode='json')
            s.get(DriverRow,driver.id).data=driver.model_copy(update={'state':'ON_DELIVERY'}).model_dump(mode='json')
            audit(s,user,'trip.departed:'+tid)
        return {'status':'ON_DELIVERY'}

    class Completion(BaseModel):
        failed:bool=False
    @app.post('/trips/{tid}/stops/{oid}/complete')
    def complete(tid:str,oid:str,body:Completion,user=Depends(current)):
        with Session.begin() as s:
            trip=trip_access(s,tid,user)
            stops=list(s.scalars(select(StopRow).where(StopRow.trip_id==tid).order_by(StopRow.sequence)))
            stop=next((x for x in stops if x.order_id==oid),None)
            if not stop: raise HTTPException(404,'Stop not found')
            target='FAILED' if body.failed else 'DELIVERED'
            if stop.status==target:return {'status':target}
            if stop.status!='PENDING':raise Conflict('Stop already completed with a different outcome')
            if trip.status!='ON_DELIVERY':raise Conflict('Trip has not departed')
            if next(x for x in stops if x.status=='PENDING').order_id!=oid:raise Conflict('Complete stops in route order')
            advance(s,s.get(Revision,1).value)
            row=s.get(OrderRow,oid)
            order=Order.model_validate(row.data)
            if not body.failed and utcnow()<order.earliest:raise Conflict('Scheduled delivery window has not opened')
            row.data=order.model_copy(update={'status':target,'delivered_at':None if body.failed else utcnow()}).model_dump(mode='json')
            stop.status=target
            if all(x.status!='PENDING' for x in stops):
                trip.status='RETURNING'
                d=s.get(DriverRow,trip.driver_id)
                d.data={**d.data,'state':'RETURNING','available_at':trip.data['returns_at']}
            audit(s,user,'stop.'+target.lower()+':'+oid)
        return {'status':target}

    @app.post('/trips/{tid}/return')
    def returned(tid:str,user=Depends(current)):
        with Session.begin() as s:
            trip=trip_access(s,tid,user)
            if trip.status=='COMPLETED':return {'status':'COMPLETED'}
            if trip.status!='RETURNING':raise Conflict('Complete all deliveries before confirming return')
            advance(s,s.get(Revision,1).value)
            trip.status='COMPLETED'; trip.active_driver=None
            trip.data={**trip.data,'actual_return':utcnow().isoformat()}
            d=s.get(DriverRow,trip.driver_id)
            off=d.data['waiter'] or Driver.model_validate(d.data).shift_end<=utcnow()
            d.data={**d.data,'state':'OFF_DUTY' if off else 'AVAILABLE','available_at':utcnow().isoformat(),
                    'authorised':False if d.data['waiter'] else d.data['authorised']}
            audit(s,user,'trip.returned:'+tid)
        return {'status':'COMPLETED'}

    @app.get('/analytics')
    def analytics(user=Depends(staff)):
        with Session() as s:
            _,orders,_,_=snapshot(s)
            delivered=[o for o in orders if o.delivered_at]
            late=[(o.delivered_at-o.deadline).total_seconds()/60 for o in delivered]
            return {'total_orders':len(orders),'delivered':len(delivered),
                    'on_time_percent':100*sum(x<=0 for x in late)/len(late) if late else None,
                    'average_lateness_minutes':sum(max(0,x) for x in late)/len(late) if late else None,
                    'basis':'Actual recorded delivery timestamps; no claimed savings'}
    @app.get('/analytics/export')
    def export(user=Depends(staff)):
        with Session() as s: _,orders,_,_=snapshot(s)
        out=io.StringIO(); writer=csv.writer(out)
        writer.writerow(['order_id','status','received_at','deadline','delivered_at'])
        for o in orders:
            # Prefix formula-leading identifiers for spreadsheet safety.
            oid="'"+o.id if o.id.startswith(('=','+','-','@')) else o.id
            writer.writerow([oid,o.status,o.received_at.isoformat(),o.deadline.isoformat(),o.delivered_at.isoformat() if o.delivered_at else ''])
        return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=deliveries.csv'})

    @app.websocket('/events')
    async def events(ws:WebSocket):
        if ws.headers.get('origin')!=os.getenv('APP_ORIGIN','http://localhost:3000') or not subject(ws.cookies.get('session','')):
            await ws.close(code=1008);return
        await ws.accept()
        previous=None
        try:
            while True:
                with Session() as s: rev=s.get(Revision,1).value
                if rev!=previous:
                    await ws.send_json({'revision':rev});previous=rev
                await asyncio.sleep(2)
        except WebSocketDisconnect: pass
    return app

app=create_app()
