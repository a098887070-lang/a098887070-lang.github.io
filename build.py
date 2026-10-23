# -*- coding: utf-8 -*-
"""
仙豐茶葉包裝材料行 — 網站產生器
讀取 content/ 內的 JSON 資料，產生完整靜態網站到 public/。
只用 Python 內建模組，Cloudflare Pages 建置指令：python build.py
"""
import os, re, json, shutil, html, datetime
from urllib.parse import quote

ROOT = os.path.dirname(os.path.abspath(__file__))
C = os.path.join(ROOT, "content")
OUT = os.path.join(ROOT, "public")
STATIC = os.path.join(ROOT, "static")

def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def load_dir(name):
    d = os.path.join(C, name); items = {}
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                obj = load(os.path.join(d, fn), {}) or {}
                obj["_id"] = fn[:-5]
                items[obj["_id"]] = obj
    return items

esc = lambda s: html.escape(str(s or ""), quote=True)

# ---------- 簡易 Markdown ----------
def inline(s):
    s = esc(s)
    s = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}" loading="lazy" decoding="async">', s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: f'<a href="{m.group(2)}" rel="noopener" target="_blank">{m.group(1)}</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return s

def md(text):
    if not text: return ""
    out, para, lst = [], [], []
    def flush():
        nonlocal para, lst
        if para: out.append("<p>" + "<br>".join(para) + "</p>"); para = []
        if lst: out.append("<ul>" + "".join(f"<li>{x}</li>" for x in lst) + "</ul>"); lst = []
    for raw in str(text).replace("\r", "").split("\n"):
        line = raw.strip()
        if not line: flush(); continue
        if re.fullmatch(r"!\[[^\]]*\]\([^)\s]+\)", line):
            flush(); out.append(f'<figure>{inline(line)}</figure>'); continue
        m = re.match(r"\[youtube\]\(([^)\s]+)\)", line)
        if m:
            flush(); out.append(f'<div class="video"><iframe src="{esc(m.group(1))}" loading="lazy" allowfullscreen title="影片"></iframe></div>'); continue
        if line.startswith("#"):
            flush(); out.append(f"<h3>{inline(line.lstrip('#').strip())}</h3>"); continue
        if line.startswith("- "):
            if para: flush()
            lst.append(inline(line[2:])); continue
        if lst: flush()
        para.append(inline(raw.rstrip()))
    flush()
    return "\n".join(out)

