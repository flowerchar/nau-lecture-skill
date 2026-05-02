#!/usr/bin/env python3
"""
南京审计大学学术讲座 — 一站式启动脚本

混合方案：
  第一阶段：爬取列表页（< 2 秒）→ 启动服务 → 浏览器立即展示
  第二阶段：后台逐条补充详情（报告人、主办方、讲座时间）

用法:
    python serve.py              # 启动服务，自动打开浏览器
    python serve.py --port 9000  # 指定端口
    python serve.py --no-browser # 不自动打开浏览器
"""

import http.server
import json
import os
import sys
import webbrowser
import argparse
import threading
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REF_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "references")
sys.path.insert(0, SCRIPT_DIR)

from crawler import get_lectures_from_list, enrich_lecture, sort_lectures, compute_stats


class LectureHTTPHandler(http.server.SimpleHTTPRequestHandler):
    cv = {
        "template_html": "",
        "alt_template_html": "",
        "init_data": None,
        "phase": "init",
        "logs": [],
        "enrich_idx": 0,
        "enrich_total": 0,
    }

    def log_message(self, format, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {args[0]}")

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._serve_html(LectureHTTPHandler.cv["template_html"])
        elif self.path == "/template.html":
            self._serve_html(LectureHTTPHandler.cv["template_html"])
        elif self.path == "/frontend-design-template.html":
            self._serve_html(LectureHTTPHandler.cv["alt_template_html"])
        elif self.path == "/crawl":
            self._serve_crawl_api()
        else:
            super().do_GET()

    def _serve_html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _serve_crawl_api(self):
        cv = LectureHTTPHandler.cv
        data = cv["init_data"]

        if data is None:
            # 尚未完成第一阶段
            status = {
                "status": "crawling",
                "phase": "phase1",
                "logs": cv["logs"][-20:],
            }
            resp = json.dumps(status, ensure_ascii=False)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(resp.encode("utf-8"))
            return

        # 加入阶段信息
        data = dict(data)
        data["phase"] = cv["phase"]
        if cv["phase"] == "enriching":
            data["enrich_progress"] = f"{cv['enrich_idx']}/{cv['enrich_total']}"

        resp = json.dumps(data, ensure_ascii=False)
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(resp.encode("utf-8"))


def enrich_background(server):
    """后台线程：逐条富化讲座数据"""
    cv = LectureHTTPHandler.cv
    lectures = cv["init_data"]["lectures"]
    cv["enrich_total"] = len(lectures)
    cv["phase"] = "enriching"

    for idx, lec in enumerate(lectures):
        cv["enrich_idx"] = idx + 1
        print(f"  [PHASE-2 {idx+1}/{len(lectures)}] {lec['url']}")
        enrich_lecture(lec)

    sorted_lectures = sort_lectures(lectures)
    stats = compute_stats(sorted_lectures)

    cv["init_data"]["lectures"] = sorted_lectures
    cv["init_data"]["stats"] = stats
    cv["init_data"]["crawl_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv["init_data"]["logs"].append(f"[PHASE-2] 全部详情补充完成")
    cv["phase"] = "done"

    print(f"\n  [DONE] 全部完成: 总计 {stats['total']} 条 "
          f"(未开始 {stats['not_started']}, 已过时 {stats['expired']}, 未知 {stats['unknown']})")
    print(f"\n  数据已就绪，5 秒后自动关闭服务...")
    threading.Timer(5, server.shutdown).start()


def main():
    parser = argparse.ArgumentParser(
        description="南京审计大学学术讲座 — 一站式查询服务"
    )
    parser.add_argument("--port", "-p", type=int, default=8080)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--timeout", "-t", type=int, default=15)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    cv = LectureHTTPHandler.cv

    # 读取模板
    template_path = os.path.join(REF_DIR, "template.html")
    alt_template_path = os.path.join(REF_DIR, "frontend-design-template.html")
    if not os.path.exists(template_path):
        print(f"[ERROR] 模板文件不存在: {template_path}")
        sys.exit(1)
    with open(template_path, "r", encoding="utf-8") as f:
        cv["template_html"] = f.read()
    if os.path.exists(alt_template_path):
        with open(alt_template_path, "r", encoding="utf-8") as f:
            cv["alt_template_html"] = f.read()

    print("=" * 56)
    print("  南京审计大学学术讲座 — 全状态查询系统")
    print("  双主题: 默认视图 / 档案视图")
    print("=" * 56)

    # === 第一阶段：列表页（秒级） ===
    print("\n[PHASE-1] 正在从列表页提取讲座基本信息...")
    lectures, list_logs = get_lectures_from_list(timeout=args.timeout)
    cv["logs"] = list_logs

    if not lectures:
        print("[ERROR] 未获取到任何讲座链接")
        sys.exit(1)

    stats = compute_stats(lectures)
    cv["init_data"] = {
        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_url": "https://www.nau.edu.cn/xshd/list1.htm",
        "stats": stats,
        "lectures": lectures,
        "logs": list_logs,
    }
    cv["phase"] = "phase1_done"

    print(f"  完成：{len(lectures)} 条讲座基本信息已就绪\n")

    # === 启动 HTTP 服务 ===
    server = http.server.HTTPServer((args.host, args.port), LectureHTTPHandler)
    url = f"http://{args.host}:{args.port}"

    print(f"  服务地址: {url}")
    print("=" * 56)

    # === 第二阶段：后台富化 ===
    print(f"\n[PHASE-2] 后台开始补充详情...")
    t = threading.Thread(target=enrich_background, args=(server,), daemon=True)
    t.start()

    # === 打开浏览器 ===
    if not args.no_browser:
        def _open_browser():
            time.sleep(0.5)
            webbrowser.open(url)
        threading.Thread(target=_open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止。")
        server.server_close()


if __name__ == "__main__":
    main()
