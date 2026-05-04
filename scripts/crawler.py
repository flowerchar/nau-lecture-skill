#!/usr/bin/env python3
"""
南京审计大学学术讲座爬虫 - 数据获取模块

混合方案：
  第一阶段：从列表页提取标题 + 链接 + 发布日期（1 次请求，秒级出结果）
  第二阶段：逐条爬取详情页补充报告人、主办方、讲座时间

用法:
    python crawler.py                     # 输出 JSON 到 stdout
    python crawler.py --output data.json  # 保存到文件
    python crawler.py --fast              # 仅列表页，不爬详情
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
from datetime import datetime
import json
import argparse
import sys
import os


# ======================== 配置 ========================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.nau.edu.cn/",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
}

MAIN_URL = "https://www.nau.edu.cn/xshd/list1.htm"
BASE_DOMAIN = "https://www.nau.edu.cn"
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".lecture_cache.json")


# ======================== 时间解析 ========================

def format_time(raw_time):
    """
    将原始时间字符串统一转换为 %Y-%m-%d %H:%M:%S 格式。
    支持半角/全角空格、中文格式、日期与时间缺省等多种变体。
    """
    if not raw_time or raw_time == "无":
        return "无"

    raw_time = raw_time.strip()
    patterns = [
        (r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})[\s\u3000]+(\d{1,2}):(\d{1,2}):(\d{1,2})",
         "%Y-%m-%d %H:%M:%S"),
        (r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})[\s\u3000]+(\d{1,2}):(\d{1,2})",
         "%Y-%m-%d %H:%M:00"),
        (r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})(\d{1,2}):(\d{1,2})(?![\d:])",
         "%Y-%m-%d %H:%M:00"),
        (r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})",
         "%Y-%m-%d 00:00:00"),
        (r"(\d{4})年(\d{1,2})月(\d{1,2})日[\s\u3000]*(\d{1,2})[:：](\d{1,2})",
         "%Y-%m-%d %H:%M:00"),
        (r"(\d{4})年(\d{1,2})月(\d{1,2})日",
         "%Y-%m-%d 00:00:00"),
    ]

    for pattern, _ in patterns:
        match = re.search(pattern, raw_time)
        if match:
            groups = match.groups()
            year = groups[0].zfill(4)
            month = groups[1].zfill(2)
            day = groups[2].zfill(2)
            hour = groups[3].zfill(2) if len(groups) >= 4 else "00"
            minute = groups[4].zfill(2) if len(groups) >= 5 else "00"
            second = groups[5].zfill(2) if len(groups) >= 6 else "00"
            return f"{year}-{month}-{day} {hour}:{minute}:{second}"

    return raw_time


def extract_date_from_url(url):
    """从 URL 路径提取发布日期，如 /2026/0430/ → 2026-04-30"""
    match = re.search(r"/(\d{4})/(\d{2})(\d{2})/", url)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return "无"


# ======================== 状态判定 ========================

def get_activity_status(formatted_time):
    """
    根据格式化后的时间判定讲座状态：
    - 未开始：当前时间 < 讲座时间
    - 已过时：当前时间 >= 讲座时间
    - 未知：无法解析时间
    """
    if formatted_time == "无":
        return "未知"

    time_pattern = r"\d{4}-\d{2}-\d{2}[\s\u3000]+\d{2}:\d{2}:\d{2}"
    if not re.search(time_pattern, formatted_time):
        return "未知"

    try:
        activity_time = datetime.strptime(formatted_time, "%Y-%m-%d %H:%M:%S")
        current_time = datetime.now()

        activity_time = activity_time.replace(second=0, microsecond=0)
        current_time = current_time.replace(second=0, microsecond=0)

        if current_time < activity_time:
            return "未开始"
        else:
            return "已过时"
    except Exception as e:
        print(f"[WARN] 时间解析失败: {formatted_time} -> {e}", file=sys.stderr)
        return "未知"


# ======================== 字段清理 ========================

def clean_field(text, prefixes):
    if not text or text == "无":
        return "无"
    text = text.strip()
    for prefix in prefixes:
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return text


def clean_reporter(reporter_text):
    prefixes = ["报告人：", "报告人:", "主讲人：", "主讲人:", "嘉宾：", "嘉宾:"]
    return clean_field(reporter_text, prefixes)


def clean_organizer(organizer_text):
    prefixes = ["举办单位：", "举办单位:", "主办方：", "主办方:", "承办单位：", "承办单位:"]
    return clean_field(organizer_text, prefixes)


def clean_location(location_text):
    prefixes = ["地点：", "地点:", "地址：", "地址:", "会场：", "会场:"]
    return clean_field(location_text, prefixes)


# ======================== 第一阶段：列表页快速提取 ========================

def get_lectures_from_list(timeout=15):
    """
    从列表页提取标题 + 链接 + 发布日期。
    返回 (lectures: list, log_lines: list)
    """
    log_lines = []
    lectures = []

    try:
        resp = requests.get(MAIN_URL, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding

        soup = BeautifulSoup(resp.text, "html.parser")
        line1_divs = soup.find_all("div", class_="line1")

        if not line1_divs:
            log_lines.append("[ERROR] 未找到任何讲座容器")
            return lectures, log_lines

        log_lines.append(f"[PHASE-1] 从列表页提取到 {len(line1_divs)} 条讲座（秒级完成）")

        seen_urls = set()
        for div in line1_divs:
            a_tags = div.find_all("a", recursive=False)
            for a in a_tags:
                href = a.get("href", "").strip()
                title = a.get("title", "").strip() or a.get_text(strip=True)
                if not href or not title:
                    continue
                full_url = urljoin(BASE_DOMAIN, href)
                if "nau.edu.cn" not in full_url or full_url in seen_urls:
                    continue
                seen_urls.add(full_url)
                pub_date = extract_date_from_url(full_url)
                lectures.append({
                    "status": "未知",
                    "formatted_time": pub_date,
                    "title": title,
                    "location": "加载中...",
                    "reporter": "加载中...",
                    "organizer": "加载中...",
                    "url": full_url,
                })

        return lectures, log_lines

    except requests.exceptions.RequestException as e:
        log_lines.append(f"[ERROR] 获取列表页失败: {e}")
        return lectures, log_lines


# ======================== 第二阶段：详情页补充 ========================

def enrich_lecture(lecture, timeout=20):
    """
    爬取详情页，补充报告人、主办方、讲座时间、地点。
    原地修改 lecture dict。
    """
    try:
        resp = requests.get(lecture["url"], headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding

        soup = BeautifulSoup(resp.text, "html.parser")

        content_div = soup.find("div", class_="wp_articlecontent")
        p_tags = []
        if content_div:
            p_tags = [
                p for p in content_div.find_all("p", limit=10)
                if p.get_text(strip=True)
            ]

        time_info = "无"
        location = "无"
        reporter = "无"
        organizer = "无"

        time_keywords = ["讲座时间", "活动时间", "举办时间", "时间", "日期", "开始"]
        location_keywords = ["地点", "地址", "会场", "教室", "会议室"]
        reporter_keywords = ["报告人", "主讲人", "嘉宾", "主讲"]
        organizer_keywords = ["举办单位", "主办方", "承办方", "承办单位", "组织方"]

        for p in p_tags:
            text = p.get_text(strip=True)
            if any(kw in text for kw in organizer_keywords):
                organizer = text
            elif any(kw in text for kw in time_keywords):
                time_info = text
            elif any(kw in text for kw in reporter_keywords):
                reporter = text
            elif any(kw in text for kw in location_keywords):
                location = text

        formatted_time = format_time(time_info)
        status = get_activity_status(formatted_time)

        lecture["status"] = status
        lecture["formatted_time"] = formatted_time
        lecture["location"] = clean_location(location)
        lecture["reporter"] = clean_reporter(reporter)
        lecture["organizer"] = clean_organizer(organizer)
        lecture["_enriched"] = True
        return True

    except requests.exceptions.RequestException as e:
        print(f"[WARN] 详情页失败 {lecture['url']}: {e}", file=sys.stderr)
        lecture["location"] = "无"
        lecture["reporter"] = "无"
        lecture["organizer"] = "无"
        lecture["_enriched"] = False
        return False


# ======================== 排序 ========================

STATUS_WEIGHT = {"未开始": 0, "已过时": 1, "未知": 2}


def sort_lectures(lectures):
    """按状态优先级 + 时间排序"""
    def sort_key(lec):
        weight = STATUS_WEIGHT.get(lec["status"], 3)
        try:
            ts = datetime.strptime(lec["formatted_time"], "%Y-%m-%d %H:%M:%S").timestamp()
        except Exception:
            ts = float("inf") if lec["status"] == "未开始" else float("-inf")
        if lec["status"] == "已过时":
            ts = -ts
        return (weight, ts)

    return sorted(lectures, key=sort_key)


# ======================== 主流程 ========================

def crawl_all(timeout=15, detail_timeout=20, fast_only=False, verbose=True):
    """
    主入口。
    fast_only=True: 仅爬列表页，不爬详情。
    返回 (lectures, stats, logs)
    """
    all_logs = []

    def log(msg):
        if verbose:
            print(msg)
        all_logs.append(msg)

    # === 第一阶段：列表页 ===
    log("[PHASE-1] 正在获取列表页...")
    lectures, list_logs = get_lectures_from_list(timeout=timeout)
    all_logs.extend(list_logs)

    if not lectures:
        log("[ERROR] 未获取到任何讲座链接")
        return [], {"total": 0, "not_started": 0, "expired": 0, "unknown": 0}, all_logs

    log(f"[PHASE-1] 完成：{len(lectures)} 条讲座基本信息已就绪")

    if fast_only:
        sorted_lectures = sort_lectures(lectures)
        stats = compute_stats(sorted_lectures)
        log(f"[DONE] 快速模式完成: 总计 {stats['total']} 条")
        return sorted_lectures, stats, all_logs

    # === 第二阶段：逐条补充详情 ===
    log(f"[PHASE-2] 正在补充 {len(lectures)} 条讲座详情...")
    for idx, lec in enumerate(lectures, 1):
        log(f"  [{idx}/{len(lectures)}] {lec['url']}")
        enrich_lecture(lec, timeout=detail_timeout)

    sorted_lectures = sort_lectures(lectures)
    stats = compute_stats(sorted_lectures)

    log(f"[DONE] 爬取完成: 总计 {stats['total']} 条 "
        f"(未开始 {stats['not_started']}, 已过时 {stats['expired']}, 未知 {stats['unknown']})")

    return sorted_lectures, stats, all_logs


def compute_stats(lectures):
    return {
        "total": len(lectures),
        "not_started": sum(1 for l in lectures if l["status"] == "未开始"),
        "expired": sum(1 for l in lectures if l["status"] == "已过时"),
        "unknown": sum(1 for l in lectures if l["status"] == "未知"),
    }


def output_json(lectures, stats, logs, output_path=None, quiet=False):
    data = {
        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_url": MAIN_URL,
        "stats": stats,
        "lectures": lectures,
        "logs": logs,
    }
    json_str = json.dumps(data, ensure_ascii=False, indent=2)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"[INFO] 数据已保存到 {output_path}")
    elif not quiet:
        print(json_str)

    return json_str, data


def save_cache(data):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def load_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def output_html_from_data(data, output_path="lectures.html", template_path=None):
    if template_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(os.path.dirname(script_dir), "references", "template.html")

    if not os.path.exists(template_path):
        print(f"[ERROR] 模板文件不存在: {template_path}", file=sys.stderr)
        return None

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    data_json = json.dumps(data, ensure_ascii=False)
    html = template.replace("__LECTURE_DATA__", data_json)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[INFO] HTML 已保存到 {output_path}")
    return output_path


def output_html(lectures, stats, logs, output_path="lectures.html", template_path=None):
    data = {
        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_url": MAIN_URL,
        "stats": stats,
        "lectures": lectures,
        "logs": logs,
    }
    return output_html_from_data(data, output_path, template_path)


def print_summary(lectures, stats, html_path=None):
    """终端打印讲座摘要 + 网页链接 + 交互提示"""
    icons = {"未开始": "●", "已过时": "O", "未知": "?"}
    bar = "─" * 54

    print()
    print(f"  {bar}")
    print(f"  {'状态':<6} {'时间':<18} {'标题':<28}")
    print(f"  {bar}")
    for l in lectures:
        icon = icons.get(l["status"], "?")
        title = l["title"]
        if len(title) > 26:
            title = title[:25] + "…"
        t = l.get("formatted_time", "无")
        if len(t) >= 16:
            t = t[:16]
        loc = l.get("location", "无")
        if loc and loc != "无" and loc != "加载中...":
            title = title + "  [" + loc + "]"
        print(f"  {icon} {l['status']:<4} {t:<18} {title}")
    print(f"  {bar}")
    print()
    print(f"  共 {stats['total']} 条讲座（未开始 {stats['not_started']} / 已过时 {stats['expired']} / 未知 {stats['unknown']}）")
    if html_path:
        abs_path = os.path.abspath(html_path)
        print(f"  [WEB] 网页查看: file:///{abs_path}")
    print()
    print("  [TIP] 你有哪些想听的讲座？需要我给出可视化面板吗？")
    print()


# ======================== CLI 入口 ========================

def main():
    if sys.platform == "win32":
        try:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(
        description="南京审计大学学术讲座爬虫 - 数据获取工具"
    )
    parser.add_argument("--output", "-o", default=None, help="输出 JSON 文件路径")
    parser.add_argument("--html", "-m", default=None, const="lectures.html", nargs="?", help="输出自包含 HTML 文件（默认: lectures.html）")
    parser.add_argument("--template", default=None, help="HTML 模板路径")
    parser.add_argument("--timeout", "-t", type=int, default=15, help="列表页超时（秒）")
    parser.add_argument("--detail-timeout", "-d", type=int, default=20, help="详情页超时（秒）")
    parser.add_argument("--fast", action="store_true", help="快速模式：仅爬列表页，不爬详情")
    parser.add_argument("--quiet", "-q", action="store_true", help="静默模式")
    args = parser.parse_args()

    # --- HTML 模式：优先用缓存，避免重复爬取 ---
    if args.html:
        cached = load_cache()
        if cached and "lectures" in cached:
            if not args.quiet:
                print("[CACHE] 使用缓存数据，无需重新爬取")
            data = cached
            lectures = data["lectures"]
            stats = data["stats"]
            logs = data.get("logs", [])
        else:
            lectures, stats, logs = crawl_all(
                timeout=args.timeout,
                detail_timeout=args.detail_timeout,
                fast_only=args.fast,
                verbose=not args.quiet,
            )
            if stats["total"] == 0:
                sys.exit(1)
            data = {
                "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "source_url": MAIN_URL,
                "stats": stats,
                "lectures": lectures,
                "logs": logs,
            }
            save_cache(data)

        output_html_from_data(data, output_path=args.html, template_path=args.template)
        if not args.quiet:
            print_summary(lectures, stats, html_path=args.html)
        return

    # --- 终端模式：爬取 + 缓存 ---
    lectures, stats, logs = crawl_all(
        timeout=args.timeout,
        detail_timeout=args.detail_timeout,
        fast_only=args.fast,
        verbose=not args.quiet,
    )

    if stats["total"] == 0:
        sys.exit(1)

    _, data = output_json(lectures, stats, logs, output_path=args.output, quiet=not args.output)
    save_cache(data)

    if not args.quiet:
        print_summary(lectures, stats)


if __name__ == "__main__":
    main()