def plain(text, n=110):
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text or "")
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[*#>\-]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return (t[:n] + "…") if len(t) > n else t

# ---------- 資料 ----------
site = load(os.path.join(C, "site.json"), {})
home = load(os.path.join(C, "home.json"), {})
cats = load_dir("categories")
prods = {k: v for k, v in load_dir("products").items() if v.get("published", True) is not False}
pages = load_dir("pages")
albums = load_dir("albums")

BASE = (site.get("base_url") or os.environ.get("SITE_URL") or os.environ.get("CF_PAGES_URL") or "").rstrip("/")
NAME = site.get("name", "仙豐茶葉包裝材料行")

def num(v, d=9999):
    try: return float(v)
    except Exception: return d

children = {}
for cid, c in cats.items():
    children.setdefault(c.get("parent") or "", []).append(cid)
for k in children: children[k].sort(key=lambda x: (num(cats[x].get("order")), cats[x].get("name", "")))

direct = {}
for pid, p in prods.items():
    direct.setdefault(p.get("category") or "", []).append(pid)
for k in direct: direct[k].sort(key=lambda x: (num(prods[x].get("order")), prods[x].get("title", "")))

def descendants(cid, seen=None):
    seen = seen or set()
    if cid in seen: return []
    seen.add(cid)
    res = list(direct.get(cid, []))
    for ch in children.get(cid, []): res += descendants(ch, seen)
    return res

count = {cid: len(descendants(cid)) for cid in cats}
visible = lambda cid: count.get(cid, 0) > 0 and cats[cid].get("hidden") is not True
tops = [c for c in children.get("", []) if visible(c)]

def chain(cid):
    out, seen = [], set()
    while cid and cid in cats and cid not in seen:
        seen.add(cid); out.insert(0, cid); cid = cats[cid].get("parent")
    return out

def first_img(p):
    imgs = [x for x in ([p.get("image")] + (p.get("gallery") or [])) if x]
    if not imgs:
        m = re.search(r"!\[[^\]]*\]\(([^)\s]+)\)", p.get("body") or "")
        if m: imgs = [m.group(1)]
    return imgs[0] if imgs else ""

def cat_img(cid):
    c = cats[cid]
    if c.get("image"): return c["image"]
    for pid in descendants(cid):
        im = first_img(prods[pid])
        if im: return im
    return ""

U = {
    "home": "/", "products": "/products/", "contact": "/contact/", "search": "/search/", "packaging": "/packaging/",
    "cat": lambda cid: f"/category/{cid}/", "prod": lambda pid: f"/product/{pid}/",
    "page": lambda s: f"/{s}/", "album": lambda a: f"/packaging/{a}/",
}

# ---------- 共用版型 ----------
LINE_URL = site.get("line_url", "")
TEL = re.sub(r"[^\d+]", "", site.get("phone", ""))

def svg(name):
    icons = {
        "line": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 3C6.5 3 2 6.6 2 11c0 3.9 3.5 7.2 8.3 7.9.3.1.8.2.9.5.1.3.1.7 0 1l-.1.9c0 .3-.2 1 .9.5 1.1-.5 5.9-3.5 8.1-6 1.5-1.6 2-3.2 2-4.8C22 6.6 17.5 3 12 3Zm-3.6 10.6H6.4c-.3 0-.5-.2-.5-.5V9.2c0-.3.2-.5.5-.5s.5.2.5.5v3.4h1.5c.3 0 .5.2.5.5s-.2.5-.5.5Zm2-.5c0 .3-.2.5-.5.5s-.5-.2-.5-.5V9.2c0-.3.2-.5.5-.5s.5.2.5.5v3.9Zm4.7 0c0 .2-.1.4-.3.5h-.2c-.2 0-.3-.1-.4-.2l-2-2.7v2.4c0 .3-.2.5-.5.5s-.5-.2-.5-.5V9.2c0-.2.1-.4.3-.5h.2c.2 0 .3.1.4.2l2 2.7V9.2c0-.3.2-.5.5-.5s.5.2.5.5v3.9Zm3.2-2.5c.3 0 .5.2.5.5s-.2.5-.5.5h-1.5v.9h1.5c.3 0 .5.2.5.5s-.2.5-.5.5h-2c-.3 0-.5-.2-.5-.5V9.2c0-.3.2-.5.5-.5h2c.3 0 .5.2.5.5s-.2.5-.5.5h-1.5v.9h1.5Z"/></svg>',
        "phone": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="1.6" d="M5 3.5h3.2l1.6 4-2 1.3a10.5 10.5 0 0 0 5.4 5.4l1.3-2 4 1.6V17A2.5 2.5 0 0 1 16 19.5 13.5 13.5 0 0 1 2.5 6 2.5 2.5 0 0 1 5 3.5Z"/></svg>',
        "search": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="m15.5 15.5 5 5" stroke="currentColor" stroke-width="1.6"/></svg>',
        "menu": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 7h18M3 12h18M3 17h18" stroke="currentColor" stroke-width="1.6"/></svg>',
    }
    return icons[name]

def menu_items():
    items = site.get("menu") or []
    if items: return items
    return [{"label": "首頁", "url": "/"}, {"label": "全部商品", "url": "/products/"}, {"label": "聯絡我們", "url": "/contact/"}]

def layout(path, title, body, desc="", image="", jsonld=None, crumbs=None, bodyclass=""):
    full_title = f"{title}｜{NAME}" if title and title != NAME else f"{NAME}｜{site.get('tagline','')}".rstrip("｜")
    desc = desc or site.get("description", "")
    canon = BASE + path if BASE else ""
    img = image or site.get("og_image") or site.get("logo") or ""
    if img and img.startswith("/") and BASE: img = BASE + img
    nav = "".join(f'<li><a href="{esc(m.get("url"))}"{" aria-current=\"page\"" if m.get("url")==path else ""}>{esc(m.get("label"))}</a></li>' for m in menu_items())
    cat_nav = "".join(f'<li><a href="{U["cat"](c)}">{esc(cats[c].get("name"))}</a></li>' for c in tops)
    ld = []
    if jsonld: ld.append(jsonld)
    if crumbs:
        ld.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, **({"item": BASE + u} if BASE else {})} for i, (n, u) in enumerate(crumbs)]})
    ld_html = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in ld)
    crumb_html = ""
    if crumbs and len(crumbs) > 1:
        crumb_html = '<nav class="crumbs" aria-label="目前位置"><ol>' + "".join(
            (f'<li><a href="{u}">{esc(n)}</a></li>' if i < len(crumbs) - 1 else f'<li aria-current="page">{esc(n)}</li>') for i, (n, u) in enumerate(crumbs)) + "</ol></nav>"
    gv = site.get("google_site_verification", "")
    ga = site.get("ga_id", "")
    ga_html = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={esc(ga)}"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag("js",new Date());gtag("config","{esc(ga)}");</script>') if ga else ""
    year = datetime.date.today().year
    return f"""<!doctype html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(desc)}">
{f'<link rel="canonical" href="{esc(canon)}">' if canon else ''}
<meta property="og:type" content="website"><meta property="og:site_name" content="{esc(NAME)}">
<meta property="og:title" content="{esc(full_title)}"><meta property="og:description" content="{esc(desc)}">
{f'<meta property="og:url" content="{esc(canon)}">' if canon else ''}{f'<meta property="og:image" content="{esc(img)}">' if img else ''}
{f'<meta name="google-site-verification" content="{esc(gv)}">' if gv else ''}
<meta name="theme-color" content="#1d2a22">
<link rel="icon" href="{esc(site.get('favicon') or '/favicon.svg')}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@500;700;900&family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/css/style.css?v={int(datetime.datetime.now().timestamp())}">
{ld_html}{ga_html}
</head>
<body class="{bodyclass}">
<a class="skip" href="#main">跳到主要內容</a>
<header class="hd">
  <div class="hd-in">
    <a class="brand" href="/" aria-label="{esc(NAME)} 首頁">
      {f'<img src="{esc(site.get("logo"))}" alt="" width="44" height="44">' if site.get('logo') else ''}
      <span class="brand-t"><b>{esc(site.get('short_name') or NAME)}</b><small>{esc(site.get('tagline',''))}</small></span>
    </a>
    <form class="sbox" action="/search/" role="search"><label class="sr" for="q">搜尋商品</label><input id="q" name="q" type="search" placeholder="搜尋商品，例如：四兩鐵罐" autocomplete="off"><button aria-label="搜尋">{svg('search')}</button></form>
    <a class="hd-line" href="{esc(LINE_URL)}" target="_blank" rel="noopener">{svg('line')}<span>LINE 詢價</span></a>
    <button class="menu-btn" aria-expanded="false" aria-controls="nav">{svg('menu')}<span class="sr">選單</span></button>
  </div>
  <nav id="nav" class="nav" aria-label="主選單"><ul class="nav-main">{nav}</ul><ul class="nav-cats">{cat_nav}</ul></nav>
</header>
<main id="main">
{crumb_html}
{body}
</main>
<footer class="ft">
  <div class="ft-in">
    <div class="ft-brand">
      <p class="ft-name">{esc(NAME)}</p>
      <p class="ft-motto">{esc(site.get('motto',''))}</p>
    </div>
    <dl class="ft-info">
      <div><dt>電話</dt><dd><a href="tel:{TEL}">{esc(site.get('phone'))}</a></dd></div>
      <div><dt>LINE</dt><dd><a href="{esc(LINE_URL)}" target="_blank" rel="noopener">{esc(site.get('line_id',''))}</a></dd></div>
      <div><dt>Email</dt><dd><a href="mailto:{esc(site.get('email'))}">{esc(site.get('email'))}</a></dd></div>
      <div><dt>地址</dt><dd><a href="https://www.google.com/maps/search/?api=1&query={quote(site.get('address',''))}" target="_blank" rel="noopener">{esc(site.get('address'))}</a></dd></div>
      <div><dt>營業時間</dt><dd>{esc(site.get('hours'))}</dd></div>
    </dl>
    <ul class="ft-cats">{cat_nav}</ul>
  </div>
  <p class="ft-copy">© {year} {esc(NAME)}{f' · <a href="{esc(site.get("facebook"))}" target="_blank" rel="noopener">Facebook 粉絲專頁</a>' if site.get('facebook') else ''}</p>
</footer>
<div class="fab" aria-label="快速聯絡">
  <a class="fab-line" href="{esc(LINE_URL)}" target="_blank" rel="noopener">{svg('line')}<span>LINE</span></a>
  <a class="fab-tel" href="tel:{TEL}">{svg('phone')}<span>撥打</span></a>
</div>
<script src="/js/site.js?v={int(datetime.datetime.now().timestamp())}" defer></script>
</body>
</html>"""

