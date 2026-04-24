"""Ключевые кадры из видео: ffmpeg, сцены + снижение дублей (шаг 3.2)."""

import subprocess
from pathlib import Path

_SCENE_THRESH = 0.35
_FALLBACK_FPS = "1/8"
_MAX_KEYFRAMES = 400


def _list_jpgs(frames_dir: Path) -> list[Path]:
    return sorted(
        p
        for p in frames_dir.iterdir()
        if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg")
    )


def _count_jpegs(frames_dir: Path) -> int:
    return len(_list_jpgs(frames_dir))


def _clear_jpegs(d: Path) -> None:
    for p in _list_jpgs(d):
        p.unlink(missing_ok=True)


def _subsample_excess(frames_dir: Path, max_n: int) -> int:
    """
    Оставляем снимки равномерно, если сцены дали слишком плотный набор.
    """
    cands = _list_jpgs(frames_dir)
    n = len(cands)
    if n <= max_n:
        return n
    step = n / max_n
    keep = {cands[int(i * step)] for i in range(max_n)}
    for p in cands:
        if p not in keep:
            p.unlink()
    return len(keep)


def _run_ffmpeg(
    i_video: Path,
    out_pattern: str,
    vf: str,
) -> None:
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(i_video),
        "-an",
        "-vf",
        vf,
        "-vsync",
        "vfr",
        "-q:v",
        "2",
        out_pattern,
    ]
    proc = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()
        if len(tail) > 400:
            tail = tail[:400] + "…"
        raise RuntimeError(
            f"ffmpeg (кадры) код {proc.returncode}: {tail}",
        )


def extract_keyframes_to_dir(
    video_path: Path,
    frames_dir: Path,
) -> int:
    """
    1) Кадры на смене сцены (min дубликатов соседних кадров).
    2) Запас: редкая выборка по fps, если (1) дала 0 кадров.
    3) Ограничение числа файлов.
    """
    frames_dir.mkdir(parents=True, exist_ok=True)
    _clear_jpegs(frames_dir)
    kf_tmpl = (frames_dir / "kf_%04d.jpg").as_posix()
    vf_scene = (
        f"select=gt(scene\\,{_SCENE_THRESH}),"
        f"scale=min(1280\\,iw):-2:flags=bicubic"
    )
    _run_ffmpeg(video_path, kf_tmpl, vf_scene)
    n = _count_jpegs(frames_dir)
    if n == 0:
        _clear_jpegs(frames_dir)
        fb = (frames_dir / "fb_%04d.jpg").as_posix()
        vf_fb = (
            f"fps={_FALLBACK_FPS},"
            f"scale=min(1280\\,iw):-2:flags=bicubic"
        )
        _run_ffmpeg(video_path, fb, vf_fb)
        n = _count_jpegs(frames_dir)
    if n == 0:
        raise RuntimeError("Не извлечён ни один кадр (keyframes).")
    n = _subsample_excess(frames_dir, _MAX_KEYFRAMES)
    return n
