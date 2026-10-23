"""Writable profile location, separate from PyInstaller's temporary assets."""
import os
from pathlib import Path
import sys
import tempfile


def app_directory():
    return Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent


def default_save_path():
    override=os.environ.get('MARBLE_SAVE_PATH')
    if override:return Path(override)
    portable=app_directory()/'user_data'
    if not getattr(sys,'frozen',False):return portable/'profile.json'
    try:
        portable.mkdir(parents=True,exist_ok=True)
        # Check the destination rather than assuming the EXE directory is writable.
        with tempfile.TemporaryFile(dir=portable):pass
        return portable/'profile.json'
    except OSError:
        base=Path(os.environ.get('LOCALAPPDATA') or Path.home()/'AppData'/'Local')
        return base/'MarbleFlick'/'user_data'/'profile.json'
