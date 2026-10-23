@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Missing .venv. Run the first-time installation commands in docs first.
    exit /b 1
)

rem Expose the source packages and the local Sentinel dependency.
set "PYTHONPATH=%CD%\packages\contracts\src;%CD%\packages\core\src;%CD%\services\account\src;%CD%\services\checkout\src;%CD%\services\payment\src;%CD%\services\api\src;%CD%\services\orchestrator\src;%PYTHONPATH%"
set "NODE_PATH=%CD%\.tmp\sentinel-node\node_modules;%NODE_PATH%"

rem Development defaults; explicit environment settings take precedence.
if not defined GSS_DATA_DIR set "GSS_DATA_DIR=%CD%\runtime"
if not defined GSS_CONFIG_DIR set "GSS_CONFIG_DIR=%CD%\config"
if not defined GSS_PROXY_CONFIG set "GSS_PROXY_CONFIG=%GSS_DATA_DIR%\proxy-gateways.json"
if not defined GSS_USE_FAKE set "GSS_USE_FAKE=0"
if not defined GSS_ENABLE_PROMO set "GSS_ENABLE_PROMO=1"

echo Starting API at http://127.0.0.1:8080 ^(GSS_USE_FAKE=%GSS_USE_FAKE%^)
"%CD%\.venv\Scripts\python.exe" -m uvicorn gss_api.main:app --host 127.0.0.1 --port 8080 --reload
exit /b %errorlevel%
