# -*- coding: utf-8 -*-
"""把 content/ 內仍指向舊站（smartweb）的圖片下載到 static/uploads/，並改成本站網址。
可重複執行：已搬過的不會重下；下載失敗的保留原網址，下次再試。"""
import os, re, json, time, hashlib, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
UP = os.path.join(ROOT, "static", "uploads")
PAT = re.compile(r"https?://(?:picture\.smartweb\.tw|tea025\.smartweb\.tw)/[^\s\"')\]]+?\.(?:jpe?g|png|gif|webp|svg)(?:\?[^\s\"')\]]*)?", re.I)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36", "Referer": "https://tea025.smartweb.tw/"}

def local_path(url):
    clean = url.split("?")[0]
    path = clean.split("smartweb.tw/", 1)[1]
    parts = [p for p in path.split("/") if p]
    sub = "misc"
    for key in ("prod", "photo", "intro", "ad", "layout", "logo"):
        if key in parts: sub = key; break
    name = re.sub(r"[^\w.\-]", "_", parts[-1]) or hashlib.md5(clean.encode()).hexdigest()[:10] + ".jpg"
    if "template" in parts: name = "site-" + name
    return sub, name

def fetch(url, dest):
    clean = url.split("?")[0]
    for k in range(4):
        try:
            req = urllib.request.Request(clean, headers=UA)
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
            if len(data) < 100: raise IOError("檔案太小")
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f: f.write(data)
            return True
        except Exception as e:
            err = e; time.sleep(2 * (k + 1))
    print("  失敗：", clean, err)
    return False

def main():
    files = []
    for d, _, fs in os.walk(CONTENT):
        files += [os.path.join(d, f) for f in fs if f.endswith(".json")]
    urls = set()
    texts = {}
    for fp in files:
        with open(fp, encoding="utf-8") as f: t = f.read()
        texts[fp] = t
        urls.update(PAT.findall(t))
    if not urls:
        print("沒有需要搬移的舊站圖片。"); return
    mapping, todo = {}, []
    used = {}
    for u in sorted(urls):
        sub, name = local_path(u)
        key = f"{sub}/{name}"
        clean = u.split("?")[0]
        if key in used and used[key] != clean:
            base, ext = os.path.splitext(name)
            name = f"{base}-{hashlib.md5(clean.encode()).hexdigest()[:6]}{ext}"; key = f"{sub}/{name}"
        used[key] = clean
        dest = os.path.join(UP, sub, name)
        mapping[u] = (f"/uploads/{key}", dest)
        if not os.path.exists(dest): todo.append((u, dest))
    print(f"舊站圖片 {len(urls)} 張，需下載 {len(todo)} 張…")
    ok = set(u for u in urls if os.path.exists(mapping[u][1]))
    with ThreadPoolExecutor(6) as ex:
        for (u, dest), res in zip(todo, ex.map(lambda x: fetch(*x), todo)):
            if res: ok.add(u)
    changed = 0
    for fp, t in texts.items():
        nt = PAT.sub(lambda m: mapping[m.group(0)][0] if m.group(0) in ok else m.group(0), t)
        if nt != t:
            with open(fp, "w", encoding="utf-8") as f: f.write(nt)
            changed += 1
    print(f"完成：成功 {len(ok)}／{len(urls)} 張，更新 {changed} 個資料檔。")

if __name__ == "__main__":
    main()
