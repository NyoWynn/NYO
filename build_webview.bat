@echo off
setlocal
echo ============================================================
echo   Video Downloader — Build EXE (pywebview + yt-dlp bundled)
echo ============================================================

REM 1. Install Python deps
echo [1/4] Instalando dependencias Python...
pip install pywebview pyinstaller customtkinter requests --quiet

REM 2. Download yt-dlp.exe standalone (no Python needed en la PC destino)
echo [2/4] Descargando yt-dlp.exe standalone...
if not exist yt-dlp.exe (
    curl -L "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" -o yt-dlp.exe
    echo     yt-dlp.exe descargado.
) else (
    echo     yt-dlp.exe ya existe, actualizando...
    yt-dlp.exe -U 2>nul || curl -L "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" -o yt-dlp.exe
)

REM 3. Build con PyInstaller
echo [3/4] Compilando con PyInstaller...
pyinstaller ^
  --onefile ^
  --windowed ^
  --name "NYO" ^
  --icon "nyo.ico" ^
  --collect-all webview ^
  --add-binary "yt-dlp.exe;." ^
  --add-data "nyo_logo_icon.png;." ^
  --hidden-import "clr" ^
  --hidden-import "webview.platforms.winforms" ^
  downloader_webview.py

REM 4. Copy to Desktop
echo [4/4] Copiando al escritorio...
if exist "dist\NYO.exe" (
    copy /Y "dist\NYO.exe" "%USERPROFILE%\Desktop\NYO.exe"
    echo.
    echo ============================================================
    echo  LISTO! NYO.exe en tu escritorio con el icono de Megumin.
    echo  Incluye yt-dlp bundled — funciona sin instalar nada.
    echo ============================================================
) else (
    echo ERROR: No se generó el EXE. Revisa los errores arriba.
)

pause
