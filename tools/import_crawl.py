# -*- coding: utf-8 -*-
"""把瀏覽器抓到的舊站資料（crawl.json）轉成 content/ 內的 JSON 檔。只在搬家時執行一次。"""
import os, re, json, sys, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = os.path.join(ROOT, "content")
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "crawl.json")
data = json.load(open(src, encoding="utf-8"))

def dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, indent=2)

for sub in ("products", "categories", "albums"):
    shutil.rmtree(os.path.join(C, sub), ignore_errors=True)

cats = data["cats"]
def full(cid, seen=()):
    c = cats.get(cid)
    if not c or cid in seen: return ""
    p = c.get("parent")
    return (full(p, seen + (cid,)) + " > " if p and p in cats else "") + (c.get("name") or "未命名")

for cid, c in cats.items():
    clean = lambda s: (s or "").replace("|", "｜").strip()
    dump(os.path.join(C, "categories", f"{cid}.json"), {
        "name": clean(c.get("name")) or "未命名分類", "full_name": full(cid), "parent": c.get("parent") or "",
        "image": c.get("image") or "", "description": "", "order": c.get("order", 9999), "hidden": False})

listed = data.get("listed", {})
featured = set(data.get("home", {}).get("featured", []))
for tid, p in data["products"].items():
    imgs = [re.sub(r"\?.*$", "", x) for x in p.get("images", []) if x]
    body = p.get("body", "")
    title = p.get("title", "").strip()
    # 商品說明第一行若只是重複商品名稱就拿掉
    lines = body.split("\n")
    if lines and lines[0].strip().startswith(title) and len(lines[0].strip()) <= len(title) + 8: lines = lines[1:]
    body = "\n".join(lines).strip()
    body = re.sub(r"\]\((https?://[^)\s]+?)\?[^)\s]*\)", r"](\1)", body)
    body = re.sub(r"!\[(title_\d+|null|undefined)\]", "![]", body)
    dump(os.path.join(C, "products", f"{tid}.json"), {
        "title": title, "category": p.get("category") or "", "price_text": p.get("price_text") or "請洽詢",
        "image": imgs[0] if imgs else "", "gallery": imgs[1:], "body": body,
        "featured": tid in featured, "published": True,
        "order": (listed.get(tid) or {}).get("order", 9999), "seo_description": "", "old_url": p.get("old_url", "")})

for aid, a in data.get("albums", {}).items():
    photos = [{"src": re.sub(r"\?.*$", "", x["src"]), "caption": x.get("caption", "")} for x in a.get("photos", [])]
    if not photos: continue
    dump(os.path.join(C, "albums", f"{aid}.json"), {"title": a.get("title") or "相簿", "cover": re.sub(r"\?.*$", "", a.get("cover") or photos[0]["src"]), "photos": photos, "order": a.get("order", 99)})

intros = data.get("intros", {})
about = intros.get("1", {})
if "好茶推薦" in about.get("body", ""): about["body"] = about["body"].split("好茶推薦")[0].rstrip()
dump(os.path.join(C, "pages", "about.json"), {"title": "仙豐故事", "body": re.sub(r"^仙豐故事\s*", "", about.get("body", "")).strip(), "gallery": [], "published": True, "seo_description": ""})
custom = intros.get("3", {})
dump(os.path.join(C, "pages", "custom.json"), {"title": "公版私用系列", "body": re.sub(r"^公版私用系列\s*", "", custom.get("body", "")).strip(), "gallery": [], "published": True, "seo_description": ""})

home = data.get("home", {})
about_body = re.sub(r"^仙豐故事\s*", "", about.get("body", "")).strip()
dump(os.path.join(C, "home.json"), {
    "lede": "茶葉禮盒、鐵罐、真空袋、提袋與茶具，從一兩到三十斤的包裝，在台中神岡一次備齊。",
    "banners": [{"image": re.sub(r"\?.*$", "", b), "alt": "仙豐茶葉包裝材料行"} for b in home.get("banners", [])],
    "featured_title": "好茶推薦", "intro_title": "仙豐的堅持",
    "intro_body": "\n\n".join(p for p in about_body.split("\n\n") if not p.startswith("![")),
})

site_fp = os.path.join(C, "site.json")
site = json.load(open(site_fp, encoding="utf-8"))
if home.get("logo"): site["logo"] = re.sub(r"\?.*$", "", home["logo"])
dump(site_fp, site)
print("商品", len(data["products"]), "分類", len(cats), "相簿", len(data.get("albums", {})))
