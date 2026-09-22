"""生成奇遇珍卷内嵌字体：Noto Sans SC 按珍卷用字子集化。

    python tools/build_card_font.py [--force]

官网 JX3BOX 珍卷页正文跟随系统字体（Windows 落到微软雅黑），且页面自带
Noto Sans SC web 字体。这里取同源 Noto Sans SC 变量字体，按珍卷固定文案与
全部奇遇名子集化，输出 templates/font/珍卷字体.woff2，渲染时以 data URI 内联，
保证任何渲染机上字形一致。
"""
from __future__ import annotations

import io
import json
import sys
import urllib.request
from pathlib import Path

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONT_URL = "https://cdn.jx3box.com/lib/fonts/Noto_Sans_SC/NotoSansSC-VariableFont_wght.ttf"
SOURCE_CACHE = ROOT / "tmp" / "NotoSansSC-VariableFont_wght.ttf"
OUTPUT = ROOT / "templates" / "font" / "珍卷字体.woff2"

FIXED_TEXT = "奇遇珍卷普通宠物绝世进度记录时间服务器角色标题【】：%0123456789/ "


def adventure_names() -> str:
    text = ""
    for kind in ("normal", "perfect", "pet"):
        url = f"https://node.jx3box.com/serendipities?type={kind}&_no_page=1"
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = json.load(response)
        text += "".join(row["szName"] for row in payload["list"] if row.get("szName"))
    return text


def main() -> int:
    force = "--force" in sys.argv
    if OUTPUT.exists() and not force:
        print(f"skip: {OUTPUT.name} 已存在（{round(OUTPUT.stat().st_size / 1024, 1)}KB），加 --force 重建")
        return 0
    if not SOURCE_CACHE.exists():
        SOURCE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(FONT_URL, timeout=180) as response:
            SOURCE_CACHE.write_bytes(response.read())

    text = FIXED_TEXT + adventure_names()
    font = TTFont(str(SOURCE_CACHE))
    options = Options()
    options.layout_features = ["*"]
    options.hinting = False
    options.flavor = "woff2"
    subsetter = Subsetter(options=options)
    subsetter.populate(text=text)
    subsetter.subset(font)
    font.flavor = "woff2"
    buffer = io.BytesIO()
    font.save(buffer)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(buffer.getvalue())
    print(
        f"built {OUTPUT.name}: glyphs={len(set(text))} "
        f"size={round(OUTPUT.stat().st_size / 1024, 1)}KB"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
