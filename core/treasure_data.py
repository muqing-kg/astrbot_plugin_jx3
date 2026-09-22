"""奇遇珍卷的静态布局数据。

绝世奇遇素材坐标来自 JX3BOX `treasure_perfect.json`（landscape 视图）。
"""

from __future__ import annotations


CDN_ROOT = "https://cdn.jx3box.com/design/treasure/"
IMG_ROOT = "https://img.jx3box.com/adventure/adventure/std/"


# 键序即官方绘制顺序（treasure_perfect.json 的 items 数组顺序），层叠关系按此叠加
PERFECT_ITEMS = {
    1: ({"top": 1, "left": 261, "width": 168}, {"top": 78, "left": 311}),
    90: ({"top": 63, "left": 345, "width": 149}, {"top": 103, "right": 280}),
    135: ({"top": 110, "left": 302, "width": 211}, {"top": 158, "left": 308}),
    111: ({"top": 66, "left": 325, "width": 314}, {"top": 180, "right": 159}),
    154: ({"top": 89, "left": 249, "width": 75}, {"top": 98, "left": 239}),
    3: ({"top": 56, "left": 67, "width": 325}, {"top": 188, "left": 211}),
    21: ({"top": 162, "left": 71, "width": 276}, {"top": 246, "left": 180}),
    126: ({"top": 276, "left": 27, "width": 321}, {"top": 402, "left": 92}),
    88: ({"top": 126, "left": 198, "width": 314}, {"top": 270, "left": 282}),
    142: ({"top": 319, "left": 273, "width": 180}, {"top": 325, "left": 348}),
    163: ({"top": 235, "left": 427, "width": 146}, {"top": 210, "right": 204}),
    136: ({"top": 295, "left": 400, "width": 144}, {"top": 289, "right": 168}),
    106: ({"top": 231, "left": 456, "width": 206}, {"top": 340, "right": 62}),
    83: ({"top": 327, "left": 467, "width": 165}, {"bottom": 202, "right": 88}),
    66: ({"top": 317, "left": 304, "width": 185}, {"top": 429, "left": 376}),
    2: ({"top": 355, "left": 398, "width": 142}, {"bottom": 152, "right": 244}),
    78: ({"top": 338, "left": 124, "width": 176}, {"bottom": 147, "left": 108}),
    121: ({"top": 500, "left": 198, "width": 436}, {"bottom": 37, "right": 310}),
    104: ({"top": 462, "left": 293, "width": 108}, {"bottom": 151, "left": 288}),
}

PERFECT_ORDER = {dw_id: index for index, dw_id in enumerate(PERFECT_ITEMS)}
