from app.database.models import Base
from app.database.connection import engine

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("Tables created successfully")

