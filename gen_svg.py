#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Uptime tính từ ngày sinh, stats lấy từ GitHub API:
- GH_PAT (secret, fine-grained PAT): đếm cả repo private
- GITHUB_TOKEN (Actions cấp sẵn): chỉ repo public
- không có token (chạy local): điền ?? để preview
"""
import html
import json
import os
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

ASCII_FILE = "ascii.txt"
USER = "jakeemma2012"
BIRTHDATE = date(2004, 2, 18)
TZ_VN = timezone(timedelta(hours=7))

GH_PAT = os.environ.get("GH_PAT") or None
TOKEN = GH_PAT or os.environ.get("GITHUB_TOKEN") or None

# ---------- màu ----------
THEMES = {
    "dark": {
        "bg": "#0d1117",
        "art": "#8b949e",
        "base": "#c9d1d9",
        "label": "#ffa657",
        "value": "#79c0ff",
        "header": "#d2a8ff",
        "line": "#30363d",
        "add": "#3fb950",
        "del": "#f85149",
    },
    "light": {
        "bg": "#ffffff",
        "art": "#57606a",
        "base": "#24292f",
        "label": "#953800",
        "value": "#0550ae",
        "header": "#8250df",
        "line": "#d0d7de",
        "add": "#1a7f37",
        "del": "#cf222e",
    },
}

# ---------- uptime ----------
def calc_uptime(today):
    y = today.year - BIRTHDATE.year
    m = today.month - BIRTHDATE.month
    d = today.day - BIRTHDATE.day
    if d < 0:
        m -= 1
        prev_month_end = today.replace(day=1) - timedelta(days=1)
        d += prev_month_end.day
    if m < 0:
        y -= 1
        m += 12
    unit = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
    return f"{unit(y, 'year')}, {unit(m, 'month')}, {unit(d, 'day')}"

# ---------- GitHub API ----------
def api(path):
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER,
            **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
        if r.status == 202:
            return None
        return json.loads(body) if body else []

def list_owned_repos():
    base = "/user/repos?affiliation=owner" if GH_PAT else f"/users/{USER}/repos?type=owner"
    repos, page = [], 1
    while True:
        batch = api(f"{base}&per_page=100&page={page}")
        repos += batch
        if len(batch) < 100:
            return repos
        page += 1

def extract_contrib(data):
    """(commits, additions, deletions) của USER từ payload stats/contributors."""
    for c in data:
        author = c.get("author") or {}
        if author.get("login", "").lower() == USER.lower():
            return (
                c["total"],
                sum(w["a"] for w in c["weeks"]),
                sum(w["d"] for w in c["weeks"]),
            )
    return 0, 0, 0

def contributor_stats(repo_names):
    """Lượt đầu gọi hết các repo để GitHub bắt đầu tính song song (202 = đang tính),
    các lượt sau chỉ hỏi lại repo chưa xong, thời gian chờ tăng dần."""
    results, pending = {}, list(repo_names)
    deadline = time.time() + 300  # đợi GitHub tính xong tối đa ~5 phút
    wait = 5
    while pending:
        still = []
        for name in pending:
            try:
                data = api(f"/repos/{USER}/{name}/stats/contributors")
            except urllib.error.HTTPError as e:
                if e.code == 451:  # repo bị GitHub chặn (DMCA) -> không đọc được stats
                    print(f"bỏ qua {name}: HTTP 451 (repo bị chặn)")
                    continue
                raise
            if data is None:
                still.append(name)
            else:
                results[name] = extract_contrib(data)
        pending = still
        if pending and time.time() >= deadline:
            # bỏ qua thay vì fail: thiếu 1 repo trong 1 ngày, lần chạy sau tự đủ lại
            print(f"cảnh báo: stats chưa tính xong, bỏ qua: {', '.join(pending)}")
            break
        if pending:
            time.sleep(wait)
            wait = min(wait * 2, 60)
    return results

def fetch_stats():
    if not TOKEN:
        return None
    # bỏ fork: lịch sử upstream không phải code của mình
    own = [r["name"] for r in list_owned_repos() if not r["fork"]]
    commits = add = dele = 0
    for c, a, d in contributor_stats(own).values():
        commits += c
        add += a
        dele += d
    return {
        "commits": commits,
        "followers": api(f"/users/{USER}")["followers"],
        "loc_add": add,
        "loc_del": dele,
    }

INFO_WIDTH = 74  # đủ chứa dòng LOC dài (số liệu hàng chục triệu)

def fmt(stats, key):
    return f"{stats[key]:,}" if stats else "??"

def twocol(v1, label2, v2, width=26):
    head = f"{v1:<4} | {label2}: "
    dots = max(width - len(head) - len(v2) - 1, 3)
    return f"{head}{'.' * dots} {v2}"

def loc_values(stats):
    if not stats:
        return "??", "??", "??"
    net = stats["loc_add"] - stats["loc_del"]
    return f"{net:,}", f"{stats['loc_add']:,}", f"{stats['loc_del']:,}"

def build_info(stats, today):
    return [
        ("HEADER", "jakeemma2012@github"),
        ("OS", "Windows 11, Ubuntu, macOS"),
        ("Uptime", calc_uptime(today)),
        ("Host", "Ho Chi Minh City, Vietnam"),
        ("Kernel", "Game Dev / Backend"),
        ("IDE", "IntelliJ IDEA, VSCode"),
        "",
        ("Languages.Programming", "Java, C#, Rust"),
        ("Languages.Computer", "JSON, YAML"),
        ("Languages.Real", "Tiếng Việt, English"),
        "",
        ("Hobbies.Software", "Game Servers, RE"),
        ("Hobbies.Hardware", "Self-hosting, VPS"),
        "",
        ("HEADER", "Contact"),
        ("Email", "tranhuuphuc.k20cva@gmail.com"),
        ("Discord", "jakeemma2012#0001"),
        "",
        ("HEADER", "GitHub Stats"),
        ("Commits", twocol(fmt(stats, "commits"), "Followers", fmt(stats, "followers"))),
        ("LOC", *loc_values(stats)),
    ]

with open(ASCII_FILE, encoding="utf-8") as f:
    art = [ln.rstrip("\n").rstrip() for ln in f]

# bỏ dòng trống đầu
while art and not art[0].strip():
    art.pop(0)
def is_solid(ln):
    s = ln.strip()
    return s != "" and set(s) <= {":", "-"}
while art and (not art[-1].strip() or is_solid(art[-1])):
    art.pop()

ART_W = max(len(l) for l in art)

# ---------- layout ----------
ART_FS, ART_LH = 11, 12
INFO_FS, INFO_LH = 14, 21
PAD = 24
CHAR_W_ART = ART_FS * 0.602
CHAR_W_INFO = INFO_FS * 0.602
ART_PX = int(ART_W * CHAR_W_ART) + 10
INFO_X = PAD + ART_PX + 30
WIDTH = INFO_X + int(INFO_WIDTH * CHAR_W_INFO) + PAD

def esc(s):
    return html.escape(s, quote=False)

def leader(label, value):
    used = len(label) + 2 + 1 + 1 + len(value)  # ". label: " + " value"
    dots = max(INFO_WIDTH - used, 3)
    return dots

def build(theme, info):
    c = THEMES[theme]
    height = PAD * 2 + max(len(art) * ART_LH, len(info) * INFO_LH)
    out = []
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" font-family="Consolas, Menlo, monospace">'
    )
    out.append(f'<rect width="100%" height="100%" fill="{c["bg"]}" rx="8"/>')

    # cột ascii
    y = PAD + ART_FS
    out.append(f'<g font-size="{ART_FS}" fill="{c["art"]}">')
    for ln in art:
        out.append(f'<text x="{PAD}" y="{y}" xml:space="preserve">{esc(ln)}</text>')
        y += ART_LH
    out.append("</g>")

    # cột info
    y = PAD + INFO_FS + 2
    out.append(f'<g font-size="{INFO_FS}" xml:space="preserve">')
    for item in info:
        if item == "":
            out.append(f'<text x="{INFO_X}" y="{y}" fill="{c["base"]}">.</text>')
        elif item[0] == "HEADER":
            title = item[1]
            bar = "─" * max(INFO_WIDTH - len(title) - 4, 3)
            out.append(
                f'<text x="{INFO_X}" y="{y}">'
                f'<tspan fill="{c["header"]}" font-weight="bold">─ {esc(title)} </tspan>'
                f'<tspan fill="{c["line"]}">{bar}</tspan></text>'
            )
        elif item[0] == "LOC":
            _, net, added, deleted = item
            label = "Lines of Code on GitHub"
            display = f"{net} ( {added}++, {deleted}-- )"
            dots = leader(label, display)
            out.append(
                f'<text x="{INFO_X}" y="{y}">'
                f'<tspan fill="{c["base"]}">. </tspan>'
                f'<tspan fill="{c["label"]}">{label}:</tspan>'
                f'<tspan fill="{c["base"]}"> {"." * dots} </tspan>'
                f'<tspan fill="{c["value"]}">{net}</tspan>'
                f'<tspan fill="{c["base"]}"> ( </tspan>'
                f'<tspan fill="{c["add"]}">{added}++</tspan>'
                f'<tspan fill="{c["base"]}">, </tspan>'
                f'<tspan fill="{c["del"]}">{deleted}--</tspan>'
                f'<tspan fill="{c["base"]}"> )</tspan></text>'
            )
        else:
            label, value = item
            dots = leader(label, value)
            out.append(
                f'<text x="{INFO_X}" y="{y}">'
                f'<tspan fill="{c["base"]}">. </tspan>'
                f'<tspan fill="{c["label"]}">{esc(label)}:</tspan>'
                f'<tspan fill="{c["base"]}"> {"." * dots} </tspan>'
                f'<tspan fill="{c["value"]}">{esc(value)}</tspan></text>'
            )
        y += INFO_LH
    out.append("</g></svg>")
    return "\n".join(out)

if __name__ == "__main__":
    stats = fetch_stats()
    if stats is None:
        print("Không có GH_PAT/GITHUB_TOKEN -> stats điền ?? (chế độ preview)")
    info = build_info(stats, datetime.now(TZ_VN).date())
    for theme in ("dark", "light"):
        fn = f"{theme}_mode.svg"
        with open(fn, "w", encoding="utf-8") as f:
            f.write(build(theme, info))
        print(f"OK -> {fn}")
    height = PAD * 2 + max(len(art) * ART_LH, len(info) * INFO_LH)
    print(f"Size: {WIDTH}x{height}px | art {len(art)} dòng x {ART_W} ký tự")
