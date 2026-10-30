import os
from sqlalchemy import create_engine, String, Integer, JSON, ForeignKey, UniqueConstraint, update, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase): pass
class Revision(Base):
    __tablename__ = 'revision'
    id: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[int] = mapped_column(default=0)
class Config(Base):
    __tablename__ = 'restaurant'
    id: Mapped[int] = mapped_column(primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)
class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    password: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(20))
    driver_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
class OrderRow(Base):
    __tablename__ = 'orders'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)
class DriverRow(Base):
    __tablename__ = 'drivers'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)
class Proposal(Base):
    __tablename__ = 'proposals'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)
class Trip(Base):
    __tablename__ = 'trips'
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    driver_id: Mapped[str] = mapped_column(ForeignKey('drivers.id'))
    active_driver: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(30))
    data: Mapped[dict] = mapped_column(JSON)
class StopRow(Base):
    __tablename__ = 'stops'
    __table_args__ = (UniqueConstraint('trip_id', 'sequence'),)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trip_id: Mapped[str] = mapped_column(ForeignKey('trips.id'))
    order_id: Mapped[str] = mapped_column(ForeignKey('orders.id'), unique=True)
    sequence: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default='PENDING')
class Audit(Base):
    __tablename__ = 'audit'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(100))
    at: Mapped[str] = mapped_column(String(40))
class Idempotency(Base):
    __tablename__ = 'idempotency'
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(300))
    result: Mapped[dict] = mapped_column(JSON)


def factory(url=None):
    url = url or os.getenv('DATABASE_URL', 'sqlite:///./dispatch.db')
    engine = create_engine(url, connect_args={'check_same_thread':False,'timeout':30} if url.startswith('sqlite') else {}, pool_pre_ping=True)
    if url.startswith('sqlite'):
        @event.listens_for(engine, 'connect')
        def sqlite_foreign_keys(connection, record):
            connection.execute('PRAGMA foreign_keys=ON')
    return engine, sessionmaker(engine, expire_on_commit=False)


class Conflict(Exception): pass


def advance(session, expected):
    result = session.execute(update(Revision).where(Revision.id==1,Revision.value==expected).values(value=expected+1))
    if result.rowcount != 1:
        raise Conflict('State changed. Refresh and regenerate the recommendation.')
