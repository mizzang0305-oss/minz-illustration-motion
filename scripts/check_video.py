"""Check a scene plan and the encoded video, then export the applied effects."""
import argparse
import json
import subprocess
from fractions import Fraction
from pathlib import Path


FPS = 30
DEMO_FRAMES = 49 * FPS
DEMO_EFFECTS = (
    "punch-shake", "parallax", "orbit", "dolly-zoom", "puppet", "entrance",
    "rack-focus", "lamp-light", "weather", "whip-pan", "ken-burns",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def has_text(value):
    return isinstance(value, str) and bool(value.strip())


def check_path(base, value, field, check_files):
    require(has_text(value), f"{field}: 파일 경로가 필요합니다.")
    if check_files:
        require((base / value).is_file(), f"{field}: 파일을 찾을 수 없습니다. {value}")


def read_plan(path, check_files, need_applied):
    plan = json.loads(path.read_text(encoding="utf-8-sig"))
    require(isinstance(plan, dict), "계획은 JSON 객체여야 합니다.")
    mode = plan.get("mode")
    require(mode in ("demo", "story"), "mode는 demo 또는 story여야 합니다.")
    scenes = plan.get("scenes")
    require(isinstance(scenes, list) and scenes, "장면을 하나 이상 입력하세요.")
    scene_ids = set()
    for index, scene in enumerate(scenes, 1):
        require(isinstance(scene, dict), f"장면 {index}: JSON 객체가 필요합니다.")
        scene_id = scene.get("id")
        require(has_text(scene_id), f"장면 {index}: id가 필요합니다.")
        require(scene_id.strip() == scene_id and scene_id not in scene_ids,
                f"장면 {index}: 공백을 정리한 고유 id가 필요합니다.")
        scene_ids.add(scene_id)
        check_path(path.parent, scene.get("image"), f"{scene_id}.image", check_files)
        effect = scene.get("effect")
        require(effect in (*DEMO_EFFECTS, "none"), f"{scene_id}: 알 수 없는 기법입니다.")
        frames = scene.get("frames")
        require(type(frames) is int and frames > 0, f"{scene_id}: frames는 양의 정수입니다.")
        intensity = scene.get("intensity")
        require(type(intensity) in (float, int) and 0 <= intensity <= 1,
                f"{scene_id}: intensity는 0~1 사이의 숫자입니다.")
        if effect == "whip-pan":
            require(index < len(scenes), f"{scene_id}: 휩 팬에 다음 장면이 필요합니다.")
        if mode == "demo":
            for field in ("label", "caption"):
                value = scene.get(field)
                require(has_text(value) and len(value.splitlines()) == 1,
                        f"{scene_id}.{field}: 한 줄 텍스트가 필요합니다.")
        layers = scene.get("layers", {})
        require(isinstance(layers, dict), f"{scene_id}: layers는 역할별 경로 객체입니다.")
        for role, source in layers.items():
            check_path(path.parent, source, f"{scene_id}.layers.{role}", check_files)
        require(isinstance(scene.get("params", {}), dict), f"{scene_id}: params는 객체입니다.")
        if need_applied:
            require(has_text(scene.get("applied")), f"{scene_id}: 실제 적용한 효과를 기록하세요.")
    total = sum(scene["frames"] for scene in scenes)
    if mode == "demo":
        require(tuple(scene["effect"] for scene in scenes) == DEMO_EFFECTS,
                "시연 모드에는 11가지 기법을 지정 순서대로 각각 한 번씩 넣으세요.")
        require(total == DEMO_FRAMES, "시연 모드는 1,470프레임(49초)이어야 합니다.")
    return scenes, total


def check_mp4(path, frames):
    require(path.suffix.lower() == ".mp4", "영상 확장자는 .mp4여야 합니다.")
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
         "-show_entries", "stream=codec_name,width,height,r_frame_rate,avg_frame_rate,pix_fmt,nb_read_frames:format=format_name",
         "-of", "json", str(path.resolve())],
        check=True, capture_output=True, text=True,
    )
    measured = json.loads(result.stdout)
    require("mp4" in measured.get("format", {}).get("format_name", "").split(","),
            "MP4 컨테이너가 필요합니다.")
    streams = measured.get("streams", [])
    require(bool(streams), "영상 스트림이 없습니다.")
    stream = streams[0]
    require((stream.get("width"), stream.get("height")) == (1080, 1920),
            "영상은 1080×1920이어야 합니다.")
    require(stream.get("codec_name") == "h264" and stream.get("pix_fmt") == "yuv420p",
            "영상은 H.264 yuv420p여야 합니다.")
    require(all(Fraction(stream.get(key, "0")) == FPS
                for key in ("r_frame_rate", "avg_frame_rate")), "영상은 30fps여야 합니다.")
    require(stream.get("nb_read_frames") == str(frames),
            f"계획은 {frames}프레임, 실제는 {stream.get('nb_read_frames', '미확인')}프레임입니다.")


def markdown_cell(value):
    text = " ".join(value.splitlines())
    for char in "\\|`*_<>&[]":
        text = text.replace(char, "\\" + char)
    return text


def write_report(path, video, scenes):
    if path.resolve() == video.resolve():
        raise ValueError("영상과 목록은 별도 경로에 저장하세요.")
    lines = [
        "# 장면별 적용 효과",
        "",
        f"- 영상 파일 {markdown_cell(video.name)}",
        "- 규격 1080×1920 · 30fps · H.264 MP4",
        "- 시간 범위에서 종료 시각은 다음 장면의 시작점입니다.",
        "",
        "| 장면 | 구간(초) | 실제 적용 효과 |",
        "| --- | --- | --- |",
    ]
    start = 0
    for scene in scenes:
        end = start + scene["frames"]
        lines.append(f"| {markdown_cell(scene['id'])} | {start / FPS:.3f}–{end / FPS:.3f} "
                     f"| {markdown_cell(scene['applied'])} |")
        start = end
    with path.open("x", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--template", action="store_true",
                        help="구조만 검사하고 그림 경로의 실재 여부는 건너뜁니다.")
    args = parser.parse_args()
    if args.report and not args.video:
        parser.error("--report에는 --video가 필요합니다.")
    if args.template and args.video:
        parser.error("--template은 계획 구조 검사에서만 사용할 수 있습니다.")
    try:
        scenes, frames = read_plan(args.plan, not args.template, bool(args.report))
        if args.video:
            check_mp4(args.video, frames)
        if args.report:
            write_report(args.report, args.video, scenes)
    except subprocess.CalledProcessError as error:
        parser.exit(1, f"ffprobe 검사 실패: {error.stderr.strip()}\n")
    except (OSError, ValueError, ZeroDivisionError) as error:
        parser.exit(1, f"검사 실패: {error}\n")
    print(f"검사 통과 · 장면 {len(scenes)}개 · {frames}프레임 · {frames / FPS:.3f}초")


if __name__ == "__main__":
    main()
