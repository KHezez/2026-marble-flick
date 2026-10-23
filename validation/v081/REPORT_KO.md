# v0.8.1 EXE 빌드 검증

- 변경 음원: 효과음 7개, BGM 4개. 기존 파일을 유지하면서 추가/교체했습니다. 실제 Ogg 파일 6개를 MP3로 변환했습니다. `audio_changes.json` 참고.
- 효과음 49개 / BGM 15개가 디코딩 및 재생 호출 검사를 통과했습니다. 미제공 효과음 5개는 합성 대체음입니다.
- Linux 소스 회귀 테스트 144개와 실행기 자가 검사(메뉴, 사진 스킨, 보스, 4배 체력, 저장)를 통과했습니다.
- PyInstaller onefile GUI 방식으로 Python·Pygame·모든 에셋을 하나의 Windows EXE에 넣습니다. 저장은 EXE 옆 user_data이며 쓰기 불가 시 LocalAppData로 대체합니다.
- Windows 빌드는 `.github/workflows/windows-exe.yml`에서 수행합니다. Windows 소스 테스트와 실제 EXE 자가 검사, EXE 두 프로세스의 TCP 경기가 통과한 파일만 릴리스합니다.
- 빌드 완료 시 이 폴더에 `windows-exe-test.json`과 `MarbleFlick.exe.sha256`을 기록합니다. 릴리스에도 같은 파일을 첨부합니다.
- 실제 두 PC의 공유기/방화벽 환경과 스피커 출력은 자동 검사 범위 밖입니다.
