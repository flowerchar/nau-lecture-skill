# AGENTS.md

## 项目概览

南京审计大学学术讲座爬虫技能 — 从 nau.edu.cn 混合爬取讲座数据，Web 双主题可视化。

## 常用命令

```bash
python scripts/serve.py              # 启动服务 + 自动打开浏览器
python scripts/serve.py --no-browser # 启动服务（不打开浏览器）
python scripts/serve.py --port 9000  # 指定端口
python scripts/crawler.py            # 仅输出 JSON 到 stdout
python scripts/crawler.py -o data.json --fast  # 快速模式（不爬详情）
```

## 代码风格

- **Python**: 简洁函数式，避免过度抽象。使用 `requests` + `BeautifulSoup` 做爬虫。
- **HTML/CSS/JS**: 单文件模板，CSS 变量驱动双主题（`body.dark` 切换）。无框架依赖。
- **函数命名**: JavaScript 使用短名（`sl`, `hl`, `fd`, `rt`, `af`, `sf`, `ts`, `us`, `rl`, `ap`）。

## 提交规范

使用 conventional commits:
- `feat:` 新功能
- `fix:` 修复 bug
- `refactor:` 重构
- `docs:` 文档
- `chore:` 杂务

## 注意事项

- 数据源: `https://www.nau.edu.cn/xshd/list1.htm`
- 列表页用 `div.line1` 提取标题+链接，详情页用 `div.wp_articlecontent` 提取时间/报告人/主办方
- 讲座时间格式多样，`format_time()` 处理粘连格式（`2026-05-1314:00`）和空格格式
- 排序规则: 未开始→已过时→未知，已过时按时间倒序

## 流程规则

- 每次修改代码后必须**先本地测试通过**再推送到 GitHub
- **推送前需征得开发者同意**，不允许未经确认直接 `git push`
- 项目同时维护工作目录（`D:\githubRep\nau-lecture-skill`）和安装目录（`~\.config\opencode\skills\nau-lecture-skill`），两者需同步
