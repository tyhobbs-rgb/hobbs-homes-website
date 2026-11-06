#!/usr/bin/env python3
"""Builds blog/index.html and blog/<slug>.html from _blog-src/posts/*.json.

Run from the repo root:  python3 -I _blog-src/build_blog.py
Styles, header and footer are copied from tips.html so the blog always matches
the rest of the site. Logos live in /assets (extracted once from tips.html).
"""
import json, re, html, glob, os, datetime, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://hobbshomesmt.com"
os.chdir(ROOT)

tips = open("tips.html", encoding="utf-8").read()
css = re.search(r"<style>(.*?)</style>", tips, re.S).group(1)
# drop the photo banner background (base64 jpeg) and the old banner rules we replace
css = re.sub(r"\.banner \{.*?\n  \}\n", "", css, count=1, flags=re.S)
css = re.sub(r"url\('data:[^']+'\)", "none", css)

BLOG_CSS = """
  /* Blog */
  .blog-hero { background: var(--black); padding: 88px 0 80px; }
  .blog-hero p.eyebrow { color: #C9A0AF; font-family: 'Playfair Display', serif; font-style: italic; font-size: 16px; margin-bottom: 12px; }
  .blog-hero h1 { color: #fff; font-size: 44px; max-width: 760px; }
  .blog-hero p.sub { color: #B8B4A9; font-size: 18px; max-width: 620px; margin-top: 18px; }
  .post-list { padding: 70px 0 90px; }
  .post-card { display: block; padding: 34px 0; border-bottom: 1px solid var(--stone-line); max-width: 820px; }
  .post-card:first-child { border-top: 1px solid var(--stone-line); }
  .post-card .meta, .post-meta { font-size: 13.5px; color: var(--text-soft); letter-spacing: 0.02em; }
  .post-card .meta .cat, .post-meta .cat { color: var(--maroon); font-weight: 600; text-transform: uppercase; font-size: 12.5px; letter-spacing: 0.05em; }
  .post-card h2 { font-size: 29px; margin: 10px 0 12px; transition: color .2s; }
  .post-card:hover h2 { color: var(--maroon); }
  .post-card p.excerpt { font-size: 16.5px; color: var(--text-soft); max-width: 680px; }
  .post-card .more { display: inline-block; margin-top: 14px; color: var(--maroon); font-weight: 500; font-size: 15px; }
  .cadence { max-width: 820px; margin-top: 40px; font-size: 15.5px; color: var(--text-soft); }

  .post-head { padding: 72px 0 8px; }
  .post-head .narrow, .post-body .narrow { max-width: 740px; margin: 0 auto; padding: 0 28px; }
  .post-head p.eyebrow { color: var(--maroon); font-family: 'Playfair Display', serif; font-style: italic; font-size: 16px; margin-bottom: 12px; }
  .post-head h1 { font-size: 42px; margin-bottom: 20px; }
  .post-body { padding: 30px 0 80px; }
  .post-body p { font-size: 18px; color: #2B2926; margin-bottom: 22px; line-height: 1.7; }
  .post-body h2 { font-size: 29px; margin: 48px 0 16px; }
  .post-body a.inline { color: var(--maroon); border-bottom: 1px solid var(--maroon); }
  .bottom-line-box { background: var(--stone); border-left: 4px solid var(--maroon); padding: 24px 28px; margin: 28px 0 38px; }
  .bottom-line-box .label, .callout .label { font-size: 12.5px; text-transform: uppercase; letter-spacing: 0.07em; font-weight: 600; color: var(--maroon); margin-bottom: 8px; }
  .bottom-line-box p { margin: 0; font-size: 18.5px; font-family: 'Playfair Display', serif; color: var(--black); line-height: 1.5; }
  .callout { background: var(--black); padding: 28px 32px; margin: 38px 0; }
  .callout .label { color: #C9A0AF; }
  .callout p { color: #F0EDE1; font-size: 17.5px; margin: 0; }
  .callout.gutcheck { background: var(--cream); border: 1px solid var(--black); }
  .callout.gutcheck .label { color: var(--maroon); }
  .callout.gutcheck p { color: var(--black); margin-bottom: 14px; }
  .callout.gutcheck p:last-child { margin-bottom: 0; }
  .numbers { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0; margin: 38px 0; border-top: 1px solid var(--black); border-bottom: 1px solid var(--stone-line); }
  .numbers > div { padding: 22px 12px 20px 0; }
  .numbers .n { font-family: 'Playfair Display', serif; font-size: 38px; color: var(--maroon); line-height: 1; }
  .numbers .t { font-size: 13.5px; color: var(--text-soft); margin-top: 8px; line-height: 1.35; }
  .back-link { display: inline-block; margin-top: 10px; color: var(--maroon); font-size: 15px; }
  @media (max-width: 860px) {
    .blog-hero { padding: 56px 0 52px; }
    .blog-hero h1, .post-head h1 { font-size: 30px; }
    .post-head { padding-top: 44px; }
    .post-body p { font-size: 17px; }
    .numbers { grid-template-columns: repeat(2, 1fr); }
    .callout { padding: 22px 22px; }
  }
"""

