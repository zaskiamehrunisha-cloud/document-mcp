import os
import subprocess
import time

# Path to PostgreSQL configuration
pg_hba_path = r"C:\Program Files\PostgreSQL\18\data\pg_hba.conf"
pg_hba_backup = r"C:\Program Files\PostgreSQL\18\data\pg_hba.conf.backup"

print("Step 1: Stopping PostgreSQL service...")
subprocess.run(["net", "stop", "postgresql-x64-18"], capture_output=True)
time.sleep(2)

print("Step 2: Backing up pg_hba.conf...")
if os.path.exists(pg_hba_path):
    with open(pg_hba_path, 'r') as f:
        content = f.read()
    with open(pg_hba_backup, 'w') as f:
        f.write(content)
    print("  ✓ Backup created")
else:
    print(f"  ✗ File not found: {pg_hba_path}")
    exit(1)

print("Step 3: Modifying pg_hba.conf to use trust authentication...")
content = content.replace('md5', 'trust')
with open(pg_hba_path, 'w') as f:
    f.write(content)
print("  ✓ Modified")

print("Step 4: Starting PostgreSQL service...")
subprocess.run(["net", "start", "postgresql-x64-18"], capture_output=True)
time.sleep(3)

print("Step 5: Setting postgres password to 'postgres'...")
env = os.environ.copy()
env['PGPASSWORD'] = 'postgres'
result = subprocess.run(
    [r"C:\Program Files\PostgreSQL\18\bin\psql.exe", "-U", "postgres", "-c", 
     "ALTER USER postgres WITH PASSWORD 'postgres';"],
    capture_output=True,
    text=True,
    env=env
)
if result.returncode == 0:
    print("  ✓ Password set successfully")
else:
    print(f"  Output: {result.stdout}")
    print(f"  Error: {result.stderr}")

print("Step 6: Restoring pg_hba.conf...")
if os.path.exists(pg_hba_backup):
    with open(pg_hba_backup, 'r') as f:
        original_content = f.read()
    with open(pg_hba_path, 'w') as f:
        f.write(original_content)
    print("  ✓ Restored")

print("Step 7: Restarting PostgreSQL service...")
subprocess.run(["net", "stop", "postgresql-x64-18"], capture_output=True)
time.sleep(2)
subprocess.run(["net", "start", "postgresql-x64-18"], capture_output=True)
time.sleep(2)

print("\n✓ Password reset complete!")
print("  New postgres password: postgres")
print("\nNow run: py setup_db.py")