def write(path, content):
    fp = os.path.join(OUT, path.strip("/"), "index.html") if not path.endswith(".html") and not path.endswith(".xml") and not path.endswith(".txt") and not path.endswith(".json") else os.path.join(OUT, path.strip("/"))
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f: f.write(content)

def tile(pid):
    p = prods[pid]; im = first_img(p)
    return f'''<li class="tile"><a href="{U["prod"](pid)}">
<span class="tile-img">{f'<img src="{esc(im)}" alt="{esc(p.get("title"))}" loading="lazy" decoding="async">' if im else '<span class="noimg">仙豐</span>'}</span>
<span class="tile-t">{esc(p.get("title"))}</span>{f'<span class="tile-p">{esc(p.get("price_text"))}</span>' if p.get("price_text") and p.get("price_text") != "請洽詢" else ''}</a></li>'''

def grid(pids): return '<ul class="grid">' + "".join(tile(x) for x in pids) + "</ul>"

def cat_row(cid, idx=None):
    c = cats[cid]; im = cat_img(cid)
    subs = [s for s in children.get(cid, []) if visible(s)]
    sub_html = ("<span class=\"shelf-sub\">" + "、".join(esc(cats[s].get("name")) for s in subs[:8]) + "</span>") if subs else ""
    return f'''<li class="shelf-row"><a href="{U["cat"](cid)}">
<span class="shelf-name">{esc(c.get("name"))}</span>{sub_html}
<span class="shelf-n">{count[cid]} 款</span>
<span class="shelf-img">{f'<img src="{esc(im)}" alt="" loading="lazy" decoding="async">' if im else ''}</span></a></li>'''

