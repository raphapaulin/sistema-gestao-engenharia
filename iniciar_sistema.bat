@echo off
cd /d "%~dp0"
set DATABASE_URL=sqlite:///data/demo.db

echo Iniciando Sistema de Gestao de Engenharia Demo...
echo.
echo Acesse no proprio computador:
echo http://127.0.0.1:8000/
echo.
echo Para acessar de outro computador, use o IP deste computador na rede.
echo Exemplo: http://192.168.0.6:8000/
echo.
echo Para encerrar o sistema, pressione CTRL + C nesta janela.
echo.

.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

pause
