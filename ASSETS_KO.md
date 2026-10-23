# v0.7 에셋 전체 목록

## 효과음 — `assets/sfx/`

아래 46개가 실제 코드에 연결된 전체 목록입니다. 파일이 없거나 디코딩에 실패하면 합성 대체음과 원인 로그를 사용합니다. 44.1/48kHz 실제 MP3 권장. 파일을 넣은 뒤 재실행하세요.

| 파일명 | 재생 상황 | 현재 포함 여부 |
|---|---|---|
| `ui_click.mp3` | 버튼 클릭 | 포함 |
| `ui_hover.mp3` | 버튼에 마우스 진입 | 포함 |
| `menu_enter.mp3` | 메인 메뉴 진입 | 포함 |
| `menu_transition.mp3` | 화면 전환 | 포함 |
| `shop_open.mp3` | 상점 열기 | 포함 |
| `gacha_start.mp3` | 뽑기 시작 | 포함 |
| `gacha_result.mp3` | 뽑기 결과 | 포함 |
| `gacha_rare.mp3` | Epic/Legendary 획득 | 포함 |
| `inventory_equip.mp3` | 장착/해제 | 포함 |
| `passive_activate.mp3` | 조건부 패시브 발동 | 포함 |
| `clutch_activate.mp3` | 클러치 발동 | 포함 |
| `match_start.mp3` | 경기 시작 | 포함 |
| `victory.mp3` | 승리 | 포함 |
| `defeat.mp3` | 패배/무승부 | **추가할 파일 · 현재 합성 대체음** |
| `marble_hit.mp3` | 구슬 충돌 | 포함 |
| `marble_flick.mp3` | 일반 발사 | 포함 |
| `marble_fall.mp3` | 장외 탈락 | 포함 |
| `wood_break.mp3` | 나무 파괴 | 포함 |
| `injury.mp3` | 부상 | 포함 |
| `brickwall_activate.mp3` | 콘크리트 굳기 | 포함 |
| `brickwall_hit.mp3` | 콘크리트 충돌 | 포함 |
| `tiger_shot.mp3` | 타이거 발사 | 포함 |
| `tiger_wind.mp3` | 풍압 | 포함 |
| `chain_start.mp3` | 체인 발사 | 포함 |
| `chain_hit.mp3` | 연속 적중 | 포함 |
| `chain_dash.mp3` | 체인 재가속 | 포함 |
| `cola_charge.mp3` | 콜라 충전/발사 | 포함 |
| `cola_explosion.mp3` | 콜라 폭발 | 포함 |
| `turn_lock.mp3` | 준비 확정 | 포함 |
| `reveal.mp3` | 동시 공개 | 포함 |
| `countdown.mp3` | 준비 시간 마지막 5초 | **추가할 파일 · 현재 합성 대체음** |
| `bull_charge.mp3` | 불 공격 돌진 | **추가할 파일 · 현재 합성 대체음** |
| `bull_ready.mp3` | 불 방어 공개 | **추가할 파일 · 현재 합성 대체음** |
| `bull_freeze.mp3` | 카운터 대상 정지 | **추가할 파일 · 현재 합성 대체음** |
| `bull_counter.mp3` | 뒤로 빠지는 카운터 준비 | **추가할 파일 · 현재 합성 대체음** |
| `bull_impact.mp3` | 카운터 들이받기 | **추가할 파일 · 현재 합성 대체음** |
| `ankle_ready.mp3` | 앵클 브레이커 공개 | **추가할 파일 · 현재 합성 대체음** |
| `ankle_dodge.mp3` | 접촉 회피 | **추가할 파일 · 현재 합성 대체음** |
| `infinity_ready.mp3` | 무하한 영역 공개 | **추가할 파일 · 현재 합성 대체음** |
| `infinity_stop.mp3` | 무하한에 접근한 적 감속 | **추가할 파일 · 현재 합성 대체음** |
| `curse_charge.mp3` | 저주 떨림 시전 | **추가할 파일 · 현재 합성 대체음** |
| `curse_release.mp3` | 저주 무작위 가속 시작 | **추가할 파일 · 현재 합성 대체음** |
| `curse_launch.mp3` | 저주로 개별 공 가속 | **추가할 파일 · 현재 합성 대체음** |
| `eyes_activate.mp3` | 천안 감지·대상 공 강조 | **추가할 파일 · 현재 합성 대체음** |
| `skin_draw.mp3` | 스킨 뽑기 결과 | **추가할 파일 · 현재 합성 대체음** |
| `walls_open.mp3` | 13턴 강철 경계벽 개방 | **추가할 파일 · 현재 합성 대체음** |

32개 믹서 채널 중 8개는 Cola 충전/폭발, 클러치/결과, 천안, 저주 충전/방출, Bull 타격용으로 보호합니다. 일반 채널 포화가 핵심 효과음을 가로채지 않습니다. `python check_sfx.py --headless`는 디코딩과 실제 재생 호출·채널 상태를 검사합니다. 사람의 스피커 청취 검사는 별도입니다.

## 배경음악 — `assets/music/`

기존 4곡은 포함되어 있습니다. 새 곡 8개는 사용자가 추가합니다. 새 전투/클러치/저주 곡이 없으면 기존 match, settings가 없으면 main_menu로 대체합니다. 기존 곡까지 없으면 무음으로 실행됩니다.

