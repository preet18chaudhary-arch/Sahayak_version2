from app.database.database import engine, Base, init_db
from app.database import models

init_db()

print("Sahayak database created successfully.")
print("Database tables:")
for table in Base.metadata.sorted_tables:
    print(f" - {table.name}")
