# How to Reset PostgreSQL postgres User Password

## Method 1: Using pgAdmin 4 (Easiest)

1. **Open pgAdmin 4** from your Start Menu
2. **Connect to your PostgreSQL server**:
   - Double-click on "PostgreSQL 18" in the browser panel
   - When prompted for a password, try any password you might have set
   - If you can't connect, use Method 2 below

3. **Once connected, reset the password**:
   - Go to **Login/Group Roles** in the browser tree
   - Right-click on **postgres** → **Properties**
   - Go to the **Definition** tab
   - Enter a new password (e.g., "postgres123")
   - Click **Save**

## Method 2: Using Command Line (If pgAdmin doesn't work)

### Step 1: Stop PostgreSQL Service
```cmd
net stop postgresql-x64-18
```

### Step 2: Edit pg_hba.conf
1. Open file: `C:\Program Files\PostgreSQL\18\data\pg_hba.conf` in Notepad (as Administrator)
2. Find the line that looks like:
   ```
   host    all             all             127.0.0.1/32            md5
   ```
3. Change `md5` to `trust`:
   ```
   host    all             all             127.0.0.1/32            trust
   ```
4. Save the file

### Step 3: Start PostgreSQL Service
```cmd
net start postgresql-x64-18
```

### Step 4: Connect Without Password
```cmd
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres
```
(It should connect without asking for a password now)

### Step 5: Reset the Password
Once connected to psql, run:
```sql
ALTER USER postgres WITH PASSWORD 'postgres123';
```

### Step 6: Exit and Restore Security
```sql
\q
```

Then edit `pg_hba.conf` again and change `trust` back to `md5`, save, and restart PostgreSQL:
```cmd
net stop postgresql-x64-18
net start postgresql-x64-18
```

## After Resetting Password

Once you've reset the password, update the `setup_db.py` file with the new password and run:
```cmd
py setup_db.py
```

## Quick Test
Test the new password with:
```cmd
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "SELECT version();"
```
(Enter the new password when prompted)