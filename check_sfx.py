"""Decode and actually schedule every SFX; missing assets use generated fallback.
Run with --headless for SDL dummy audio, or normally to hear every sound.
"""
import argparse
import os
import logging

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--headless',action='store_true');args=parser.parse_args()
    if args.headless:os.environ['SDL_AUDIODRIVER']='dummy'
    import pygame
    from audio import SoundBox
    logging.basicConfig(level=logging.INFO)
    pygame.mixer.pre_init(44100,-16,2,512)
    box=SoundBox();failed=[]
    for name,filename in box.FILES.items():
        channel=box.play(name)
        busy=bool(channel and channel.get_busy())
        print(f'{filename}: {box.diagnostics[name]}; channel_active={busy}; volume={box.sfx_volume}')
        if not busy or (box.root/'sfx'/filename).exists() and box.samples[name] is None:failed.append(filename)
        pygame.time.wait(5 if args.headless else 450)
    print('Mixer:',pygame.mixer.get_init(),'driver:',os.environ.get('SDL_AUDIODRIVER','system'))
    print('Headless verifies decoding and scheduling, NOT speaker output.' if args.headless else 'Listen to confirm speaker output.')
    pygame.quit()
    return 1 if failed else 0
if __name__=='__main__':raise SystemExit(main())
