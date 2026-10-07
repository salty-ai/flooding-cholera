"""Shared pytest fixtures.

The application engine points at PostgreSQL/PostGIS. Tests that need a
deterministic database — an *empty* one in particular — bind the ORM to an
in-memory SQLite database instead and override the `get_db` dependency. Two
shims make the PostGIS-flavoured models loadable on SQLite:

  * geometry columns compile to TEXT (no geometry is exercised by these tests);
  * GeoAlchemy2's SpatiaLite DDL hooks are bypassed for the sqlite dialect.

Both shims are scoped to the sqlite dialect, so PostgreSQL behaviour is
unchanged for the tests that talk to a real database.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import geoalchemy2.admin as _ga_admin
from geoalchemy2 import Geometry
from geoalchemy2.admin import dialects as _ga_dialects


@compiles(Geometry, "sqlite")
def _geometry_as_text_on_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "TEXT"


_ga_select_dialect = _ga_admin.select_dialect


def _select_dialect_without_spatialite(name):
    """Skip the SpatiaLite DDL hooks that plain SQLite cannot satisfy."""
    if name == "sqlite":
        return _ga_dialects.common
    return _ga_select_dialect(name)


_ga_admin.select_dialect = _select_dialect_without_spatialite

import app.models  # noqa: E402,F401  (registers every table on Base.metadata)
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


#: Spatial functions GeoAlchemy2 wraps around geometry binds/columns. On this
#: engine they are pass-throughs: the models are exercised, the geometry is not.
_NOOP_SPATIAL_FUNCTIONS = (
    "GeomFromEWKT", "ST_GeomFromEWKT", "GeomFromEWKB", "ST_GeomFromEWKB",
    "AsEWKB", "ST_AsEWKB", "AsEWKT", "ST_AsEWKT",
)


@pytest.fixture
def sqlite_engine():
    """A fresh, empty in-memory database with the full application schema."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _register_noop_spatial_functions(dbapi_connection, _record):
        for name in _NOOP_SPATIAL_FUNCTIONS:
            dbapi_connection.create_function(name, 1, lambda value: value)

    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(sqlite_engine):
    """Session bound to the in-memory database; shared with the test client."""
    factory = sessionmaker(bind=sqlite_engine, autoflush=False, autocommit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sqlite_client(db_session):
    """TestClient whose request handlers see the in-memory database.

    Instantiated without the context manager on purpose: entering it would run
    the app lifespan, which initialises and auto-seeds the *real* database.
    """
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)
