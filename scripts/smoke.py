"""Live HTTP smoke test using disposable data and the built Next.js proxy."""
import os
import secrets
import subprocess
import tempfile
import time
from pathlib import Path
import httpx
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
    env=os.environ.copy();env.update(DATABASE_URL='sqlite:///'+tmp+'/smoke.db',SESSION_SECRET=secrets.token_hex(32),DEMO_PASSWORD=secrets.token_urlsafe(24),APP_ORIGIN='http://localhost:3000')
    api_dir=root/'services/api'
    subprocess.run(['python','-m','alembic','upgrade','head'],cwd=api_dir,env=env,check=True)
    subprocess.run(['python','-m','app.seed'],cwd=api_dir,env=env,check=True)
    processes=[]
    try:
        processes.append(subprocess.Popen(['python','-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000'],cwd=api_dir,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        processes.append(subprocess.Popen(['npm','run','start','--','--port','3000'],cwd=root/'apps/web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        with httpx.Client(base_url='http://127.0.0.1:3000',timeout=20,trust_env=False) as client:
            for attempt in range(50):
                try:
                    if client.get('/api/health').status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.2)
            else:raise AssertionError('Application did not become healthy')
            assert client.get('/').status_code==200
            r=client.post('/api/auth/login',json={'username':'manager','password':env['DEMO_PASSWORD']});assert r.status_code==200,r.text
            plan=client.post('/api/plans');assert plan.status_code==200,plan.text
            plan=plan.json();assert plan['routes']
            r=client.post('/api/plans/'+plan['id']+'/commit',json={'route_index':0,'idempotency_key':'smoke-commit-key'});assert r.status_code==200,r.text
            tid=r.json()['trip_id'];r=client.post('/api/trips/'+tid+'/depart');assert r.status_code==200,r.text
            trip=next(t for t in client.get('/api/state').json()['trips'] if t['id']==tid)
            for stop in trip['stops']:
                r=client.post(f"/api/trips/{tid}/stops/{stop['order_id']}/complete",json={});assert r.status_code==200,r.text
            assert client.post('/api/trips/'+tid+'/return').status_code==200
            assert client.get('/api/analytics').json()['delivered']==len(trip['stops'])
            print('PASS: Next.js page, API proxy, login, optimisation, commit, departure, deliveries, return, analytics')
    finally:
        for p in processes:p.terminate()
        for p in processes:
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill()
