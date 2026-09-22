"""核对奇遇珍卷本地素材是否覆盖全部奇遇（按奇遇名匹配文件名）。"""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "templates" / "img" / "奇遇珍卷"
INVALID = re.compile(r'[\\/:*?"<>|]')


def safe(name: str) -> str:
    return INVALID.sub("_", str(name).strip())


def names(kind: str) -> list[str]:
    url = f"https://node.jx3box.com/serendipities?type={kind}&_no_page=1"
    with urllib.request.urlopen(url, timeout=30) as response:
        payload = json.load(response)
    return [row["szName"] for row in payload["list"] if row.get("szName")]


def main() -> int:
    pt, js, cw = names("normal"), names("perfect"), names("pet")
    miss_pt = [n for n in pt if not (BASE / "普通奇遇" / f"{safe(n)}.webp").exists()]
    miss_js = [
        n
        for n in js
        if not (BASE / "绝世奇遇" / f"{safe(n)}.webp").exists()
        or not (BASE / "绝世奇遇" / f"{safe(n)}_已出.webp").exists()
    ]
    miss_cw = [n for n in cw if not (BASE / "宠物奇遇" / f"{safe(n)}.webp").exists()]
    static = [
        "卷轴底.png",
        "卷轴纸.png",
        "卷轴轴头左.png",
        "卷轴轴头右.png",
        "普通奇遇计数条.png",
        "宠物奇遇计数条.png",
        "绝世奇遇计数条.png",
        "普通奇遇名条.png",
        "普通奇遇缺省.png",
        "宠物奇遇边框.png",
        "绝世底图.svg",
        "绝世名条.png",
        "绝世名条已出.png",
        "奇遇珍卷标题.png",
        "题诗.png",
    ]
    print("普通", len(pt), "缺", miss_pt)
    print("绝世", len(js), "缺", miss_js)
    print("宠物", len(cw), "缺", miss_cw)
    print("静态缺", [n for n in static if not (BASE / n).exists()])
    print("logo", (ROOT / "templates" / "img" / "剑网3标识.png").exists())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
