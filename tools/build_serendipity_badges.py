"""按 JX3BOX 名表与奇遇图集补齐奇遇徽记。

    python tools/build_serendipity_badges.py --check    # 只比对，不写文件
    python tools/build_serendipity_badges.py            # 只补缺失的徽记
    python tools/build_serendipity_badges.py --force    # 全部重新裁切

名表（node.jx3box.com 的 serendipities）给出每个奇遇的图集路径 szNamePath
与帧号 nNameFrame；同名 .UITex 是帧坐标表：头 24 字节为宽高与帧数，随后
64 字节纹理名，再往后每帧 20 字节 (flag, x, y, w, h)。按帧矩形裁切即可，
不需要再靠肉眼对齐网格。

图集地址不放代码里，按优先级读取：
  1. 环境变量 JX3_SERENDIPITY_ATLAS
  2. tmp/serendipity_atlas/source.txt 内的一行模板
模板里用 {name} 占位纹理名，例如 https://host/ui/Image/UICommon/{name}
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import struct
import sys
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = Path(os.environ.get("JX3_SERENDIPITY_OUT") or ROOT / "templates" / "img" / "serendipity")
CACHE_DIR = ROOT / "tmp" / "serendipity_atlas"
SOURCE_FILE = CACHE_DIR / "source.txt"

TABLE_URL = "https://node.jx3box.com/api/node/serendipities?page={page}"
USER_AGENT = "Mozilla/5.0"
TEX_HEADER = 24 + 64
FRAME_SIZE = 20
INVALID = re.compile(r'[\\/:*?"<>|]')


def fetch(url: str, timeout: int = 30) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def atlas_source() -> str:
    template = os.environ.get("JX3_SERENDIPITY_ATLAS", "").strip()
    if not template and SOURCE_FILE.exists():
        template = SOURCE_FILE.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    if "{name}" not in template:
        raise SystemExit(
            "缺少图集地址：请设置环境变量 JX3_SERENDIPITY_ATLAS，"
            f"或把模板（含 {{name}} 占位）写入 {SOURCE_FILE}"
        )
    return template


def serendipities() -> list[dict]:
    rows: list[dict] = []
    for page in range(1, 20):
        payload = json.loads(fetch(TABLE_URL.format(page=page)))
        items = payload.get("list") or []
        if not items:
            break
        rows.extend([row for row in items if isinstance(row, dict)])
    return rows


def uitex_frames(blob: bytes) -> tuple[int, int, list[tuple[int, int, int, int, int]]]:
    width = int.from_bytes(blob[4:8], "little")
    height = int.from_bytes(blob[8:12], "little")
    count = int.from_bytes(blob[12:16], "little")
    frames = [
        struct.unpack_from("<5I", blob, TEX_HEADER + index * FRAME_SIZE)
        for index in range(count)
    ]
    return width, height, frames


def cached(name: str, template: str, force: bool) -> bytes:
    path = CACHE_DIR / name
    if force or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(fetch(template.format(name=name)))
    return path.read_bytes()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="补齐奇遇徽记")
    parser.add_argument("--check", action="store_true", help="只比对现有徽记，不写文件")
    parser.add_argument("--force", action="store_true", help="重新下载图集并全部重裁")
    args = parser.parse_args()

    template = atlas_source()
    rows = serendipities()
    atlases: dict[str, Image.Image] = {}
    frames: dict[str, list[tuple[int, int, int, int, int]]] = {}

    written = matched = drifted = missing = skipped = 0
    drift_examples: list[str] = []
    for row in rows:
        name = str(row.get("szName") or "").strip()
        stem = Path(str(row.get("szNamePath") or "").replace("\\", "/")).stem
        frame = row.get("nNameFrame")
        if not name or not stem or frame is None:
            skipped += 1
            continue
        if stem not in atlases:
            try:
                _, _, parsed = uitex_frames(cached(f"{stem}.UITex", template, args.force))
                atlas = Image.open(
                    io.BytesIO(cached(f"{stem}.Tga", template, args.force))
                ).convert("RGBA")
            except Exception as error:  # 图集缺失或镜像不可用时跳过该批
                print(f"跳过 {stem}: {error}", file=sys.stderr)
                atlases[stem] = None
                continue
            atlases[stem] = atlas
            frames[stem] = parsed
        atlas = atlases.get(stem)
        if atlas is None or not 0 <= int(frame) < len(frames[stem]):
            skipped += 1
            continue

        _, x, y, width, height = frames[stem][int(frame)]
        badge = atlas.crop((x, y, x + width, y + height))
        target = OUT_DIR / f"{INVALID.sub('_', name)}.png"

        if args.check:
            if not target.exists():
                missing += 1
                continue
            current = Image.open(target).convert("RGBA")
            if current.size != badge.size:
                drifted += 1
                if len(drift_examples) < 10:
                    drift_examples.append(f"{name} 现有 {current.size} / 帧表 {badge.size}")
                continue
            from PIL import ImageChops

            box = ImageChops.difference(current, badge).getbbox()
            if box is None:
                matched += 1
            else:
                drifted += 1
                if len(drift_examples) < 10:
                    drift_examples.append(f"{name} 像素差异 {box}")
            continue

        if target.exists() and not args.force:
            continue
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        badge.save(target)
        written += 1

    if args.check:
        print(f"名表 {len(rows)} 条；与帧表完全一致 {matched}，尺寸或像素有差异 {drifted}，本地缺失 {missing}，跳过 {skipped}")
        for line in drift_examples:
            print("   ", line)
    else:
        print(f"名表 {len(rows)} 条；新写入 {written}（已存在 {len(rows) - written - skipped}，跳过 {skipped}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
