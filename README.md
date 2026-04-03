<div align="center">
  <img src="nyo_logo_full.png" alt="NYO" width="160"/>

  # NYO
  **Video Downloader — YouTube · Twitch · TikTok · Twitter**

  ![Version](https://img.shields.io/badge/version-0.1-brightgreen?style=flat-square)
  ![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)
  ![Platform](https://img.shields.io/badge/platform-Windows-lightgrey?style=flat-square)
  ![License](https://img.shields.io/badge/license-MIT-orange?style=flat-square)
</div>

---

## ¿Qué es NYO?

NYO es una app de escritorio para descargar videos de YouTube, Twitch, TikTok y Twitter/X con una interfaz moderna tipo "command center". Disponible como `.exe` portable que no requiere instalar Python ni dependencias — todo viene bundleado.

Built on top of [yt-dlp](https://github.com/yt-dlp/yt-dlp) with a pywebview UI following the **Stitch design system**: obsidian dark theme, neon mint accent, Space Grotesk typography.

---

## Features

- **Multi-plataforma**: YouTube, Twitch, TikTok, Twitter/X y cualquier sitio soportado por yt-dlp
- **Formatos**: MP4, MKV, WEBM, MP3, M4A, WAV
- **Calidades**: Best, 4K, 1080p, 720p, 480p, 360p
- **Cookies del navegador**: Edge, Chrome, Firefox, Brave (fix para errores 403 de YouTube)
- **Retry automático**: si las cookies fallan (navegador abierto), reintenta sin ellas
- **Log en tiempo real**: salida de yt-dlp línea por línea
- **Bundled yt-dlp**: el EXE incluye yt-dlp internamente — no hay que instalar nada
- **Abre carpeta automáticamente** al terminar la descarga

---

## Screenshots

<div align="center">
  <img src="nyo_logo_icon.png" alt="NYO App Icon" width="120"/>
</div>

---

## Instalación

### Opción A — EXE portable (recomendado)

1. Descarga `NYO.exe` desde [Releases](https://github.com/NyoWynn/NYO/releases)
2. Ejecuta el `.exe` — no requiere instalar nada
3. Pega una URL, selecciona formato/calidad y descarga

> **Requisito**: Windows 10/11 con [Edge WebView2 Runtime](https://go.microsoft.com/fwlink/p/?LinkId=2124703) (viene preinstalado en Windows 10 21H2+ y Windows 11)

### Opción B — Desde el código fuente

```bash
# Clonar el repo
git clone https://github.com/NyoWynn/NYO.git
cd NYO

# Instalar dependencias
pip install pywebview pyinstaller

# También necesitas yt-dlp
pip install yt-dlp

# Correr directamente
python downloader_webview.py
```

---

## Build del EXE

```batch
cd NYO
build_webview.bat
```

El script hace automáticamente:
1. Instala dependencias Python (`pywebview`, `pyinstaller`)
2. Descarga `yt-dlp.exe` standalone desde GitHub
3. Compila con PyInstaller (yt-dlp bundled dentro)
4. Copia `NYO.exe` al escritorio

---

## Estructura del Proyecto

```
NYO/
├── downloader_webview.py   # App principal (pywebview + HTML UI embebido)
├── build_webview.bat        # Script de compilación
├── nyo_logo_icon.png        # Logo circular (in-app)
├── nyo_logo_full.png        # Logo completo (con texto NYO)
├── nyo.ico                  # Ícono del EXE (.ico)
└── requirements.txt         # Dependencias Python
```

---

## Uso

1. **Pegar URL** en el campo de texto — la app detecta automáticamente la plataforma
2. **Seleccionar formato** (MP4 / MKV / MP3 / etc.)
3. **Seleccionar calidad** (Best / 4K / 1080p / etc.)
4. **Cookies**: seleccionar el navegador donde tienes sesión iniciada (ayuda con videos de YouTube)
   - El navegador debe estar **cerrado** al momento de descargar para que las cookies no estén bloqueadas
5. **Cambiar carpeta** de destino si quieres (por defecto `~/Downloads`)
6. **Click DESCARGAR** — el log muestra el progreso en tiempo real

---

## Troubleshooting

| Error | Solución |
|-------|----------|
| `ERROR 403 Forbidden` | Seleccionar el navegador con sesión de YouTube y cerrarlo antes de descargar |
| Cookies bloqueadas | La app reintenta automáticamente sin cookies |
| Ventana no abre | Instalar [Edge WebView2 Runtime](https://go.microsoft.com/fwlink/p/?LinkId=2124703) |
| Video privado | Debes tener acceso y usar cookies del navegador correcto |

---

## Tech Stack

| Componente | Tecnología |
|---|---|
| UI | [pywebview](https://pywebview.flowrl.com/) + HTML/CSS/JS |
| Design | Stitch Design System (Space Grotesk + Inter, obsidian dark) |
| Descarga | [yt-dlp](https://github.com/yt-dlp/yt-dlp) |
| Build | [PyInstaller](https://pyinstaller.org/) |

---

## License

MIT — libre para usar y modificar.

---

<div align="center">
  Made with 💚 by <a href="https://github.com/NyoWynn">NyoWynn</a>
</div>
