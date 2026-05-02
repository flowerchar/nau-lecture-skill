---
name: nau-lecture-skill
description: 当用户提及南京审计大学学术讲座、讲座查询、NAU讲座，或需要爬取/查询/展示南京审计大学学术讲座信息时，使用此skill
version: "1.0.0"
user-invocable: true
---

# 南京审计大学学术讲座爬虫技能

## 概述

本技能从南京审计大学官网学术活动页面（`https://www.nau.edu.cn/xshd/list1.htm`）爬取讲座信息，支持状态智能判定（未开始 / 已过时 / 未知），并通过本地 Web 服务提供一站式可视化查询。

## 触发条件

当用户表达以下意图时使用此 skill：
- "查看南京审计大学讲座"
- "查一下 NAU 最近的讲座"
- "获取南审学术讲座"
- 任何涉及南京审计大学讲座查询的需求

## 使用流程

### 主入口：一键启动

```bash
python scripts/serve.py
```

**这一个命令会依次完成：**
1. 后台线程实时爬取最新讲座数据
2. 立即启动本地 HTTP 服务（默认 `http://127.0.0.1:8080`）
3. **自动打开浏览器** → 页面显示 loading 动画 + 实时日志
4. 爬取完成后数据自动渲染，loading 消失

点击页面右上角"刷新数据"可实时重爬。

### 参数选项

```bash
python scripts/serve.py --port 9000      # 指定端口
python scripts/serve.py --no-browser     # 不自动打开浏览器
python scripts/serve.py --timeout 20     # 自定义爬取超时
python scripts/serve.py --host 0.0.0.0  # 允许局域网访问
```

### 备选方案：仅获取 JSON 数据

```bash
python scripts/crawler.py                    # 输出 JSON 到 stdout
python scripts/crawler.py -o data.json -q    # 静默保存到文件
```

## 技能结构

```
nau-lecture-skill/
├── SKILL.md                              # 本文件
├── scripts/
│   ├── serve.py                          # 主入口
│   └── crawler.py                        # 数据获取模块
└── references/
    ├── template.html                     # 默认视图（蓝色企业风格）
    └── frontend-design-template.html     # 档案视图（深色学术风格）
```

## HTML 界面功能

| 功能 | 说明 |
|------|------|
| 双主题切换 | 默认视图 ⇄ 档案视图，数据通过 sessionStorage 共享，不重复请求 |
| Loading 动画 | 先展示过渡动画 + 实时爬取进度，数据就绪后自动渲染 |
| 统计卡片 | 总讲座数、未开始 / 已过时 / 未知数量 |
| 状态筛选 | 一键过滤三种状态 |
| 关键词搜索 | 实时搜索标题、报告人、主办方 |
| 时间排序 | 点击表头切换升降序 |
| 颜色标记 | 行底色按状态自动着色（绿 / 红 / 灰） |
| 刷新按钮 | 触发服务端实时重爬（带 loading 动画） |
| 日志面板 | 显示爬取进度和错误信息 |
| 详情链接 | 点击直接打开原讲座页面 |

## 状态判定规则

| 状态 | 颜色 | 判定逻辑 |
|------|------|----------|
| 未开始 | 绿 `#00B42A` | 当前时间 < 讲座时间 |
| 已过时 | 红 `#F53F3F` | 当前时间 >= 讲座时间 |
| 未知 | 灰 `#86909C` | 无法解析讲座时间（兜底，提示官网格式变动） |

## 工作流详解

当用户说"查看南审讲座"时，skill 应执行：

1. **启动服务**：运行 `python scripts/serve.py`
2. **告知用户**：服务地址（如 `http://127.0.0.1:8080`）和浏览器已自动打开
3. **交互说明**：用户在网页中可筛选/搜索/排序/刷新

### 响应模板

```
已启动南京审计大学学术讲座查询服务

✅ 数据已获取：共 X 条讲座（未开始 X / 已过时 X）
🌐 浏览器已打开：http://127.0.0.1:8080
🔄 点击页面右上角"刷新数据"可实时更新
⏹ 按 Ctrl+C 停止服务
```

## 扩展与修改

### 修改爬取目标
编辑 `scripts/crawler.py` 的 `MAIN_URL` 变量。

### 添加时间格式
在 `format_time()` 函数（约第 53 行）的 `patterns` 列表中添加正则匹配规则。

### 自定义样式
修改 `references/template.html` 中 `:root` 下的 CSS 变量：
```css
--primary: #165DFF;   /* 主色 */
--success: #00B42A;   /* 未开始 */
--danger: #F53F3F;    /* 已过时 */
--gray: #86909C;      /* 未知 */
```

## 依赖项

```bash
pip install requests beautifulsoup4
```

Python 标准库：`threading`, `datetime`, `re`, `json`, `http.server`, `webbrowser`

## 核心模块

| 文件 | 功能 |
|------|------|
| `scripts/serve.py` | 主入口：后台爬取 → HTTP 服务（双模板路由） → 自动打开浏览器 |
| `scripts/crawler.py` | 数据获取：列表页链接提取 → 详情页解析 → JSON 输出 |
| `references/template.html` | 默认视图：蓝色企业风格（Microsoft YaHei） |
| `references/frontend-design-template.html` | 档案视图：深色学术风格（Cormorant Garamond + JetBrains Mono + grain texture） |
