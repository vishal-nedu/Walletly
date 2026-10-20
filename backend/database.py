from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from decouple import config
DATABASE_URL = config("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(autocommit=False,autoflush=False,bind=engine)