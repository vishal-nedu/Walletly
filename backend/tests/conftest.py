import os

import pytest
from decouple import config as env_config

# Force the test process to use the dedicated test database.
# This must happen before importing main.py or database.py.
test_database_url = env_config("TEST_DATABASE_URL")
os.environ["DATABASE_URL"] = test_database_url

from fastapi.testclient import TestClient

import databasemodel
from database import Session, engine
from sqlalchemy import text
from sqlalchemy.engine import make_url

# Prevent tests from using the development database.
if make_url(test_database_url).database != "wallet_test":
    raise RuntimeError(
        "Tests must use the wallet_test database."
    )

with engine.connect() as connection:
    actual_database = connection.execute(
        text("SELECT current_database()")
    ).scalar_one()

if actual_database != "wallet_test":
    raise RuntimeError(
        f"Unsafe test database: {actual_database}"
    )

from main import app, get_db


# Ensure the tables exist in the test database.
databasemodel.Base.metadata.create_all(bind=engine)


def override_get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_test_database():
    # PostgreSQL-specific cleanup: test data only.
    with engine.begin() as connection:
        connection.exec_driver_sql(
            'TRUNCATE TABLE transfer, wallet, "user" '
            "RESTART IDENTITY CASCADE"
        )

    yield

    with engine.begin() as connection:
        connection.exec_driver_sql(
            'TRUNCATE TABLE transfer, wallet, "user" '
            "RESTART IDENTITY CASCADE"
        )