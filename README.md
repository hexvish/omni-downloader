# Omni Downloader

A professional, web-based universal media downloader built with Python and Flask. Powered by the robust `yt-dlp` engine, Omni Downloader allows you to fetch metadata, select resolutions, and download media from virtually any supported platform.

## 🚀 Features

- **Universal Media Downloader**: Support for hundreds of sites including YouTube, Instagram, TikTok, and more.
- **Intelligent Format Fetching**: Preview and choose from available resolutions and formats before downloading.
- **Multiple Quality Options**: Automatically lists from high-definition (4K/1080p) down to mobile-friendly resolutions.
- **Audio Extraction**: Single-click conversion to high-quality MP3.
- **Clean Interface**: A modern, glassmorphism-inspired web UI.
- **Mobile-Friendly**: Fully responsive design for downloading on the go.
- **Self-Cleaning**: Automatic background cleanup of temporary download files.

## 🛠️ Tech Stack

- **Backend**: Python 3, Flask, yt-dlp
- **Frontend**: HTML5, CSS3 (Vanilla), JavaScript (Vanilla)
- **Processing**: FFmpeg (for audio/merging)

## 📂 Project Structure

```text
omni-downloader/
├── app.py              # Flask server and downloader logic
├── requirements.txt    # Python dependencies
├── downloads/          # Temporary media storage
└── templates/
    └── index.html      # Responsive frontend
```

## 🌏 Supported Sites

Omni Downloader leverages `yt-dlp`, supporting any platform it covers, including:
- **Instagram** (Posts, Reels, Stories)
- **TikTok** (No watermark where supported)
- **YouTube** (Shorts, Videos)
- **X (Twitter)**
- **Facebook**
- **Pinterest**
- *...and hundreds more.*

## ⚙️ Installation

### Prerequisites
- Python 3.8+
- [FFmpeg](https://ffmpeg.org/download.html) (Installed and in system PATH)

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/hexvish/omni-downloader.git
   cd omni-downloader
   ```

2. **Setup virtual environment (Recommended)**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the UI**
   Open your browser and navigate to `http://localhost:5000`.

## 🤝 Contributing

This project is open-source. Feel free to fork, report issues, or submit pull requests for Phase 3 features.

## ⚖️ License

Distributed under the MIT License. See `LICENSE` for more information.
