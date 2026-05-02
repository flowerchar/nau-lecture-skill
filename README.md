# nau-lecture-skill

南京审计大学学术讲座爬虫技能 — 一键爬取 + 可视化查询。

## 快速开始

```bash
pip install requests beautifulsoup4
python scripts/serve.py
```

浏览器自动打开 → 秒出列表 → 后台逐条补充报告人/主办方。

## 功能

- **混合爬取**：列表页 1 次请求秒出标题+日期，后台逐条富化报告人、主办方、精确时间
- **状态判定**：未开始 / 已过时 / 未知，颜色标记（绿 / 红 / 灰）
- **Web 界面**：统计卡片、状态筛选、关键词搜索、时间排序、一键刷新
- **CLI 模式**：`python scripts/crawler.py -o data.json` 输出结构化 JSON

## 项目结构

```
├── scripts/
│   ├── serve.py         # 主入口：HTTP 服务 + 自动打开浏览器
│   └── crawler.py       # 爬虫模块：列表页 → 详情页 → JSON
└── references/
    └── template.html    # HTML 渲染模板
```

## 参数

| 参数 | 说明 |
|------|------|
| `--port 9000` | 指定端口（默认 8080） |
| `--no-browser` | 不自动打开浏览器 |
| `--timeout 20` | 爬取超时（秒） |
| `--fast` | 仅列表页，不爬详情 |
| `--host 0.0.0.0` | 局域网可访问 |

## 数据源

[https://www.nau.edu.cn/xshd/list1.htm](https://www.nau.edu.cn/xshd/list1.htm)
