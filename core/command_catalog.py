from __future__ import annotations

from unicodedata import category
from difflib import SequenceMatcher

DEFAULT_COMMAND_ROWS = [
    {
        'id': '日常',
        'group': '日常活动',
        'command': '日常',
        'command_tpl': '日常 | 日常 [天数]',
        'example_tpl': '日常 | 日常 1',
        'desc': '日常活动 / 日常',
    },
    {
        'id': '日常预测',
        'group': '日常活动',
        'command': '日常预测',
        'command_tpl': '日常预测',
        'example_tpl': '日常预测',
        'desc': '日常活动 / 日常预测',
    },
    {
        'id': '开服',
        'group': '日常活动',
        'command': '开服',
        'command_tpl': '开服 | 开服 [服务器]',
        'example_tpl': '开服 | 开服 飞龙在天',
        'desc': '日常活动 / 开服',
    },
    {
        'id': '科举',
        'group': '日常活动',
        'command': '科举',
        'command_tpl': '科举 [题目] [条数]',
        'example_tpl': '科举 李白',
        'desc': '日常活动 / 科举',
    },
    {
        'id': '小药',
        'group': '日常活动',
        'command': '小药',
        'command_tpl': '小药',
        'example_tpl': '小药',
        'desc': '日常活动 / 小药',
    },
    {
        'id': '金价',
        'group': '物价交易',
        'command': '金价',
        'command_tpl': '金价 | 金价 [服务器]',
        'example_tpl': '金价 | 金价 飞龙在天',
        'desc': '物价交易 / 金价',
    },
    {
        'id': '物价',
        'group': '物价交易',
        'command': '物价',
        'command_tpl': '物价 [外观] [服务器]',
        'example_tpl': '物价 狐金 | 物价 狐金 飞龙在天',
        'desc': '物价交易 / 物价',
    },
    {
        'id': '外观搜索',
        'group': '物价交易',
        'command': '外观搜索',
        'command_tpl': '外观搜索 [关键词]',
        'example_tpl': '外观搜索 狐金',
        'desc': '物价交易 / 外观搜索',
    },
    {
        'id': '交易行',
        'group': '物价交易',
        'command': '交易行',
        'command_tpl': '交易行 [服务器] [物品]',
        'example_tpl': '交易行 飞龙在天 六级',
        'desc': '物价交易 / 交易行',
    },
    {
        'id': '万宝楼',
        'group': '物价交易',
        'command': '万宝楼',
        'command_tpl': '万宝楼 [编号]',
        'example_tpl': '万宝楼 123456',
        'desc': '物价交易 / 万宝楼',
    },
    {
        'id': '贴吧物价',
        'group': '物价交易',
        'command': '贴吧物价',
        'command_tpl': '贴吧物价 [名称] [服务器] [数量]',
        'example_tpl': '贴吧物价 狐金 飞龙在天',
        'desc': '物价交易 / 贴吧物价',
    },
    {
        'id': '花价',
        'group': '物价交易',
        'command': '花价',
        'command_tpl': '花价 [服务器] [名称] [地图]',
        'example_tpl': '花价 飞龙在天',
        'desc': '物价交易 / 花价',
    },
    {
        'id': '装饰',
        'group': '物价交易',
        'command': '装饰',
        'command_tpl': '装饰 [名称]',
        'example_tpl': '装饰 桌',
        'desc': '物价交易 / 装饰',
    },
    {
        'id': '器物谱',
        'group': '物价交易',
        'command': '器物谱',
        'command_tpl': '器物谱 [地图]',
        'example_tpl': '器物谱 浩气盟',
        'desc': '物价交易 / 器物谱',
    },
    {
        'id': '拍卖',
        'group': '物价交易',
        'command': '拍卖',
        'command_tpl': '拍卖 [服务器] [物品] [数量]',
        'example_tpl': '拍卖 飞龙在天',
        'desc': '物价交易 / 拍卖',
    },
    {
        'id': '配方',
        'group': '物价交易',
        'command': '配方',
        'command_tpl': '配方 [服务器] [物品]',
        'example_tpl': '配方 飞龙在天 狐金',
        'desc': '物价交易 / 配方',
    },
    {
        'id': '配装',
        'group': '配装工具',
        'command': '配装',
        'command_tpl': '配装 [心法] [类型]',
        'example_tpl': '配装 剑纯',
        'desc': '配装工具 / 配装',
    },
    {
        'id': '宏',
        'group': '配装工具',
        'command': '宏',
        'command_tpl': '宏 [心法]',
        'example_tpl': '宏 鲸鱼',
        'desc': '配装工具 / 宏',
    },
    {
        'id': '技能',
        'group': '配装工具',
        'command': '技能',
        'command_tpl': '技能 [心法]',
        'example_tpl': '技能 毒经',
        'desc': '配装工具 / 技能',
    },
    {
        'id': '奇穴',
        'group': '配装工具',
        'command': '奇穴',
        'command_tpl': '奇穴 [心法]',
        'example_tpl': '奇穴 毒经',
        'desc': '配装工具 / 奇穴',
    },
    {
        'id': '阵眼',
        'group': '配装工具',
        'command': '阵眼',
        'command_tpl': '阵眼 [心法]',
        'example_tpl': '阵眼 毒经',
        'desc': '配装工具 / 阵眼',
    },
    {
        'id': '沙盘',
        'group': '配装工具',
        'command': '沙盘',
        'command_tpl': '沙盘 | 沙盘 [服务器]',
        'example_tpl': '沙盘 | 沙盘 飞龙在天',
        'desc': '配装工具 / 沙盘',
    },
    {
        'id': '技改',
        'group': '配装工具',
        'command': '技改',
        'command_tpl': '技改',
        'example_tpl': '技改',
        'desc': '配装工具 / 技改',
    },
    {
        'id': '骚话',
        'group': '日常活动',
        'command': '骚话',
        'command_tpl': '骚话',
        'example_tpl': '骚话',
        'desc': '日常活动 / 骚话',
    },
    {
        'id': '聊天',
        'group': '配装工具',
        'command': '聊天',
        'command_tpl': '聊天 [服务器] [角色] [条数] [页数]',
        'example_tpl': '聊天 飞龙在天 小螺卜头',
        'desc': '配装工具 / 聊天',
    },
    {
        'id': '掉落',
        'group': '副本掉落',
        'command': '掉落',
        'command_tpl': '掉落 [物品] [服务器] [数量]',
        'example_tpl': '掉落 太一玄晶 飞龙在天',
        'desc': '副本掉落 / 掉落',
    },
    {
        'id': '烟花',
        'group': '副本掉落',
        'command': '烟花',
        'command_tpl': '烟花 [服务器] [角色]',
        'example_tpl': '烟花 飞龙在天 小螺卜头',
        'desc': '副本掉落 / 烟花',
    },
    {
        'id': '查询',
        'group': '奇遇宠物',
        'command': '查询',
        'command_tpl': '查询 [服务器] [角色]',
        'example_tpl': '查询 飞龙在天 小螺卜头',
        'desc': '奇遇宠物 / 角色奇遇',
    },
    {
        'id': '未出',
        'group': '奇遇宠物',
        'command': '未出',
        'command_tpl': '未出 [服务器] [角色]',
        'example_tpl': '未出 飞龙在天 小螺卜头',
        'desc': '奇遇宠物 / 未出',
    },
    {
        'id': '汇总',
        'group': '奇遇宠物',
        'command': '汇总',
        'command_tpl': '汇总 [服务器] [天数]',
        'example_tpl': '汇总 飞龙在天',
        'desc': '奇遇宠物 / 汇总',
    },
    {
        'id': '近期',
        'group': '奇遇宠物',
        'command': '近期',
        'command_tpl': '近期 [服务器] [数量]',
        'example_tpl': '近期 飞龙在天',
        'desc': '奇遇宠物 / 近期',
    },
    {
        'id': '统计',
        'group': '奇遇宠物',
        'command': '统计',
        'command_tpl': '统计 [奇遇] [服务器] [数量]',
        'example_tpl': '统计 追魂骨 飞龙在天',
        'desc': '奇遇宠物 / 统计',
    },
    {
        'id': '攻略',
        'group': '奇遇宠物',
        'command': '攻略',
        'command_tpl': '攻略 [奇遇]',
        'example_tpl': '攻略 生死判',
        'desc': '奇遇宠物 / 攻略',
    },
    {
        'id': '马场',
        'group': '奇遇宠物',
        'command': '马场',
        'command_tpl': '马场 | 马场 [服务器]',
        'example_tpl': '马场 | 马场 飞龙在天',
        'desc': '奇遇宠物 / 马场',
    },
    {
        'id': '刷马',
        'group': '奇遇宠物',
        'command': '刷马',
        'command_tpl': '刷马 | 刷马 [服务器]',
        'example_tpl': '刷马 | 刷马 飞龙在天',
        'desc': '奇遇宠物 / 刷马',
    },
    {
        'id': '的卢',
        'group': '奇遇宠物',
        'command': '的卢',
        'command_tpl': '的卢 [服务器]',
        'example_tpl': '的卢 飞龙在天',
        'desc': '奇遇宠物 / 的卢',
    },
    {
        'id': '赤兔',
        'group': '奇遇宠物',
        'command': '赤兔',
        'command_tpl': '赤兔',
        'example_tpl': '赤兔',
        'desc': '奇遇宠物 / 赤兔',
    },
    {
        'id': '本周赤兔',
        'group': '奇遇宠物',
        'command': '本周赤兔',
        'command_tpl': '本周赤兔',
        'example_tpl': '本周赤兔',
        'desc': '奇遇宠物 / 本周赤兔',
    },
    {
        'id': '角色',
        'group': '角色资料',
        'command': '角色',
        'command_tpl': '角色 [服务器] [角色]',
        'example_tpl': '角色 飞龙在天 小螺卜头',
        'desc': '角色资料 / 角色',
    },
    {
        'id': '名片',
        'group': '角色资料',
        'command': '名片',
        'command_tpl': '名片 [服务器] [角色]',
        'example_tpl': '名片 飞龙在天 小螺卜头',
        'desc': '角色资料 / 名片',
    },
    {
        'id': '全部名片',
        'group': '角色资料',
        'command': '全部名片',
        'command_tpl': '全部名片 [服务器] [角色]',
        'example_tpl': '全部名片 飞龙在天 小螺卜头',
        'desc': '角色资料 / 全部名片',
    },
    {
        'id': '随机名片',
        'group': '角色资料',
        'command': '随机名片',
        'command_tpl': '随机名片 [服务器] [门派] [体型]',
        'example_tpl': '随机名片 飞龙在天',
        'desc': '角色资料 / 随机名片',
    },
    {
        'id': '精耐',
        'group': '角色资料',
        'command': '精耐',
        'command_tpl': '精耐 [服务器] [角色]',
        'example_tpl': '精耐 飞龙在天 小螺卜头',
        'desc': '角色资料 / 精耐',
    },
    {
        'id': '成就',
        'group': '角色资料',
        'command': '成就',
        'command_tpl': '成就 [服务器] [角色] [成就]',
        'example_tpl': '成就 飞龙在天 小螺卜头 名剑',
        'desc': '角色资料 / 成就',
    },
    {
        'id': '资历',
        'group': '角色资料',
        'command': '资历',
        'command_tpl': '资历 [服务器] [角色]',
        'example_tpl': '资历 飞龙在天 小螺卜头',
        'desc': '角色资料 / 资历',
    },
    {
        'id': '资历分布',
        'group': '角色资料',
        'command': '资历分布',
        'command_tpl': '资历分布 [服务器] [角色] [分类]',
        'example_tpl': '资历分布 飞龙在天 小螺卜头',
        'desc': '角色资料 / 资历分布',
    },
    {
        'id': '战绩',
        'group': '角色资料',
        'command': '战绩',
        'command_tpl': '战绩 [服务器] [角色] [模式]',
        'example_tpl': '战绩 飞龙在天 小螺卜头',
        'desc': '角色资料 / 战绩',
    },
    {
        'id': '名剑排行',
        'group': '排行榜单',
        'command': '名剑排行',
        'command_tpl': '名剑排行 [模式] [数量]',
        'example_tpl': '名剑排行 33',
        'desc': '排行榜单 / 名剑排行',
    },
    {
        'id': '名剑统计',
        'group': '排行榜单',
        'command': '名剑统计',
        'command_tpl': '名剑统计 [模式]',
        'example_tpl': '名剑统计 33',
        'desc': '排行榜单 / 名剑统计',
    },
    {
        'id': '跨服名剑榜',
        'group': '排行榜单',
        'command': '跨服名剑榜',
        'command_tpl': '跨服名剑榜 [服务器] [模式]',
        'example_tpl': '跨服名剑榜 飞龙在天 33',
        'desc': '排行榜单 / 跨服名剑榜',
    },
    {
        'id': '武林争霸',
        'group': '排行榜单',
        'command': '武林争霸赛',
        'command_tpl': '武林争霸赛 [服务器] [阵营]',
        'example_tpl': '武林争霸赛 飞龙在天',
        'desc': '排行榜单 / 武林争霸赛',
    },
    {
        'id': '捕快荣誉榜',
        'group': '排行榜单',
        'command': '捕快荣誉榜',
        'command_tpl': '捕快荣誉榜 [服务器]',
        'example_tpl': '捕快荣誉榜 飞龙在天',
        'desc': '排行榜单 / 捕快荣誉榜',
    },
    {
        'id': '江湖浪客榜',
        'group': '排行榜单',
        'command': '江湖浪客榜',
        'command_tpl': '江湖浪客榜 [服务器]',
        'example_tpl': '江湖浪客榜 飞龙在天',
        'desc': '排行榜单 / 江湖浪客榜',
    },
    {
        'id': '决斗挑战榜',
        'group': '排行榜单',
        'command': '决斗挑战榜',
        'command_tpl': '决斗挑战榜 [服务器] [公开/私密]',
        'example_tpl': '决斗挑战榜 飞龙在天',
        'desc': '排行榜单 / 决斗挑战榜',
    },
    {
        'id': '资历排行',
        'group': '排行榜单',
        'command': '资历排行',
        'command_tpl': '资历排行 [服务器] [门派]',
        'example_tpl': '资历排行 飞龙在天',
        'desc': '排行榜单 / 资历排行',
    },
    {
        'id': '名士排行',
        'group': '排行榜单',
        'command': '名士排行',
        'command_tpl': '名士排行 [服务器]',
        'example_tpl': '名士排行 飞龙在天',
        'desc': '排行榜单 / 名士排行',
    },
    {
        'id': '江湖排行',
        'group': '排行榜单',
        'command': '江湖排行',
        'command_tpl': '江湖排行 [服务器]',
        'example_tpl': '江湖排行 飞龙在天',
        'desc': '排行榜单 / 江湖排行',
    },
    {
        'id': '兵甲排行',
        'group': '排行榜单',
        'command': '兵甲排行',
        'command_tpl': '兵甲排行 [服务器]',
        'example_tpl': '兵甲排行 飞龙在天',
        'desc': '排行榜单 / 兵甲排行',
    },
    {
        'id': '名师排行',
        'group': '排行榜单',
        'command': '名师排行',
        'command_tpl': '名师排行 [服务器]',
        'example_tpl': '名师排行 飞龙在天',
        'desc': '排行榜单 / 名师排行',
    },
    {
        'id': '阵营排行',
        'group': '排行榜单',
        'command': '阵营排行',
        'command_tpl': '阵营排行 [服务器]',
        'example_tpl': '阵营排行 飞龙在天',
        'desc': '排行榜单 / 阵营排行',
    },
    {
        'id': '薪火排行',
        'group': '排行榜单',
        'command': '薪火排行',
        'command_tpl': '薪火排行 [服务器]',
        'example_tpl': '薪火排行 飞龙在天',
        'desc': '排行榜单 / 薪火排行',
    },
    {
        'id': '家园排行',
        'group': '排行榜单',
        'command': '家园排行',
        'command_tpl': '家园排行 [服务器]',
        'example_tpl': '家园排行 飞龙在天',
        'desc': '排行榜单 / 家园排行',
    },
    {
        'id': '浩气神兵排行',
        'group': '排行榜单',
        'command': '浩气神兵排行',
        'command_tpl': '浩气神兵排行 [服务器]',
        'example_tpl': '浩气神兵排行 飞龙在天',
        'desc': '排行榜单 / 浩气神兵排行',
    },
    {
        'id': '恶人神兵排行',
        'group': '排行榜单',
        'command': '恶人神兵排行',
        'command_tpl': '恶人神兵排行 [服务器]',
        'example_tpl': '恶人神兵排行 飞龙在天',
        'desc': '排行榜单 / 恶人神兵排行',
    },
    {
        'id': '浩气爱心排行',
        'group': '排行榜单',
        'command': '浩气爱心排行',
        'command_tpl': '浩气爱心排行 [服务器]',
        'example_tpl': '浩气爱心排行 飞龙在天',
        'desc': '排行榜单 / 浩气爱心排行',
    },
    {
        'id': '恶人爱心排行',
        'group': '排行榜单',
        'command': '恶人爱心排行',
        'command_tpl': '恶人爱心排行 [服务器]',
        'example_tpl': '恶人爱心排行 飞龙在天',
        'desc': '排行榜单 / 恶人爱心排行',
    },
    {
        'id': '试炼之地',
        'group': '排行榜单',
        'command': '试炼之地排行',
        'command_tpl': '试炼之地排行 [服务器] [心法]',
        'example_tpl': '试炼之地排行 飞龙在天 剑纯',
        'desc': '排行榜单 / 试炼之地排行',
    },
    {
        'id': '赛季恶人战功榜',
        'group': '排行榜单',
        'command': '赛季恶人战功榜',
        'command_tpl': '赛季恶人战功榜 [服务器]',
        'example_tpl': '赛季恶人战功榜 飞龙在天',
        'desc': '排行榜单 / 赛季恶人战功榜',
    },
    {
        'id': '赛季浩气战功榜',
        'group': '排行榜单',
        'command': '赛季浩气战功榜',
        'command_tpl': '赛季浩气战功榜 [服务器]',
        'example_tpl': '赛季浩气战功榜 飞龙在天',
        'desc': '排行榜单 / 赛季浩气战功榜',
    },
    {
        'id': '上周恶人战功榜',
        'group': '排行榜单',
        'command': '上周恶人战功榜',
        'command_tpl': '上周恶人战功榜 [服务器]',
        'example_tpl': '上周恶人战功榜 飞龙在天',
        'desc': '排行榜单 / 上周恶人战功榜',
    },
    {
        'id': '上周浩气战功榜',
        'group': '排行榜单',
        'command': '上周浩气战功榜',
        'command_tpl': '上周浩气战功榜 [服务器]',
        'example_tpl': '上周浩气战功榜 飞龙在天',
        'desc': '排行榜单 / 上周浩气战功榜',
    },
    {
        'id': '本周恶人战功榜',
        'group': '排行榜单',
        'command': '本周恶人战功榜',
        'command_tpl': '本周恶人战功榜 [服务器]',
        'example_tpl': '本周恶人战功榜 飞龙在天',
        'desc': '排行榜单 / 本周恶人战功榜',
    },
    {
        'id': '本周浩气战功榜',
        'group': '排行榜单',
        'command': '本周浩气战功榜',
        'command_tpl': '本周浩气战功榜 [服务器]',
        'example_tpl': '本周浩气战功榜 飞龙在天',
        'desc': '排行榜单 / 本周浩气战功榜',
    },
    {
        'id': '排行榜',
        'group': '排行榜单',
        'command': '排行榜',
        'command_tpl': '排行榜',
        'example_tpl': '排行榜',
        'desc': '排行榜单 / 排行榜',
    },
    {
        'id': '战功榜',
        'group': '排行榜单',
        'command': '战功榜',
        'command_tpl': '战功榜 [阵营]',
        'example_tpl': '战功榜 恶人',
        'desc': '排行榜单 / 战功榜',
    },
    {
        'id': '百战',
        'group': '阵营帮会',
        'command': '百战',
        'command_tpl': '百战',
        'example_tpl': '百战',
        'desc': '阵营帮会 / 百战',
    },
    {
        'id': '楚天社',
        'group': '阵营帮会',
        'command': '楚天社',
        'command_tpl': '楚天社',
        'example_tpl': '楚天社',
        'desc': '阵营帮会 / 楚天社',
    },
    {
        'id': '云从社',
        'group': '阵营帮会',
        'command': '云从社',
        'command_tpl': '云从社',
        'example_tpl': '云从社',
        'desc': '阵营帮会 / 云从社',
    },
    {
        'id': '披风会',
        'group': '阵营帮会',
        'command': '披风会',
        'command_tpl': '披风会',
        'example_tpl': '披风会',
        'desc': '阵营帮会 / 披风会',
    },
    {
        'id': '穹野卫',
        'group': '阵营帮会',
        'command': '穹野卫',
        'command_tpl': '穹野卫',
        'example_tpl': '穹野卫',
        'desc': '阵营帮会 / 穹野卫',
    },
    {
        'id': '统战',
        'group': '阵营帮会',
        'command': '统战',
        'command_tpl': '统战 [服务器]',
        'example_tpl': '统战 飞龙在天',
        'desc': '阵营帮会 / 统战',
    },
    {
        'id': '关隘首领',
        'group': '阵营帮会',
        'command': '关隘首领',
        'command_tpl': '关隘首领',
        'example_tpl': '关隘首领',
        'desc': '阵营帮会 / 关隘首领',
    },
    {
        'id': '诛恶',
        'group': '阵营帮会',
        'command': '诛恶',
        'command_tpl': '诛恶 [服务器]',
        'example_tpl': '诛恶 飞龙在天',
        'desc': '阵营帮会 / 诛恶',
    },
    {
        'id': '帮战',
        'group': '阵营帮会',
        'command': '帮战',
        'command_tpl': '帮战 [服务器]',
        'example_tpl': '帮战 飞龙在天',
        'desc': '阵营帮会 / 帮战',
    },
    {
        'id': '阵营事件',
        'group': '阵营帮会',
        'command': '阵营事件',
        'command_tpl': '阵营事件 [阵营]',
        'example_tpl': '阵营事件 浩气盟',
        'desc': '阵营帮会 / 阵营事件',
    },
    {
        'id': '招募',
        'group': '开团招募',
        'command': '招募',
        'command_tpl': '招募 [服务器] [副本]',
        'example_tpl': '招募 飞龙在天 浪客行',
        'desc': '开团招募 / 招募',
    },
    {
        'id': '团长',
        'group': '开团招募',
        'command': '团长',
        'command_tpl': '团长 [服务器] [名称]',
        'example_tpl': '团长 飞龙在天 小螺卜头',
        'desc': '开团招募 / 团长',
    },
    {
        'id': '团牌',
        'group': '开团招募',
        'command': '团牌',
        'command_tpl': '团牌 [服务器] [内容]',
        'example_tpl': '团牌 飞龙在天 开团',
        'desc': '开团招募 / 团牌',
    },
    {
        'id': '拜师',
        'group': '开团招募',
        'command': '拜师',
        'command_tpl': '拜师 [服务器] [关键词]',
        'example_tpl': '拜师 飞龙在天',
        'desc': '开团招募 / 拜师',
    },
    {
        'id': '收徒',
        'group': '开团招募',
        'command': '收徒',
        'command_tpl': '收徒 [服务器] [关键词]',
        'example_tpl': '收徒 飞龙在天',
        'desc': '开团招募 / 收徒',
    },
    {
        'id': '功能',
        'group': '帮助入口',
        'command': '功能',
        'command_tpl': '功能',
        'example_tpl': '功能',
        'desc': '帮助入口 / 功能',
    },
    {
        'id': '认领',
        'group': '会话设置',
        'command': '认领',
        'command_tpl': '认领 [名称]',
        'example_tpl': '认领 剑网3机器人',
        'desc': '会话设置 / 认领',
    },
    {
        'id': '绑定',
        'group': '会话设置',
        'command': '绑定',
        'command_tpl': '绑定 [区服]',
        'example_tpl': '绑定 飞龙在天',
        'desc': '会话设置 / 绑定',
    },
    {
        'id': '查询令牌',
        'group': '会话设置',
        'command': '查询令牌',
        'command_tpl': '查询令牌',
        'example_tpl': '查询令牌',
        'desc': '会话设置 / 查询令牌',
    },
    {
        'id': '授权管理',
        'group': '会话设置',
        'command': '授权管理',
        'command_tpl': '授权管理 [@成员]',
        'example_tpl': '授权管理 @唐小珂',
        'desc': '会话设置 / 授权管理',
    },
    {
        'id': '查看管理',
        'group': '会话设置',
        'command': '查看管理',
        'command_tpl': '查看管理',
        'example_tpl': '查看管理',
        'desc': '会话设置 / 查看管理',
    },
    {
        'id': '删除管理',
        'group': '会话设置',
        'command': '删除管理',
        'command_tpl': '删除管理 [序号]',
        'example_tpl': '删除管理 2',
        'desc': '会话设置 / 删除管理',
    },
    {
        'id': '通知管理',
        'group': '会话设置',
        'command': '通知管理',
        'command_tpl': '通知管理',
        'example_tpl': '通知管理',
        'desc': '会话设置 / 通知管理',
    },
    {
        'id': '打开',
        'group': '会话设置',
        'command': '打开',
        'command_tpl': '打开 [类型]',
        'example_tpl': '打开 新闻',
        'desc': '会话设置 / 打开',
    },
    {
        'id': '关闭',
        'group': '会话设置',
        'command': '关闭',
        'command_tpl': '关闭 [类型]',
        'example_tpl': '关闭 新闻',
        'desc': '会话设置 / 关闭',
    },
    {
        'id': 'Token',
        'group': '会话设置',
        'command': 'Token',
        'command_tpl': '私聊 {command} [UMO] [密钥]',
        'example_tpl': '私聊 {command} UMO 密钥',
        'desc': '会话设置 / Token，仅私聊可用',
    },
    {
        'id': '推栏',
        'group': '会话设置',
        'command': '推栏',
        'command_tpl': '私聊 {command} [UMO] [标识]',
        'example_tpl': '私聊 {command} UMO 标识',
        'desc': '会话设置 / 推栏，仅私聊可用',
    },
    {
        'id': '新闻',
        'group': '日常活动',
        'command': '新闻',
        'command_tpl': '新闻 [数量]',
        'example_tpl': '新闻',
        'desc': '日常活动 / 新闻',
    },
    {
        'id': '维护',
        'group': '日常活动',
        'command': '维护',
        'command_tpl': '维护 [数量]',
        'example_tpl': '维护',
        'desc': '日常活动 / 维护',
    },
    {
        'id': '818',
        'group': '日常活动',
        'command': '818',
        'command_tpl': '818 [服务器] [数量]',
        'example_tpl': '818 飞龙在天',
        'desc': '日常活动 / 818',
    },
    {
        'id': '答案之书',
        'group': '日常活动',
        'command': '答案之书',
        'command_tpl': '答案之书',
        'example_tpl': '答案之书',
        'desc': '日常活动 / 答案之书',
    },
    {
        'id': '舔狗语录',
        'group': '日常活动',
        'command': '舔狗语录',
        'command_tpl': '舔狗语录',
        'example_tpl': '舔狗语录',
        'desc': '日常活动 / 舔狗语录',
    },
    {
        'id': '喝什么',
        'group': '日常活动',
        'command': '喝什么',
        'command_tpl': '喝什么',
        'example_tpl': '喝什么',
        'desc': '日常活动 / 喝什么',
    },
    {
        'id': '吃什么',
        'group': '日常活动',
        'command': '吃什么',
        'command_tpl': '吃什么',
        'example_tpl': '吃什么',
        'desc': '日常活动 / 吃什么',
    },
    {
        'id': '渣男语录',
        'group': '日常活动',
        'command': '渣男语录',
        'command_tpl': '渣男语录',
        'example_tpl': '渣男语录',
        'desc': '日常活动 / 渣男语录',
    },
]

