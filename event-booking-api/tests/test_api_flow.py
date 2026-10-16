"""HTTP-level contract tests using a disposable in-memory DB and mocked auth.
They exercise real routers, booking/payment services and Pydantic validation.
Not a replacement for real JWT, PostgreSQL concurrency or live payment tests.
"""
import importlib
import sys
import types
from datetime import datetime, timedelta, timezone
import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import models
from utils.helpers import get_db

@pytest.fixture
def environment(monkeypatch):
    monkeypatch.setenv("ENABLE_MOCK_PAYMENTS", "true")
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread":False})
    models.Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    session.add_all([models.User(username="admin", password="x", is_active=True, role="admin"),
                     models.User(username="alice", password="x", is_active=True, role="user"),
                     models.User(username="bob", password="x", is_active=True, role="user")])
    session.commit()
    auth = types.ModuleType("core.security")
    auth.get_current_user = lambda: None
    fake_limiter = types.ModuleType("core.limiter")
    fake_limiter.limiter = types.SimpleNamespace(limit=lambda *args: (lambda fn:fn))
    cloud = types.ModuleType("cloudinary")
    cloud.config = lambda **kw: None
    cloud.__path__ = []
    cloud_upload = types.ModuleType("cloudinary.uploader")
    cloud_upload.upload = lambda *args, **kw: {"secure_url":"https://example.org/fake.jpg"}
    cloud.uploader = cloud_upload
    modules = {"core.security":auth, "core.limiter":fake_limiter,
               "cloudinary":cloud,"cloudinary.uploader":cloud_upload}
    with monkeypatch.context() as mp:
        for name, module in modules.items(): mp.setitem(sys.modules, name, module)
        for name in ["routers.bookings","routers.payment","routers.seating","routers.events","core.cloudinary_config"]:
            sys.modules.pop(name, None)
        imported = {n:importlib.import_module("routers."+n) for n in ("bookings","payment","seating","events")}
        app=FastAPI()
        app.include_router(imported["bookings"].router, prefix="/api/bookings")
        app.include_router(imported["payment"].router, prefix="/api/payment")
        app.include_router(imported["seating"].router, prefix="/api/seating")
        app.include_router(imported["events"].router, prefix="/api/events")
        def db_dep(): yield session
        def test_auth(request:Request):
            username = request.headers.get("authorization", "").removeprefix("Bearer ")
            account = session.query(models.User).filter_by(username=username).first()
            if not account: raise HTTPException(status_code=401, detail="Sign in")
            return {"username":account.username,"role":account.role}
        app.dependency_overrides[get_db] = db_dep
        app.dependency_overrides[auth.get_current_user] = test_auth
        try:
            with TestClient(app) as client:
                yield client, session
        finally:
            session.close(); engine.dispose()
            for name in list(imported)+["core.cloudinary_config"]:
                sys.modules.pop("routers."+name if name in imported else name,None)

def headers(user="alice"): return {"Authorization":f"Bearer {user}"}
def expect_ok(response):
    assert response.status_code in (200,201), (response.status_code,response.text)
    return response.json()

def event_for(db, kind):
    event=models.Event(title=f"{kind} Concert", location="Auditorium", inventory_type=kind,
                       status="published", date_time=datetime.now(timezone.utc)+timedelta(days=4))
    db.add(event);db.commit();return event

def layout_for(client, event, kind):
    layout=expect_ok(client.post(f"/api/seating/admin/events/{event.id}/layout",json={"event_id":event.id,"name":"Hall"},headers=headers("admin")))
    z=expect_ok(client.post(f"/api/seating/admin/layouts/{layout['id']}/zones",json={"name":"VIP","code":"VIP","zone_type":"seated" if kind=="seat" else "general","capacity":3,"base_price":499},headers=headers("admin")))
    return z

def test_assigned_seat_http_purchase_and_customer_isolation(environment):
    client,db=environment
    draft=expect_ok(client.post("/api/events/",json={"title":"Seat Test","location":"Hall","inventory_type":"seat"},headers=headers("admin")))
    assert draft["status"]=="draft"
    assert all(e["id"]!=draft["id"] for e in expect_ok(client.get("/api/events/")))
    assert client.put(f"/api/events/{draft['id']}",json={"status":"published"},headers=headers("admin")).status_code==409
    event=db.get(models.Event,draft["id"])
    zone=layout_for(client,event,"seat")
    row=expect_ok(client.post(f"/api/seating/admin/zones/{zone['id']}/rows",json={"zone_id":zone["id"],"row_label":"A","seat_count":2},headers=headers("admin")))
    expect_ok(client.put(f"/api/events/{event.id}",json={"status":"published"},headers=headers("admin")))
    inventory=expect_ok(client.get(f"/api/events/{event.id}/inventory"))
    seat_id=inventory["zones"][0]["seats"][0]["id"]
    payload={"event_id":event.id,"seat_ids":[seat_id],"idempotency_key":"http-seat-1"}
    booking=expect_ok(client.post("/api/bookings",json=payload,headers=headers()))
    assert booking["status"]=="held" and booking["items"][0]["label"]=="VIP-A-1"
    assert expect_ok(client.post("/api/bookings",json=payload,headers=headers()))["id"]==booking["id"]
    assert client.get(f"/api/bookings/{booking['id']}/status",headers=headers("bob")).status_code==404
    assert client.post("/api/bookings",json={"event_id":event.id,"seat_ids":[seat_id]},headers=headers("bob")).status_code==400
    assert client.get(f"/api/bookings/{booking['id']}/tickets",headers=headers()).status_code==409
    payment=expect_ok(client.post("/api/payment/",json={"booking_id":booking["id"],"method":"mock"},headers=headers()))
    assert payment["amount"]==499
    assert expect_ok(client.post("/api/payment/",json={"booking_id":booking["id"],"method":"mock"},headers=headers()))["id"]==payment["id"]
    assert client.post("/api/payment/",json={"booking_id":booking["id"],"method":"mock"},headers=headers("bob")).status_code==404
    details=expect_ok(client.get(f"/api/bookings/{booking['id']}/status",headers=headers()))
    assert details["status"]=="confirmed" and details["payment_status"]=="paid"
    assert details["payment"]["transaction_id"]
    assert len(details["ticket_details"])==1 and details["ticket_details"][0]["label"]=="VIP-A-1"
    assert len(expect_ok(client.get(f"/api/bookings/{booking['id']}/tickets",headers=headers())))==1
    assert expect_ok(client.get("/api/bookings/my-bookings",headers=headers()))[0]["ticket_details"][0]["ticket_code"]
    assert client.delete(f"/api/bookings/book/{booking['id']}",headers=headers()).status_code==409

