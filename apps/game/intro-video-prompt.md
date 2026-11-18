# 「용범의 탑」 인트로 영상 생성 프롬프트

## 제작 설정

- 길이: 15초 (클립 4개 분할 생성 후 편집으로 연결)
- 화면비: 16:9
- 해상도: 1920 × 1080 이상
- 분위기: 웅장하고 신비로운 다크 판타지 게임 시네마틱
- 용도: 게임 시작 전 타이틀 인트로
- 원칙: 기존 웹툰·애니메이션·게임의 캐릭터, 장면, 로고, 음악을 모방하지 않는 오리지널 영상

## 사용 방법

- 대부분의 영상 생성 도구는 클립당 5~10초로 제한되므로 15초를 한 번에 생성하지 않고, 클립 A~D를 각각 생성한다.
- 모든 클립 프롬프트 앞에 공통 스타일 블록을 그대로 붙여 넣어 색감·건축 양식을 고정한다.
- 이미지 입력을 지원하는 도구는 클립 A의 마지막 프레임을 클립 B의 시작 이미지로, 같은 방식으로 B→C, C→D를 연결한다.
- 도구가 오디오 생성을 지원하지 않으면 사운드 지시는 제외하고, 음원은 편집 단계에서 별도로 얹는다.
- 각 클립은 3~4초 분량이며, 편집에서 0.3~0.5초 크로스 디졸브로 연결한다.

## 공통 스타일 블록

```text
Original dark-fantasy game intro cinematic for a Korean fantasy game titled "Yongbeom's Tower". Visual identity: an impossibly tall ancient tower rising above a sea of clouds at night, mysterious violet shadows, muted indigo, antique gold light, weathered stone, drifting ash and tiny magical motes. Epic but emotionally intimate, premium game-trailer cinematography. Original world and architecture; do not imitate any existing anime, webtoon, game, film, character, logo, or recognizable scene. Camera: smooth deliberate movement, cinematic depth of field, no shaky camera, no abrupt zooms. Lighting: low-key moonlight, strong warm-gold focal highlights, restrained violet rim light, atmospheric volumetric fog. Composition: clear silhouettes, uncluttered frame, 16:9. Negative: subtitles, UI, readable text, logos, watermarks, extra fingers, deformed faces, modern buildings, guns, gore, fast action combat. The traveler is anonymous, seen mostly from behind, wearing a weathered dark cloak.
```

## 클립별 프롬프트

### 클립 A (0–4초) — 도착

```text
[Common style block]
Shot: Begin in near darkness. A single warm golden lantern flickers in the foreground as a lone young traveler in a weathered cloak approaches a colossal stone gate. Slow camera push-in, soft wind moves the cloak, faint dust floats through the light. The last frame holds the traveler small in front of the closed gate, centered, stable.
Sound: low orchestral drone, distant wind.
```

### 클립 B (4–8초) — 문 개방

```text
[Common style block]
Start from the provided first frame: the traveler small in front of the closed colossal stone gate.
Shot: The ancient gate opens by itself with a deep, restrained rumble. Thin violet and gold runes awaken across the stone, revealing glimpses of impossible stairways and distant lights inside the tower. The traveler remains a small silhouette to emphasize scale. Camera nearly static with a very slow push-in.
Sound: deep stone resonance, soft rumble, quiet rising strings.
```

### 클립 C (8–12초) — 상승

```text
[Common style block]
Shot: The camera rises along the tower exterior in a controlled vertical ascent, passing several distant illuminated windows and cloud layers. A brief, subtle shimmer suggests an unreliable memory, then settles; the tower structure itself does not change. Runes are abstract ornamental patterns only, no readable writing, no symbols resembling a known franchise.
Sound: rising but restrained string-and-choir swell, wind.
```

### 클립 D (12–15초) — 정상과 타이틀 카드

```text
[Common style block]
Shot: Reach the summit above the clouds. The tower's highest seal lights up like a small golden star. Then slowly settle into a clean, dark indigo title-card background with a few drifting motes, leaving generous centered negative space for a title to be added in post-production. The final second is a stable, nearly still frame with no subject in the center.
Sound: one clear bell-like tone as the seal ignites, then a short reverberant tail. No lyrics, no recognizable melody.
```

## 화면 자막 후반 작업

영상 모델이 한글 제목을 정확히 그리지 못할 수 있으므로, 마지막 타이틀은 편집 단계에서 별도로 얹는다.

- 제목: **용범의 탑**
- 보조 문구(선택): **기억을 믿을 것인가, 기록을 믿을 것인가**
- 등장 시점: 약 12.5초
- 연출: 금빛 얇은 획이 먼저 나타나고 제목이 천천히 드러난 뒤, 마지막 0.5초는 정지에 가깝게 유지
- 제목 글꼴: 획이 선명한 한국어 명조 계열 또는 분위기에 맞는 라이선스 확인된 디스플레이 서체
- 타이틀 배경과 글자 사이 대비를 충분히 확보

## 생성 후 확인 사항

- 타워와 문양이 특정 기존 작품의 상징이나 구도를 연상시키지 않는지 확인한다.
- 클립 간 경계에서 타워 형태, 문 크기, 조명 색, 여행자 복장이 일치하는지 확인한다.
- 클립 D 끝부분에 제목을 넣을 여백과 안정된 프레임이 있는지 확인한다.
- 음원, 글꼴, 생성 도구 결과물의 상업적 이용 조건을 배포 전에 확인한다.
- 짧은 영상에서 깜박임, 형태 변형, 타워 구조의 급격한 변화가 없는지 확인한다.
- 클립별 생성 길이가 지시 구간(3~4초)과 다르면 편집에서 속도 조정 또는 트리밍으로 15초에 맞춘다.
