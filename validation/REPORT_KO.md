# v0.6 검증 보고서

## 실행 환경

Linux x86_64, Python 3.12.14, Pygame 2.6.1 / SDL 2.28.4.
SDL_VIDEODRIVER=dummy, SDL_AUDIODRIVER=dummy를 사용했습니다.
테스트용 저장 파일은 임시 폴더에 격리하며 실제 사용자 저장 데이터는 배포하지 않습니다.

## 결과

- 자동 테스트 **87개 성공, 실패 0개, 스킵 0개**. 기존 v0.5 테스트 46개와 신규 41개입니다.
- 실제 Pygame Game 객체를 생성하고 메뉴 클릭 이벤트, 상점 뽑기 연출, 인벤토리 선택/장착, 스탯 변경, START, 경기 화면, 결과 화면, 종료 루프를 실행했습니다.
- CPU Easy/Normal/Hard 및 로컬 모드의 한 턴 진행을 실제 Game.update 경로에서 검증했습니다.
- 1/4/5/6/7/8/9/10개 × normal/ice/mud 조합에서 실제 크기·강화 속도·장애물 물리를 실행해 유한 좌표와 경계 처리를 검증했습니다.
- Heavenly Restricted 홀수 올림, 1v1 제한, 확률 2배, Heavy/Juggernaut 배타성, 모든 정적 패시브의 실제 반경·질량·발사속도, 부상 중첩 방지, Tungsten 기간 감소를 검사했습니다.
- Last Resort의 같은 스텝 2개 장외(반대 배열 순서 포함), 보호 만료, 1v1 예외, Cola 희생으로 마지막 알이 되는 경우를 검사했습니다.
- Curve Shot 실제 속도 방향 변화와 속력 보존, Friendship 실시간 군집/이탈/상한, 고속 Rat+Heavenly+Sniper Tiger가 얇은 강철을 통과하지 않는지 검사했습니다.
- Eyes 준비 확정 전 비공개, 확정 후 공개 및 8턴 쿨타임, 스킬 비공개 렌더, 클러치 단 한 번 초기화를 검사했습니다.
- 뽑기 등급별 후보, 소유권/장착 제한, 재구매 환급, 돈 부족 시 무변경, 경기 보상 단 한 번, 저장/재실행/손상 백업 복구를 검사했습니다.
- 일반 P키 무효, 개발 모드 P키 지급, Tab 턴 넘기기, 0개 스킬 로드아웃도 검사했습니다.
- 화면 흔들림/줌/파티클 렌더링이 실제 물리 좌표를 바꾸지 않는지 검사했습니다.
- MP3 디코딩, 실제 믹서 채널 예약·재생, 채널 포화, 음소거/볼륨, 누락·잘못된 포맷의 대체음을 검사했습니다.
- 임시 MP3를 각 BGM 슬롯에 넣어 화면별 음악 로드/전환/음소거 경로를 실행했습니다. 최종 배포에 실제 BGM은 들어 있지 않습니다.

명령:

```text
python -m unittest discover -s tests -v
python check_sfx.py --headless
```

전체 실행 로그: `tests_linux.log`, `audio_linux.log`.
실제 렌더링 화면: `home.png`, `inventory.png`, `shop.png`, `setup.png`, `match.png`.

## Cola 사운드 원인과 수정 근거

원본 `cola_charge.mp3`와 `cola_explosion.mp3`는 실제로 MP4/M4A 컨테이너의 AAC 오디오였습니다.
`ffprobe` 결과: codec_name=aac, format_name=mov,mp4,m4a,3gp,3g2,mj2.
원본 두 파일을 `pygame.mixer.Sound`로 로딩하면 모두 `Unrecognized audio format`이 발생했습니다.
기존 SoundBox는 해당 오류를 무시했고, check_sfx.py는 파일 존재만 검사해서 OK를 표시했습니다.
따라서 파일명이 올바르고 경로가 존재하더라도 실제 MP3 로딩 성공을 의미하지 않았습니다.

제공된 기존 17개를 FFmpeg/libmp3lame로 실제 MP3로 변환했습니다. 나머지 15개 역시 원래 Ogg/Vorbis를 MP3로 이름만 바꾼 파일이었습니다. 원본 ZIP은 변경하지 않았고 배포된 assets/sfx에만 변환 파일을 넣었습니다. 이전 assets 루트 중복 사운드 파일은 혼동을 피하기 위해 배포에서 제외했습니다.

변환 후 Pygame에서 Cola 충전 1.854초, 폭발 0.682초 디코딩 및 실제 채널 활성화를 확인했습니다. Game의 준비→공개→발사→정지→폭발 경로에서 충전 호출 1회, 폭발 호출 1회가 확인되었습니다. 이전의 explosion/sacrifice 양쪽 폭발음 중복 호출을 제거했고 충전과 폭발의 예약 채널을 분리했습니다. 모든 효과음은 로딩 실패 원인, 누락 대체음, 채널 부족을 기록하며 --audio-debug로 개별 호출/볼륨/채널 활성화 로그를 출력합니다.

## 성능 및 한계

Hard CPU의 10v10(Heavenly로 한 팀 5개), ice/mixed, Juggernaut/Friendship/Metal 대 Heavenly/Rat/Sniper 샘플에서 27개 후보의 계산은 후보당 평균 약 31ms, 최대 약 39ms였습니다. 후보 한 개씩 프레임에 나누어 계산합니다. 이 값은 현재 컨테이너의 참고 측정치이며 Windows FPS 보장이 아닙니다. 파티클 400개, 충격파 32개 상한이 있으며 고속 충돌은 최소 반경 기반 서브스텝을 적용합니다.

**미검증**: Windows OS에서 .bat 직접 실행, 실제 사운드 장치로 청취, 실제 그래픽 디스플레이 입력 지연, 여러 시간의 수동 플레이 및 경쟁 밸런스. 더미 오디오는 디코딩/재생 호출/채널 상태를 확인하지만 사람이 들리는지 증명하지 않습니다. 제공된 Windows 배치파일과 한국어 조작 설명을 포함했습니다.

**의도적으로 미구현**: Bull, Ankle Breaker, 노곡빈의 저주, 무하한의 전투 동작; 온라인 대전/현금 결제/서버 재화 검증; 여러 로드아웃 선택 UI. 파일 구조/미래 스킬 메타데이터는 준비되어 있습니다.