def test_pooled_zone_and_pass_http_limits_and_release(environment):
    client,db=environment
    zone_event=event_for(db,"zone")
    zone=layout_for(client,zone_event,"zone")
    held=expect_ok(client.post("/api/bookings",json={"event_id":zone_event.id,"zone_id":zone["id"],"tickets":2},headers=headers()))
    assert held["total_amount"]==998 and held["items"][0]["quantity"]==2
    assert client.post("/api/bookings",json={"event_id":zone_event.id,"zone_id":zone["id"],"tickets":2},headers=headers("bob")).status_code==400
    expect_ok(client.delete(f"/api/bookings/book/{held['id']}",headers=headers()))
    assert expect_ok(client.get(f"/api/events/{zone_event.id}/inventory"))["zones"][0]["available"]==3
    general=event_for(db,"general")
    kind=expect_ok(client.post(f"/api/events/{general.id}/ticket-types",json={"event_id":general.id,"name":"Early Bird","price":299,"inventory_limit":2},headers=headers("admin")))
    held=expect_ok(client.post("/api/bookings",json={"event_id":general.id,"ticket_type_id":kind["id"],"tickets":2},headers=headers("bob")))
    assert held["total_amount"]==598 and held["items"][0]["label"]=="Early Bird"
    assert client.post("/api/payment/",json={"booking_id":held["id"],"method":"upi"},headers=headers("bob")).status_code==422
    expect_ok(client.post("/api/payment/",json={"booking_id":held["id"],"method":"mock"},headers=headers("bob")))
    assert len(expect_ok(client.get(f"/api/bookings/{held['id']}/tickets",headers=headers("bob"))))==2
    assert expect_ok(client.get(f"/api/events/{general.id}/inventory"))["ticket_types"][0]["available"]==0

def test_expired_hold_not_payable_and_mock_opt_in(environment,monkeypatch):
    client,db=environment
    event=event_for(db,"general")
    kind=models.TicketType(event_id=event.id,name="Standard",price=10,inventory_limit=4)
    db.add(kind);db.commit()
    held=expect_ok(client.post("/api/bookings",json={"event_id":event.id,"ticket_type_id":kind.id},headers=headers()))
    monkeypatch.setenv("ENABLE_MOCK_PAYMENTS","false")
    assert client.post("/api/payment/",json={"booking_id":held["id"],"method":"mock"},headers=headers()).status_code==503
    monkeypatch.setenv("ENABLE_MOCK_PAYMENTS","true")
    db.get(models.Booking,held["id"]).expires_at=datetime.now(timezone.utc)-timedelta(minutes=1)
    db.commit()
    assert expect_ok(client.get(f"/api/bookings/{held['id']}/status",headers=headers()))["status"]=="expired"
    assert client.post("/api/payment/",json={"booking_id":held["id"],"method":"mock"},headers=headers()).status_code==409
    assert db.query(models.Payment).count()==0

def test_public_event_cards_use_actual_inventory_and_unlimited_passes(environment):
    client,db=environment
    event=event_for(db,"general")
    kind=expect_ok(client.post(f"/api/events/{event.id}/ticket-types",
        json={"event_id":event.id,"name":"Anytime","price":350,"inventory_limit":None},
        headers=headers("admin")))
    listing=expect_ok(client.get("/api/events/"))
    card=next(row for row in listing if row["id"]==event.id)
    assert card["price"]==350 and card["available_seats"] is None
    assert any(row["id"]==event.id for row in expect_ok(client.get("/api/events/?min_price=300")))
    assert all(row["id"]!=event.id for row in expect_ok(client.get("/api/events/?max_price=300")))
    details=expect_ok(client.get(f"/api/events/{event.id}/inventory"))
    assert details["ticket_types"][0]["available"] is None
    held=expect_ok(client.post("/api/bookings",json={"event_id":event.id,"ticket_type_id":kind["id"],"tickets":10},headers=headers()))
    assert held["total_amount"] == 3500
    assert client.post("/api/bookings",json={"event_id":event.id,"ticket_type_id":kind["id"],"tickets":11},headers=headers("bob")).status_code==422
