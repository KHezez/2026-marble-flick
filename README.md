# Marble Flick v0.8

Python / Pygame arcade marble PvP, expanded from the existing v0.7 codebase.

- 12 passives, 8 skills, Korean/English UI, 6 maps, persistent shop and loadouts.
- 6 supplied photo skins (17 total); cosmetic art preserves the normal collision radius.
- Three solo/cooperative bosses, including two-phase Gokbin and its exclusive red skin reward.
- Host-authoritative two-player LAN: versus, shared-team CPU battles and cooperative bosses.
- Tiger Shot nerf; supplied music/SFX decoded and mislabeled Ogg files converted to real MP3.
- No EXE build yet. Run `play_windows.bat`, or install `requirements.txt` and run `python main.py`.

[한국어 설치·조작·LAN 안내](README_KO.md) · [전체 에셋 목록](ASSETS_KO.md) · [검증 결과](validation/v08/REPORT_KO.md)

[Download v0.8 ZIP](https://github.com/KHezez/2026-marble-flick/raw/refs/heads/main/downloads/marble_flick_v0.8.zip)

Keep your existing `user_data` folder when upgrading. Save data is not included in the release.

Tests: `python -m unittest discover -s tests` or `test_windows.bat`.
LAN uses IPv4 TCP 24872 on the same network; no matchmaking server. P grants 1000 Coins offline only.