HEAD_FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
              '<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;1,400'
              '&family=Work+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">')

HEADER = """<header>
  <div class="hdr-top">
    <a class="hdr-kw" href="/index.html"><img class="kw-logo" alt="Keller Williams Realty Western Montana" src="/assets/kw-logo.png"></a>
    <a class="hdr-logo" href="/index.html"><img class="logo" src="/assets/hobbs-logo.png" alt="Hobbs Homes, Missoula MT"></a>
    <a class="nav-phone hdr-cta" href="/index.html#contact">Schedule a Consult</a>
  </div>
  <nav>
    <a href="/index.html">Home</a>
    <a href="/index.html#contact">Buy a Home</a>
    <a href="/index.html#paths">New Builds</a>
    <a href="/index.html#past-projects">Past Projects</a>
    <a href="/tips.html">Buyer &amp; Seller Tips</a>
    <a href="/blog/" class="active">Blog</a>
    <a href="/about.html">About</a>
  </nav>
</header>"""

FOOTER = """<footer>
  <div class="wrap">
    <div class="footer-grid">
      <div>
        <img class="logo-f" src="/assets/hobbs-logo-footer.png" alt="Hobbs Homes">
        <p class="blurb">Real estate and new construction in Missoula &amp; Western Montana. Locally built, locally sold.</p>
        <img class="kw-logo-f" alt="Keller Williams Realty Western Montana" src="/assets/kw-logo-footer.png">
      </div>
      <div class="footer-col">
        <h4>Explore</h4>
        <a href="/index.html#contact">Buy a Home</a>
        <a href="/index.html#paths">New Builds</a>
        <a href="/index.html#past-projects">Past Projects</a>
        <a href="/tips.html">Buyer &amp; Seller Tips</a>
        <a href="/blog/">Blog</a>
        <a href="/about.html">About</a>
      </div>
      <div class="footer-col">
        <h4>Contact</h4>
        <a href="tel:4065449794">(406) 544-9794</a>
        <a href="mailto:tyhobbs@kw.com">tyhobbs@kw.com</a>
        <a href="#">Missoula, MT</a>
      </div>
      <div class="footer-col">
        <h4>Follow</h4>
        <a href="https://www.instagram.com/hobbshomesmt/" target="_blank" rel="noopener">Instagram</a>
        <a href="https://www.facebook.com/profile.php?id=100064876065050" target="_blank" rel="noopener">Facebook</a>
      </div>
    </div>
    <div class="wrap footer-bottom">
      <p>&copy; 2026 Hobbs Homes. Missoula, MT. Equal Housing Opportunity.</p>
      <p>Licensed Realtor &amp; Residential Builder &mdash; MT License #RRE-RBS-LIC-46476</p>
    </div>
  </div>
</footer>"""

SCRIPT = """<script>
(function(){function s(){var h=document.querySelector('header'),n=h&&h.querySelector('nav');if(!n)return;h.style.setProperty('--stick',(-n.offsetTop)+'px');}
window.addEventListener('load',s);window.addEventListener('resize',s);s();})();
</script>"""

CTA = """<section class="bottom-line">
  <div class="wrap">
    <p class="eyebrow">Your Move</p>
    <h2>Thinking about buying, selling, or both? Let's talk it through.</h2>
    <a class="btn btn-primary" href="/index.html#contact">Book a Consultation</a>
    <p style="color:#B8B4A9;font-size:15.5px;margin-top:26px;">Or call or text Ty at <a href="tel:4065449794" style="color:#fff;border-bottom:1px solid #8A8678;">(406) 544-9794</a>
    &nbsp;&middot;&nbsp; <a href="https://www.instagram.com/hobbshomesmt/" target="_blank" rel="noopener" style="color:#fff;border-bottom:1px solid #8A8678;">Follow @hobbshomesmt</a></p>
  </div>
</section>"""


