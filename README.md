# hdfilm-dl

CLI tool to download videos from [hdfilmcehennemi.nl](https://www.hdfilmcehennemi.nl).

## Install

```bash
pip install hdfilm-dl
```

Playwright (required — site behind Cloudflare):

```bash
pip install 'hdfilm-dl[playwright]'
playwright install chromium
```

## Usage

**Download a series episode:**

```bash
hdfilm-dl download "https://www.hdfilmcehennemi.nl/dizi/mentalist/sezon-1/bolum-1/"
```

**Download a movie:**

```bash
hdfilm-dl download "https://www.hdfilmcehennemi.nl/esaretin-bedeli/"
```

**Batch download episodes 1-12:**

```bash
hdfilm-dl batch "https://www.hdfilmcehennemi.nl/dizi/mentalist/sezon-1/bolum-1/" --start 1 --end 12
```

**Inspect available video sources:**

```bash
hdfilm-dl inspect "https://www.hdfilmcehennemi.nl/dizi/mentalist/sezon-1/bolum-1/"
```

### Source selection

When downloading, you can choose between video source alternatives
(Close / Rapidrame). Default is Rapidrame (most reliable).

```
Available sources:
  [0] Active Close
  [1] Inactive Rapidrame
Choose source [1]:
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `-o, --output` | `.` | Output directory |

## How it works

1. Fetches the episode/movie page with Playwright (required — Cloudflare protected)
2. Clicks the play button and selects the video source (Rapidrame)
3. Captures the `master.m3u8` HLS stream URL from network requests
4. Downloads with yt-dlp (merges to MP4)

Video streams are delivered via HLS (`.m3u8` playlists). No direct MP4 links available.

## Requirements

- Python 3.10+
- Playwright with Chromium (`playwright install chromium`)
- yt-dlp (automatically installed)
- ffmpeg (required for yt-dlp merge operations)
