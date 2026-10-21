# Marble Flick v0.6

기존 Python/Pygame v0.5 프로젝트를 확장한 로컬 2D 알까기 게임입니다.

**[전체 프로젝트 ZIP 다운로드](https://github.com/KHezez/2026-marble-flick/archive/refs/heads/main.zip)**

압축을 모두 해제한 뒤 `play_windows.bat`를 실행하세요. Python 3.11~3.13(권장 3.12)이 필요하며, 최초 실행 시 Pygame을 설치합니다.

- [한국어 사용 설명서](README_KO.md)
- [MP3·BGM·PNG 전체 파일 목록](ASSETS_KO.md)
- [실행 및 자동 테스트 결과](validation/REPORT_KO.md)

패시브 12종, 기존 스킬 4종, CPU 3개 난이도 및 로컬 2P, 경기 전 로드아웃, 상점·뽑기·화폐·JSON 저장, 메뉴 UI 및 타격 효과를 포함합니다. 신규 액티브 4종은 향후 확장 구조만 준비했습니다.

자동 테스트 87개가 Linux SDL 더미 화면·오디오 환경에서 통과했습니다. Windows 실기 실행 및 실제 스피커 청취는 미검증입니다. 새 효과음과 BGM/PNG는 선택 사항이며, 누락 시 대체음·기본 배경·무음 BGM으로 실행됩니다.
