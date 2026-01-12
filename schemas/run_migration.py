#!/usr/bin/env python3
"""Run database migration script"""
import pg8000

# Connection parameters
conn_params = {
    'host': 'reportmate-database.postgres.database.azure.com',
    'port': 5432,
    'database': 'reportmate',
    'user': 'reportmate_admin',
    'password': 'ReportMateDB2024!',
    'ssl_context': True
}

# Read migration file
with open('004-add-platform-column.sql', 'r') as f:
    sql = f.read()

# Connect and execute
print("Connecting to database...")
conn = pg8000.connect(**conn_params)
cursor = conn.cursor()

print("Running migration...")
# Split by semicolons and execute each statement
statements = [s.strip() for s in sql.split(';') if s.strip()]
for i, statement in enumerate(statements, 1):
    print(f"Executing statement {i}/{len(statements)}...")
    cursor.execute(statement)
    
conn.commit()
print("Migration completed successfully!")

cursor.close()
conn.close()
