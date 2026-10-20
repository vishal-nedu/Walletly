from sqlalchemy import text
from database import engine


def test_database_connection_uses_wallet_test():
    with engine.connect() as connection:
        database_name = connection.execute(
            text("SELECT current_database()")
        ).scalar_one()

    assert database_name == "wallet_test"