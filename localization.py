"""Korean/English UI and combat strings. English fallback never crashes rendering."""
import re
from abilities import SKILL_NAMES,SKILL_DESCRIPTIONS
from perks import PERKS

SKILL_KO={'brickwall':'브릭월','tiger':'타이거 샷','chain':'체인','cola':'코카 콜라 에스푸마','bull':'불','ankle_breaker':'앵클 브레이커','curse':'노곡빈의 저주','infinity':'무하한'}
PERK_KO=dict(zip(PERKS,['천여주박','헤비','저거너트','스나이퍼','라스트 리조트','메탈','텅스텐','랫','슬리퍼 빌드','커브 샷','천국의 눈','우정의 힘']))
DESC_KO={
'brickwall':'콘크리트처럼 고정됩니다. 크기 +75%, 부상 면역. 공격 2턴 / 방어 1턴 유지.',
 'tiger':'속도 +100%, 파워 +80%, 조준 오차 0. 나무를 즉시 부수고 풍압으로 주변을 밀칩니다.',
 'chain':'적중 후 E로 마우스 방향 재가속. 최대 5회, 매번 속도와 파워가 감소합니다.',
 'cola':'정지 시 충격파로 폭발합니다. 마지막 아군이 아니라면 자신도 사라집니다.',
 'bull':'공격: 속도·파워 +50%, 나무 파괴. 방어: 적 정지 → 뒤로 빠짐 → 돌진. 반 파워 밀치기와 3턴 부상.',
 'ankle_breaker':'방어 전용. 접촉 시 옆으로 피하고 잠시 무적이 됩니다. 적은 원래 방향으로 계속 이동합니다.',
 'curse':'10턴이 지난 뒤 경기당 1회. 상대 전체가 떨다가 무작위 방향으로 최대 세기로 발사됩니다.',
 'infinity':'방어 전용. 접근하는 적을 점점 느리게 하여 접촉 전에 멈춥니다. 충돌·풍압 면역.',
 'heavenly':'아군 수 절반(올림), 주요 전투 능력 ×2. 1대1에서는 장착할 수 없습니다.',
 'heavy':'크기·파워·맷집 +25%, 속도 -25%. 저거너트와 함께 장착할 수 없습니다.',
 'juggernaut':'크기·파워·맷집 +50%, 속도 -50%. 헤비와 함께 장착할 수 없습니다.',
 'sniper':'정확도 +50%(오차각 감소), 속도 +20%.',
 'last_resort':'마지막 한 알이 된 현재 턴 동안 경계벽 보호. 경기당 한 번 발동합니다.',
 'metal':'맷집 +30%, 속도 -20%.',
 'tungsten':'맷집 +60%, 속도 -35%. 부상 지속이 한 턴 짧아집니다.',
 'rat':'크기·맷집 -30%, 파워 +15%, 속도 +30%.',
 'sleeper':'크기·맷집 -15%, 파워 +30%.',
 'curve':'조준 중 C / C+휠로 곡선의 방향과 강도를 조절합니다. 실제 궤도가 휘어집니다.',
 'eyes':'상대 방어 확정 시 어떤 능력을 어느 구슬에 썼는지 크게 표시합니다. 재사용 8턴.',
 'friendship':'95px 안 아군이 자신 포함 둘 이상이면 알당 맷집 +5%, 최대 +25%.',
}
TEXT={
 'START':'시작','SHOP':'상점','INVENTORY':'인벤토리','SETTINGS':'설정','BACK':'뒤로',
 'SKILLS':'스킬','PASSIVES':'패시브','SKINS':'스킨','STATS':'스탯','EQUIP':'장착','UNEQUIP':'해제',
 'BLUE':'파랑','RED':'빨강','BLUE LOADOUT':'파랑 로드아웃','RED / CPU':'빨강 / CPU',
 'READY':'준비 완료','EMPTY':'빈 슬롯','LOCKED':'미보유','OWNED':'보유','SELECT SLOT':'장착할 슬롯 선택',
 'TEAM SIZE':'팀당 구슬','OPPONENT':'상대','SURFACE':'기본 바닥','OBSTACLES':'장애물','MAP':'맵',
 'LOCAL 2P':'로컬 2인','EASY':'쉬움','NORMAL':'보통','HARD':'어려움','NONE':'없음','WOOD':'나무','STEEL':'강철','MIXED':'혼합',
 'ICE':'얼음','MUD':'진흙','CLASSIC':'클래식','CONFIRM & START':'확정하고 시작','EDIT LOADOUT':'로드아웃 편집',
 'LANGUAGE':'언어','KOREAN':'한국어','ENGLISH':'English','SCREEN SHAKE':'화면 흔들림','WINDOW SHAKE (EXPERIMENTAL)':'창 자체 흔들림 (실험적)',
 'HIT STOP':'짧은 타격 정지','FLASH EFFECTS':'섬광 효과','ON':'켜짐','OFF':'꺼짐','MUTE':'음소거','UNMUTE':'소리 켜기',
 'MUSIC VOLUME':'배경음악','SFX VOLUME':'효과음','OPTIONS':'환경 설정','REMATCH':'다시 경기','MENU':'메뉴','FINAL RESULT':'경기 결과',
 'BLUE WINS!':'파랑 승리!','RED WINS!':'빨강 승리!','DRAW!':'무승부!','TURN PASSED':'턴을 넘겼습니다',
 'DEFENSE LOCKED':'방어 준비 완료','SKILL CANCELLED':'스킬 준비 취소','SKILL ON COOLDOWN':'아직 사용할 수 없습니다',
 'ATTACK SKILL: NOT AVAILABLE IN DEFENSE':'이 능력은 현재 역할에서 사용할 수 없습니다',
 'SHOOT THE MARBLE WITH THE ARMED ATTACK SKILL':'공격 스킬을 준비한 구슬로 발사하세요',
 'BRICKWALL IS IMMOBILE: SHOOT A DIFFERENT MARBLE':'브릭월은 움직일 수 없습니다. 다른 구슬을 발사하세요',
 'ATTACK LOCKED! WAITING FOR DEFENDER READY':'공격 확정! 방어 준비를 기다립니다',
 'E: CLICK YOUR MARBLE TO ARM SKILL':'자신의 구슬을 클릭해 스킬을 준비하세요','SKILL SELECTION CANCELLED':'스킬 선택 취소',
 'DEFENSE ALREADY READY':'이미 방어 준비를 확정했습니다','CLUTCH! SKILLS RESET':'클러치! 스킬 재사용 시간 초기화',
 'LAST RESORT! EDGE SHIELD':'라스트 리조트! 경계 보호 발동','LOCK REVEAL  /  SKILLS EXPOSED':'조준과 방어 능력 공개',
 'PHYSICS RUNNING':'구슬 이동 중','MATCH FINISHED':'경기 종료','ATTACK: DRAG + RELEASE TO LOCK (DOES NOT FIRE YET)':'공격: 반대로 당겼다 놓으면 조준 확정',
 'DEFENSE: E + CLICK BRICKWALL, THEN SPACE / READY':'방어: E → 자신의 구슬 클릭 → Space로 준비 완료',
 'WAITING FOR LOCKS...':'양쪽 준비를 기다립니다','REVEALING LOCKED AIM AND HIDDEN DEFENSE...':'숨겨진 조준과 방어 능력을 공개합니다',
 'WAIT FOR MARBLES TO STOP...':'구슬이 멈출 때까지 기다리세요','CHAIN: POINT MOUSE + PRESS E TO DASH AGAIN':'체인: 마우스로 방향을 정하고 E로 다시 돌진',
 'R REMATCH     ESC MENU':'R 다시 경기     Esc 메뉴','RED  /  OPPONENT':'빨강 / 상대','BLUE  /  YOUR SIDE':'파랑 / 아군',
 '0 DEG AIM ERROR':'조준 오차 0도','PERFECT AIM':'정확한 조준','READY [SPACE]':'방어 완료 [Space]',
 'P: +1000 Coins':'P: 코인 1,000 추가','COINS +1000':'코인 1,000 추가!',
 'CURSE: AVAILABLE AFTER TURN 10, ONCE PER MATCH':'저주: 10턴 이후 경기당 한 번만 사용 가능',
 'STEEL WALLS OPEN!':'강철 경계 개방! 이제 장외로 떨어뜨리세요',
 'NEW! Added to your inventory':'새 아이템! 인벤토리에 추가했습니다','OPENING...':'열고 있습니다...',
 'Common':'일반','Rare':'희귀','Epic':'영웅','Legendary':'전설',
 'Not enough Coins. Finish a match to earn more!':'코인이 부족합니다. P키로 1,000코인을 추가할 수 있습니다.',
 'Item is not owned. Try the shop!':'아직 보유하지 않은 아이템입니다. 상점에서 뽑아 보세요.',
 'Equip up to 3 different passives.':'서로 다른 패시브를 최대 3개 장착할 수 있습니다.',
 'Heavy and Juggernaut cannot be equipped together.':'헤비와 저거너트는 함께 장착할 수 없습니다.',
 'Heavenly Restricted is unavailable in 1v1.':'천여주박은 1대1에서 사용할 수 없습니다.',
 'Invalid slot':'장착할 슬롯을 선택하세요',
}
TEXT.update({
 'SKILL NOT AVAILABLE ON THIS TURN':'이 스킬은 현재 역할에서 사용할 수 없습니다',
 'CURSE: TURN 11+, ONCE PER MATCH':'저주: 11턴부터 경기당 한 번만 사용 가능',
 'CURSE UNLEASHED!':'노곡빈의 저주!', 'USED':'사용 완료',
 'DEFENSE: E + CLICK MARBLE, THEN SPACE / READY':'방어: E → 구슬 클릭 → Space 준비 완료',
 'PASSIVES + SKILLS  /  V0.7':'패시브 + 스킬  /  V0.7',
 '1/2 SLOT   E SKILL   SPACE DEF READY   TAB PASS   D DEBUG   F FAST':'1/2 스킬 선택 · E 사용 · Space 방어 완료 · Tab 턴 넘김 · F10 설정',
 'SKILL CANCELLED':'스킬 준비를 취소했습니다',
 'Not enough Coins':'코인이 부족합니다',
})
STAT_KO={'accuracy':'정확도','speed':'속도','power':'파워','toughness':'맷집','critical':'치명'}

