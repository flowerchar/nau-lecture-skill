# nau-lecture-skill

南京审计大学学术讲座爬虫技能 — 一键爬取 + 自包含 HTML 可视化。

## 快速开始

```bash
pip install requests beautifulsoup4
python scripts/crawler.py -m
```

爬取完成后生成 `lectures.html`，浏览器直接打开即可查看。

## 功能

- **混合爬取**：列表页 1 次请求秒出标题+日期，逐条富化报告人、主办方、精确时间
- **状态判定**：未开始 / 已过时 / 未知，颜色标记（绿 / 红 / 灰）
- **终端摘要**：爬取后终端打印讲座列表 + 相对时间 + HTML 链接
- **静态 HTML**：数据内嵌，无服务器依赖，双击即开
- **Web 界面**：统计卡片、状态筛选、关键词搜索、时间排序、相对时间、双主题切换
- **CLI 模式**：`python scripts/crawler.py -o data.json` 输出结构化 JSON

## 项目结构

```
├── scripts/
│   └── crawler.py       # 爬虫模块：列表页 → 详情页 → JSON/HTML → 终端摘要
└── references/
    └── template.html    # HTML 渲染模板（数据内嵌）
```

## 参数

| 参数 | 说明 |
|------|------|
| `-m` | 生成 HTML（默认 `lectures.html`） |
| `-m out.html` | 指定 HTML 文件名 |
| `-o data.json` | 输出 JSON 到文件 |
| `--fast` | 仅列表页，不爬详情 |
| `--quiet / -q` | 静默模式 |

## 数据源

[https://www.nau.edu.cn/xshd/list1.htm](https://www.nau.edu.cn/xshd/list1.htm)
