from datetime import datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.domain import *
from app.routing import DemoProvider,Matrix,RoutingError,NODES
from app.optimisation import optimise
from app.main import create_app
from app.db import Base
from app.seed import seed
NOW=datetime(2026,10,30,18,tzinfo=timezone.utc)
def order(oid,node='north',**kw):
    lat,lng=NODES[node]
    return Order(**(dict(id=oid,location=Location(address='Demo '+node,lat=lat,lng=lng,node=node),received_at=NOW-timedelta(minutes=10),ready_at=NOW,actual_ready_at=NOW,earliest=NOW,deadline=NOW+timedelta(minutes=30),status='READY')|kw))
def driver(oid='d1',**kw):
    return Driver(**(dict(id=oid,name=oid,available_at=NOW,shift_end=NOW+timedelta(hours=3))|kw))
def solve(orders,drivers,**kw):
    settings=Settings(); matrix=DemoProvider().matrix([settings.depot]+[o.location for o in orders])
    return optimise(orders,drivers,settings,matrix,NOW,**kw)
def test_A_standard_grouping():
    p=solve([order('1','north'),order('2','far_north'),order('3','east'),order('4','far_east')],[driver(capacity=2),driver('d2',capacity=2)])
    assert not p.unassigned and len(p.routes)==2
    assert {frozenset(r.order_ids) for r in p.routes}=={frozenset(['1','2']),frozenset(['3','4'])}
def test_B_along_route():
    assert solve([order('outer','far_north'),order('inner','north')],[driver()]).routes[0].order_ids==['inner','outer']
def test_C_asymmetry():
    m=DemoProvider().matrix([Settings().depot,order('a').location])
    assert m.seconds[0][1]==240 and m.seconds[1][0]==420
    assert solve([order('outer','far_north'),order('inner','north')],[driver()]).routes[0].order_ids==['inner','outer']
def test_D_shortage():
    p=solve([order(str(i)) for i in range(8)],[driver(),driver('d2',state='RETURNING',available_at=NOW+timedelta(minutes=10))])
    assert sum(len(r.order_ids) for r in p.routes)==8
    assert not next(r for r in p.routes if r.driver_id=='d2').executable
    assert len({x for r in p.routes for x in r.order_ids})==8
def test_E_scheduled():
    o=order('scheduled',earliest=NOW+timedelta(minutes=10),deadline=NOW+timedelta(minutes=15),kind='SCHEDULED')
    p=solve([o,order('asap','far_north')],[driver()])
    stop=next(s for r in p.routes for s in r.stops if s.order_id=='scheduled')
    assert o.earliest<=stop.arrival<=o.deadline
def test_F_waiter():
    assert solve([order('a')],[driver(waiter=True)]).unassigned
    assert solve([order('a')],[driver(waiter=True,authorised=True,return_by=NOW+timedelta(minutes=20))]).routes
    assert solve([order('a')],[driver(waiter=True,authorised=True,return_by=NOW+timedelta(minutes=5))]).unassigned
def test_G_frozen():
    p=solve([order('old',status='ASSIGNED'),order('urgent',deadline=NOW+timedelta(minutes=3))],[driver()])
    assert all('old' not in r.order_ids for r in p.routes)
    assert p.routes[0].warnings
def test_H_delay():
    p=solve([order('ready'),order('delayed','far_north',status='PREPARING',actual_ready_at=None,ready_at=NOW+timedelta(minutes=15))],[driver(),driver('d2')])
    assert len(p.routes)==2
    assert next(r for r in p.routes if 'ready' in r.order_ids).executable
    assert not next(r for r in p.routes if 'delayed' in r.order_ids).executable
def test_I_infeasible():
    p=solve([order('a')],[]); assert p.unassigned and not p.routes
def test_K_same_address():
    p=solve([order('a'),order('b')],[driver()])
    assert len(p.routes[0].stops)==2 and p.routes[0].travel_seconds==660
def test_L_bad_matrix():
    with pytest.raises(RoutingError):optimise([order('a')],[driver()],Settings(),Matrix([[0]],[[0]],'broken'),NOW)
def test_N_dst():
    with pytest.raises(ValidationError):order('naive',earliest=datetime(2026,10,25,1,30))
    a=order('a',earliest=datetime.fromisoformat('2026-10-25T01:30:00+01:00'))
    b=order('b',earliest=datetime.fromisoformat('2026-10-25T01:30:00+00:00'))
    assert (b.earliest-a.earliest).total_seconds()==3600
def test_O_capacity():
    p=solve([order('large',units=3),order('small')],[driver(capacity=1),driver('d2',capacity=3)])
    assert not p.unassigned and 'large' in next(r for r in p.routes if r.driver_id=='d2').order_ids
def test_fallback():
    p=solve([order('a'),order('b','far_north')],[driver()],force_fallback=True)
    assert 'fallback' in p.solver and len(p.routes)==1