def item_name(key,kind,lang='ko'):
    if kind=='skill':return SKILL_KO[key] if lang=='ko' else SKILL_NAMES[key]
    if kind=='passive':return PERK_KO[key] if lang=='ko' else PERKS[key].name
    from skins import SKINS
    return SKINS[key].ko if lang=='ko' else SKINS[key].en

def description(key,kind,lang='ko'):
    if kind=='skin':return '외형만 바뀝니다. 능력치는 그대로입니다.' if lang=='ko' else 'Cosmetic only. Stats are unchanged.'
    return DESC_KO[key] if lang=='ko' else SKILL_DESCRIPTIONS[key] if kind=='skill' else PERKS[key].description

def tr(text,lang='ko'):
    text=str(text)
    if lang!='ko':return text
    if text in TEXT:return TEXT[text]
    text=re.sub(r'BLUE STARTS  \|  (.+?)  \|  50 POINTS / TEAM',r'파랑 선공 · \1 · 팀당 50포인트',text)
    text=re.sub(r'(\d+) TURNS  \|  (\d+) COLLISIONS',r'\1턴 · 충돌 \2회',text)
    text=text.replace('LOCK ON: ','대상 포착: ').replace(' / 50 POINTS',' / 50포인트')
    for key,name in SKILL_NAMES.items():text=text.replace(name,SKILL_KO[key])
    for key,p in PERKS.items():text=text.replace(p.name,PERK_KO[key])
    for source,target in [('TURN ','턴 '),(' SEC',' 초'),('AIM ERROR: ','조준 오차: '),(' DEG','도'),('SIMULATION SPEED: ','시뮬레이션 속도: '),('x PHYSICS','배속'),('HITS: ','충돌: '),('EYES: ','천국의 눈: '),('EYES OF HEAVEN: ','천국의 눈: '),(' ARMED: MARBLE #',' 준비: 구슬 #'),('SLOT ','슬롯 '),('CHAIN! E TO DASH  /  ','체인! E로 돌진 / '),(' Coins',' 코인'),(' turns','턴'),('DUPLICATE: +','중복 보상: +'),('COOLDOWN ','재사용 '),(' CURVE ',' 커브 '),('PULL ','당김 '),('DEF READY','방어 완료'),('ATK LOCKED','공격 확정'),('ATK AIMING','조준 중'),('DEF PLANNING','방어 준비 중'),('NORMAL','보통'),('ICE','얼음'),('MUD','진흙'),('NONE','없음'),('WOOD','나무'),('STEEL','강철'),('MIXED','혼합'),('BLUE','파랑'),('RED','빨강')]:text=text.replace(source,target)
    return text
