# Omni Downloader

A modern, high-performance web-based universal media downloader built with Python and Flask. Powered by `yt-dlp` and `FFmpeg`, Omni Downloader allows you to extract YouTube Music, high-fidelity audio tracks with customizable bitrates, high-definition videos up to 4K, and entire playlists packaged into organized `.zip` archives.

---

## 🚀 Features

- **🎵 YouTube Music & Hi-Fi Audio Extraction**:
  - Download pure audio in **MP3, AAC, M4A, FLAC, WAV, or OPUS**.
  - Customizable bitrate selection: **320 kbps (High Fidelity), 256 kbps, 192 kbps, 128 kbps**, or Lossless Studio Quality.
  - Automatic metadata tagging (embeds title, artist, channel, and album art).
- **📦 Full Playlist Downloads (.ZIP)**:
  - Download entire YouTube or YouTube Music playlists at once.
  - Automatically numbers, tags, and compresses all tracks into a single clean `.zip` archive.
  - Built-in error tolerance skips unavailable/private tracks without failing the whole batch.
- **📑 Interactive Playlist Tracklist**:
  - Explore playlist contents directly in the UI.
  - Pick and download individual tracks on demand.
- **🎬 High-Definition Video Downloads**:
  - Extract videos across resolutions up to 4K (2160p, 1440p, 1080p, 720p, etc.) merged into standard MP4.
- **⚡ Smart Engine & Zero-Config FFmpeg**:
  - Automatically detects system `ffmpeg` on `PATH` or uses the bundled `imageio-ffmpeg` package. No manual environment variable setup required!
- **📊 Real-Time Progress Tracking**:
  - Live progress percentage, transfer speed, and status stages (downloading, transcoding, zipping).
- **💎 Premium Glassmorphism UI**:
  - Clean dark-mode interface with smooth micro-animations, mode toggles, and responsive mobile-first design.
- **🧹 Self-Cleaning Storage**:
  - Automatic background cleanup thread sweeps expired temporary downloads.

---

## 🛠️ Tech Stack

- **Backend**: Python 3, Flask, yt-dlp, imageio-ffmpeg
- **Processing**: FFmpeg (dynamic auto-discovery / fallback to `imageio-ffmpeg`)
- **Frontend**: HTML5, Vanilla CSS3 (Glassmorphism), Vanilla JavaScript (Asynchronous Task Polling)

---

## 📂 Project Structure

```text
omni-downloader/
├── app.py                  # Flask server and API route handlers
├── desktop.py              # Native desktop window launcher (pywebview)
├── build_standalone.py     # Standalone distribution & installer builder
├── installer.iss           # Inno Setup Windows installer compiler script
├── version_info.txt        # Windows PE executable metadata & version info
├── app.ico                 # Multi-resolution application icon
├── config.py               # Global settings & engine discovery
├── requirements.txt        # Python dependencies
├── run.bat                 # One-click Windows launcher & auto-updater
├── downloader/
│   ├── engine.py           # yt-dlp & FFmpeg dynamic engine manager
│   ├── extractor.py        # yt-dlp extraction & background task worker
│   ├── formatter.py        # Audio/video format & playlist parsers
│   └── updater.py          # Automatic yt-dlp update checker
├── utils/
│   ├── cleanup.py          # Background temporary file cleaner
│   └── validators.py       # URL validation & input sanitization
├── static/
│   ├── css/style.css       # Dedicated glassmorphism design system
│   ├── js/app.js           # Client-side state, polling & cancel handlers
│   └── img/icon.png        # Official high-resolution logo artwork
├── templates/
│   └── index.html          # Lightweight semantic HTML interface
└── downloads/              # Temporary download staging area
```

---

## 🌏 Supported Platforms

Omni Downloader leverages `yt-dlp`, supporting hundreds of platforms including:
- **YouTube & YouTube Music** (Tracks, Playlists, Videos, Shorts)
- **Instagram** (Reels, Posts, Stories)
- **TikTok** (Watermark-free where supported)
- **X (Twitter)**
- **Facebook**
- **Pinterest**
- *...and hundreds more.*

---

## ⚙️ Installation & Usage

### 📦 Windows Installer (Recommended for End Users)
Download the latest **`OmniDownloader-Setup-v1.0.2.exe`** from [**Releases**](https://github.com/hexvish/omni-downloader/releases):
- **1-Click Setup**: Installs to your user profile without requiring administrator/UAC privileges.
- **Self-Contained Engine**: Bundles `FFmpeg`, `yt-dlp`, and all required C++ runtimes out of the box—no manual environment setup required.
- **Desktop & Start Menu Shortcuts**: Full Windows integration with custom application icon.
- **Dual-Mode GUI**: Runs as a lightweight native desktop app powered by Edge WebView2 with automatic browser fallback.
- **Auto-Updating Engine**: Automatically keeps `yt-dlp` updated on launch so downloads never break when platforms update.

---

### 🚀 Quick Start from Source (Windows - One Click)
> [!IMPORTANT]
> If you downloaded the repository as a ZIP from GitHub, right-click the zip and choose **Extract All...** first before running. Do not run directly from inside the zip archive preview.

Simply double-click **`run.bat`** (or run `run.bat` in Command Prompt / PowerShell).
It will automatically:
1. Verify Python and setup `.venv` if not already created.
2. Check and install all dependencies from `requirements.txt`.
3. Auto-update `yt-dlp` and `imageio-ffmpeg` to their latest releases.
4. Launch the local web server and automatically open **http://localhost:5000** in your default browser.

---

### 🔨 Building the Standalone App & Installer (.exe)

To compile the standalone desktop distribution and Windows Installer wizard yourself:

1. Ensure dependencies and [Inno Setup 6](https://jrsoftware.org/isdl.php) are installed:
   ```powershell
   winget install JRSoftware.InnoSetup
   pip install -r requirements.txt pyinstaller pillow
   ```
2. Run the build automation script:
   ```powershell
   python build_standalone.py
   ```
3. The compiled outputs will be available in the `dist/` directory:
   - `dist/OmniDownloader-Setup-v1.0.2.exe` (Windows Installer wizard)
   - `dist/OmniDownloader-v1.0.2-Windows.zip` (Portable standalone folder)

---

### Manual Setup (Cross-Platform)

#### 1. Clone the repository
```bash
git clone https://github.com/hexvish/omni-downloader.git
cd omni-downloader
```

#### 2. Setup a virtual environment
```bash
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On Linux / macOS:
source .venv/bin/activate
```

#### 3. Install dependencies
```bash
pip install -r requirements.txt
```
> [!NOTE]
> FFmpeg is automatically provided through `imageio-ffmpeg` or your system `PATH`. No manual binary installation is necessary.

#### 4. Run the application
```bash
# Web server mode:
python app.py

# Native desktop window mode:
python desktop.py
```

#### 5. Access the Web UI
Open your browser and navigate to:
```
http://localhost:5000
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the repository issues.

---

## ⚖️ License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