DEFAULT_COMMANDS = {row['id']: row for row in DEFAULT_COMMAND_ROWS}


from copy import deepcopy
import re


def _clone(catalog: dict) -> dict:
    return deepcopy(catalog)


def apply_command_overrides(overrides: dict[str, str] | None) -> dict:
    catalog = _clone(DEFAULT_COMMANDS)
    for command_id, name in (overrides or {}).items():
        catalog, error = set_command_name(catalog, command_id, name)
        if error:
            continue
    return catalog


def command_collision(catalog: dict, command_id: str, name: str) -> str:
    name = (name or "").strip()
    if not name:
        return "命令不能为空"
    if " " in name or "\t" in name:
        return "命令不能包含空格"
    current = catalog.get(command_id)
    if not current:
        return "未知命令"
    for other_id, row in catalog.items():
        if other_id == command_id:
            continue
        if str(row.get("command") or "") == name:
            return f"命令已被「{other_id}」占用"
    return ""


def set_command_name(catalog: dict, command_id: str, name: str) -> tuple[dict, str]:
    catalog = _clone(catalog)
    error = command_collision(catalog, command_id, name)
    if error:
        return catalog, error
    catalog[command_id]["command"] = name.strip()
    return catalog, ""


# WebUI 描述列使用 JX3API 官方 OpenAPI 描述；插件自有管理命令使用功能说明。
HELP_EXCLUDED_COMMAND_IDS = {"打开", "关闭", "通知管理"}
WEB_COMMAND_DESCRIPTIONS = {
    "日常": "单日或前后区间的日常活动推演",
    "日常预测": "单日或前后区间的日常活动推演",
    "开服": "type=1（默认）从 seasun.status 合集取数据；其他值拉 xoyo 服务器列表（60 秒缓存）解析在线状态，指定服返回单条，否则返回收录的全部",
    "科举": "按题目或拼音模糊匹配，返回候选答案（原 question/pinyin LIKE 双查）",
    "小药": "指定心法则返回该心法的小吃小药，否则返回全部",
    "金价": "各渠道金币比价（search.price）；指定服返回该服最近 limit 条，否则每服最新一条",
    "物价": "定位外观（search.main）后取各区 / 指定服历史成交价（search.sales，各最近 10 条）",
    "外观搜索": "按名称查外观（search.main）；先精确 name/alias/feiniu，无则模糊 name/alias/allalias/feiniu",
    "交易行": "定位外观（search.main）后取各区 / 指定服历史成交价（search.sales，各最近 10 条）",
    "万宝楼": "按角色编号查万宝楼账号详情（aijx3 两跳：查 zhanghaoId 再取详情，密文 base64+zlib 解开）",
    "贴吧物价": "在贴吧楼层（search.floor）里按物品名搜相关帖子（正则 + 分词兜底）",
    "花价": "白名单校验后查推栏鲜花行情，按地图归组（鲜花名剥离括号色，括号内作 color）",
    "装饰": "按装饰名查 travel 合集，补全图片链接",
    "器物谱": "按器物名查 travel 合集（produce 列），补全图片链接",
    "拍卖": "按大区查角色竞拍记录，可按物品名模糊筛选，时间倒序",
    "配方": "按成品配方（seasun.recipe/cooking）算材料成本：商店材料取固定售价，交易行材料 + 成品取实时价（jx3box）",
    "配装": "按心法 + 玩法模式取推栏推荐配装；赛季与配装各缓存 7 天（少打推栏）",
    "宏": "按心法查询可用宏配置",
    "技能": "按心法取推栏各分类（remark）下的招式技能",
    "奇穴": "按心法取推栏各等级的招式（class=1）/ 奇穴（class=0）技能，按等级升序",
    "阵眼": "按心法取推栏阵眼（阵法）效果与描述",
    "沙盘": "各据点归属帮会 / 阵营 + 本周被献祭（防守）次数",
    "技改": "拉 xoyo 公告列表（10 分钟缓存），筛出标题含「武学调整」的技改公告",
    "骚话": "从骚话库随机取一条",
    "聊天": "分页查询指定服务器角色的聊天记录，按 time 字段降序",
    "掉落": "按物品名模糊匹配掉落记录，时间倒序；指定服查单服，不指定查全服",
    "烟花": "角色作为送花人或收花人的烟花记录，时间倒序",
    "查询": "整合角色全局事件(binding) + 服务器事件(event) + 魔盒成就，可补全未触发",
    "未出": "返回该角色尚未触发的奇遇（不在全局 binding / 服务器 event 记录里的 event.master 项）",
    "汇总": "白名单每个奇遇：最近 num 天在该服的触发次数 + 历史最新一条（角色名/时间）",
    "近期": "某服最近触发的奇遇事件，时间倒序",
    "统计": "某奇遇最近的触发记录，时间倒序；指定服查单服，不指定查全服",
    "攻略": "返回该奇遇的白名单配置（event.master + touch.master 合并）",
    "马场": "jx3box 马场播报预告 + 本周期赤兔（mount）/ 的卢（steed）出世情况，附提示",
    "刷马": "爬 jx3box 马场 NPC 播报，解析各地图「下一匹 X 出世还有 N 分钟」的预计时刻",
    "的卢": "指定服返回最新 10 条；不指定则每服最新 1 条（按收录服列全，无记录给空）",
    "赤兔": "查 ranch 合集当天的赤兔记录",
    "本周赤兔": "爬 jx3box 播报，解析各服本周(周二 7 点重置后)赤兔到达地图",
    "角色": "角色名片（roles 合集）；每次都采集 ermaozi 历史去重入库以持续收录 history=1：同步先采集再返回最新历史；history=0：采集甩到响应之后异步跑，客户端零等待",
    "名片": "转发远程取已缓存名片",
    "全部名片": "转发远程取角色名片历史列表",
    "随机名片": "转发远程按门派 / 体型随机取一张名片",
    "精耐": "角色的百战技能配装（体力 / 精力 / 场次 / 技能列表）；未打过则取全服默认技能",
    "成就": "角色名片 + 成就库按 名称/分类/子类/详情 模糊匹配，标记该角色是否已完成（魔盒成就）",
    "资历": "按分类查询角色资历与完成度",
    "资历分布": "角色名片 + 按 子类/详情/地图/副本 汇总的资历完成度 静态骨架（各桶 total + 排序 + totalScore）按 class 缓存，每次请求只查用户已完成子集叠加 speed",
    "战绩": "角色竞技场名片、各模式战绩表现、历史对战，指定模式时附趋势",
    "名剑排行": "某比赛模式竞技场排行榜前 limit 名",
    "名剑统计": "某比赛模式下各门派的竞技场周统计",
    "跨服名剑榜": "按竞技模式（0=2v2 / 1=3v3 / 2=5v5）查军团赛季战绩榜；指定服查单服，否则全服",
    "武林争霸": "按阵营（1=浩气 / 2=恶人）查帮会争霸赛季榜（与名剑榜共用 season 合集，每赛季清零）",
    "捕快荣誉榜": "与江湖浪客榜同字段格式（bounty 合集）",
    "江湖浪客榜": "实时榜（bounty 合集），显式列字段，nRank 排名序号不返回",
    "决斗挑战榜": "按类型（1=公开 / 2=私密）查决斗悬赏榜（bounty 合集，mode 存的是字符串）",
    "资历排行": "指定服 / 门派（默认全服全门派）的资历前 100 名，补门派名",
    "名士排行": "指定服查该服该榜单，否则查全服该榜单",
    "江湖排行": "指定服查该服该榜单，否则查全服该榜单",
    "兵甲排行": "指定服查该服该榜单，否则查全服该榜单",
    "名师排行": "指定服查该服该榜单，否则查全服该榜单",
    "阵营排行": "指定服查该服该榜单，否则查全服该榜单",
    "薪火排行": "指定服查该服该榜单，否则查全服该榜单",
    "家园排行": "指定服查该服该榜单，否则查全服该榜单",
    "浩气神兵排行": "指定服查该服该榜单，否则查全服该榜单",
    "恶人神兵排行": "指定服查该服该榜单，否则查全服该榜单",
    "浩气爱心排行": "指定服查该服该榜单，否则查全服该榜单",
    "恶人爱心排行": "指定服查该服该榜单，否则查全服该榜单",
    "试炼之地": "同榜单查询，山居剑意归并到藏剑；行是位置字段 1~4，重建成具名字段",
    "赛季恶人战功榜": "指定服查该服该榜单，否则查全服该榜单",
    "赛季浩气战功榜": "指定服查该服该榜单，否则查全服该榜单",
    "上周恶人战功榜": "指定服查该服该榜单，否则查全服该榜单",
    "上周浩气战功榜": "指定服查该服该榜单，否则查全服该榜单",
    "本周恶人战功榜": "指定服查该服该榜单，否则查全服该榜单",
    "本周浩气战功榜": "指定服查该服该榜单，否则查全服该榜单",
    "排行榜": "查看可选择查询的榜单列表",
    "战功榜": "查看可选择查询的战功榜列表",
    "百战": "本周首领列表及 buff 效果，附荡剑恩仇轮换首领",
    "楚天社": "楚天社 / 云从社 / 披风会接下来 10 条排期",
    "云从社": "楚天社 / 云从社 / 披风会接下来 10 条排期",
    "披风会": "楚天社 / 云从社 / 披风会接下来 10 条排期",
    "穹野卫": "楚天社 / 云从社 / 披风会接下来 10 条排期",
    "统战": "查各服 YY 语音频道的在线主播；指定服查该服两营，不指定则每服每营取一个代表",
    "关隘首领": "各服关隘首领的当前状态（可拾取 / 保护期 / 可抢占 / 每日 7-12 点统一保护），按服务器分组",
    "诛恶": "恶人（诛恶）刷新记录，时间倒序；指定服查单服，不指定查全服",
    "帮战": "查某服最近 30 场帮战，区分已结束 / 进行中并算出时长与结束时间",
    "阵营事件": "据点争夺记录，按占领时间倒序；给了阵营名则只看该阵营（原 id DESC → seize_time DESC）",
    "招募": "转发远程取招募名单，按关键字（活动/团长/内容）过滤，超量截断",
    "团长": "转发远程取招募名单，按关键字（活动/团长/内容）过滤，超量截断",
    "团牌": "转发远程取招募名单，按关键字（活动/团长/内容）过滤，超量截断",
    "拜师": "转发远程取师徒名单，按关键字过滤评论，超量随机抽样",
    "收徒": "转发远程取师徒名单，按关键字过滤评论，超量随机抽样",
    "功能": "查看自主查询命令帮助图",
    "认领": "在私聊认领本插件的管理身份",
    "绑定": "为当前群聊或私聊绑定默认区服",
    "查询令牌": "查询 JX3API Token 的等级、已用次数、剩余次数或到期时间",
    "授权管理": "授权被 @ 的成员管理本会话通知",
    "查看管理": "查看本会话认领人与授权管理员",
    "删除管理": "按序号移除本会话授权管理员",
    "通知管理": "查看和管理本会话主动推送事件",
    "打开": "开启指定事件的主动推送",
    "关闭": "关闭指定事件的主动推送",
    "Token": "为指定会话配置 JX3API Token，仅私聊可用",
    "推栏": "为指定会话配置推栏标识，仅私聊可用",
    "新闻": "最新资讯列表；原 id DESC → _id DESC（导入按原 id 升序插入，等价于最新在前）",
    "维护": "标题含“版本更新”的公告，最新在前",
    "818": "按帖子类型随机取近 31 天的帖子（seasun.tieba），可选指定服",
    "答案之书": "从 stable.ANSWERS_BOOK 抽 1 条答案，再从 stable.ANSWERS_HEARTEN 抽 1 条鼓励语",
    "舔狗语录": "从舔狗日志库随机取一条",
    "喝什么": "从 stable.DRINK_LIST 中随机抽 2~4 条",
    "吃什么": "从 stable.FOOD_LIST 中随机抽 2~4 条",
    "渣男语录": "从渣男语录库随机取一条",
}


