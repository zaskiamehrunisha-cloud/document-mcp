@echo off
set PGPASSWORD=Zaskiaarizani
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -f create_user.sql
pause