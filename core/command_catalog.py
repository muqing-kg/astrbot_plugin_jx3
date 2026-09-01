from __future__ import annotations

from unicodedata import category
from difflib import SequenceMatcher

DEFAULT_COMMAND_ROWS = [
    {
        'id': '日常',
        'group': '日常活动',
        'command': '日常',
        'command_tpl': '日常 | 日常 [天数]',
        'desc': '日常活动 / 日常',
    },
    {
        'id': '日常预测',
        'group': '日常活动',
        'command': '日常预测',
        'command_tpl': '日常预测',
        'desc': '日常活动 / 日常预测',
    },
    {
        'id': '开服',
        'group': '日常活动',
        'command': '开服',
        'command_tpl': '开服 | 开服 [服务器]',
        'desc': '日常活动 / 开服',
    },
    {
        'id': '科举',
        'group': '日常活动',
        'command': '科举',
        'command_tpl': '科举 [题目] [条数]',
        'desc': '日常活动 / 科举',
    },
    {
        'id': '小药',
        'group': '日常活动',
        'command': '小药',
        'command_tpl': '小药 [心法]',
        'desc': '日常活动 / 小药',
    },
    {
        'id': '金价',
        'group': '物价交易',
        'command': '金价',
        'command_tpl': '金价 | 金价 [服务器] [数量]',
        'desc': '物价交易 / 金价',
    },
    {
        'id': '物价',
        'group': '物价交易',
        'command': '物价',
        'command_tpl': '物价 [外观] [服务器]',
        'desc': '物价交易 / 物价',
    },
    {
        'id': '外观搜索',
        'group': '物价交易',
        'command': '外观搜索',
        'command_tpl': '外观搜索 [关键词]',
        'desc': '物价交易 / 外观搜索',
    },
    {
        'id': '交易行',
        'group': '物价交易',
        'command': '交易行',
        'command_tpl': '交易行 [服务器] [物品]',
        'desc': '物价交易 / 交易行',
    },
    {
        'id': '万宝楼',
        'group': '物价交易',
        'command': '万宝楼',
        'command_tpl': '万宝楼 [编号]',
        'desc': '物价交易 / 万宝楼',
    },
    {
        'id': '花价',
        'group': '物价交易',
        'command': '花价',
        'command_tpl': '花价 [服务器] [名称] [地图]',
        'desc': '物价交易 / 花价',
    },
    {
        'id': '装饰',
        'group': '物价交易',
        'command': '装饰',
        'command_tpl': '装饰 [名称]',
        'desc': '物价交易 / 装饰',
    },
    {
        'id': '器物谱',
        'group': '物价交易',
        'command': '器物谱',
        'command_tpl': '器物谱 [地图]',
        'desc': '物价交易 / 器物谱',
    },
    {
        'id': '阵营拍卖',
        'group': '物价交易',
        'command': '阵营拍卖',
        'command_tpl': '阵营拍卖 [服务器] [物品] [数量]',
        'desc': '物价交易 / 阵营拍卖',
    },
    {
        'id': '配方',
        'group': '物价交易',
        'command': '配方',
        'command_tpl': '配方 [服务器] [物品] [来源]',
        'desc': '物价交易 / 配方',
    },
    {
        'id': '配装',
        'group': '配装工具',
        'command': '配装',
        'command_tpl': '配装 [心法] [类型]',
        'desc': '配装工具 / 配装',
    },
    {
        'id': '宏',
        'group': '配装工具',
        'command': '宏',
        'command_tpl': '宏 [心法]',
        'desc': '配装工具 / 宏',
    },
    {
        'id': '技能',
        'group': '配装工具',
        'command': '技能',
        'command_tpl': '技能 [心法]',
        'desc': '配装工具 / 技能',
    },
    {
        'id': '奇穴',
        'group': '配装工具',
        'command': '奇穴',
        'command_tpl': '奇穴 [心法]',
        'desc': '配装工具 / 奇穴',
    },
    {
        'id': '阵眼',
        'group': '配装工具',
        'command': '阵眼',
        'command_tpl': '阵眼 [心法]',
        'desc': '配装工具 / 阵眼',
    },
    {
        'id': '沙盘',
        'group': '配装工具',
        'command': '沙盘',
        'command_tpl': '沙盘 | 沙盘 [服务器]',
        'desc': '各据点归属帮会 / 阵营 + 本周被献祭（防守）次数',
    },
    {
        'id': '技改',
        'group': '配装工具',
        'command': '技改',
        'command_tpl': '技改',
        'desc': '配装工具 / 技改',
    },
    {
        'id': '骚话',
        'group': '日常活动',
        'command': '骚话',
        'command_tpl': '骚话',
        'desc': '日常活动 / 骚话',
    },
    {
        'id': '聊天',
        'group': '配装工具',
        'command': '聊天',
        'command_tpl': '聊天 [服务器] [角色] [条数] [页数]',
        'desc': '配装工具 / 聊天',
    },
    {
        'id': '掉落',
        'group': '副本掉落',
        'command': '掉落',
        'command_tpl': '掉落 [物品] [服务器] [数量]',
        'desc': '副本掉落 / 掉落',
    },
    {
        'id': '烟花',
        'group': '副本掉落',
        'command': '烟花',
        'command_tpl': '烟花 [服务器] [角色]',
        'desc': '副本掉落 / 烟花',
    },
    {
        'id': '查询',
        'group': '奇遇宠物',
        'command': '查询',
        'command_tpl': '查询 [服务器] [角色]',
        'desc': '奇遇宠物 / 角色奇遇',
    },
    {
        'id': '未出',
        'group': '奇遇宠物',
        'command': '未出',
        'command_tpl': '未出 [服务器] [角色]',
        'desc': '奇遇宠物 / 未出',
    },
    {
        'id': '汇总',
        'group': '奇遇宠物',
        'command': '汇总',
        'command_tpl': '汇总 [服务器] [天数]',
        'desc': '奇遇宠物 / 汇总',
    },
    {
        'id': '近期',
        'group': '奇遇宠物',
        'command': '近期',
        'command_tpl': '近期 [服务器] [数量]',
        'desc': '奇遇宠物 / 近期',
    },
    {
        'id': '统计',
        'group': '奇遇宠物',
        'command': '统计',
        'command_tpl': '统计 [奇遇] [服务器] [数量]',
        'desc': '奇遇宠物 / 统计',
    },
    {
        'id': '攻略',
        'group': '奇遇宠物',
        'command': '攻略',
        'command_tpl': '攻略 [奇遇]',
        'desc': '奇遇宠物 / 攻略',
    },
    {
        'id': '马场',
        'group': '奇遇宠物',
        'command': '马场',
        'command_tpl': '马场 | 马场 [服务器]',
        'desc': '奇遇宠物 / 马场',
    },
    {
        'id': '刷马',
        'group': '奇遇宠物',
        'command': '刷马',
        'command_tpl': '刷马 | 刷马 [服务器]',
        'desc': '奇遇宠物 / 刷马',
    },
    {
        'id': '的卢拍卖',
        'group': '奇遇宠物',
        'command': '的卢拍卖',
        'command_tpl': '的卢拍卖 [服务器]',
        'desc': '奇遇宠物 / 的卢拍卖',
    },
    {
        'id': '赤兔',
        'group': '奇遇宠物',
        'command': '赤兔',
        'command_tpl': '赤兔',
        'desc': '奇遇宠物 / 赤兔',
    },
    {
        'id': '本周赤兔',
        'group': '奇遇宠物',
        'command': '本周赤兔',
        'command_tpl': '本周赤兔',
        'desc': '奇遇宠物 / 本周赤兔',
    },
    {
        'id': '角色',
        'group': '角色资料',
        'command': '角色',
        'command_tpl': '角色 [服务器] [角色]',
        'desc': '角色资料 / 角色',
    },
    {
        'id': '在线',
        'group': '角色资料',
        'command': '在线',
        'command_tpl': '在线 [服务器] [角色]',
        'desc': '角色资料 / 在线状态',
    },
    {
        'id': '名片',
        'group': '角色资料',
        'command': '名片',
        'command_tpl': '名片 [服务器] [角色]',
        'desc': '角色资料 / 名片',
    },
    {
        'id': '全部名片',
        'group': '角色资料',
        'command': '全部名片',
        'command_tpl': '全部名片 [服务器] [角色]',
        'desc': '角色资料 / 全部名片',
    },
    {
        'id': '随机名片',
        'group': '角色资料',
        'command': '随机名片',
        'command_tpl': '随机名片 [服务器] [门派] [体型]',
        'desc': '角色资料 / 随机名片',
    },
    {
        'id': '精耐',
        'group': '角色资料',
        'command': '精耐',
        'command_tpl': '精耐 [服务器] [角色]',
        'desc': '角色资料 / 精耐',
    },
    {
        'id': '成就',
        'group': '角色资料',
        'command': '成就',
        'command_tpl': '成就 [服务器] [角色] [成就]',
        'desc': '角色资料 / 成就',
    },
    {
        'id': '资历',
        'group': '角色资料',
        'command': '资历',
        'command_tpl': '资历 [服务器] [角色]',
        'desc': '角色资料 / 资历',
    },
    {
        'id': '资历分布',
        'group': '角色资料',
        'command': '资历分布',
        'command_tpl': '资历分布 [服务器] [角色] [分类]',
        'desc': '角色资料 / 资历分布',
    },
    {
        'id': '战绩',
        'group': '角色资料',
        'command': '战绩',
        'command_tpl': '战绩 [服务器] [角色] [模式]',
        'desc': '角色资料 / 战绩',
    },
    {
        'id': '名剑排行',
        'group': '排行榜单',
        'command': '名剑排行',
        'command_tpl': '名剑排行 [模式] [数量]',
        'desc': '排行榜单 / 名剑排行',
    },
    {
        'id': '名剑统计',
        'group': '排行榜单',
        'command': '名剑统计',
        'command_tpl': '名剑统计 [模式]',
        'desc': '排行榜单 / 名剑统计',
    },
    {
        'id': '跨服名剑榜',
        'group': '排行榜单',
        'command': '跨服名剑榜',
        'command_tpl': '跨服名剑榜 [服务器] [模式]',
        'desc': '排行榜单 / 跨服名剑榜',
    },
    {
        'id': '武林争霸赛',
        'group': '排行榜单',
        'command': '武林争霸赛',
        'command_tpl': '武林争霸赛 [阵营]',
        'desc': '排行榜单 / 武林争霸赛',
    },
    {
        'id': '捕快荣誉榜',
        'group': '排行榜单',
        'command': '捕快荣誉榜',
        'command_tpl': '捕快荣誉榜 [服务器|全服]',
        'desc': '排行榜单 / 捕快荣誉榜',
    },
    {
        'id': '江湖浪客榜',
        'group': '排行榜单',
        'command': '江湖浪客榜',
        'command_tpl': '江湖浪客榜 [服务器|全服]',
        'desc': '排行榜单 / 江湖浪客榜',
    },
    {
        'id': '决斗挑战榜',
        'group': '排行榜单',
        'command': '决斗挑战榜',
        'command_tpl': '决斗挑战榜 [服务器|全服] [公开/私密]',
        'desc': '排行榜单 / 决斗挑战榜',
    },
    {
        'id': '资历排行',
        'group': '排行榜单',
        'command': '资历排行',
        'command_tpl': '资历排行 [服务器] [门派]',
        'desc': '排行榜单 / 资历排行',
    },
    {
        'id': '名士排行',
        'group': '排行榜单',
        'command': '名士排行',
        'command_tpl': '名士排行 [服务器]',
        'desc': '排行榜单 / 名士排行',
    },
    {
        'id': '江湖排行',
        'group': '排行榜单',
        'command': '江湖排行',
        'command_tpl': '江湖排行 [服务器]',
        'desc': '排行榜单 / 江湖排行',
    },
    {
        'id': '兵甲排行',
        'group': '排行榜单',
        'command': '兵甲排行',
        'command_tpl': '兵甲排行 [服务器]',
        'desc': '排行榜单 / 兵甲排行',
    },
    {
        'id': '名师排行',
        'group': '排行榜单',
        'command': '名师排行',
        'command_tpl': '名师排行 [服务器]',
        'desc': '排行榜单 / 名师排行',
    },
    {
        'id': '阵营排行',
        'group': '排行榜单',
        'command': '阵营排行',
        'command_tpl': '阵营排行 [服务器]',
        'desc': '排行榜单 / 阵营排行',
    },
    {
        'id': '薪火排行',
        'group': '排行榜单',
        'command': '薪火排行',
        'command_tpl': '薪火排行 [服务器]',
        'desc': '排行榜单 / 薪火排行',
    },
    {
        'id': '家园排行',
        'group': '排行榜单',
        'command': '家园排行',
        'command_tpl': '家园排行 [服务器]',
        'desc': '排行榜单 / 家园排行',
    },
    {
        'id': '浩气神兵排行',
        'group': '排行榜单',
        'command': '浩气神兵排行',
        'command_tpl': '浩气神兵排行 [服务器]',
        'desc': '排行榜单 / 浩气神兵排行',
    },
    {
        'id': '恶人神兵排行',
        'group': '排行榜单',
        'command': '恶人神兵排行',
        'command_tpl': '恶人神兵排行 [服务器]',
        'desc': '排行榜单 / 恶人神兵排行',
    },
    {
        'id': '浩气爱心排行',
        'group': '排行榜单',
        'command': '浩气爱心排行',
        'command_tpl': '浩气爱心排行 [服务器]',
        'desc': '排行榜单 / 浩气爱心排行',
    },
    {
        'id': '恶人爱心排行',
        'group': '排行榜单',
        'command': '恶人爱心排行',
        'command_tpl': '恶人爱心排行 [服务器]',
        'desc': '排行榜单 / 恶人爱心排行',
    },
    {
        'id': '试炼之地排行',
        'group': '排行榜单',
        'command': '试炼之地',
        'command_tpl': '试炼之地 [服务器] [心法]',
        'desc': '排行榜单 / 试炼之地',
    },
    {
        'id': '赛季恶人战功榜',
        'group': '排行榜单',
        'command': '赛季恶人战功榜',
        'command_tpl': '赛季恶人战功榜 [服务器]',
        'desc': '排行榜单 / 赛季恶人战功榜',
    },
    {
        'id': '赛季浩气战功榜',
        'group': '排行榜单',
        'command': '赛季浩气战功榜',
        'command_tpl': '赛季浩气战功榜 [服务器]',
        'desc': '排行榜单 / 赛季浩气战功榜',
    },
    {
        'id': '上周恶人战功榜',
        'group': '排行榜单',
        'command': '上周恶人战功榜',
        'command_tpl': '上周恶人战功榜 [服务器]',
        'desc': '排行榜单 / 上周恶人战功榜',
    },
    {
        'id': '上周浩气战功榜',
        'group': '排行榜单',
        'command': '上周浩气战功榜',
        'command_tpl': '上周浩气战功榜 [服务器]',
        'desc': '排行榜单 / 上周浩气战功榜',
    },
    {
        'id': '本周恶人战功榜',
        'group': '排行榜单',
        'command': '本周恶人战功榜',
        'command_tpl': '本周恶人战功榜 [服务器]',
        'desc': '排行榜单 / 本周恶人战功榜',
    },
    {
        'id': '本周浩气战功榜',
        'group': '排行榜单',
        'command': '本周浩气战功榜',
        'command_tpl': '本周浩气战功榜 [服务器]',
        'desc': '排行榜单 / 本周浩气战功榜',
    },
    {
        'id': '排行榜',
        'group': '排行榜单',
        'command': '排行榜',
        'command_tpl': '排行榜',
        'desc': '排行榜单 / 排行榜',
    },
    {
        'id': '战功榜',
        'group': '排行榜单',
        'command': '战功榜',
        'command_tpl': '战功榜 [阵营]',
        'desc': '排行榜单 / 战功榜',
    },
    {
        'id': '百战',
        'group': '阵营帮会',
        'command': '百战',
        'command_tpl': '百战',
        'desc': '阵营帮会 / 百战',
    },
    {
        'id': '楚天社',
        'group': '阵营帮会',
        'command': '楚天社',
        'command_tpl': '楚天社',
        'desc': '阵营帮会 / 楚天社',
    },
    {
        'id': '云从社',
        'group': '阵营帮会',
        'command': '云从社',
        'command_tpl': '云从社',
        'desc': '阵营帮会 / 云从社',
    },
    {
        'id': '披风会',
        'group': '阵营帮会',
        'command': '披风会',
        'command_tpl': '披风会',
        'desc': '阵营帮会 / 披风会',
    },
    {
        'id': '穹野卫',
        'group': '阵营帮会',
        'command': '穹野卫',
        'command_tpl': '穹野卫',
        'desc': '阵营帮会 / 穹野卫',
    },
    {
        'id': '统战',
        'group': '阵营帮会',
        'command': '统战',
        'command_tpl': '统战 [服务器]',
        'desc': '阵营帮会 / 统战',
    },
    {
        'id': '诛恶',
        'group': '阵营帮会',
        'command': '诛恶',
        'command_tpl': '诛恶 [服务器]',
        'desc': '阵营帮会 / 诛恶',
    },
    {
        'id': '帮战',
        'group': '阵营帮会',
        'command': '帮战',
        'command_tpl': '帮战 [服务器]',
        'desc': '阵营帮会 / 帮战',
    },
    {
        'id': '招募',
        'group': '开团招募',
        'command': '招募',
        'command_tpl': '招募 [服务器] [副本]',
        'desc': '开团招募 / 招募',
    },
    {
        'id': '团长',
        'group': '开团招募',
        'command': '团长',
        'command_tpl': '团长 [服务器] [名称]',
        'desc': '开团招募 / 团长',
    },
    {
        'id': '团牌',
        'group': '开团招募',
        'command': '团牌',
        'command_tpl': '团牌 [服务器] [内容]',
        'desc': '开团招募 / 团牌',
    },
    {
        'id': '拜师',
        'group': '开团招募',
        'command': '拜师',
        'command_tpl': '拜师 [服务器] [关键词]',
        'desc': '开团招募 / 拜师',
    },
    {
        'id': '收徒',
        'group': '开团招募',
        'command': '收徒',
        'command_tpl': '收徒 [服务器] [关键词]',
        'desc': '开团招募 / 收徒',
    },
    {
        'id': '功能',
        'group': '帮助入口',
        'command': '功能',
        'command_tpl': '功能',
        'desc': '帮助入口 / 功能',
    },
    {
        'id': '认领',
        'group': '会话设置',
        'command': '认领',
        'command_tpl': '认领 [名称]',
        'desc': '会话设置 / 认领',
    },
    {
        'id': '绑定',
        'group': '会话设置',
        'command': '绑定',
        'command_tpl': '绑定 [区服]',
        'desc': '会话设置 / 绑定',
    },
    {
        'id': '查询令牌',
        'group': '会话设置',
        'command': '查询接口令牌',
        'command_tpl': '查询接口令牌',
        'desc': '会话设置 / 查询接口令牌',
    },
    {
        'id': '查询推送令牌',
        'group': '会话设置',
        'command': '查询推送令牌',
        'command_tpl': '查询推送令牌',
        'desc': '会话设置 / 查询推送令牌',
    },
    {
        'id': '授权管理',
        'group': '会话设置',
        'command': '授权管理',
        'command_tpl': '授权管理 [@成员]',
        'desc': '会话设置 / 授权管理',
    },
    {
        'id': '查看管理',
        'group': '会话设置',
        'command': '查看管理',
        'command_tpl': '查看管理',
        'desc': '会话设置 / 查看管理',
    },
    {
        'id': '删除管理',
        'group': '会话设置',
        'command': '删除管理',
        'command_tpl': '删除管理 [序号]',
        'desc': '会话设置 / 删除管理',
    },
    {
        'id': '张嘴',
        'group': '会话设置',
        'command': '张嘴',
        'command_tpl': '张嘴',
        'desc': '会话设置 / 张嘴',
    },
    {
        'id': '闭嘴',
        'group': '会话设置',
        'command': '闭嘴',
        'command_tpl': '闭嘴',
        'desc': '会话设置 / 闭嘴',
    },
    {
        'id': '通知管理',
        'group': '会话设置',
        'command': '通知管理',
        'command_tpl': '通知管理',
        'desc': '会话设置 / 通知管理',
    },
    {
        'id': '打开',
        'group': '会话设置',
        'command': '打开',
        'command_tpl': '打开 [类型]',
        'desc': '会话设置 / 打开',
    },
    {
        'id': '关闭',
        'group': '会话设置',
        'command': '关闭',
        'command_tpl': '关闭 [类型]',
        'desc': '会话设置 / 关闭',
    },
    {
        'id': 'Token',
        'group': '会话设置',
        'command': '接口令牌',
        'command_tpl': '私聊 {command} [UMO] [密钥]',
        'desc': '会话设置 / 接口令牌，仅私聊配置群聊会话',
    },
    {
        'id': '推送令牌',
        'group': '会话设置',
        'command': '推送令牌',
        'command_tpl': '私聊 {command} [UMO] [密钥]',
        'desc': '会话设置 / 推送令牌，仅私聊配置群聊会话',
    },
    {
        'id': '推栏',
        'group': '会话设置',
        'command': '推栏',
        'command_tpl': '私聊 {command} [UMO] [标识]',
        'desc': '会话设置 / 推栏，仅私聊配置群聊会话',
    },
    {
        'id': '新闻',
        'group': '日常活动',
        'command': '新闻',
        'command_tpl': '新闻 [数量]',
        'desc': '日常活动 / 新闻',
    },
    {
        'id': '维护',
        'group': '日常活动',
        'command': '维护',
        'command_tpl': '维护 [数量]',
        'desc': '日常活动 / 维护',
    },
    {
        'id': '答案之书',
        'group': '日常活动',
        'command': '答案之书',
        'command_tpl': '答案之书',
        'desc': '日常活动 / 答案之书',
    },
    {
        'id': '舔狗语录',
        'group': '日常活动',
        'command': '舔狗语录',
        'command_tpl': '舔狗语录',
        'desc': '日常活动 / 舔狗语录',
    },
    {
        'id': '喝什么',
        'group': '日常活动',
        'command': '喝什么',
        'command_tpl': '喝什么',
        'desc': '日常活动 / 喝什么',
    },
    {
        'id': '吃什么',
        'group': '日常活动',
        'command': '吃什么',
        'command_tpl': '吃什么',
        'desc': '日常活动 / 吃什么',
    },
    {
        'id': '渣男语录',
        'group': '日常活动',
        'command': '渣男语录',
        'command_tpl': '渣男语录',
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
    if any(char.isspace() for char in name):
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
    "日常": "查询当日或指定偏移天数的日常活动",
    "日常预测": "查询未来 15 天的日常活动安排",
    "开服": "查询服务器开服状态；不指定服务器时返回全部服务器",
    "科举": "按题目关键词搜索科举答案",
    "小药": "指定心法则返回该心法的小吃小药，否则返回全部",
    "金价": "查询各交易平台金币价格，可指定服务器和条数",
    "物价": "按外观名称查询各区或指定服务器的历史成交价",
    "外观搜索": "按名称搜索外观及其别名信息",
    "交易行": "查询外观在交易行的历史成交价格",
    "万宝楼": "按角色编号查询万宝楼账号详情",
    "花价": "查询各地图鲜花行情",
    "装饰": "按名称查询家园装饰信息",
    "器物谱": "按地图或名称查询器物谱信息",
    "阵营拍卖": "查询阵营拍卖记录，可按物品名称筛选",
    "配方": "查询成品配方的材料与成本",
    "配装": "按心法和玩法查询推荐配装",
    "宏": "按心法查询可用宏配置",
    "技能": "按心法取推栏各分类下的招式技能",
    "奇穴": "按心法查询各等级奇穴配置",
    "阵眼": "按心法查询阵眼效果与说明",
    "沙盘": "查询阵营据点归属、帮会和防守情况",
    "技改": "查询最近的武学调整公告",
    "骚话": "从骚话库随机取一条",
    "聊天": "分页查询指定角色的聊天记录",
    "掉落": "按物品名模糊匹配掉落记录，时间倒序；指定服查单服，不指定查全服",
    "烟花": "角色作为送花人或收花人的烟花记录，时间倒序",
    "查询": "查询角色奇遇与成就概况",
    "未出": "查询角色尚未触发的奇遇",
    "汇总": "汇总指定天数内各奇遇的触发情况",
    "近期": "某服最近触发的奇遇事件，时间倒序",
    "统计": "某奇遇最近的触发记录，时间倒序；指定服查单服，不指定查全服",
    "攻略": "查询指定奇遇的攻略",
    "马场": "查询马场预告以及赤兔、的卢出世情况",
    "刷马": "查询各地图下一匹马驹的预计出世时间",
    "的卢拍卖": "查询的卢拍卖记录",
    "赤兔": "查询当日赤兔记录",
    "本周赤兔": "查询本周各服务器赤兔到达地图",
    "角色": "查询角色名片与基础信息",
    "名片": "查询角色名片",
    "全部名片": "查询角色历史名片列表",
    "随机名片": "按门派和体型随机查询一张名片",
    "精耐": "查询角色百战配置与技能",
    "成就": "按条件查询角色成就完成状态",
    "资历": "按分类查询角色资历与完成度",
    "资历分布": "查询角色资历分布和完成度",
    "战绩": "角色竞技场名片、各模式战绩表现、历史对战，指定模式时附趋势",
    "名剑排行": "按模式查询名剑排行，默认前 50 名，最多 100 名",
    "名剑统计": "某比赛模式下各门派的竞技场周统计",
    "跨服名剑榜": "按 2V2、3V3 或 5V5 查询跨服名剑赛季榜",
    "武林争霸赛": "按阵营查询帮会争霸赛季榜",
    "捕快荣誉榜": "查询捕快荣誉排行榜",
    "江湖浪客榜": "查询江湖浪客排行榜",
    "决斗挑战榜": "按公开或私密类型查询决斗挑战榜",
    "资历排行": "按服务器和门派查询资历排行",
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
    "试炼之地排行": "按服务器和心法查询试炼之地排行",
    "赛季恶人战功榜": "指定服查该服该榜单，否则查全服该榜单",
    "赛季浩气战功榜": "指定服查该服该榜单，否则查全服该榜单",
    "上周恶人战功榜": "指定服查该服该榜单，否则查全服该榜单",
    "上周浩气战功榜": "指定服查该服该榜单，否则查全服该榜单",
    "本周恶人战功榜": "指定服查该服该榜单，否则查全服该榜单",
    "本周浩气战功榜": "指定服查该服该榜单，否则查全服该榜单",
    "排行榜": "查看可选择查询的榜单列表",
    "战功榜": "查看可选择查询的战功榜列表",
    "百战": "查询本周百战首领与特殊效果",
    "楚天社": "查询楚天社接下来的活动排期",
    "云从社": "查询云从社接下来的活动排期",
    "披风会": "查询披风会接下来的活动排期",
    "穹野卫": "查询穹野卫接下来的活动排期",
    "统战": "查询各服务器统战频道信息",
    "诛恶": "查询诛恶刷新记录",
    "帮战": "查询最近帮战记录与战况",
    "招募": "按副本或关键字查询团队招募",
    "团长": "按团长查询团队招募",
    "团牌": "按团牌内容查询团队招募",
    "拜师": "按服务器或关键字查询拜师列表",
    "收徒": "按服务器或关键字查询收徒列表",
    "功能": "查看自主查询命令帮助图",
    "认领": "在私聊认领本插件的管理身份",
    "绑定": "为当前群聊绑定默认区服",
    "查询令牌": "查询接口令牌的等级、已用次数、剩余次数或到期时间",
    "推送令牌": "为指定群聊会话配置 JX3API 推送令牌，仅私聊可用",
    "查询推送令牌": "查询推送令牌的等级、已用次数、剩余次数或到期时间",
    "授权管理": "授权被 @ 的成员管理本会话通知",
    "查看管理": "查看本会话认领人与授权管理员",
    "删除管理": "按序号移除本会话授权管理员",
    "张嘴": "允许被 @ 后触发 LLM 回话",
    "闭嘴": "禁止被 @ 后触发 LLM 回话",
    "通知管理": "查看和管理本会话主动推送事件",
    "打开": "开启指定事件的主动推送",
    "关闭": "关闭指定事件的主动推送",
    "Token": "为指定群聊会话配置 JX3API 接口令牌，仅私聊可用",
    "推栏": "为指定群聊会话配置推栏标识，仅私聊可用",
    "新闻": "查询最新官方资讯",
    "维护": "标题含“版本更新”的公告，最新在前",
    "答案之书": "随机返回一条答案和鼓励语",
    "舔狗语录": "随机返回一条舔狗语录",
    "喝什么": "随机推荐 2 至 4 种饮品",
    "吃什么": "随机推荐 2 至 4 种食物",
    "渣男语录": "随机返回一条渣男语录",
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


def _web_description(item: dict, row: dict, old: str, new: str) -> str:
    desc = WEB_COMMAND_DESCRIPTIONS.get(item["id"], "")
    if desc:
        return desc
    desc = str(row.get("desc") or "")
    if not desc or desc == f"{item['group']} / {item['id']}":
        return _replace_command_text(str(item.get("command_tpl") or item["id"]), old, new)
    return _replace_command_text(desc, old, new)


def help_rows(
    catalog: dict | None = None,
    *,
    exclude_groups: set[str] | None = None,
    exclude_ids: set[str] | None = None,
) -> list[dict]:
    catalog = catalog or DEFAULT_COMMANDS
    from .session_policy import NEED_TICKET, NEED_TOKEN
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
            "word": new,
            "command": _replace_command_text(item["command_tpl"], old, new),
            "web_desc": _web_description(item, row, old, new),
            "fee": (
                "token_ticket"
                if item["id"] in NEED_TICKET and item["id"] in NEED_TOKEN
                else "token" if item["id"] in NEED_TOKEN
                else ""
            ),
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
        desc = desc or _web_description(item, row, old, new)
        rows.append({
            "id": item["id"],
            "group": item["group"],
            "command": new,
            "params": _replace_command_text(item["command_tpl"], old, new),
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