pages_written = []
def page(path, *a, **k):
    write(path, layout(path, *a, **k)); pages_written.append(path)

# ---------- 首頁 ----------
def build_home():
    banners = [b for b in (home.get("banners") or []) if b.get("image")]
    hero_img = banners[0]["image"] if banners else ""
    featured = [pid for pid, p in prods.items() if p.get("featured")]
    featured.sort(key=lambda x: num(prods[x].get("order")))
    motto = site.get("motto_vertical") or ["採好茶", "喝好茶", "賣好茶"]
    v = "".join(f"<span>{esc(m)}</span>" for m in motto)
    slides = "".join(f'<img src="{esc(b["image"])}" alt="{esc(b.get("alt") or NAME)}" {"" if i==0 else "loading=\"lazy\""} class="{"on" if i==0 else ""}">' for i, b in enumerate(banners))
    intro = home.get("intro_body") or ""
    total = len(prods)
    body = f'''
<section class="hero">
  <div class="hero-photo">{slides}</div>
  <div class="hero-copy">
    <h1 class="hero-v" aria-label="{esc('、'.join(motto))}">{v}</h1>
    <div class="hero-side">
      <p class="hero-lede">{esc(home.get("lede") or "茶葉禮盒、鐵罐、真空袋、提袋與茶具，從一兩到三十斤的包裝，在神岡一次備齊。")}</p>
      <div class="hero-act">
        <a class="btn btn-solid" href="/products/">看全部 {total} 款商品</a>
        <a class="btn btn-line" href="{esc(LINE_URL)}" target="_blank" rel="noopener">{svg('line')} LINE 詢價</a>
      </div>
    </div>
  </div>
</section>
<section class="shelf" aria-labelledby="shelf-h">
  <div class="sec-hd"><h2 id="shelf-h">商品分類</h2><p>依包裝種類找，點進去看規格與尺寸。</p></div>
  <ul class="shelf-list">{"".join(cat_row(c) for c in tops)}</ul>
</section>
{f"""<section class="feat" aria-labelledby="feat-h"><div class="sec-hd"><h2 id="feat-h">{esc(home.get('featured_title') or '好茶推薦')}</h2></div>{grid(featured[:12])}</section>""" if featured else ''}
<section class="story">
  <div class="story-in">
    <h2>{esc(home.get("intro_title") or "仙豐的堅持")}</h2>
    <div class="prose">{md(intro)}</div>
    <a class="btn btn-line" href="/about/">閱讀仙豐故事</a>
  </div>
</section>
<section class="visit">
  <div class="visit-in">
    <h2>到店看實品</h2>
    <p class="visit-addr">{esc(site.get("address"))}</p>
    <p>{esc(site.get("hours"))}</p>
    <div class="hero-act"><a class="btn btn-solid" href="tel:{TEL}">{svg('phone')} {esc(site.get("phone"))}</a><a class="btn btn-line" href="/contact/">交通與聯絡方式</a></div>
  </div>
</section>'''
    store = {"@context": "https://schema.org", "@type": "Store", "name": NAME, "description": site.get("description"),
             "telephone": site.get("phone"), "email": site.get("email"),
             "address": {"@type": "PostalAddress", "streetAddress": site.get("street", site.get("address")), "addressLocality": site.get("locality", "神岡區"), "addressRegion": site.get("region", "台中市"), "addressCountry": "TW"},
             "openingHours": site.get("opening_hours_schema", "Mo-Fr 09:00-18:00"), "sameAs": [x for x in [site.get("facebook")] if x]}
    if BASE: store["url"] = BASE + "/"
    if site.get("logo"): store["image"] = (BASE + site["logo"]) if BASE and site["logo"].startswith("/") else site["logo"]
    page("/", NAME, body, jsonld=store, bodyclass="is-home")

