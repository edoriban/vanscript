"""URL parsing, filename sanitization, and other utilities."""

import os
import re
import subprocess
import sys
from pathlib import Path

from models import InvalidURLError

# Matches 11-char YouTube video IDs from various URL formats
_VIDEO_ID_PATTERNS = [
    # youtube.com/watch?v=ID
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})"),
    # youtu.be/ID
    re.compile(r"(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})"),
    # youtube.com/embed/ID
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})"),
    # youtube.com/shorts/ID
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})"),
    # youtube.com/live/ID
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/live/([a-zA-Z0-9_-]{11})"),
    # bare 11-char ID
    re.compile(r"^([a-zA-Z0-9_-]{11})$"),
]

# Characters not allowed in Windows filenames
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def extract_video_id(raw: str) -> str:
    """Extract a YouTube video ID from a URL or bare ID string."""
    raw = raw.strip()
    for pattern in _VIDEO_ID_PATTERNS:
        match = pattern.search(raw)
        if match:
            return match.group(1)
    raise InvalidURLError(f"Cannot extract video ID from: {raw}")


def parse_url_list(text: str) -> list[str]:
    """Parse multiline text into a list of video IDs. Skips blank lines and comments."""
    video_ids: list[str] = []
    seen: set[str] = set()
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            vid = extract_video_id(line)
            if vid not in seen:
                video_ids.append(vid)
                seen.add(vid)
        except InvalidURLError:
            pass  # caller handles invalid lines via core.py
    return video_ids


def sanitize_filename(name: str) -> str:
    """Remove characters invalid for Windows filenames and trim length."""
    name = _INVALID_FILENAME_CHARS.sub("", name)
    name = name.strip(". ")
    # Limit to 100 chars to leave room for date suffix and extension
    if len(name) > 100:
        name = name[:100].rstrip()
    return name or "transcript"


def build_output_filename(titles: list[str], dates: list[str]) -> str:
    """Generate a descriptive filename based on video titles and dates."""
    count = len(titles)
    match count:
        case 0:
            return "transcripts.txt"
        case 1:
            safe_title = sanitize_filename(titles[0])
            date_part = dates[0] if dates else "unknown"
            return f"{safe_title}_{date_part}.txt"
        case 2:
            t1 = sanitize_filename(titles[0])
            t2 = sanitize_filename(titles[1])
            # Shorten each title to 40 chars max for combined name
            t1 = t1[:40].rstrip() if len(t1) > 40 else t1
            t2 = t2[:40].rstrip() if len(t2) > 40 else t2
            date_part = dates[0] if dates else "unknown"
            return f"{t1}_and_{t2}_{date_part}.txt"
        case _:
            safe_title = sanitize_filename(titles[0])
            safe_title = safe_title[:50].rstrip() if len(safe_title) > 50 else safe_title
            sorted_dates = sorted(d for d in dates if d)
            if sorted_dates:
                date_range = f"{sorted_dates[0]}_to_{sorted_dates[-1]}"
            else:
                date_range = "unknown"
            return f"{safe_title}_and_{count - 1}_more_{date_range}.txt"


def _is_wsl() -> bool:
    """Detect if running inside WSL."""
    try:
        with open("/proc/version", encoding="utf-8") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def get_default_downloads_folder() -> Path:
    """Return the logged-in user's Downloads folder (Windows native, WSL, macOS, or Linux)."""

    # WSL: get the Windows user's Downloads via /mnt/c/Users/<user>/Downloads
    if _is_wsl():
        try:
            # Ask Windows for the USERPROFILE path
            result = subprocess.run(
                ["cmd.exe", "/C", "echo", "%USERPROFILE%"],
                capture_output=True, text=True, timeout=5,
            )
            win_profile = result.stdout.strip()  # e.g. C:\Users\Edgar
            if win_profile and "%" not in win_profile:
                # Convert Windows path to WSL path: C:\Users\Edgar -> /mnt/c/Users/Edgar
                drive = win_profile[0].lower()
                rest = win_profile[3:].replace("\\", "/")
                wsl_downloads = Path(f"/mnt/{drive}/{rest}/Downloads")
                if wsl_downloads.is_dir():
                    return wsl_downloads
        except Exception:
            pass
        # Fallback: scan /mnt/c/Users for a non-system user with Downloads
        try:
            users_dir = Path("/mnt/c/Users")
            skip = {"All Users", "Default", "Default User", "Public", "WsiAccount", "desktop.ini"}
            for entry in sorted(users_dir.iterdir()):
                if entry.name in skip or not entry.is_dir():
                    continue
                downloads = entry / "Downloads"
                if downloads.is_dir():
                    return downloads
        except Exception:
            pass

    # Native Windows: use the shell API
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            FOLDERID_Downloads = ctypes.c_char_p(
                b"\x90\xe2\x4d\x37\x3f\x12\x65\x45\x91\x64\x39\xc4\x92\x5e\x46\x7b"
            )
            _SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
            _SHGetKnownFolderPath.argtypes = [
                ctypes.c_char_p, wintypes.DWORD, wintypes.HANDLE,
                ctypes.POINTER(ctypes.c_wchar_p),
            ]
            _SHGetKnownFolderPath.restype = ctypes.HRESULT

            path_ptr = ctypes.c_wchar_p()
            hr = _SHGetKnownFolderPath(FOLDERID_Downloads, 0, None, ctypes.byref(path_ptr))
            if hr == 0 and path_ptr.value:
                folder = Path(path_ptr.value)
                ctypes.windll.ole32.CoTaskMemFree(path_ptr)
                if folder.is_dir():
                    return folder
        except Exception:
            pass

        user_profile = os.environ.get("USERPROFILE", "")
        if user_profile:
            downloads = Path(user_profile) / "Downloads"
            if downloads.is_dir():
                return downloads

    # macOS / Linux fallback
    downloads = Path.home() / "Downloads"
    if downloads.is_dir():
        return downloads
    return Path.home()


def ensure_unique_path(path: Path) -> Path:
    """If path exists, append _1, _2, etc. until unique."""
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    while True:
        new_path = parent / f"{stem}_{counter}{suffix}"
        if not new_path.exists():
            return new_path
        counter += 1
