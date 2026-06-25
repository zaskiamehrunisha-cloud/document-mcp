import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Connect to default postgres database
try:
    conn = psycopg2.connect(
        host="localhost",
        database="postgres",
        user="postgres",
        password="postgres",
        port="5432"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # Create user
    try:
        cursor.execute("CREATE USER doccontrol WITH PASSWORD 'secure_password';")
        print("✓ Created user 'doccontrol'")
    except Exception as e:
        if "already exists" in str(e):
            print("✓ User 'doccontrol' already exists")
        else:
            print(f"Error creating user: {e}")
    
    # Create database
    try:
        cursor.execute("CREATE DATABASE engineering_docs OWNER doccontrol;")
        print("✓ Created database 'engineering_docs'")
    except Exception as e:
        if "already exists" in str(e):
            print("✓ Database 'engineering_docs' already exists")
        else:
            print(f"Error creating database: {e}")
    
    cursor.close()
    conn.close()
    print("\n✓ Database setup complete!")
    
except Exception as e:
    print(f"✗ Connection failed: {e}")
    print("\nPlease verify:")
    print("1. PostgreSQL service is running")
    print("2. Password 'postgres' is correct for user 'postgres'")
