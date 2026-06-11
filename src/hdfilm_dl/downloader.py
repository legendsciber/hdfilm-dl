import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from hdfilm_dl.models import EpisodeInfo, VideoSource

console = Console()


def _check_deps():
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, check=True)
        return "yt-dlp"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True)
        return "ffmpeg"
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print(
            "[red]Error: yt-dlp or ffmpeg not found.[/red]\n"
            "Install: pip install yt-dlp  or  https://ffmpeg.org/download.html"
        )
        sys.exit(1)


def download_episode(
    source: VideoSource,
    info: EpisodeInfo,
    output_dir: str = ".",
    quality: str = "best",
):
    _check_deps()

    out_dir = Path(output_dir) / _sanitize(info.anime_title)
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = f"S{info.season:02d}E{info.episode:02d} - {_sanitize(info.title or f'Episode {info.episode}')}.mp4"
    out_path = out_dir / filename

    if out_path.exists():
        console.print(f"[yellow]Already exists:[/yellow] {out_path}")
        return out_path

    console.print(f"[cyan]Downloading:[/cyan] {_sanitize(info.anime_title)} - {_sanitize(info.title)}")

    _download_m3u8(source.url, str(out_path), source.referer)

    console.print(f"[green]Done:[/green] {out_path}")
    return out_path


def _download_m3u8(url: str, out_path: str, referer: str = ""):
    cmd = [
        "yt-dlp",
        "--no-progress",
        "--no-warnings",
        "--output", out_path,
        "--merge-output-format", "mp4",
        "--remux-video", "mp4",
        "--retries", "10",
        "--http-chunk-size", "10M",
    ]

    if referer:
        cmd.extend(["--referer", referer])

    cmd.append(url)

    progress = Progress(
        TextColumn("[cyan]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        transient=True,
    )

    with progress:
        task = progress.add_task("[yellow]Downloading...", total=None)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                console.print(f"[red]yt-dlp error:[/red] {result.stderr.strip()}")
                raise RuntimeError(f"yt-dlp failed: {result.stderr}")
        finally:
            progress.remove_task(task)


def download_movie(
    source: VideoSource,
    title: str,
    year: str = "",
    output_dir: str = ".",
):
    _check_deps()

    out_dir = Path(output_dir) / "Movies"
    out_dir.mkdir(parents=True, exist_ok=True)

    year_part = f" ({year})" if year else ""
    filename = f"{_sanitize(title)}{year_part}.mp4"
    out_path = out_dir / filename

    if out_path.exists():
        console.print(f"[yellow]Already exists:[/yellow] {out_path}")
        return out_path

    console.print(f"[cyan]Downloading:[/cyan] {_sanitize(title)}")
    _download_m3u8(source.url, str(out_path), source.referer)
    console.print(f"[green]Done:[/green] {out_path}")
    return out_path


def _sanitize(name: str) -> str:
    return "".join(c if c.isalnum() or c in " ._-()" else "_" for c in name).strip()
