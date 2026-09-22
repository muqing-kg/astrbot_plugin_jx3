"""把 JX3BOX 宠物奇遇奖励图标本地高清化，按奇遇名归档。

    python tmp/build_pet_icons.py [--force]

源图约 466x494，页面按 47px 显示；直接由浏览器缩放会发虚。
这里按 2 倍显示尺寸（94px 宽）用 Lanczos 预缩，输出到
templates/img/奇遇珍卷/宠物奇遇/<奇遇名>.webp，运行时直接读取本地素材。
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
OUT_DIR = ROOT / "templates" / "img" / "奇遇珍卷" / "宠物奇遇"
IMG_ROOT = "https://img.jx3box.com/adventure/adventure/std/"
TARGET_WIDTH = 94
INVALID = re.compile(r'[\\/:*?"<>|]')


def safe(name: str) -> str:
    return INVALID.sub("_", str(name).strip())


def reward_url(path: str) -> str:
    clean = str(path or "").strip().lower().replace("\\", "/")
    clean = clean.replace("ui/image/adventure/", "")
    return IMG_ROOT + clean[:-4] + ".png" if clean.endswith(".tga") else IMG_ROOT + clean


async def main() -> int:
    force = "--force" in sys.argv
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(
            "https://node.jx3box.com/serendipities",
            params={"type": "pet", "_no_page": 1},
        ) as response:
            payload = await response.json()
        rows = [
            row
            for row in payload.get("list") or []
            if row.get("szOpenRewardPath") and row.get("szName")
        ]

        done = skipped = failed = 0
        for row in rows:
            target = OUT_DIR / f"{safe(row['szName'])}.webp"
            if target.exists() and not force:
                skipped += 1
                continue
            try:
                async with session.get(reward_url(row["szOpenRewardPath"])) as response:
                    response.raise_for_status()
                    raw = await response.read()
                image = Image.open(io.BytesIO(raw)).convert("RGBA")
                height = max(1, round(image.height * TARGET_WIDTH / image.width))
                image.resize((TARGET_WIDTH, height), Image.LANCZOS).save(
                    target, "WEBP", quality=90, method=6
                )
                done += 1
            except Exception as exc:
                failed += 1
                print(f"fail {row.get('dwID')} {row.get('szName')}: {exc}")
    total = sum(f.stat().st_size for f in OUT_DIR.glob("*.webp"))
    print(f"built={done} skipped={skipped} failed={failed} total={len(rows)} size={round(total / 1024)}KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
