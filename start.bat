@echo off
chcp 65001 >nul
title Piper TTS Server
cd /d "%~dp0"

echo [TTS] Kiem tra Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [FAIL] Python khong tim thay. Cai dat Python 3.10+ truoc.
    pause & exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
    echo [TTS] Tao virtual environment...
    python -m venv .venv
    if errorlevel 1 ( echo [FAIL] Khong tao duoc venv. & pause & exit /b 1 )
)

echo [TTS] Kich hoat venv...
call .venv\Scripts\activate.bat

echo [TTS] Cai dat dependencies...
pip install -r backend\requirements.txt
if errorlevel 1 (
    echo [FAIL] Cai dat thu vien that bai.
    pause & exit /b 1
)

echo.
echo [TTS] Kiem tra piper.exe...
if not exist "piper\piper.exe" (
    echo [FAIL] Chua co piper\piper.exe
    echo        Tai piper_windows_amd64.zip tu:
    echo        https://github.com/rhasspy/piper/releases
    echo        Giai nen TOAN BO noi dung zip vao thu muc 'piper\'
    echo.
    pause & exit /b 1
)
echo [OK]   piper.exe tim thay.

echo [TTS] Kiem tra model giong noi (.onnx)...
set "FOUND_MODEL=0"
for %%F in (models\*.onnx) do set "FOUND_MODEL=1"
if "%FOUND_MODEL%"=="0" (
    echo [WARN] Chua co model giong noi trong thu muc 'models\'
    echo        Tai file .onnx + .onnx.json tu:
    echo        https://huggingface.co/rhasspy/piper-voices
    echo        Vi du tieng Viet: vi_VN-vivos-medium.onnx
    echo        Dat ca hai file vao thu muc 'models\' roi chay lai.
    echo.
    pause & exit /b 1
)
for %%F in (models\*.onnx) do echo [OK]   Model tim thay: %%~nxF

echo [TTS] Khoi dong server tai http://localhost:8000
echo [TTS] Nhan Ctrl+C de dung.
echo.

python backend\app.py
pause
