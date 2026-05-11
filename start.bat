@echo off
echo ====================================
echo  Facebook Ads Preview - Starting...
echo ====================================
cd /d "%~dp0"

if not exist .env (
    echo.
    echo [!] ไม่พบไฟล์ .env - copy .env.example .env แล้วใส่ Token
    pause
    exit /b 1
)

if not exist node_modules (
    echo [>>] กำลังติดตั้ง dependencies...
    call npm install
)

echo.
echo [OK] Server กำลังเริ่ม...
echo [OK] เปิดเบราว์เซอร์ที่ http://localhost:8000
echo.
start "" "http://localhost:8000"
node server.js
pause
