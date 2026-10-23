"""Windows GUI entry point and diagnostics for the single-file distribution."""
import logging
from pathlib import Path
import sys
from runtime_paths import default_save_path


def main():
    # CI exercises the exact packaged binary, without relying on installed Python.
    if '--self-test' in sys.argv:
        from packaged_smoke import self_test
        return self_test(sys.argv[sys.argv.index('--self-test')+1])
    if '--lan-smoke' in sys.argv:
        from packaged_smoke import lan_peer
        i=sys.argv.index('--lan-smoke')
        return lan_peer(sys.argv[i+1],sys.argv[i+2])
    log_dir=default_save_path().parent
    log_dir.mkdir(parents=True,exist_ok=True)
    log_path=log_dir/'game.log'
    logging.basicConfig(filename=str(log_path),filemode='w',level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(name)s: %(message)s',encoding='utf-8',force=True)
    try:
        from main import Game
        Game().run()
    except Exception:
        logging.exception('Game terminated unexpectedly')
        if sys.platform=='win32':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,'게임 실행 오류입니다. 다음 로그를 확인해 주세요.\nGame error. See log:\n'+str(log_path),'Marble Flick',0x10)
        return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
