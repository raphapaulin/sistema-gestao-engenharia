@echo off
cd /d "%~dp0"

echo Fazendo backup opcional do banco demo...
echo.

.\.venv\Scripts\python.exe scripts\backup_db.py --database data\demo.db

echo.
echo Backup finalizado.
pause
