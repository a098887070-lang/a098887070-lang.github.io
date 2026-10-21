# -*- coding: utf-8 -*-
"""第一次上傳時使用：把放在根目錄的檔案搬到正確資料夾，並匯入舊站資料。執行完會自動刪除自己。"""
import os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
MOVE = {
    "style.css": "static/css/style.css",
    "site.js": "static/js/site.js",
    "admin-index.html": "static/admin/index.html",
    "admin-config.yml": "static/admin/config.yml",
    "favicon.svg": "static/favicon.svg",
    "migrate_images.py": "tools/migrate_images.py",
    "import_crawl.py": "tools/import_crawl.py",
    "crawl_old_site.py": "tools/crawl_old_site.py",
    "site.json": "content/site.json",
    "gitignore.txt": ".gitignore",
}
for src, dst in MOVE.items():
    s = os.path.join(ROOT, src)
    if os.path.exists(s):
        d = os.path.join(ROOT, dst)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.move(s, d)
        print("搬移", src, "→", dst)
os.makedirs(os.path.join(ROOT, "static", "uploads"), exist_ok=True)
open(os.path.join(ROOT, "static", "uploads", ".keep"), "w").close()
crawl = os.path.join(ROOT, "crawl.json")
if not os.path.exists(crawl):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "beautifulsoup4"])
    subprocess.check_call([sys.executable, os.path.join(ROOT, "tools", "crawl_old_site.py"), crawl])
if os.path.exists(crawl):
    subprocess.check_call([sys.executable, os.path.join(ROOT, "tools", "import_crawl.py"), crawl])
    os.remove(crawl)
os.remove(os.path.abspath(__file__))
print("初始化完成")
