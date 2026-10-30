import httpx
import pytest
from app.routing import GoogleProvider,RoutingError
from app.domain import Settings,Location

@pytest.fixture
def google(monkeypatch):
    monkeypatch.setenv('GOOGLE_MAPS_API_KEY','test-only-key')
    return GoogleProvider()

def fake_client(monkeypatch,callback):
    real=httpx.Client
    monkeypatch.setattr(httpx,'Client',lambda **kw:real(transport=httpx.MockTransport(callback),trust_env=False))

def test_google_preserves_asymmetric_response(google,monkeypatch):
    def callback(request):
        assert request.url.path=='/distanceMatrix/v2:computeRouteMatrix'
        assert 'status' in request.headers['X-Goog-FieldMask']
        return httpx.Response(200,json=[{'originIndex':i,'destinationIndex':j,'condition':'ROUTE_EXISTS','duration':f'{v}s','distanceMeters':v*7} for i,j,v in [(0,0,0),(0,1,60),(1,0,180),(1,1,0)]])
    fake_client(monkeypatch,callback)
    m=google.matrix([Settings().depot,Location(address='Verified destination',lat=52.15,lng=-.46)])
    assert m.seconds==[[0,60],[180,0]]
    assert m.metres[1][0]==1260

def test_google_incomplete_matrix_rejected(google,monkeypatch):
    fake_client(monkeypatch,lambda request:httpx.Response(200,json=[]))
    with pytest.raises(RoutingError,match='Incomplete'):google.matrix([Settings().depot])

def test_google_element_error_rejected(google,monkeypatch):
    fake_client(monkeypatch,lambda request:httpx.Response(200,json=[{'originIndex':0,'destinationIndex':0,'status':{'code':13}}]))
    with pytest.raises(RoutingError,match='element error'):google.matrix([Settings().depot])

def test_google_unreachable_explicit(google,monkeypatch):
    fake_client(monkeypatch,lambda request:httpx.Response(200,json=[{'originIndex':0,'destinationIndex':0,'condition':'ROUTE_NOT_FOUND'}]))
    assert google.matrix([Settings().depot]).seconds==[[None]]

def test_google_quota_failure_no_demo_fallback(google,monkeypatch):
    calls=[]
    def callback(request):calls.append(request);return httpx.Response(429,json={})
    fake_client(monkeypatch,callback)
    monkeypatch.setattr('app.routing.time.sleep',lambda seconds:None)
    with pytest.raises(RoutingError,match='quota'):google.matrix([Settings().depot])
    assert len(calls)==3