# ---------- 分類 ----------
def build_categories():
    body = f'''<section class="page-hd"><h1>全部商品</h1><p>共 {len(prods)} 款，分成 {len(tops)} 大類。</p></section>
<section class="shelf"><ul class="shelf-list">{"".join(cat_row(c) for c in tops)}</ul></section>'''
    page("/products/", "全部商品", body, crumbs=[("首頁", "/"), ("全部商品", "/products/")])
    for cid, c in cats.items():
        if not visible(cid): continue
        subs = [s for s in children.get(cid, []) if visible(s)]
        mine = direct.get(cid, [])
        chips = ""
        if subs:
            chips = '<ul class="chips">' + "".join(f'<li><a href="{U["cat"](s)}">{esc(cats[s].get("name"))}<span>{count[s]}</span></a></li>' for s in subs) + "</ul>"
        parts = []
        if mine: parts.append(grid(mine))
        for s in subs:
            ps = descendants(s)
            parts.append(f'<section class="subsec"><div class="sec-hd"><h2><a href="{U["cat"](s)}">{esc(cats[s].get("name"))}</a></h2><a class="more" href="{U["cat"](s)}">全部 {len(ps)} 款</a></div>{grid(ps[:8])}</section>')
        ch = chain(cid)
        crumbs = [("首頁", "/"), ("全部商品", "/products/")] + [(cats[x].get("name"), U["cat"](x)) for x in ch]
        parent = cats.get(c.get("parent") or "", {})
        desc_txt = c.get("description") or f"{NAME}{('｜' + parent.get('name')) if parent else ''}「{c.get('name')}」共 {count[cid]} 款，歡迎來電或 LINE 詢價，台中神岡門市可看實品。"
        body = f'''<section class="page-hd"><h1>{esc(c.get("name"))}</h1><p>{esc(c.get("description") or f"共 {count[cid]} 款")}</p>{chips}</section>
<div class="wrap">{"".join(parts)}</div>'''
        page(U["cat"](cid), (f"{parent.get('name')} {c.get('name')}" if parent else c.get("name")), body, desc=desc_txt, image=cat_img(cid), crumbs=crumbs)

