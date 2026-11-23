# MINZ 일러스트 모션

정지 일러스트의 선과 색, 얼굴과 의상 형태를 유지하면서 9:16 영상으로 만드는 Codex 스킬입니다. 장면별로 그림, 기법, 길이, 강도를 정할 수 있습니다.

## 설치

저장소의 스킬 폴더를 사용자 또는 프로젝트의 Codex 스킬 디렉터리에 `minz-illustration-motion` 이름으로 추가합니다. 폴더 안에 `SKILL.md`, `agents/`, `assets/`, `references/`, `scripts/`가 함께 있어야 합니다.

그림을 첨부하고 다음과 같이 요청합니다.

> $minz-illustration-motion으로 첨부한 일러스트를 파일 순서대로 30초 이야기용 세로 영상으로 제작해줘. 얼굴과 손 형태를 유지하고 MP4와 장면별 적용 효과를 함께 줘.

## 사용

- **시연** — 49초에 11가지 연출을 넣는 [장면 프리셋](assets/demo-plan.json)입니다. 그림 경로를 제작용 그림으로 교체합니다.
- **이야기** — 각 장면의 감정과 행동에 맞는 연출을 고릅니다. 기법명과 설명 자막은 시연에 사용합니다.
- **렌더** — 프로젝트 렌더러를 우선 사용합니다. 새 렌더는 [연출 가이드](references/direction.md)의 Remotion과 FFmpeg 워크플로로 구성합니다.
- **검수** — Python 3과 ffprobe로 1080×1920·30fps MP4의 해상도, 코덱과 프레임 수를 검사합니다. 얼굴 왜곡, 레이어 경계, 화면 가장자리, 초점과 자막은 렌더 영상을 재생해 확인합니다.

```sh
python scripts/check_video.py assets/demo-plan.json --template
python scripts/check_video.py plan.json --video final.mp4 --report scene-effects.md
```

11가지 효과 구현 설명과 검수 유틸리티가 포함됩니다. 제작할 때는 제공한 원본 그림 및 필요한 파생 레이어와 프로젝트 렌더러를 사용합니다.
