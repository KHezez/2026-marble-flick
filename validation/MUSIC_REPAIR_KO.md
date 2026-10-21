# BGM 4곡 형식 수정

업로드된 music.zip의 네 파일은 모두 확장자는 .mp3였지만 실제 Ogg/Vorbis였습니다.
Pygame의 music 로더가 MP3 디코더를 선택하면서 네 파일 모두 로딩에 실패했습니다.
FFmpeg로 실제 MPEG Layer III(MP3), 44.1kHz, 스테레오, 192kbps로 변환했습니다.
업로드된 원본 ZIP은 변경하지 않았습니다. 코드를 변경할 필요 없이 음악만 교체하면 됩니다.

검증: 네 파일 전체 FFmpeg 디코딩 성공(-xerror), Pygame 2.6.1 SoundBox의 화면별 음악 전환/로드/재생 성공, 각 트랙 중간 및 끝부분 탐색 후 재생 채널 활성화 확인.
Linux SDL dummy 오디오 검사이며 Windows 실기 및 실제 스피커 청취는 미검증입니다.
상세 기록: music_repair.log. REPORT_KO.md의 BGM 미제공 설명은 최초 배포 당시 기준입니다.

음악 교체 ZIP: ../downloads/music_fixed.zip
게임을 종료하고 ZIP의 music 폴더 안 MP3 네 파일을 게임의 assets/music 폴더에 덮어쓴 뒤 재실행하세요.
