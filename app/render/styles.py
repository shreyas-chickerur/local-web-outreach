"""The stylesheet for generated sites.

Kept as a token-substituted string (``__ACCENT__`` etc.) rather than %-formatting
because CSS is mostly braces and percent signs; token replacement keeps it
readable and avoids escaping every rule.

Design decisions worth knowing:
* Editorial scale — a large, tightly-tracked display face against generous space
  is what separates a designed page from a bootstrap template.
* Solid buttons on photography. Outlined buttons over an unknown image are
  unreadable; the hero also carries a gradient scrim for the same reason.
* Motion is additive and always gated behind ``prefers-reduced-motion``.
* Every interactive element has a visible ``:focus-visible`` ring.
"""

from __future__ import annotations

from app.render.theme import Palette

CSS = """
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --ink:__INK__; --accent:__ACCENT__; --accent-dark:__ACCENT_DARK__;
  --tint:__TINT__; --sand:__SAND__; --eyebrow:__EYEBROW__;
  --muted:#5b6472; --line:#e6e8ec; --radius:14px;
  --shadow:0 1px 2px rgba(16,24,40,.04),0 12px 32px -12px rgba(16,24,40,.18);
  --shadow-lg:0 24px 60px -20px rgba(16,24,40,.34);
}
html{scroll-behavior:smooth}
body{font:400 17px/1.65 ui-sans-serif,-apple-system,BlinkMacSystemFont,'Segoe UI',
     Inter,Helvetica,Arial,sans-serif;color:var(--ink);background:#fff;
     -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;
     overflow-x:hidden}
img{max-width:100%;display:block}
a{color:inherit}
:focus-visible{outline:3px solid var(--accent);outline-offset:3px;border-radius:4px}
.wrap{width:min(1160px,100% - 48px);margin-inline:auto}

/* ---------- type ---------- */
.display{font-weight:800;letter-spacing:-.035em;line-height:.98;
     font-size:clamp(2.6rem,7.5vw,5.4rem)}
h2.section-title{font-weight:800;letter-spacing:-.028em;line-height:1.05;
     font-size:clamp(1.9rem,4vw,3rem)}
.eyebrow{font-size:.76rem;font-weight:800;letter-spacing:.16em;text-transform:uppercase;
     color:var(--eyebrow);display:flex;align-items:center;gap:10px}
.eyebrow::before{content:"";width:26px;height:2px;background:currentColor;flex:none}
.lede{font-size:clamp(1.05rem,1.6vw,1.25rem);color:var(--muted);max-width:62ch}

/* ---------- nav ---------- */
.nav{position:fixed;inset:0 0 auto;z-index:50;transition:background .3s,box-shadow .3s,
     backdrop-filter .3s;padding:18px 0}
.nav .bar{display:flex;align-items:center;justify-content:space-between;gap:16px}
.nav .brand{font-weight:800;letter-spacing:-.02em;font-size:1.06rem;color:#fff;
     text-shadow:0 1px 12px rgba(0,0,0,.45);text-decoration:none}
.nav.solid{background:rgba(255,255,255,.86);backdrop-filter:saturate(180%) blur(14px);
     box-shadow:0 1px 0 var(--line);padding:12px 0}
.nav.solid .brand{color:var(--ink);text-shadow:none}
.nav-links{display:none;gap:26px;font-size:.94rem;font-weight:600}
.nav.solid .nav-links a{color:var(--ink)}
.nav-links a{color:#fff;text-decoration:none;opacity:.92;text-shadow:0 1px 10px rgba(0,0,0,.4)}
.nav-links a:hover{opacity:1}
@media(min-width:900px){.nav-links{display:flex}}

/* ---------- buttons ---------- */
.btn{display:inline-flex;align-items:center;gap:9px;text-decoration:none;font-weight:700;
     padding:15px 26px;border-radius:999px;font-size:.98rem;border:2px solid transparent;
     transition:transform .18s cubic-bezier(.2,.8,.2,1),box-shadow .18s,background .18s;
     white-space:nowrap}
.btn:hover{transform:translateY(-2px)}
.btn-primary{background:var(--accent);color:#fff;box-shadow:0 10px 24px -10px var(--accent)}
.btn-primary:hover{background:var(--accent-dark)}
/* On photography an outlined button is unreadable — use a solid light fill. */
.btn-on-photo{background:rgba(255,255,255,.96);color:var(--ink);
     box-shadow:0 10px 30px -12px rgba(0,0,0,.7)}
.btn-on-photo:hover{background:#fff}
.btn-quiet{background:var(--sand);color:var(--ink)}
.btn-quiet:hover{background:var(--tint)}
.btn-lg{padding:18px 34px;font-size:1.05rem}

/* ---------- hero ---------- */
.hero{position:relative;min-height:min(92vh,780px);display:flex;align-items:flex-end;
     background:var(--ink);overflow:hidden}
.hero .bg{position:absolute;inset:0;background-size:cover;background-position:center;
     transform:scale(1.06);animation:kenburns 22s ease-out forwards}
.hero .scrim{position:absolute;inset:0;
     background:linear-gradient(180deg,rgba(6,8,12,.62) 0%,rgba(6,8,12,.30) 38%,
     rgba(6,8,12,.86) 100%)}
.hero .inner{position:relative;padding:150px 0 74px;color:#fff;width:100%}
.hero .display{color:#fff;max-width:16ch;text-shadow:0 2px 30px rgba(0,0,0,.35)}
.hero .eyebrow{color:#fff;opacity:.95}
.hero .sub{margin-top:20px;font-size:clamp(1.05rem,1.9vw,1.4rem);color:#eef1f5;
     max-width:52ch;text-shadow:0 1px 16px rgba(0,0,0,.5)}
.hero .cta-row{display:flex;flex-wrap:wrap;gap:12px;margin-top:36px}
.hero--plain{background:linear-gradient(160deg,var(--tint),#fff 62%);min-height:auto}
.hero--plain .inner{padding:150px 0 90px;color:var(--ink)}
.hero--plain .display,.hero--plain .sub{color:var(--ink);text-shadow:none}
.hero--plain .sub{color:var(--muted)}
.hero--plain .eyebrow{color:var(--eyebrow)}
@keyframes kenburns{to{transform:scale(1)}}

/* ---------- sections ---------- */
section{padding:clamp(64px,9vw,120px) 0}
.section-head{display:flex;flex-direction:column;gap:14px;margin-bottom:52px;max-width:70ch}
.band-tint{background:var(--tint)}
.band-sand{background:var(--sand)}

/* offerings — numbered editorial grid */
.offer-grid{display:grid;gap:2px;background:var(--line);border:1px solid var(--line);
     border-radius:var(--radius);overflow:hidden;
     grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.offer{background:#fff;padding:34px 30px;display:flex;flex-direction:column;gap:12px;
     transition:background .25s,transform .25s}
.offer:hover{background:var(--tint)}
.offer .num{font-variant-numeric:tabular-nums;font-weight:800;font-size:.82rem;
     letter-spacing:.14em;color:var(--accent)}
.offer .name{font-size:1.22rem;font-weight:700;letter-spacing:-.015em;line-height:1.25}

/* hours — dot leaders */
.hours{display:grid;gap:0;max-width:640px;border-top:1px solid var(--line)}
.hours .row{display:flex;align-items:baseline;gap:14px;padding:18px 4px;
     border-bottom:1px solid var(--line);font-size:1.06rem}
.hours .row .dots{flex:1;border-bottom:1px dotted #c8ced8;transform:translateY(-4px)}
.hours .row .when{font-weight:700}

/* story */
.story-grid{display:grid;gap:44px;align-items:start}
@media(min-width:900px){.story-grid{grid-template-columns:1.1fr .9fr}}
.story p{font-size:clamp(1.1rem,1.7vw,1.32rem);line-height:1.6;color:#2b3340}
.story p::first-letter{float:left;font-size:3.6em;line-height:.82;padding:6px 12px 0 0;
     font-weight:800;color:var(--accent)}
.stat-card{background:var(--ink);color:#fff;border-radius:var(--radius);padding:34px;
     box-shadow:var(--shadow-lg)}
.stat-card .big{font-size:3.4rem;font-weight:800;letter-spacing:-.04em;line-height:1}
.stat-card .stars{color:#fbbf24;font-size:1.35rem;letter-spacing:3px;margin-top:8px}
.stat-card .cap{margin-top:10px;color:#c3cad6;font-size:.94rem}

/* gallery — clickable, keyboard reachable */
.gallery{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(230px,1fr))}
.gallery button{border:0;padding:0;background:none;cursor:zoom-in;border-radius:var(--radius);
     overflow:hidden;position:relative;aspect-ratio:4/3;box-shadow:var(--shadow)}
.gallery img{width:100%;height:100%;object-fit:cover;
     transition:transform .5s cubic-bezier(.2,.8,.2,1)}
.gallery button:hover img{transform:scale(1.06)}
.gallery button::after{content:"⤢";position:absolute;right:12px;bottom:10px;color:#fff;
     font-size:1.05rem;opacity:0;transition:opacity .25s;text-shadow:0 2px 8px rgba(0,0,0,.6)}
.gallery button:hover::after{opacity:1}
.gallery button:first-child{grid-column:span 2}
@media(max-width:620px){.gallery button:first-child{grid-column:span 1}}

/* lightbox */
.lightbox{position:fixed;inset:0;z-index:100;background:rgba(8,10,14,.94);display:none;
     align-items:center;justify-content:center;padding:28px}
.lightbox.open{display:flex}
.lightbox img{max-width:min(1100px,94vw);max-height:88vh;width:auto;border-radius:10px;
     box-shadow:var(--shadow-lg)}
.lightbox .x,.lightbox .arrow{position:absolute;background:rgba(255,255,255,.12);
     border:0;color:#fff;width:50px;height:50px;border-radius:50%;font-size:1.4rem;
     cursor:pointer;display:grid;place-items:center;transition:background .2s}
.lightbox .x:hover,.lightbox .arrow:hover{background:rgba(255,255,255,.26)}
.lightbox .x{top:22px;right:22px}
.lightbox .prev{left:22px;top:50%;transform:translateY(-50%)}
.lightbox .next{right:22px;top:50%;transform:translateY(-50%)}

/* contact / closing */
.closing{background:var(--ink);color:#fff;text-align:center}
.closing h2{color:#fff}
.closing .lede{color:#c3cad6;margin-inline:auto}
.contact-grid{display:grid;gap:18px;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));
     margin-top:44px;text-align:left}
.contact-card{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.14);
     border-radius:var(--radius);padding:24px}
.contact-card .k{font-size:.74rem;letter-spacing:.14em;text-transform:uppercase;
     color:#9aa5b5;font-weight:800}
.contact-card .v{margin-top:8px;font-size:1.1rem;font-weight:600;word-break:break-word}
.contact-card a{text-decoration:none}
.contact-card a:hover{color:#fff;text-decoration:underline}

footer{background:var(--ink);color:#8b95a5;padding:34px 0 46px;font-size:.9rem;
     border-top:1px solid rgba(255,255,255,.1)}
footer .bar{display:flex;gap:18px;justify-content:space-between;flex-wrap:wrap;
     align-items:center}
.socials{display:flex;gap:10px;flex-wrap:wrap}
.socials a{border:1px solid rgba(255,255,255,.2);color:#d3d9e2;text-decoration:none;
     padding:8px 16px;border-radius:999px;font-size:.86rem;font-weight:600;
     transition:background .2s,color .2s}
.socials a:hover{background:#fff;color:var(--ink)}

/* draft marker */
.draft{position:fixed;left:50%;transform:translateX(-50%);bottom:20px;z-index:60;
     background:rgba(17,20,26,.92);color:#fff;padding:10px 20px;border-radius:999px;
     font-size:.78rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;
     backdrop-filter:blur(8px);box-shadow:var(--shadow-lg)}

/* scroll reveal */
.reveal{opacity:0;transform:translateY(22px);
     transition:opacity .7s cubic-bezier(.2,.8,.2,1),transform .7s cubic-bezier(.2,.8,.2,1)}
.reveal.in{opacity:1;transform:none}
@media(prefers-reduced-motion:reduce){
  *,*::before,*::after{animation:none!important;transition:none!important;
     scroll-behavior:auto!important}
  .reveal{opacity:1;transform:none}
  .hero .bg{transform:none}
}
"""


def css_for(palette: Palette) -> str:
    return (CSS
            .replace("__INK__", palette.ink)
            .replace("__ACCENT_DARK__", palette.accent_dark)
            .replace("__ACCENT__", palette.accent)
            .replace("__TINT__", palette.tint)
            .replace("__SAND__", palette.sand)
            .replace("__EYEBROW__", palette.eyebrow))
