# -*- coding: utf-8 -*-
"""從舊站 tea025.smartweb.tw 抓取全部分類、商品、相簿與介紹頁，輸出 crawl.json。
舊站有流量限制，程式會自動放慢與重試。用法：python tools/crawl_old_site.py [輸出檔]"""
import os, re, sys, json, time, urllib.request
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from bs4 import BeautifulSoup, NavigableString, Tag

SITE = "https://tea025.smartweb.tw"
BASE_HREF = SITE + "/template/c30/1181/zh-TW/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36", "Accept-Language": "zh-TW,zh;q=0.9"}
DELAY = float(os.environ.get("CRAWL_DELAY", "0.8"))

def log(*a): print(*a, flush=True)

def get(path, tries=8):
    url = path if path.startswith("http") else SITE + path
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                body = r.read().decode("utf-8", "replace"); st = r.status
            if st == 200 and len(body) > 5000:
                time.sleep(DELAY); return body
            wait = 4 * (k + 1)
        except Exception as e:
            wait = 4 * (k + 1)
        time.sleep(wait)
    raise IOError("抓取失敗：" + url)

def q(href):
    return {k: v[0] for k, v in parse_qs(urlparse(href).query).items()}

def absu(s):
    s = (s or "").strip()
    return urljoin(BASE_HREF, s) if s else ""