def resolve_command(catalog: dict, trigger: str) -> str | None:
    trigger = (trigger or "").strip()
    if not trigger:
        return None
    for command_id, row in catalog.items():
        if str(row.get("command") or "") == trigger:
            return command_id
    return None


def _command_similarity(left: str, right: str) -> float:
    left = (left or "").strip()
    right = (right or "").strip()
    if not left or not right:
        return 0.0
    if any(category(ch)[0] in {"P", "S"} for ch in left):
        return 0.0
    if len(left) == 1 or len(right) == 1:
        return 0.0
    if left == right:
        return 1.0
    base = SequenceMatcher(None, left, right).ratio()
    if abs(len(left) - len(right)) == 1:
        shorter = left if len(left) < len(right) else right
        longer = right if len(right) > len(left) else left
        for index in range(len(longer)):
            if longer[:index] + longer[index + 1:] == shorter:
                return max(base, 0.86)
    if len(left) == len(right):
        diff = sum(1 for a, b in zip(left, right) if a != b)
        if diff == 1:
            return max(base, 0.90)
    if right.startswith(left) and len(right) > 2:
        return max(base, 0.66)
    if len(right) == 1:
        return 0.0
    return base


def suggest_command(catalog: dict | None, trigger: str) -> str | None:
    catalog = catalog or DEFAULT_COMMANDS
    trigger = (trigger or "").strip()
    if not trigger:
        return None
    if len(trigger) == 1:
        return None
    candidates = []
    for command_id, row in catalog.items():
        name = str(row.get("command") or "")
        if not name:
            continue
        usage_head = str(row.get("command_tpl") or name).split("|")[0].strip()
        if "[" not in usage_head:
            continue
        score = _command_similarity(trigger, name)
        if score > 0:
            candidates.append((score, name, command_id))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], len(item[1])))
    best = candidates[0]
    if best[0] < 0.7:
        return None
    second = candidates[1] if len(candidates) > 1 else (0.0, "", "")
    if best[0] - second[0] < 0.08:
        return None
    return best[2]


