from database import engine, Base
# Import your models here
# from your_models_file import YourModel

def create_tables():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    create_tables()
    print("Tables created successfully")