@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('SESSION_SECRET','a'*48);monkeypatch.setenv('DEMO_PASSWORD','testing-password-only')
    app=create_app('sqlite:///'+str(tmp_path/'test.db'));Base.metadata.create_all(app.state.engine);seed(app.state.Session)
    with TestClient(app) as c:
        assert c.post('/auth/login',json={'username':'manager','password':'testing-password-only'}).status_code==200
        yield c
def proposal(c):
    r=c.post('/plans');assert r.status_code==200,r.text;return r.json()
def commit(c,p,key='test-key-123'):
    return c.post('/plans/'+p['id']+'/commit',json={'route_index':0,'idempotency_key':key})
def test_J_stale(client):
    p=proposal(client);st=client.get('/state').json();d=st['drivers'][0];d['state']='UNAVAILABLE'
    assert client.put('/drivers/'+d['id'],params={'revision':st['revision']},json=d).status_code==200
    assert commit(client,p).status_code==409
def test_M_concurrent(client):
    p=proposal(client)
    with ThreadPoolExecutor(2) as pool: results=list(pool.map(lambda k:commit(client,p,k).status_code,['concurrent-one','concurrent-two']))
    assert sorted(results)==[200,409]
    assert len(client.get('/state').json()['trips'])==1
def test_end_to_end(client):
    p=proposal(client);r=commit(client,p);assert r.status_code==200,r.text
    assert commit(client,p).json()==r.json();tid=r.json()['trip_id']
    assert client.post(f'/trips/{tid}/return').status_code==409
    assert client.post(f'/trips/{tid}/depart').status_code==200
    trip=next(t for t in client.get('/state').json()['trips'] if t['id']==tid)
    for stop in trip['stops']:
        url=f"/trips/{tid}/stops/{stop['order_id']}/complete"
        assert client.post(url,json={}).status_code==200
        assert client.post(url,json={}).status_code==200
    assert client.post(f'/trips/{tid}/return').status_code==200
    assert client.post(f'/trips/{tid}/return').status_code==200
    assert client.get('/analytics').json()['delivered']==len(trip['stops'])
def test_authorisation(client):
    p=proposal(client);tid=commit(client,p).json()['trip_id'];other='driver2' if p['routes'][0]['driver_id']=='d1' else 'driver1'
    client.post('/auth/login',json={'username':other,'password':'testing-password-only'})
    assert client.post('/plans').status_code==403
    assert client.post(f'/trips/{tid}/depart').status_code==403
    assert client.get('/state').json()['orders']==[]
    assert client.post('/auth/logout',headers={'Origin':'https://evil.example'}).status_code==403
def test_provider_failure_preserves_state(client,monkeypatch):
    commit(client,proposal(client))
    def fail(*a):raise RoutingError('offline')
    monkeypatch.setattr(DemoProvider,'matrix',fail)
    assert client.post('/plans').status_code==503
    assert client.get('/state').json()['trips'][0]['status']=='RESERVED'
def test_provisional_commit_rejected(client):
    for o in client.get('/state').json()['orders']:
        st=client.get('/state').json();o['status']='PREPARING';o['actual_ready_at']=None
        assert client.put('/orders/'+o['id'],params={'revision':st['revision']},json=o).status_code==200
    p=proposal(client);assert all(not r['executable'] for r in p['routes'])
    assert commit(client,p).status_code==409

def test_release_reserved_trip(client):
    tid=commit(client,proposal(client)).json()['trip_id']
    assert client.post(f'/trips/{tid}/release').status_code==200
    state=client.get('/state').json()
    assert all(o['status']=='READY' for o in state['orders'])
    p=proposal(client);tid=commit(client,p,'new-trip-key').json()['trip_id']
    assert client.post(f'/trips/{tid}/depart').status_code==200
    assert client.post(f'/trips/{tid}/release').status_code==409

def test_expired_freshness_rejected_at_commit(client,monkeypatch):
    p=proposal(client)
    import app.main as main
    # Keep the proposal fresh but make a newly stricter freshness rule observable via evaluate.
    monkeypatch.setattr(main,'evaluate',lambda *args:None)
    assert commit(client,p).status_code==409
    assert client.get('/state').json()['trips']==[]

def test_return_after_shift_remains_readable(client):
    tid=commit(client,proposal(client)).json()['trip_id']
    client.post(f'/trips/{tid}/depart')
    trip=next(t for t in client.get('/state').json()['trips'] if t['id']==tid)
    for stop in trip['stops']:client.post(f"/trips/{tid}/stops/{stop['order_id']}/complete",json={})
    from app.db import DriverRow
    with client.app.state.Session.begin() as s:
        row=s.get(DriverRow,trip['driver_id']);row.data={**row.data,'shift_end':(utcnow()-timedelta(minutes=1)).isoformat()}
    assert client.post(f'/trips/{tid}/return').status_code==200
    state=client.get('/state');assert state.status_code==200
    assert next(d for d in state.json()['drivers'] if d['id']==trip['driver_id'])['state']=='OFF_DUTY'
