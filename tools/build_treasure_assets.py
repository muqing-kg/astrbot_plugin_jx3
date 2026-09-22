"""把奇遇珍卷需要的 JX3BOX 素材全部下载到本地，按中文奇遇名归档。

    python tmp/build_treasure_assets.py [--force]

输出（templates/img/奇遇珍卷）：
- 卷轴纸、转轴、计数条、名条、标题、题诗等静态素材，中文命名
- 普通奇遇/<奇遇名>.webp：源图已是 2 倍显示尺寸
- 绝世奇遇/<奇遇名>.webp 与 <奇遇名>_已出.webp：按布局宽度的 2 倍 Lanczos 预缩
"""
from __future__ import annotations

import asyncio
import io
import re
import sys
from pathlib import Path

import aiohttp
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.treasure_data import CDN_ROOT, PERFECT_ITEMS  # noqa: E402

OUT_ROOT = ROOT / "templates" / "img" / "奇遇珍卷"
SCALE = 2
INVALID = re.compile(r'[\\/:*?"<>|]')

STATIC_FILES = {
    "landscape/bg.png": "卷轴底.png",
    "content_bg.png": "卷轴纸.png",
    "landscape/left.png": "卷轴轴头左.png",
    "landscape/right.png": "卷轴轴头右.png",
    "landscape/pt_qy_bg.png": "普通奇遇计数条.png",
    "landscape/pet_qy_bg.png": "宠物奇遇计数条.png",
    "landscape/world_qy_bg.png": "绝世奇遇计数条.png",
    "landscape/title_icon.png": "奇遇珍卷标题.png",
    "pt/text_bg.png": "普通奇遇名条.png",
    "pt/default.png": "普通奇遇缺省.png",
    "pet_img_border.png": "宠物奇遇边框.png",
    "world/world_bg.svg": "绝世底图.svg",
    "world/text_bg.png": "绝世名条.png",
    "world/text_bg_act.png": "绝世名条已出.png",
    "poetry_lan.png": "题诗.png",
}


def safe(name: str) -> str:
    return INVALID.sub("_", str(name).strip())


async def fetch(session: aiohttp.ClientSession, url: str) -> bytes | None:
    async with session.get(url) as response:
        if response.status != 200:
            return None
        return await response.read()


async def fetch_names(session: aiohttp.ClientSession, kind: str) -> dict[int, str]:
    async with session.get(
        "https://node.jx3box.com/serendipities",
        params={"type": kind, "_no_page": 1},
    ) as response:
        payload = await response.json()
    return {
        int(row["dwID"]): safe(row["szName"])
        for row in payload.get("list") or []
        if row.get("dwID") and row.get("szName")
    }


async def download_static(session: aiohttp.ClientSession, force: bool) -> tuple[int, int]:
    done = skipped = 0
    for rel, name in STATIC_FILES.items():
        target = OUT_ROOT / name
        if target.exists() and not force:
            skipped += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        raw = await fetch(session, CDN_ROOT + rel)
        if raw is None:
            print(f"fail static {rel}")
            continue
        target.write_bytes(raw)
        done += 1
    return done, skipped


async def download_normal(
    session: aiohttp.ClientSession, names: dict[int, str], force: bool
) -> tuple[int, int]:
    done = skipped = 0
    for dw_id, name in names.items():
        target = OUT_ROOT / "普通奇遇" / f"{name}.webp"
        if target.exists() and not force:
            skipped += 1
            continue
        raw = await fetch(session, f"{CDN_ROOT}pt/{dw_id}.png")
        if raw is None:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        Image.open(io.BytesIO(raw)).convert("RGBA").save(target, "WEBP", quality=90, method=6)
        done += 1
    return done, skipped


async def download_perfect(
    session: aiohttp.ClientSession, names: dict[int, str], force: bool
) -> tuple[int, int]:
    done = skipped = 0
    for dw_id, (image_style, _label_style) in PERFECT_ITEMS.items():
        name = names.get(dw_id, str(dw_id))
        width = int(image_style.get("width") or 0) * SCALE
        for suffix, out_suffix in (("", ""), ("_act", "_已出")):
            target = OUT_ROOT / "绝世奇遇" / f"{name}{out_suffix}.webp"
            if target.exists() and not force:
                skipped += 1
                continue
            raw = await fetch(session, f"{CDN_ROOT}world/{dw_id}{suffix}.png")
            if raw is None:
                print(f"fail world/{dw_id}{suffix}.png")
                continue
            image = Image.open(io.BytesIO(raw)).convert("RGBA")
            if width and image.width > width:
                height = max(1, round(image.height * width / image.width))
                image = image.resize((width, height), Image.LANCZOS)
            target.parent.mkdir(parents=True, exist_ok=True)
            image.save(target, "WEBP", quality=90, method=6)
            done += 1
    return done, skipped


async def main() -> int:
    force = "--force" in sys.argv
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        normal_names = await fetch_names(session, "normal")
        perfect_names = await fetch_names(session, "perfect")
        static_done, static_skip = await download_static(session, force)
        normal_done, normal_skip = await download_normal(session, normal_names, force)
        perfect_done, perfect_skip = await download_perfect(session, perfect_names, force)
    total = sum(f.stat().st_size for f in OUT_ROOT.rglob("*") if f.is_file())
    print(
        f"static={static_done}/{static_skip} 普通={normal_done}/{normal_skip} "
        f"绝世={perfect_done}/{perfect_skip} total={round(total / 1024)}KB"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
