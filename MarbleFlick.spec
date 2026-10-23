# Build with Windows Python: python -m PyInstaller --clean --noconfirm MarbleFlick.spec
from pathlib import Path
ROOT = Path(SPECPATH)
a = Analysis([str(ROOT / 'exe_entry.py')], pathex=[str(ROOT)],
             binaries=[], datas=[(str(ROOT / 'assets'), 'assets')],
             hiddenimports=['pygame._sdl2.video'],
             hookspath=[], hooksconfig={}, runtime_hooks=[],
             excludes=['tkinter', 'pytest', 'numpy', 'matplotlib', 'PIL', 'unittest'],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='MarbleFlick',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False,
          version=str(ROOT / 'windows_version.txt'))