# ---------- 商品 ----------
def build_products():
    for pid, p in prods.items():
        imgs = [x for x in ([p.get("image")] + (p.get("gallery") or [])) if x]
        seen = set(); imgs = [x for x in imgs if not (x in seen or seen.add(x))]
        cid = p.get("category")
        ch = chain(cid)
        crumbs = [("首頁", "/"), ("全部商品", "/products/")] + [(cats[x].get("name"), U["cat"](x)) for x in ch] + [(p.get("title"), U["prod"](pid))]
        main_img = imgs[0] if imgs else ""
        thumbs = "".join(f'<li><button type="button" data-src="{esc(x)}" aria-label="看第 {i+1} 張"{" aria-current=\"true\"" if i==0 else ""}><img src="{esc(x)}" alt="" loading="lazy"></button></li>' for i, x in enumerate(imgs)) if len(imgs) > 1 else ""
        siblings = [x for x in direct.get(cid, []) if x != pid][:8]
        msg = f"您好，想詢問「{p.get('title')}」的價格與數量。"
        desc = p.get("seo_description") or plain(p.get("body")) or f"{p.get('title')}，{NAME}，歡迎來電或 LINE 詢價。"
        body = f'''<article class="pd">
<div class="pd-media">
  <figure class="pd-main">{f'<img id="pd-img" src="{esc(main_img)}" alt="{esc(p.get("title"))}">' if main_img else '<span class="noimg">仙豐</span>'}</figure>
  {f'<ul class="pd-thumbs">{thumbs}</ul>' if thumbs else ''}
</div>
<div class="pd-info">
  {f'<a class="pd-cat" href="{U["cat"](cid)}">{esc(cats[cid].get("name"))}</a>' if cid in cats else ''}
  <h1>{esc(p.get("title"))}</h1>
  <p class="pd-price">{esc(p.get("price_text") or "請洽詢")}</p>
  {f'<div class="prose pd-body">{md(p.get("body"))}</div>' if (p.get("body") or "").strip() else ''}
  <div class="pd-act">
    <a class="btn btn-solid" href="{esc(LINE_URL)}" target="_blank" rel="noopener" data-copy="{esc(msg)}">{svg('line')} 用 LINE 詢價</a>
    <a class="btn btn-line" href="tel:{TEL}">{svg('phone')} {esc(site.get("phone"))}</a>
  </div>
</div>
</article>
{f'<section class="related"><div class="sec-hd"><h2>同類商品</h2><a class="more" href="{U["cat"](cid)}">看全部</a></div>{grid(siblings)}</section>' if siblings else ''}'''
        page(U["prod"](pid), p.get("title"), body, desc=desc, image=main_img, crumbs=crumbs)