def page(title, description, canonical, body, extra_head="", og_type="website"):
    t = html.escape(title, quote=True)
    d = html.escape(description, quote=True)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{t}</title>
<meta name="description" content="{d}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{canonical}">
<meta property="og:site_name" content="Hobbs Homes">
{HEAD_FONTS}
<style>{css}{BLOG_CSS}</style>
{extra_head}
</head>
<body>

{HEADER}

{body}

{FOOTER}

{SCRIPT}
</body>
</html>
"""


def fmt_date(iso):
    d = datetime.date.fromisoformat(iso)
    return d.strftime("%B ") + str(d.day) + d.strftime(", %Y")


def reading_minutes(body_html):
    words = len(re.sub(r"<[^>]+>", " ", body_html).split())
    return max(1, round(words / 220))


posts = []
for f in glob.glob("_blog-src/posts/*.json"):
    p = json.load(open(f, encoding="utf-8"))
    p["slug"] = os.path.splitext(os.path.basename(f))[0]
    posts.append(p)
posts.sort(key=lambda p: p["date"], reverse=True)

os.makedirs("blog", exist_ok=True)

for p in posts:
    url = f"{SITE}/blog/{p['slug']}"
    mins = reading_minutes(p["body_html"])
    ld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": p["title"],
        "description": p["description"],
        "datePublished": p["date"],
        "dateModified": p.get("updated", p["date"]),
        "author": {"@type": "Person", "name": "Ty Hobbs", "url": f"{SITE}/about.html"},
        "publisher": {"@type": "Organization", "name": "Hobbs Homes", "url": SITE,
                      "logo": {"@type": "ImageObject", "url": f"{SITE}/assets/hobbs-logo.png"}},
        "mainEntityOfPage": url,
    }
    extra = '<script type="application/ld+json">' + json.dumps(ld) + "</script>"
    body = f"""<section class="post-head">
  <div class="narrow">
    <p class="eyebrow">{html.escape(p['category'])}</p>
    <h1>{p['title_html'] if 'title_html' in p else html.escape(p['title'])}</h1>
    <p class="post-meta">By Ty Hobbs &nbsp;&middot;&nbsp; {fmt_date(p['date'])} &nbsp;&middot;&nbsp; {mins} min read</p>
  </div>
</section>
<article class="post-body">
  <div class="narrow">
{p['body_html']}
    <a class="back-link" href="/blog/">&larr; All posts</a>
  </div>
</article>
{CTA}"""
    out = page(p["title"] + " | Hobbs Homes", p["description"], url, body, extra, "article")
    open(f"blog/{p['slug']}.html", "w", encoding="utf-8").write(out)

cards = ""
for p in posts:
    mins = reading_minutes(p["body_html"])
    cards += f"""      <a class="post-card" href="/blog/{p['slug']}">
        <div class="meta"><span class="cat">{html.escape(p['category'])}</span> &nbsp;&middot;&nbsp; {fmt_date(p['date'])} &nbsp;&middot;&nbsp; {mins} min read</div>
        <h2>{html.escape(p['title'])}</h2>
        <p class="excerpt">{html.escape(p['excerpt'])}</p>
        <span class="more">Read the post &rarr;</span>
      </a>
"""

index_body = f"""<section class="blog-hero">
  <div class="wrap">
    <p class="eyebrow">The Hobbs Homes Blog</p>
    <h1>Straight talk on Missoula and Western Montana real estate.</h1>
    <p class="sub">Market numbers, what a builder sees when he walks a house, local area guides, and the occasional story. New post every week.</p>
  </div>
</section>
<section class="post-list">
  <div class="wrap">
{cards}    <p class="cadence">Questions you want answered here? Text Ty at <a href="tel:4065449794" style="color:var(--maroon);border-bottom:1px solid var(--maroon);">(406) 544-9794</a>.</p>
  </div>
</section>
{CTA}"""
open("blog/index.html", "w", encoding="utf-8").write(
    page("Blog | Hobbs Homes, Missoula MT",
         "Straight talk on Missoula and Western Montana real estate from Realtor and builder Ty Hobbs: market updates, builder insights, area guides, and stories.",
         f"{SITE}/blog/", index_body))

print(f"Built {len(posts)} post(s) + blog index")
