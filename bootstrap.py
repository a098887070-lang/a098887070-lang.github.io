# -*- coding: utf-8 -*-
"""一次性：從舊站補抓每項商品的「產品詳情」（編號、尺寸）與附加圖片，寫回 content/products。執行完自動刪除。"""
import os, re, sys, json, time, subprocess, urllib.request
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "beautifulsoup4"])
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = os.path.dirname(os.path.abspath(__file__))
PD = os.path.join(ROOT, "content", "products")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126 Safari/537.36"}

def get(url, tries=8):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                b = r.read().decode("utf-8", "replace")
            if len(b) > 5000:
                time.sleep(0.8); return b
        except Exception:
            pass
        time.sleep(4 * (k + 1))
    return None

def exists(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA, method="HEAD"), timeout=20) as r:
            return r.status == 200
    except Exception:
        return False

def text_of(node):
    out = []
    def walk(n):
        if isinstance(n, NavigableString):
            if n.__class__.__name__ in ("Comment",): return
            out.append(re.sub(r"[ \t\r\n]+", " ", str(n))); return
        if not isinstance(n, Tag): return
        if n.name in ("script", "style", "button", "form", "input", "select", "h4"): return
        if n.name == "br": out.append("\n"); return
        block = n.name in ("p", "div", "li", "tr", "table", "ul", "ol")
        hi = "background" in (n.get("style") or "") or n.name in ("strong", "b")
        if block: out.append("\n")
        s = len(out)
        for c in n.children: walk(c)
        if hi and "".join(out[s:]).strip(): out.insert(s, "**"); out.append("**")
        if block: out.append("\n")
    walk(node)
    lines = [l.strip() for l in "".join(out).replace("****", "").split("\n")]
    return "\n".join(l for l in lines if l and l != "****")

done = fixed = imgs_added = 0
files = sorted(f for f in os.listdir(PD) if f.endswith(".json"))
for i, fn in enumerate(files, 1):
    fp = os.path.join(PD, fn)
    p = json.load(open(fp, encoding="utf-8"))
    url = p.get("old_url")
    if not url: continue
    html = get(url)
    if not html: print("讀不到", url); continue
    soup = BeautifulSoup(html, "html.parser")
    pic = soup.select_one(".product_detail_picture")
    row = pic.find_parent(class_="sm-product-detail") if pic else None
    cols = [c for c in row.find_all(recursive=False)] if row else []
    changed = False
    if len(cols) > 1:
        spec = text_of(cols[1])
        body = p.get("body") or ""
        if spec and spec.replace("**", "")[:20] not in body.replace("**", ""):
            p["body"] = (spec + ("\n\n" + body if body else "")).strip(); changed = True; fixed += 1
    gallery = list(p.get("gallery") or [])
    have = set([p.get("image")] + gallery)
    for im in (row.select("img.product_spec_picture, .product_spec_picture img") if row else []):
        src = (im.get("src") or "").strip().split("?")[0]
        if not src or "/title_" in src: continue
        full = src.replace("_thumb.", ".")
        use = full if exists(full) else src
        if use not in have:
            gallery.append(use); have.add(use); imgs_added += 1; changed = True
    if changed:
        p["gallery"] = gallery
        with open(fp, "w", encoding="utf-8") as f: json.dump(p, f, ensure_ascii=False, indent=2)
    done += 1
    if i % 50 == 0: print(f"{i}/{len(files)}：補上詳情 {fixed}、附加圖片 {imgs_added}", flush=True)

print(f"完成：處理 {done} 項，補上產品詳情 {fixed} 項，附加圖片 {imgs_added} 張")
os.remove(os.path.abspath(__file__))
