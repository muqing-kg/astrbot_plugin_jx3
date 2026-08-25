from __future__ import annotations

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
        'id': '全服状态',
        'group': '日常活动',
        'command': '全服状态',
        'command_tpl': '全服状态',
        'example_tpl': '全服状态',
        'desc': '日常活动 / 全服状态',
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
        'id': '加速',
        'group': '配装工具',
        'command': '加速',
        'command_tpl': '加速 [技能CD]',
        'example_tpl': '加速 1.5',
        'desc': '配装工具 / 加速',
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
        'desc': '配装工具 / 骚话',
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
        'id': '副本',
        'group': '副本掉落',
        'command': '副本',
        'command_tpl': '副本 [服务器] [角色]',
        'example_tpl': '副本 飞龙在天 小螺卜头',
        'desc': '副本掉落 / 副本',
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
        'id': '试炼秒伤',
        'group': '副本掉落',
        'command': '试炼秒伤',
        'command_tpl': '试炼秒伤 [赛季] [层数]',
        'example_tpl': '试炼秒伤 1 10',
        'desc': '副本掉落 / 试炼秒伤',
    },
    {
        'id': '试炼赛季',
        'group': '副本掉落',
        'command': '试炼赛季',
        'command_tpl': '试炼赛季',
        'example_tpl': '试炼赛季',
        'desc': '副本掉落 / 试炼赛季',
    },
    {
        'id': '奇遇',
        'group': '奇遇宠物',
        'command': '奇遇',
        'command_tpl': '奇遇 [服务器] [角色]',
        'example_tpl': '奇遇 飞龙在天 小螺卜头',
        'desc': '奇遇宠物 / 奇遇',
    },
    {
        'id': '查询',
        'group': '奇遇宠物',
        'command': '查询',
        'command_tpl': '查询 [服务器] [角色]',
        'example_tpl': '查询 飞龙在天 小螺卜头',
        'desc': '奇遇宠物 / 查询',
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
        'command': '武林争霸',
        'command_tpl': '武林争霸 [服务器] [阵营]',
        'example_tpl': '武林争霸 飞龙在天',
        'desc': '排行榜单 / 武林争霸',
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
        'id': '试炼之地',
        'group': '排行榜单',
        'command': '试炼之地',
        'command_tpl': '试炼之地 [服务器] [心法]',
        'example_tpl': '试炼之地 飞龙在天 剑纯',
        'desc': '排行榜单 / 试炼之地',
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
        'group': '会话设置',
        'command': '功能',
        'command_tpl': '功能',
        'example_tpl': '功能',
        'desc': '会话设置 / 功能',
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
        'desc': '会话设置 / 新闻',
    },
    {
        'id': '维护',
        'group': '日常活动',
        'command': '维护',
        'command_tpl': '维护 [数量]',
        'example_tpl': '维护',
        'desc': '会话设置 / 维护',
    },
    {
        'id': '818',
        'group': '日常活动',
        'command': '818',
        'command_tpl': '818 [服务器] [数量]',
        'example_tpl': '818 飞龙在天',
        'desc': '会话设置 / 818',
    },
    {
        'id': '答案之书',
        'group': '日常活动',
        'command': '答案之书',
        'command_tpl': '答案之书',
        'example_tpl': '答案之书',
        'desc': '会话设置 / 答案之书',
    },
    {
        'id': '舔狗语录',
        'group': '日常活动',
        'command': '舔狗语录',
        'command_tpl': '舔狗语录',
        'example_tpl': '舔狗语录',
        'desc': '会话设置 / 舔狗语录',
    },
    {
        'id': '喝什么',
        'group': '日常活动',
        'command': '喝什么',
        'command_tpl': '喝什么',
        'example_tpl': '喝什么',
        'desc': '会话设置 / 喝什么',
    },
    {
        'id': '吃什么',
        'group': '日常活动',
        'command': '吃什么',
        'command_tpl': '吃什么',
        'example_tpl': '吃什么',
        'desc': '会话设置 / 吃什么',
    },
    {
        'id': '渣男语录',
        'group': '日常活动',
        'command': '渣男语录',
        'command_tpl': '渣男语录',
        'example_tpl': '渣男语录',
        'desc': '会话设置 / 渣男语录',
    },
]

DEFAULT_COMMANDS = {row['id']: row for row in DEFAULT_COMMAND_ROWS}


from copy import deepcopy
import re


def _clone(catalog: dict) -> dict:
    return deepcopy(catalog)


def default_command_for(command_id: str) -> str:
    row = DEFAULT_COMMANDS.get(command_id) or {}
    return str(row.get("command") or command_id)


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


def resolve_command(catalog: dict, trigger: str) -> str | None:
    trigger = (trigger or "").strip()
    if not trigger:
        return None
    for command_id, row in catalog.items():
        if str(row.get("command") or "") == trigger:
            return command_id
    return None


def _replace_command_text(text: str, old: str, new: str) -> str:
    if not text:
        return text
    if "{command}" in text:
        return text.replace("{command}", new)
    return re.sub(rf"(?<!\S){re.escape(old)}(?!\S)", new, text)


def help_rows(catalog: dict | None = None) -> list[dict]:
    catalog = catalog or DEFAULT_COMMANDS
    group_order = []
    for item in DEFAULT_COMMAND_ROWS:
        if item["group"] not in group_order:
            group_order.append(item["group"])
    ordered = sorted(DEFAULT_COMMAND_ROWS, key=lambda item: (group_order.index(item["group"]), DEFAULT_COMMAND_ROWS.index(item)))
    rows = []
    for item in ordered:
        row = catalog.get(item["id"], item)
        old = item["command"]
        new = str(row.get("command") or old)
        rows.append({
            "id": item["id"],
            "group": item["group"],
            "command": _replace_command_text(item["command_tpl"], old, new),
            "example": _replace_command_text(item["example_tpl"], old, new),
            "desc": str(row.get("desc") or item["desc"]),
        })
    return rows


def public_command_rows(catalog: dict | None = None) -> list[dict]:
    catalog = catalog or DEFAULT_COMMANDS
    rows = []
    for item in DEFAULT_COMMAND_ROWS:
        row = catalog.get(item["id"], item)
        desc = str(row.get("desc") or "")
        if not desc or desc == f"{item['group']} / {item['id']}":
            desc = str(item.get("command_tpl") or item["id"])
        rows.append({
            "id": item["id"],
            "group": item["group"],
            "default_command": item["command"],
            "command": str(row.get("command") or item["command"]),
            "desc": desc,
        })
    return rows


def command_usage(command_id: str, catalog: dict | None = None) -> str:
    catalog = catalog or DEFAULT_COMMANDS
    row = (catalog.get(command_id) or DEFAULT_COMMANDS.get(command_id) or {})
    tpl = str(row.get("command_tpl") or row.get("command") or command_id)
    name = str(row.get("command") or command_id)
    # Keep the first pattern only, drop alternate "cmd | cmd [x]" duplication.
    first = tpl.split("|")[0].strip()
    return first or name