def _replace_command_text(text: str, old: str, new: str) -> str:
    if not text:
        return text
    if "{command}" in text:
        return text.replace("{command}", new)
    return re.sub(rf"(?<!\S){re.escape(old)}(?!\S)", new, text)


def help_rows(
    catalog: dict | None = None,
    *,
    exclude_groups: set[str] | None = None,
    exclude_ids: set[str] | None = None,
) -> list[dict]:
    catalog = catalog or DEFAULT_COMMANDS
    group_order = []
    for item in DEFAULT_COMMAND_ROWS:
        if item["group"] not in group_order:
            group_order.append(item["group"])
    ordered = sorted(DEFAULT_COMMAND_ROWS, key=lambda item: (group_order.index(item["group"]), DEFAULT_COMMAND_ROWS.index(item)))
    rows = []
    for item in ordered:
        if exclude_groups and item["group"] in exclude_groups:
            continue
        if exclude_ids and item["id"] in exclude_ids:
            continue
        row = catalog.get(item["id"], item)
        old = item["command"]
        new = str(row.get("command") or old)
        rows.append({
            "id": item["id"],
            "group": item["group"],
            "command": _replace_command_text(item["command_tpl"], old, new),
            "example": _replace_command_text(item["example_tpl"], old, new),
            "desc": _replace_command_text(str(row.get("desc") or item["desc"]), old, new),
        })
    return rows