# ---------- 頁面 / 相簿 / 聯絡 / 搜尋 ----------
def build_pages():
    for slug, pg in pages.items():
        if pg.get("published", True) is False: continue
        gal = "".join(f'<li><img src="{esc(x)}" alt="" loading="lazy"></li>' for x in (pg.get("gallery") or []))
        body = f'''<section class="page-hd"><h1>{esc(pg.get("title"))}</h1></section>
<div class="wrap narrow prose">{md(pg.get("body")) or '<p>內容整理中，歡迎直接來電或 LINE 詢問。</p>'}</div>
{f'<ul class="gallery wrap">{gal}</ul>' if gal else ''}'''
        page(U["page"](slug), pg.get("title"), body, desc=pg.get("seo_description") or plain(pg.get("body")), crumbs=[("首頁", "/"), (pg.get("title"), U["page"](slug))])

    al = sorted(albums.values(), key=lambda a: num(a.get("order")))
    al = [a for a in al if a.get("photos")]
    rows = "".join(f'''<li class="tile"><a href="{U["album"](a["_id"])}"><span class="tile-img"><img src="{esc(a.get("cover") or a["photos"][0].get("src"))}" alt="" loading="lazy"></span><span class="tile-t">{esc(a.get("title"))}</span><span class="tile-p">{len(a["photos"])} 張</span></a></li>''' for a in al)
    page("/packaging/", "茶葉包裝耗材", f'<section class="page-hd"><h1>茶葉包裝耗材</h1><p>鐵罐、紙盒、真空袋、提袋、脫氧劑等實品照片，依類別整理。</p></section><div class="wrap"><ul class="grid">{rows}</ul></div>', crumbs=[("首頁", "/"), ("茶葉包裝耗材", "/packaging/")])
    for a in al:
        ph = "".join(f'<li><figure><img src="{esc(x.get("src"))}" alt="{esc(x.get("caption") or a.get("title"))}" loading="lazy">{f"<figcaption>{esc(x.get("caption"))}</figcaption>" if x.get("caption") else ""}</figure></li>' for x in a["photos"])
        page(U["album"](a["_id"]), f'{a.get("title")}｜茶葉包裝耗材', f'<section class="page-hd"><h1>{esc(a.get("title"))}</h1><p>{len(a["photos"])} 張實品照片，點圖可放大。</p></section><ul class="gallery wrap">{ph}</ul>',
             crumbs=[("首頁", "/"), ("茶葉包裝耗材", "/packaging/"), (a.get("title"), U["album"](a["_id"]))])

    addr = site.get("address", "")
    body = f'''<section class="page-hd"><h1>聯絡我們</h1><p>報價、樣品、客製印刷都可以先 LINE 傳照片給我們。</p></section>
<div class="wrap contact">
  <dl class="contact-list">
    <div><dt>電話</dt><dd><a href="tel:{TEL}">{esc(site.get("phone"))}</a></dd></div>
    <div><dt>LINE</dt><dd><a href="{esc(LINE_URL)}" target="_blank" rel="noopener">{esc(site.get("line_id"))}</a></dd></div>
    <div><dt>Email</dt><dd><a href="mailto:{esc(site.get("email"))}">{esc(site.get("email"))}</a></dd></div>
    <div><dt>地址</dt><dd>{esc(addr)}</dd></div>
    <div><dt>營業時間</dt><dd>{esc(site.get("hours"))}</dd></div>
  </dl>
  <div class="map"><iframe title="{esc(NAME)} 地圖" loading="lazy" src="https://www.google.com/maps?q={quote(addr)}&output=embed"></iframe></div>
</div>'''
    page("/contact/", "聯絡我們", body, crumbs=[("首頁", "/"), ("聯絡我們", "/contact/")])

    idx = [{"t": p.get("title"), "u": U["prod"](pid), "i": first_img(p), "c": cats.get(p.get("category"), {}).get("name", "")} for pid, p in prods.items()]
    write("/search.json", json.dumps(idx, ensure_ascii=False))
    page("/search/", "搜尋商品", '<section class="page-hd"><h1 id="s-h">搜尋商品</h1><p id="s-n">輸入商品名稱、容量或材質。</p></section><div class="wrap"><ul class="grid" id="s-res"></ul></div>', bodyclass="is-search")

    write("/404.html", layout("/404.html", "找不到這個頁面", '<section class="page-hd"><h1>找不到這個頁面</h1><p>網址可能已更換。可以從商品分類重新找，或直接 LINE 問我們。</p><div class="hero-act"><a class="btn btn-solid" href="/products/">看全部商品</a></div></section>'))

def build_seo():
    today = datetime.date.today().isoformat()
    if BASE:
        urls = "".join(f"<url><loc>{esc(BASE + u)}</loc><lastmod>{today}</lastmod></url>" for u in pages_written if u != "/search/")
        write("/sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    write("/robots.txt", "User-agent: *\nDisallow: /admin/\nDisallow: /search/\n" + (f"Sitemap: {BASE}/sitemap.xml\n" if BASE else ""))

def build_admin():
    tpl = os.path.join(STATIC, "admin", "config.yml")
    if os.path.exists(tpl):
        with open(tpl, encoding="utf-8") as f: txt = f.read()
        txt = txt.replace("__GITHUB_REPO__", site.get("github_repo") or "YOUR-NAME/xianfeng-site")
        os.makedirs(os.path.join(OUT, "admin"), exist_ok=True)
        with open(os.path.join(OUT, "admin", "config.yml"), "w", encoding="utf-8") as f: f.write(txt)

def main():
    if os.path.isdir(OUT): shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT)
    build_home(); build_categories(); build_products(); build_pages(); build_seo(); build_admin()
    print(f"完成：{len(pages_written)} 頁，商品 {len(prods)}，分類 {sum(1 for c in cats if visible(c))}，相簿 {len(albums)}；網址 {BASE or '(尚未設定 base_url)'}")

if __name__ == "__main__":
    main()
