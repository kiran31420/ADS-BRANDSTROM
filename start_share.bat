@echo off
cd /d "%~dp0"
set NGROK="C:\Users\Karum\AppData\Local\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe"

echo ====================================
echo  Facebook Ads Preview - Starting...
echo ====================================
echo.

:: Stop old processes
taskkill /f /im node.exe >nul 2>&1
taskkill /f /im ngrok.exe >nul 2>&1
timeout /t 1 /nobreak >nul

:: Start Node server
start "AdsServer" /min node server.js
timeout /t 2 /nobreak >nul

:: Start ngrok
start "ngrok" /min %NGROK% http 8000
timeout /t 5 /nobreak >nul

:: Get URL via PowerShell
for /f "delims=" %%i in ('powershell -command "(Invoke-WebRequest http://localhost:4040/api/tunnels -UseBasicParsing | ConvertFrom-Json).tunnels | Where-Object {$_.proto -eq 'https'} | Select-Object -ExpandProperty public_url"') do set URL=%%i

echo.
echo ====================================
echo  URL สำหรับส่งให้ทีม:
echo.
echo   %URL%
echo.
echo ====================================
echo  เปิดเบราว์เซอร์...
echo  (อย่าปิดหน้าต่างนี้ ไม่งั้นทีมเข้าไม่ได้)
echo ====================================
echo.

:: Open browser
start "" "%URL%"

:: Save URL to file
echo %URL% > current_url.txt
echo URL บันทึกไว้ที่ไฟล์ current_url.txt แล้ว
echo.
pause