def public_command_rows(catalog: dict | None = None) -> list[dict]:
    catalog = catalog or DEFAULT_COMMANDS
    group_order = []
    for item in DEFAULT_COMMAND_ROWS:
        if item["group"] not in group_order:
            group_order.append(item["group"])
    ordered = sorted(
        DEFAULT_COMMAND_ROWS,
        key=lambda item: (group_order.index(item["group"]), DEFAULT_COMMAND_ROWS.index(item)),
    )
    rows = []
    for item in ordered:
        row = catalog.get(item["id"], item)
        old = item["command"]
        new = str(row.get("command") or old)
        desc = WEB_COMMAND_DESCRIPTIONS.get(item["id"], "")
        if not desc:
            desc = str(row.get("desc") or "")
            if not desc or desc == f"{item['group']} / {item['id']}":
                desc = _replace_command_text(str(item.get("command_tpl") or item["id"]), old, new)
            else:
                desc = _replace_command_text(desc, old, new)
        rows.append({
            "id": item["id"],
            "group": item["group"],
            "default_command": item["command"],
            "command": new,
            "example": _replace_command_text(item["example_tpl"], old, new),
            "desc": desc,
        })
    return rows


def command_usage(command_id: str, catalog: dict | None = None) -> str:
    catalog = catalog or DEFAULT_COMMANDS
    row = (catalog.get(command_id) or DEFAULT_COMMANDS.get(command_id) or {})
    tpl = str(row.get("command_tpl") or row.get("command") or command_id)
    default_row = DEFAULT_COMMANDS.get(command_id) or {}
    old = str(default_row.get("command") or command_id)
    name = str(row.get("command") or command_id)
    # Keep the first pattern only, drop alternate "cmd | cmd [x]" duplication.
    tpl = _replace_command_text(tpl, old, name)
    first = tpl.split("|")[0].strip()
    return first or name
