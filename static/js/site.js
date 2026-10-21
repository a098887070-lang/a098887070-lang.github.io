(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // 手機選單
  var mb = $(".menu-btn"), nav = $("#nav");
  if (mb && nav) mb.addEventListener("click", function () {
    var open = nav.classList.toggle("open");
    mb.setAttribute("aria-expanded", open ? "true" : "false");
  });

  // 首頁輪播
  var slides = $$(".hero-photo img");
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (slides.length > 1 && !reduce) {
    var i = 0;
    setInterval(function () {
      slides[i].classList.remove("on");
      i = (i + 1) % slides.length;
      slides[i].classList.add("on");
    }, 6000);
  }

  // 商品圖切換
  var main = $("#pd-img");
  $$(".pd-thumbs button").forEach(function (b) {
    b.addEventListener("click", function () {
      if (!main) return;
      main.src = b.getAttribute("data-src");
      $$(".pd-thumbs button").forEach(function (x) { x.removeAttribute("aria-current"); });
      b.setAttribute("aria-current", "true");
    });
  });

  // 燈箱
  function lightbox(src, alt) {
    var d = document.createElement("div");
    d.className = "lb"; d.setAttribute("role", "dialog"); d.setAttribute("aria-label", "放大圖片");
    var im = new Image(); im.src = src; im.alt = alt || "";
    d.appendChild(im); document.body.appendChild(d);
    requestAnimationFrame(function () { d.classList.add("on"); });
    function close() { d.remove(); document.removeEventListener("keydown", key); }
    function key(e) { if (e.key === "Escape") close(); }
    d.addEventListener("click", close); document.addEventListener("keydown", key);
  }
  document.addEventListener("click", function (e) {
    var t = e.target;
    if (t.tagName === "IMG" && (t.closest(".pd-main") || t.closest(".gallery") || t.closest(".pd-body"))) {
      lightbox(t.currentSrc || t.src, t.alt);
    }
  });

  // LINE 詢價：先複製詢價訊息
  $$("a[data-copy]").forEach(function (a) {
    a.addEventListener("click", function () {
      var msg = a.getAttribute("data-copy") + "\n" + location.href;
      if (navigator.clipboard) navigator.clipboard.writeText(msg).then(function () { toast("已複製詢價訊息，開啟 LINE 後貼上即可"); }).catch(function () {});
    });
  });
  function toast(text) {
    var t = document.createElement("div");
    t.textContent = text;
    t.style.cssText = "position:fixed;left:50%;bottom:24px;transform:translateX(-50%);background:#1d2a22;color:#eef1ec;padding:12px 20px;border-radius:999px;z-index:120;font-size:15px";
    document.body.appendChild(t); setTimeout(function () { t.remove(); }, 3200);
  }

  // 搜尋
  if (document.body.classList.contains("is-search")) {
    var q = (new URLSearchParams(location.search).get("q") || "").trim();
    var inp = $("#q"); if (inp) inp.value = q;
    var res = $("#s-res"), n = $("#s-n"), h = $("#s-h");
    if (q) {
      h.textContent = "「" + q + "」的搜尋結果";
      fetch("/search.json").then(function (r) { return r.json(); }).then(function (all) {
        var words = q.toLowerCase().split(/\s+/);
        var hit = all.filter(function (x) { var s = (x.t + " " + x.c).toLowerCase(); return words.every(function (w) { return s.indexOf(w) > -1; }); });
        n.textContent = hit.length ? "找到 " + hit.length + " 款商品" : "找不到符合的商品。換個關鍵字，或直接 LINE 問我們。";
        res.innerHTML = hit.slice(0, 200).map(function (x) {
          var e = function (s) { return String(s || "").replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
          return '<li class="tile"><a href="' + e(x.u) + '"><span class="tile-img">' + (x.i ? '<img src="' + e(x.i) + '" alt="" loading="lazy">' : "") + '</span><span class="tile-t">' + e(x.t) + '</span><span class="tile-p">' + e(x.c) + "</span></a></li>";
        }).join("");
      });
    }
  }
})();
