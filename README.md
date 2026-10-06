# 亚洲新闻速览 Asia News Digest

每日自动聚合 13 家国际媒体的**亚洲新闻**，翻译成中文，按日期归档。

🌐 在线阅读：https://curzydj8.github.io/asia-news-digest/

## 新闻来源（13 家）

| 媒体 | RSS |
|---|---|
| CNN | edition.rss |
| The New York Times（纽约时报） | World |
| The Washington Post（华盛顿邮报） | world |
| The Wall Street Journal（华尔街日报） | World News |
| Fox News（福克斯新闻） | world |
| NBC News | world |
| ABC News | international |
| CBS News | world |
| NPR | world |
| BBC News | Asia |
| The Guardian（卫报） | world |
| Financial Times（金融时报） | world |
| Euronews（欧洲新闻） | news |

## 功能

- ✅ 每日自动抓取（北京时间早 7 点）
- ✅ 亚洲关键词过滤（国家/地区/人名/海域等 80+ 关键词）
- ✅ 视频类内容自动跳过（用户要求：视频不转）
- ✅ 标题+摘要机器翻译成中文（保留英文原文，可一键对照）
- ✅ 原文配图直接展示（外链）
- ✅ 按日期归档：左侧日期栏从上到下由新到旧，点击进入当天新闻
- ✅ 每条新闻按发布时间倒序，新的在最前

## 技术

- `fetch_news.py`：纯 Python 标准库抓取 + 解析 RSS/Atom，无第三方依赖
- 翻译：Google 翻译接口 + 本地缓存（`.translate_cache.json`），避免重复翻译
- 前端：单文件 `index.html`，无框架，`data/*.json` 驱动
- 数据：`data/YYYY-MM-DD.json` 每日新闻，`data/index.json` 日期索引

## 免责

新闻内容与图片版权归各原媒体所有，本站仅做聚合翻译，供学习交流。
