import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import cloudinary
from dotenv import load_dotenv 

# Load environment variables from .env file
load_dotenv()


cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# Try to create the DB if it doesn't exist
try:
    conn = psycopg2.connect(dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"), password=os.getenv("DB_PASS"), host=os.getenv("DB_HOST"))
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE {os.getenv('DB_NAME')}")
    cur.close()
    conn.close()
except psycopg2.errors.DuplicateDatabase:
    pass
except Exception as e:
    print(f"Warning: {e}")

# Setup SQLAlchemy engine
SQLALCHEMY_DATABASE_URL = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
