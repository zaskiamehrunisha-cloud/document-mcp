@echo off
echo Resetting PostgreSQL postgres user password...

REM Stop PostgreSQL service
net stop postgresql-x64-18

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Backup pg_hba.conf
copy "C:\Program Files\PostgreSQL\18\data\pg_hba.conf" "C:\Program Files\PostgreSQL\18\data\pg_hba.conf.backup"

REM Modify pg_hba.conf to use trust authentication for local connections
powershell -Command "(Get-Content 'C:\Program Files\PostgreSQL\18\data\pg_hba.conf') -replace 'md5', 'trust' | Set-Content 'C:\Program Files\PostgreSQL\18\data\pg_hba.conf'"

REM Start PostgreSQL service
net start postgresql-x64-18

REM Wait for service to start
timeout /t 3 /nobreak >nul

REM Reset postgres password
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "ALTER USER postgres WITH PASSWORD 'postgres';"

REM Restore pg_hba.conf
copy "C:\Program Files\PostgreSQL\18\data\pg_hba.conf.backup" "C:\Program Files\PostgreSQL\18\data\pg_hba.conf"

REM Restart PostgreSQL service
net stop postgresql-x64-18
timeout /t 2 /nobreak >nul
net start postgresql-x64-18

echo.
echo Password has been reset to: postgres
echo.
pause