def md(node):
    out = []
    def walk(n):
        if isinstance(n, NavigableString):
            if n.__class__.__name__ in ("Comment", "Doctype"): return
            out.append(re.sub(r"[ \t\r\n]+", " ", str(n))); return
        if not isinstance(n, Tag): return
        t = n.name.upper()
        if t in ("SCRIPT", "STYLE", "NOSCRIPT", "BUTTON", "FORM", "INPUT", "SELECT"): return
        if t == "IFRAME":
            s = n.get("src") or ""
            if "youtube" in s: out.append("\n[youtube](" + absu(s) + ")\n")
            return
        if t == "IMG":
            s = absu(n.get("src"))
            if re.search(r"space\.gif|/template/", s): return
            alt = (n.get("alt") or n.get("title") or "")
            alt = "" if alt == "null" else alt.replace("[", "").replace("]", "")
            out.append("\n![" + alt + "](" + s + ")\n"); return
        if t == "BR": out.append("\n"); return
        block = t in ("P", "DIV", "TR", "LI", "H1", "H2", "H3", "H4", "H5", "H6", "TABLE", "UL", "OL", "SECTION")
        if block: out.append("\n")
        if t == "LI": out.append("- ")
        if re.fullmatch(r"H[1-6]", t): out.append("### ")
        bold = t in ("STRONG", "B")
        if bold: out.append("**")
        start = len(out)
        for c in n.children: walk(c)
        if t == "A":
            href = n.get("href") or ""
            txt = "".join(out[start:]).strip()
            if re.match(r"^https?:", href) and "smartweb.tw" not in href and txt and "![" not in txt:
                del out[start:]; out.append("[" + txt + "](" + href + ")")
        if t in ("TD", "TH"): out.append("　")
        if bold: out.append("**")
        if block: out.append("\n")
    walk(node)
    s = "".join(out)
    s = re.sub(r"\*\*\s*\*\*", "", s)
    s = "\n".join(l.rstrip().lstrip(" ") for l in s.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", s).strip()

C = {"cats": {}, "products": {}, "listed": {}, "albums": {}, "intros": {}, "home": {}}
order = [0]

def see_cat(cid, name, mn):
    if not cid: return
    c = C["cats"].setdefault(cid, {"id": cid, "name": "", "parent": None, "image": "", "mn": mn, "order": order[0]})
    if c["order"] == order[0]: order[0] += 1
    if name and not c["name"]: c["name"] = name.strip()

def apply_crumbs(soup):
    prev = None; mn = None
    for a in soup.select(".site_location a"):
        p = q(a.get("href", "")); mn = p.get("mn", mn); cid = p.get("catid")
        if p.get("module") == "product" and not cid and not p.get("tid") and mn and mn != "1":
            see_cat("mn" + mn, a.get_text(strip=True), mn); prev = "mn" + mn; continue
        if cid:
            see_cat(cid, a.get_text(strip=True), mn)
            if prev and prev != cid and not C["cats"][cid]["parent"]: C["cats"][cid]["parent"] = prev
            prev = cid
    return prev

def main_el(soup):
    return soup.select_one("#main-content-main") or soup.select_one("#main-content") or soup.body

def og(soup, k):
    m = soup.find("meta", attrs={"property": "og:" + k})
    return (m.get("content") if m else "") or ""

def max_page(M):
    mp = 1
    for a in M.select('a[href*="page="]'):
        try: mp = max(mp, int(q(a["href"]).get("page", 1)))
        except Exception: pass
    return mp

def parse_product(path, html):
    soup = BeautifulSoup(html, "html.parser"); p = q(path); tid = p.get("tid")
    title = og(soup, "title").split("::")[-1].strip()
    if not title or "下架" in (soup.title.get_text() if soup.title else ""): return
    leaf = apply_crumbs(soup); M = main_el(soup)
    h4 = M.find("h4"); h4t = h4.get_text(strip=True) if h4 else ""
    price = h4t[len(title):].strip() if h4t.startswith(title) else ""
    pics = []
    for i in soup.select(".product_detail_picture img, #product_main_pic img"):
        s = absu(i.get("src"))
        if s and s not in pics: pics.append(s)
    b = soup.select_one("#product_all_content")
    C["products"][tid] = {"id": tid, "title": title, "price_text": price or "請洽詢",
        "category": leaf or (C["listed"].get(tid) or {}).get("cat") or ("mn" + p.get("mn", "1")),
        "images": pics or ([og(soup, "image")] if og(soup, "image") else []), "body": md(b) if b else "",
        "old_url": SITE + path, "mn": p.get("mn")}

def nav_cats(soup):
    for a in soup.select('a[href*="catid="]'):
        p = q(a.get("href", ""))
        if p.get("module") == "product" and p.get("catid") and not p.get("tid"):
            see_cat(p["catid"], a.get_text(strip=True), p.get("mn"))

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "crawl.json"
    log("讀取首頁…")
    home = BeautifulSoup(get("/"), "html.parser"); nav_cats(home)
    C["home"] = {"banners": [absu(i.get("src")) for i in home.find_all("img") if "/ad/" in absu(i.get("src"))],
                 "logo": next((absu(i.get("src")) for i in home.find_all("img") if "logo" in (i.get("src") or "")), ""),
                 "featured": [q(a["href"]).get("tid") for a in home.select('a[href*="f=content"]') if q(a["href"]).get("tid")]}
    # 分類總覽（全部商品、隨身包）
    for mn in ("1", "2"):
        s = BeautifulSoup(get(f"/index.php?module=product&mn={mn}"), "html.parser"); nav_cats(s); M = main_el(s)
        title = og(s, "title").split("::")[-1].strip()
        for a in M.select('a[href*="catid="]'):
            c = q(a["href"]).get("catid"); see_cat(c, a.get_text(strip=True), mn)
            img = a.find("img")
            if img and "space.gif" not in (img.get("src") or ""): C["cats"][c]["image"] = absu(img.get("src"))
            if mn != "1":
                see_cat("mn" + mn, title, mn)
                if not C["cats"][c]["parent"]: C["cats"][c]["parent"] = "mn" + mn
    # 逐一分類、逐頁
    need = []
    seen_cat = set()
    while True:
        todo = [c for c in C["cats"] if c.isdigit() and c not in seen_cat]
        if not todo: break
        for cid in todo:
            seen_cat.add(cid); mn = C["cats"][cid].get("mn") or "1"; page, mp = 1, 1
            while page <= mp:
                path = f"/index.php?module=product&mn={mn}&catid={cid}" + (f"&page={page}" if page > 1 else "")
                try:
                    s = BeautifulSoup(get(path), "html.parser")
                except IOError as e:
                    log(e); break
                apply_crumbs(s); M = main_el(s); mp = max(mp, max_page(M))
                i = 0; new_on_page = 0
                for a in M.select('a[href*="f=content"]'):
                    t = q(a["href"]).get("tid")
                    if not t: continue
                    if t not in C["listed"]:
                        C["listed"][t] = {"cat": cid, "order": page * 1000 + i}; i += 1; new_on_page += 1
                        need.append(f"/index.php?module=product&mn={mn}&f=content&tid={t}")
                for a in M.select('a[href*="catid="]'):
                    c = q(a["href"]).get("catid"); img = a.find("img")
                    if c and c not in C["cats"]: see_cat(c, a.get_text(strip=True), mn)
                    if c and img and "space.gif" not in (img.get("src") or ""): C["cats"][c]["image"] = absu(img.get("src"))
                if page == mp and new_on_page >= 10: mp += 1  # 分頁列只顯示附近頁碼時，繼續往下一頁試
                page += 1
            log(f"分類 {C['cats'][cid]['name']}：累計商品 {len(need)}")
    # 商品
    for k, path in enumerate(need, 1):
        try: parse_product(path, get(path))
        except IOError as e: log(e)
        if k % 50 == 0: log(f"商品 {k}/{len(need)}")
    # 介紹頁
    for mn in ("1", "3"):
        s = BeautifulSoup(get(f"/index.php?module=intro&mn={mn}"), "html.parser"); M = main_el(s)
        for x in M.select(".site_location"): x.decompose()
        C["intros"][mn] = {"title": og(s, "title").split("::")[-1].strip(), "body": md(M)}
    # 相簿
    s = BeautifulSoup(get("/index.php?module=photo&mn=1"), "html.parser"); M = main_el(s)
    for k, a in enumerate(M.select('a[href*="Aid="]')):
        aid = q(a["href"]).get("Aid")
        if not aid or aid in C["albums"]: continue
        box = a.find_parent(class_="album")
        name = box.select_one(".album_name") if box else None
        info = box.select_one(".album_info") if box else None
        total = re.search(r"(\d+)\s*/", info.get_text()) if info else None
        img = a.find("img")
        C["albums"][aid] = {"id": aid, "title": name.get_text(strip=True) if name else "", "order": k, "photos": [],
                            "cover": absu(img.get("src")).split("?")[0] if img else "", "total": int(total.group(1)) if total else 0}
    for aid, al in C["albums"].items():
        page = 1
        while page <= 60:
            path = f"/index.php?module=photo&mn=1&f=plist&Aid={aid}&first=1" + (f"&page={page}" if page > 1 else "")
            try: s = BeautifulSoup(get(path), "html.parser")
            except IOError as e: log(e); break
            M = main_el(s); before = len(al["photos"])
            for i in M.find_all("img"):
                src = absu(i.get("src"))
                if "/photo/" in src:
                    clean = src.split("?")[0]
                    if not any(x["src"] == clean for x in al["photos"]):
                        al["photos"].append({"src": clean, "caption": (i.get("alt") or i.get("title") or "").strip()})
            if len(al["photos"]) == before or (al.get("total") and len(al["photos"]) >= al["total"]): break
            page += 1
        log(f"相簿 {al['title']}：{len(al['photos'])} 張")
    with open(out, "w", encoding="utf-8") as f: json.dump(C, f, ensure_ascii=False)
    log(f"完成：商品 {len(C['products'])}、分類 {len(C['cats'])}、相簿 {len(C['albums'])}")

if __name__ == "__main__":
    main()
