"""Find an interpreter that actually imports pygame; never delete existing environments."""
from pathlib import Path
import os
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parent

def candidates():
    found=[]
    for folder in ('.venv-game','.venv','.venv-py312','.venv-1'):
        p=ROOT/folder/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        if p.is_file():found.append([str(p)])
    # Windows App Execution Aliases are deliberately excluded.
    if 'windowsapps' not in sys.executable.lower():found.append([sys.executable])
    py=shutil.which('py')
    if py:
        for version in ('3.13','3.12','3.11'):found.append([py,'-'+version])
    if os.name=='nt':
        base=Path(os.environ.get('LOCALAPPDATA',''))/'Programs/Python'
        for version in ('313','312','311'):
            p=base/('Python'+version)/'python.exe'
            if p.is_file():found.append([str(p)])
    for name in ('python3.13','python3.12','python3.11','python3','python'):
        p=shutil.which(name)
        if p and 'windowsapps' not in p.lower():found.append([p])
    unique=[]
    for command in found:
        if command not in unique:unique.append(command)
    return unique

def check(command,code):
    try:return subprocess.run(command+['-c',code],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=15).returncode==0
    except (OSError,subprocess.TimeoutExpired):return False

def find_runtime(options):
    for command in options:
        if check(command,"import pygame; assert pygame.version.ver == '2.6.1'"):return command,True
    for command in options:
        if check(command,"import sys,struct; assert (3,11)<=sys.version_info[:2]<=(3,13) and struct.calcsize('P')==8"):return command,False
    return None,False

def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    command,ready=find_runtime(candidates())
    if command is None:
        print('Install Python 3.13 (64-bit): https://www.python.org/downloads/windows/');return 1
    if not ready:
        target=ROOT/'.venv-game';python=target/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        if target.exists():
            if not python.is_file():
                print('Keep your files: rename the incomplete .venv-game folder, then retry.');return 1
        else:
            if subprocess.call(command+['-m','venv',str(target)]):return 1
        command=[str(python)]
        if subprocess.call(command+['-m','pip','install','--only-binary=:all:','-r',str(ROOT/'requirements.txt')]):return 1
    print('Game Python:', ' '.join(command),flush=True)
    if '--test' in argv:
        os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
        args=['-m','unittest','discover','-s','tests','-v']
    else:args=[str(ROOT/'main.py')]+argv
    return subprocess.call(command+args,cwd=ROOT)

if __name__=='__main__':raise SystemExit(main())