| 파일명 | 전환 상황 | 상태 |
|---|---|---|
| `main_menu.mp3` | 메인·경기 설정 | 포함 |
| `shop.mp3` | 상점 | 포함 |
| `inventory.mp3` | 인벤토리 | 포함 |
| `match.mp3` | 클래식 경기 / 새 전투 음악의 대체 곡 | 포함 |
| `settings.mp3` | 환경 설정 | **추가할 파일** |
| `battle_desert.mp3` | 사막 유적 경기 | **추가할 파일** |
| `battle_jungle.mp3` | 정글 습지 경기 | **추가할 파일** |
| `battle_barricade.mp3` | 돌파 작전 경기 | **추가할 파일** |
| `battle_steel.mp3` | 강철 링 경기 | **추가할 파일** |
| `battle_ice.mp3` | 빙하 삼각주 경기 | **추가할 파일** |
| `clutch.mp3` | 어느 팀이든 둘 이상에서 최후 1개로 줄어든 이후 | **추가할 파일** |
| `curse.mp3` | 노곡빈의 저주 1.8초 시전 중, 이후 기존 전투/클러치 곡 복귀 | **추가할 파일** |

페이드 아웃 0.3초 / 페이드 인 0.5초, 반복 재생. Ogg/WAV/FLAC를 MP3로 잘못 이름 붙인 경우 헤더로 실제 디코더를 선택합니다. MP4/AAC 등은 실제 MP3로 변환하세요.

## 배경 PNG — `assets/themes/`

노곡빈 PNG만 직접 넣으면 됩니다. 나머지 기본 배경은 포함되어 있으며 교체할 수 있습니다. 이미지 미제공을 이유로 실행이 중단되지 않습니다.

| 파일명 | 권장 해상도 | 사용 |
|---|---|---|
| `노곡빈.png` | **1280×900** | **사용자가 추가**. 저주 시전 중 창 배경과 경기장 배경에 강제 표시. 미제공 시 보라색 임시 연출 |
| `main_menu.png` | 1280×900 | 메뉴·설정, 짙은 오버레이 아래 배경 |
| `shop.png` | 1280×900 | 상점 배경 |
| `inventory.png` | 1280×900 | 인벤토리 배경 |
| `arena_normal.png` | 1120×1350 | 클래식 일반 / 강철 링 |
| `arena_ice.png` | 1120×1350 | 클래식 얼음 / 빙하 삼각주 |
| `arena_mud.png` | 1120×1350 | 클래식 진흙 |
| `arena_desert.png` | 1120×1350 | 사막 유적 / 돌파 작전, 황금 모래·유적 테두리 |
| `arena_jungle.png` | 1120×1350 | 정글 습지, 녹색 식물·석재 바닥 |

경기장 실제 표시 영역은 560×675입니다. 배경 그림에 있는 돌·나무는 장식이며 물리 충돌체는 게임이 따로 그립니다. 메뉴 배경도 버튼/텍스트를 넣지 않는 것을 권장합니다.

## GUI와 VFX PNG — 포함된 제작 에셋

아틀라스(여러 그림을 일정 칸에 모은 PNG)로 저장하여 각 항목을 따로 표시합니다. 아래 순서는 왼쪽→오른쪽, 위→아래입니다. PNG 교체 시 칸 수와 순서를 유지하세요.

| 경로 | 칸 | 내용 |
|---|---|---|
| `assets/gui/skills_a.png` | 2×2 | 브릭월 / 타이거 / 체인 / 콜라 |
| `assets/gui/skills_b.png` | 2×2 | Bull / 앵클 / 저주 / 무하한 |
| `assets/gui/perks_a.png` | 2×2 | 천여주박 / 헤비 / 저거너트 / 스나이퍼 |
| `assets/gui/perks_b.png` | 2×2 | 라스트 리조트 / 메탈 / 텅스텐 / 랫 |
| `assets/gui/perks_c.png` | 2×2 | 슬리퍼 빌드 / 커브 / 천국의 눈 / 우정의 힘 |
| `assets/gui/skill_frames.png` | 4×2, 투명 | 위 8스킬 순서의 개별 선택 테두리 |
| `assets/gui/gui_panels.png` | 2×2 | 파랑 / 초록 / 보라 / 주황 버튼 패널 |
| `assets/vfx/vfx_burst.png` | 4×2, 투명 | 충돌 / 타이거·체인 / Bull / 앵클 / 저주 / 무하한 / 콜라 / 클러치 |
| `assets/vfx/eyes_of_heaven.png` | 단일 투명 PNG | 천안 발동 시 540×180으로 잠깐 표시 |

스킬·패시브 아이콘 시트 권장 1024×1024, 프레임/VFX 시트 2048×1024, 천안 1080×360. 현재 파일은 이 비율에 맞춰 런타임에서 스케일링합니다. 아이콘과 효과는 AI 생성 원본을 사용하며 실제 판정을 바꾸지 않습니다.

## 한국어 글꼴

`assets/fonts/NotoSansKR-Regular.ttf`, `NotoSansKR-Bold.ttf`를 포함합니다. Google Fonts의 Noto Sans KR 가변 글꼴에서 400/700 두께를 고정한 인스턴스입니다. SIL Open Font License 전문은 `assets/fonts/OFL.txt`. 시스템 글꼴 설치 없이 한글을 표시합니다.
