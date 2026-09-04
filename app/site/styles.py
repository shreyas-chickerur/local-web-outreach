"""The stylesheet and the motion layer for a generated site.

Kept apart from the markup because this is the half that decides whether the
page looks made or generated. The rules that matter:

* motion is choreography, not decoration — things arrive in the order you read
  them, and every animation is cancelled under `prefers-reduced-motion`;
* type is fluid (`clamp`) so a headline is right on a phone and on a 27" screen
  without a breakpoint for each;
* every image reserves its space with `aspect-ratio`, so nothing jumps as
  photos load — layout shift is the cheapest tell that a site was thrown
  together.
"""

from __future__ import annotations

from app.site.theme import Theme

GRAIN = (
    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
    "width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence "
    "type='fractalNoise' baseFrequency='.85' numOctaves='3'/%3E%3C/filter%3E"
    "%3Crect width='140' height='140' filter='url(%23n)' opacity='.32'/%3E"
    "%3C/svg%3E\")")


def _type_rules(t: Theme) -> str:
    """The type scale, its optics, and the axes, emitted per level.

    Three things happen here that a single global rule cannot do:

    * sizes come off one modular scale, so h1/h2/h3 keep a fixed relationship
      to the body size rather than drifting between three unrelated clamps;
    * tracking is this face's value, easing toward zero as size drops — the
      figure that flatters a 96px headline is too tight at 22px;
    * `opsz` and `wght` are driven per level, which is the only reason to be
      paying for a variable font at all. Where the face is static (Archivo
      Black) the property is omitted entirely and `font-weight` does the work.
    """
    scale = t.scale
    levels = (("h1", t.display_steps, t.display_weight, 144.0),
              ("h2", max(2, t.display_steps - 2), t.heading_weight, 72.0),
              ("h3", 2, t.heading_weight, 36.0))
    lines = []
    for selector, steps, weight, optical in levels:
        rules = [
            f"font-size:calc({scale[selector]} * var(--density-scale))",
            f"letter-spacing:{t.tracking_for(steps)}",
        ]
        variation = t.display.variation(weight, optical)
        rules.append(f"font-variation-settings:{variation}" if variation
                     else f"font-weight:{weight}")
        lines.append(f"{selector}{{{';'.join(rules)}}}")
    lines.append(f".lede{{font-size:calc({scale['lede']} * var(--density-scale))}}")
    body_variation = t.body.variation(400, 18.0)
    if body_variation:
        lines.append(f"body{{font-variation-settings:{body_variation}}}")
    return "\n".join(lines)


def _layout_rules(t: Theme) -> str:
    """Structural intent, keyed off the bias each theme declares.

    This is what stops six moods being one page in six colourways: an airy
    theme gets its whitespace and loses its borders, a structural one gets
    hairline rules and a micro-shadow, an editorial one offsets its columns.
    """
    return """
/* airy — space does the separating, so the lines get out of the way */
[data-theme-layout="airy"] section{padding:clamp(88px,13vw,180px) 0}
[data-theme-layout="airy"] .card,[data-theme-layout="airy"] .offer,
[data-theme-layout="airy"] .quote{border-color:transparent;
  box-shadow:0 1px 2px rgba(0,0,0,.03),0 18px 40px -28px rgba(0,0,0,.22)}
[data-theme-layout="airy"] .split{gap:clamp(48px,8vw,120px)}
[data-theme-layout="airy"] .listing li{border-bottom-color:transparent;
  padding-block:clamp(28px,3.4vw,46px)}

/* structured — hairlines and a shallow shadow; the grid is meant to show */
[data-theme-layout="structured"] section+section{border-top:1px solid var(--line)}
[data-theme-layout="structured"] .card,[data-theme-layout="structured"] .offer,
[data-theme-layout="structured"] .quote{box-shadow:0 1px 0 var(--line),
  0 10px 24px -20px rgba(0,0,0,.3)}
[data-theme-layout="structured"] .wrap{position:relative}

/* contained — compact and blocky; edges are the point */
[data-theme-layout="contained"] section{padding:clamp(52px,7.5vw,104px) 0}
[data-theme-layout="contained"] .wrap{width:min(1080px,100% - var(--pad)*2)}
[data-theme-layout="contained"] .card,[data-theme-layout="contained"] .offer,
[data-theme-layout="contained"] .quote{border-width:2px;box-shadow:none}
[data-theme-layout="contained"] h1,[data-theme-layout="contained"] h2{
  text-transform:uppercase}

/* editorial — asymmetry, a wider gutter, and the heading held off the edge */
[data-theme-layout="editorial"] .wrap{width:min(1240px,100% - var(--pad)*2)}
[data-theme-layout="editorial"] .split{
  grid-template-columns:minmax(0,.72fr) minmax(0,1.28fr);
  gap:clamp(40px,7vw,110px)}
[data-theme-layout="editorial"] .head{margin-left:clamp(0px,4vw,80px)}
[data-theme-layout="editorial"] .offers-editorial{
  grid-template-columns:minmax(0,.86fr) minmax(0,1.14fr)}
[data-theme-layout="editorial"] .card,[data-theme-layout="editorial"] .offer,
[data-theme-layout="editorial"] .quote{border-radius:var(--r);box-shadow:none;
  border-color:var(--line)}
@media (max-width:900px){
  [data-theme-layout="editorial"] .split{grid-template-columns:1fr}
  [data-theme-layout="editorial"] .head{margin-left:0}
}
"""


def css(t: Theme) -> str:
    grain_layer = f'''
body::after{{content:"";position:fixed;inset:0;pointer-events:none;z-index:1;
  background-image:{GRAIN};opacity:.05;mix-blend-mode:multiply}}''' if t.grain else ""
    type_rules = _type_rules(t)
    layout_rules = _layout_rules(t)
    body_size = t.scale["body"]
    listing_size = t.step(max(2, t.display_steps - 3))
    return f'''
:root{{
  --bg:{t.bg}; --surface:{t.surface}; --raise:{t.raise_}; --ink:{t.ink};
  --dim:{t.dim}; --accent:{t.accent}; --accent-soft:{t.accent_soft};
  --accent-ink:{t.accent_ink}; --line:{t.line}; --r:{t.radius};
  --shadow:0 1px 2px rgba(0,0,0,.04),0 12px 32px -18px rgba(0,0,0,.28);
  --lift:0 2px 6px rgba(0,0,0,.06),0 28px 56px -28px rgba(0,0,0,.36);
  --pad:clamp(20px,5vw,44px);
}}
*{{box-sizing:border-box}}
/* `overflow-x:hidden` on BODY makes the body its own scroll container, and
   window.scrollTo then cannot scroll the page back up — which is exactly how
   the back-to-top button came to do nothing. `clip` on the root contains a
   stray wide element without creating a scroller. */
html{{scroll-behavior:smooth;-webkit-text-size-adjust:100%;
  overflow-x:hidden;overflow-x:clip}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:{t.body.stack};
  font-size:{body_size};line-height:1.65;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}}
{grain_layer}
h1,h2,h3{{font-family:{t.display.stack};line-height:1.05;margin:0 0 .5em}}
{type_rules}
p{{margin:0 0 1em;max-width:68ch}}
a{{color:var(--accent)}}
img{{max-width:100%;display:block}}
.wrap{{width:min(1180px,100% - var(--pad)*2);margin-inline:auto}}
.wrap.narrow{{width:min(760px,100% - var(--pad)*2)}}
section{{padding:clamp(64px,10vw,140px) 0;position:relative}}
section.band{{background:var(--raise)}}
.eyebrow{{font-size:12px;letter-spacing:.18em;text-transform:uppercase;
  font-weight:700;color:var(--accent);margin:0 0 14px;font-family:{t.body.stack}}}

/* ---------------------------------------------------------------- chrome -- */
.bar{{position:fixed;inset:0 0 auto;z-index:40;display:flex;align-items:center;
  gap:22px;padding:14px clamp(18px,4vw,40px);transition:background .35s ease,
  box-shadow .35s ease,padding .35s ease;color:#fff}}
.bar.stuck{{background:var(--surface);color:var(--ink);box-shadow:var(--shadow);
  padding-top:10px;padding-bottom:10px}}
.bar .mark{{font-family:{t.display.stack};font-weight:700;font-size:19px;
  letter-spacing:-.02em;text-decoration:none;color:inherit}}
.bar nav{{margin-left:auto;display:flex;gap:26px}}
.bar nav a{{color:inherit;text-decoration:none;font-size:14.5px;font-weight:600;
  opacity:.86;position:relative;padding:4px 0}}
.bar nav a::after{{content:"";position:absolute;left:0;right:100%;bottom:0;height:2px;
  background:var(--accent);transition:right .3s cubic-bezier(.2,.7,.3,1)}}
.bar nav a:hover::after,.bar nav a[aria-current=true]::after{{right:0}}
.bar .book{{background:var(--accent);color:var(--accent-ink);padding:10px 20px;
  border-radius:var(--r);text-decoration:none;font-weight:700;font-size:14.5px;
  transition:transform .2s ease,filter .2s ease}}
.bar .book:hover{{transform:translateY(-2px);filter:brightness(1.08)}}
.burger{{display:none;margin-left:auto;background:none;border:0;color:inherit;
  font-size:24px;cursor:pointer;line-height:1}}
.progress{{position:fixed;top:0;left:0;height:3px;width:0;background:var(--accent);
  z-index:50;transition:width .1s linear}}

/* ------------------------------------------------------------------ hero -- */
.hero{{min-height:min(94vh,900px);display:grid;align-items:end;position:relative;
  overflow:hidden;background:var(--raise);isolation:isolate}}
.hero .bgimg{{position:absolute;inset:-8% 0 0;z-index:-2;background-size:cover;
  background-position:center;will-change:transform}}
.hero .veil{{position:absolute;inset:0;z-index:-1;background:{t.hero_overlay}}}
.hero.has-photo{{color:#fff}}
.hero .wrap{{padding-bottom:clamp(52px,9vh,110px);padding-top:120px}}
.hero h1{{margin-bottom:.22em;max-width:16ch}}
.hero .sub{{font-size:clamp(17px,2vw,25px);max-width:40ch;opacity:.94;
  margin-bottom:30px;line-height:1.4}}
.hero .facts{{display:flex;gap:26px;flex-wrap:wrap;margin-bottom:32px;
  font-size:14.5px;font-weight:600;opacity:.92}}
.hero .facts span{{display:inline-flex;align-items:center;gap:8px}}
.actions{{display:flex;gap:12px;flex-wrap:wrap}}
.cta{{display:inline-flex;align-items:center;gap:9px;background:var(--accent);
  color:var(--accent-ink);text-decoration:none;font-weight:700;
  padding:16px 30px;border-radius:var(--r);font-size:16px;
  transition:transform .22s cubic-bezier(.2,.7,.3,1),box-shadow .22s ease}}
.cta:hover{{transform:translateY(-3px);box-shadow:var(--lift)}}
.cta.ghost{{background:transparent;color:inherit;border:1.5px solid currentColor}}
.cta.ghost:hover{{background:rgba(255,255,255,.12)}}
.scrollcue{{position:absolute;left:50%;bottom:26px;translate:-50% 0;width:22px;
  height:34px;border:2px solid currentColor;border-radius:12px;opacity:.5}}
.scrollcue::after{{content:"";position:absolute;left:50%;top:7px;translate:-50% 0;
  width:3px;height:7px;border-radius:2px;background:currentColor;
  animation:cue 1.7s ease-in-out infinite}}
@keyframes cue{{0%,100%{{transform:translateY(0);opacity:1}}
  60%{{transform:translateY(9px);opacity:0}}}}

/* -------------------------------------------------------------- sections -- */
.lede{{line-height:1.5;color:var(--dim);
  max-width:34ch;margin:0}}
.split{{display:grid;grid-template-columns:minmax(240px,.9fr) 1.4fr;
  gap:clamp(28px,5vw,72px);align-items:start}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px}}
.card{{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);
  padding:30px 28px;transition:transform .3s cubic-bezier(.2,.7,.3,1),
  box-shadow .3s ease,border-color .3s ease;position:relative;overflow:hidden}}
.card:hover{{transform:translateY(-5px);box-shadow:var(--lift);
  border-color:color-mix(in srgb,var(--accent) 40%,var(--line))}}
.card .num{{font-family:{t.display.stack};font-size:13px;color:var(--accent);
  letter-spacing:.1em;margin-bottom:12px}}
.card h3{{margin:0}}
section.band .card{{background:var(--bg)}}

/* ---------------------------------------------------------------- offers -- */
.head{{max-width:44ch;margin-bottom:clamp(30px,5vw,56px)}}
/* Type scales inversely with how much of it there is. The clamp keeps doing
   the responsive work; --density-scale only shifts where it sits, so a section
   with two services is set larger than one with nine without a second set of
   breakpoints. Defaulted here so any section without the attribute is unmoved. */
section{{--density-scale:1}}

/* Four or more: the grid is genuinely right, and auto-fit belongs here. */
.offers{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
  gap:clamp(12px,1.6vw,20px)}}
/* Exactly three: hold three across so none of them stretches into a slab. */
[data-density="balanced"] .offers{{
  grid-template-columns:repeat(3,minmax(0,1fr))}}

/* One or two: no grid of cards at all. An asymmetric split — display type
   holding the left, the offerings set large against rules on the right —
   because two cards in a row built for four leave a gutter of dead space
   down the middle, which is what a template looks like. */
.offers-editorial{{display:grid;
  grid-template-columns:minmax(0,1.02fr) minmax(0,.98fr);
  gap:clamp(34px,6vw,96px);align-items:start}}
.offers-editorial .display{{position:sticky;top:96px}}
.offers-editorial .display h2{{max-width:14ch}}
.offers-editorial .lede{{margin-top:18px}}
.listing{{list-style:none;margin:0;padding:0;border-top:1px solid var(--line)}}
.listing li{{display:grid;grid-template-columns:auto 1fr;gap:0 18px;
  align-items:baseline;padding:clamp(22px,2.6vw,34px) 0;
  border-bottom:1px solid var(--line);transition:padding-left .4s
  cubic-bezier(.2,.7,.3,1)}}
.listing li:hover{{padding-left:10px}}
.listing .idx{{font-family:{t.display.stack};font-size:12px;letter-spacing:.16em;
  color:var(--accent)}}
.listing h3{{margin:0;line-height:1.08;
  font-size:calc({listing_size} * var(--density-scale))}}
.editorial-art{{margin-top:clamp(24px,3vw,40px);border-radius:var(--r);
  overflow:hidden;aspect-ratio:5/3}}
.editorial-art img{{width:100%;height:100%;object-fit:cover;
  transition:transform 1.1s cubic-bezier(.2,.7,.3,1),
    clip-path 1s cubic-bezier(.2,.7,.3,1);clip-path:inset(14% 0 0 0)}}
.editorial-art.in img{{clip-path:inset(0 0 0 0)}}
.editorial-art:hover img{{transform:scale(1.04)}}
.offer{{position:relative;border-radius:var(--r);overflow:hidden;
  background:var(--surface);border:1px solid var(--line);min-height:180px;
  display:flex;flex-direction:column;justify-content:flex-end;padding:26px 24px;
  transition:transform .45s cubic-bezier(.2,.7,.3,1),box-shadow .45s ease,
    border-color .45s ease}}
.offer:hover{{transform:translateY(-6px);box-shadow:var(--lift)}}
.offer .idx{{font-family:{t.display.stack};font-size:12px;letter-spacing:.16em;
  color:var(--accent);margin-bottom:auto}}
.offer h3{{margin:14px 0 0;line-height:1.15}}
.offer .rule{{display:block;height:2px;width:34px;background:var(--accent);
  margin-top:18px;transition:width .45s cubic-bezier(.2,.7,.3,1)}}
.offer:hover .rule{{width:78px}}
/* Photo-led cards: the picture is the card, the words sit on the glass. */
.offer.has-art{{min-height:min(340px,42vw);padding:0;border:0;color:#fff;
  aspect-ratio:4/5}}
.offer.has-art .art{{position:absolute;inset:0;overflow:hidden}}
.offer.has-art img{{width:100%;height:100%;object-fit:cover;
  transition:transform 1.1s cubic-bezier(.2,.7,.3,1),filter .5s ease;
  clip-path:inset(12% 0 0 0);}}
.offer.has-art.in img{{clip-path:inset(0 0 0 0)}}
.offer.has-art:hover img{{transform:scale(1.07)}}
.offer.has-art .label{{position:relative;z-index:1;margin-top:auto;
  padding:24px 22px;width:100%;
  background:linear-gradient(180deg,transparent,rgba(8,8,10,.86) 62%)}}
.offer.has-art .idx{{color:#fff;opacity:.75}}
.offer.has-art h3{{color:#fff;text-shadow:0 1px 18px rgba(0,0,0,.4)}}
.offers .offer.has-art:first-child{{grid-column:span 2;aspect-ratio:16/10}}

/* ----------------------------------------------------------------- stats -- */
.statband{{padding:clamp(40px,6vw,72px) 0;background:var(--accent);
  color:var(--accent-ink)}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:26px;text-align:center}}
.stat b{{display:block;font-family:{t.display.stack};font-size:clamp(38px,5.4vw,64px);
  line-height:1;font-variant-numeric:tabular-nums}}
.stat span{{display:block;margin-top:10px;font-size:13.5px;letter-spacing:.1em;
  text-transform:uppercase;opacity:.86;font-weight:600}}

/* ------------------------------------------------------------------ menu -- */
.filters{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:30px}}
.filters button{{background:transparent;border:1.5px solid var(--line);
  color:var(--dim);font:inherit;font-size:14px;font-weight:600;padding:9px 18px;
  border-radius:99px;cursor:pointer;transition:all .22s ease}}
.filters button:hover{{border-color:var(--accent);color:var(--accent)}}
.filters button[aria-pressed=true]{{background:var(--accent);border-color:var(--accent);
  color:var(--accent-ink)}}
.dishes{{list-style:none;padding:0;margin:0;display:grid;
  grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:0 clamp(28px,5vw,64px)}}
.dishes li{{display:grid;grid-template-columns:1fr auto;gap:3px 16px;
  padding:20px 0;border-bottom:1px solid var(--line);align-items:baseline;
  transition:opacity .3s ease,transform .3s ease}}
.dishes li.hide{{display:none}}
.dishes .n{{font-weight:650;font-size:17px}}
.dishes .p{{font-weight:700;color:var(--accent);font-variant-numeric:tabular-nums}}
.dishes .d{{grid-column:1/-1;color:var(--dim);font-size:15px;margin:0}}

/* --------------------------------------------------------------- gallery -- */
.mosaic{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
  gap:10px;grid-auto-flow:dense}}
.mosaic button{{padding:0;border:0;background:none;cursor:zoom-in;overflow:hidden;
  border-radius:var(--r);position:relative;aspect-ratio:4/3}}
.mosaic button:nth-child(6n+1){{grid-column:span 2;aspect-ratio:8/5}}
.mosaic img{{width:100%;height:100%;object-fit:cover;
  transition:transform .7s cubic-bezier(.2,.7,.3,1),
    clip-path 1s cubic-bezier(.2,.7,.3,1);clip-path:inset(14% 0 0 0)}}
.mosaic button.in img{{clip-path:inset(0 0 0 0)}}
.mosaic button:hover img{{transform:scale(1.06)}}
.lightbox{{position:fixed;inset:0;z-index:60;background:rgba(8,8,10,.94);
  display:none;place-items:center;padding:26px;backdrop-filter:blur(4px)}}
.lightbox[open]{{display:grid}}
.lightbox img{{max-width:94vw;max-height:86vh;border-radius:var(--r);
  animation:pop .34s cubic-bezier(.2,.7,.3,1)}}
@keyframes pop{{from{{opacity:0;transform:scale(.965)}}to{{opacity:1;transform:none}}}}
.lightbox .close,.lightbox .prev,.lightbox .next{{position:absolute;background:none;
  border:0;color:#fff;font-size:32px;cursor:pointer;padding:16px;opacity:.75}}
.lightbox .close:hover,.lightbox .prev:hover,.lightbox .next:hover{{opacity:1}}
.lightbox .close{{top:10px;right:14px}}
.lightbox .prev{{left:8px;top:50%;translate:0 -50%}}
.lightbox .next{{right:8px;top:50%;translate:0 -50%}}
.lightbox .count{{position:absolute;bottom:22px;left:50%;translate:-50% 0;
  color:#fff;opacity:.7;font-size:14px;font-variant-numeric:tabular-nums}}

/* --------------------------------------------------------------- reviews -- */
.quotes{{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:16px}}
.quote{{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);
  padding:30px 28px;display:flex;flex-direction:column;gap:14px}}
section.band .quote{{background:var(--bg)}}
.quote p{{margin:0;font-size:16.5px;line-height:1.6}}
.quote .who{{margin-top:auto;font-size:13.5px;color:var(--dim);font-weight:600}}
.stars{{color:var(--accent);letter-spacing:3px;font-size:15px}}

/* ----------------------------------------------------------------- hours -- */
.hourlist{{list-style:none;padding:0;margin:0}}
.hourlist li{{display:flex;justify-content:space-between;gap:20px;padding:14px 0;
  border-bottom:1px solid var(--line);font-size:16px}}
.openflag{{display:inline-flex;align-items:center;gap:8px;font-weight:700;
  color:var(--accent);background:var(--accent-soft);padding:7px 15px;
  border-radius:99px;font-size:14px;margin-bottom:18px}}
.openflag i{{width:8px;height:8px;border-radius:50%;background:currentColor;
  animation:pulse 2.4s ease-in-out infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.35}}}}

/* --------------------------------------------------------------- contact -- */
.reach{{display:grid;gap:14px}}
.reach a{{display:flex;align-items:baseline;gap:14px;text-decoration:none;
  color:inherit;padding:16px 0;border-bottom:1px solid var(--line);
  transition:padding-left .25s ease}}
.reach a:hover{{padding-left:8px}}
.reach .k{{font-size:12px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--dim);min-width:92px;font-weight:700}}
.reach .v{{font-size:18px;font-weight:600}}
.map{{border:1px solid var(--line);border-radius:var(--r);overflow:hidden;
  aspect-ratio:16/10;background:var(--raise)}}
.map iframe{{width:100%;height:100%;border:0;display:block;filter:saturate(.9)}}
.callbar{{display:none}}

footer{{padding:56px 0 44px;border-top:1px solid var(--line);color:var(--dim);
  font-size:14px}}
footer .row{{display:flex;gap:20px;flex-wrap:wrap;align-items:center}}
footer a{{color:inherit;text-decoration:none}}
footer a:hover{{color:var(--accent)}}
.top{{margin-left:auto;background:var(--surface);border:1px solid var(--line);
  border-radius:var(--r);padding:10px 18px;cursor:pointer;font:inherit;
  color:inherit;transition:all .2s ease}}
.top:hover{{border-color:var(--accent);color:var(--accent)}}

/* ---------------------------------------------------------------- motion -- */
[data-reveal]{{opacity:0;transform:translateY(26px);
  transition:opacity .8s cubic-bezier(.2,.7,.3,1),transform .8s cubic-bezier(.2,.7,.3,1)}}
[data-reveal].in{{opacity:1;transform:none}}
[data-reveal][data-delay="1"]{{transition-delay:.09s}}
[data-reveal][data-delay="2"]{{transition-delay:.18s}}
[data-reveal][data-delay="3"]{{transition-delay:.27s}}
[data-reveal][data-delay="4"]{{transition-delay:.36s}}
.hero h1,.hero .sub,.hero .facts,.hero .actions{{
  animation:rise 1s cubic-bezier(.16,.84,.32,1) both}}
.hero .sub{{animation-delay:.12s}} .hero .facts{{animation-delay:.2s}}
.hero .actions{{animation-delay:.3s}}
@keyframes rise{{from{{opacity:0;transform:translateY(30px)}}to{{opacity:1;transform:none}}}}

@media (max-width:900px){{
  .offers-editorial{{grid-template-columns:1fr;gap:30px}}
  .offers-editorial .display{{position:static}}
  [data-density="balanced"] .offers{{
    grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}}
}}
@media (max-width:700px){{
  .offers .offer.has-art:first-child{{grid-column:span 1;aspect-ratio:4/5}}
}}
@media (max-width:860px){{
  .split{{grid-template-columns:1fr}}
  .bar nav{{display:none}}
  .burger{{display:block}}
  .bar.open nav{{display:flex;position:absolute;inset:100% 0 auto;flex-direction:column;
    background:var(--surface);color:var(--ink);padding:18px var(--pad);gap:14px;
    box-shadow:var(--shadow)}}
  .mosaic button:nth-child(6n+1){{grid-column:span 1;aspect-ratio:4/3}}
  .callbar{{display:flex;position:fixed;inset:auto 0 0;z-index:45;gap:10px;
    padding:12px 16px calc(12px + env(safe-area-inset-bottom));
    background:var(--surface);border-top:1px solid var(--line)}}
  .callbar a{{flex:1;text-align:center;justify-content:center}}
  body{{padding-bottom:74px}}
}}
{layout_rules}
@media (prefers-reduced-motion:reduce){{
  html{{scroll-behavior:auto}}
  *,*::before,*::after{{animation:none!important;transition:none!important}}
  [data-reveal]{{opacity:1!important;transform:none!important}}
  .hero .bgimg{{transform:none!important}}
  .offer.has-art img,.mosaic img,.editorial-art img{{clip-path:none!important}}
}}
'''


def script() -> str:
    """Behaviour. Everything here degrades to a working page without it."""
    return '''
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

/* Sections arrive in reading order rather than all at once. */
const io = new IntersectionObserver((entries) => {
  for (const entry of entries) {
    if (entry.isIntersecting) { entry.target.classList.add("in"); io.unobserve(entry.target); }
  }
}, {rootMargin: "0px 0px -12% 0px", threshold: 0.08});
document.querySelectorAll("[data-reveal]").forEach(el => io.observe(el));

/* Header state, scroll progress, and which section you are in. */
const bar = document.querySelector(".bar");
const progress = document.querySelector(".progress");
const links = [...document.querySelectorAll(".bar nav a")];
const targets = links.map(a => document.querySelector(a.getAttribute("href")))
                     .filter(Boolean);
const hero = document.querySelector(".hero .bgimg");

function onScroll() {
  const y = window.scrollY;
  if (bar) bar.classList.toggle("stuck", y > window.innerHeight * 0.72);
  if (progress) {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    progress.style.width = (max > 0 ? (y / max) * 100 : 0) + "%";
  }
  if (hero && !reduced) hero.style.transform = `translate3d(0,${y * 0.28}px,0)`;
  let active = null;
  for (const section of targets) {
    if (section.getBoundingClientRect().top <= 140) active = section;
  }
  links.forEach(a => a.setAttribute(
    "aria-current", String(!!active && a.getAttribute("href") === "#" + active.id)));
}
addEventListener("scroll", onScroll, {passive: true});
onScroll();

const burger = document.querySelector(".burger");
if (burger) burger.onclick = () => bar.classList.toggle("open");
document.querySelectorAll(".bar nav a").forEach(a =>
  a.addEventListener("click", () => bar.classList.remove("open")));

/* Menu filtering, when the menu has more than one course. */
document.querySelectorAll(".filters button").forEach(button => {
  button.onclick = () => {
    const want = button.dataset.group;
    document.querySelectorAll(".filters button").forEach(b =>
      b.setAttribute("aria-pressed", String(b === button)));
    document.querySelectorAll(".dishes li").forEach(li =>
      li.classList.toggle("hide", want !== "all" && li.dataset.group !== want));
  };
});

/* Gallery lightbox: click, arrow keys, escape. */
const box = document.querySelector(".lightbox");
if (box) {
  const shots = [...document.querySelectorAll(".mosaic img")];
  const view = box.querySelector("img");
  const count = box.querySelector(".count");
  let at = 0;
  const show = (i) => {
    at = (i + shots.length) % shots.length;
    view.src = shots[at].dataset.full || shots[at].src;
    if (count) count.textContent = `${at + 1} / ${shots.length}`;
  };
  document.querySelectorAll(".mosaic button").forEach((b, i) =>
    b.onclick = () => { show(i); box.setAttribute("open", ""); });
  box.querySelector(".close").onclick = () => box.removeAttribute("open");
  box.querySelector(".prev").onclick = (e) => { e.stopPropagation(); show(at - 1); };
  box.querySelector(".next").onclick = (e) => { e.stopPropagation(); show(at + 1); };
  box.onclick = (e) => { if (e.target === box) box.removeAttribute("open"); };
  addEventListener("keydown", (e) => {
    if (!box.hasAttribute("open")) return;
    if (e.key === "Escape") box.removeAttribute("open");
    if (e.key === "ArrowLeft") show(at - 1);
    if (e.key === "ArrowRight") show(at + 1);
  });
}

/* Back to top. Bound here rather than inline: inside an onclick attribute the
   element is in scope, so `scrollTo` resolves to the button's own
   Element.scrollTo and quietly scrolls the button instead of the page. */
const toTop = document.querySelector(".top");
if (toTop) toTop.addEventListener("click", () => {
  const from = window.scrollY;
  if (reduced) { window.scrollTo({top: 0, behavior: "instant"}); return; }
  window.scrollTo({top: 0, behavior: "smooth"});
  // Some engines ignore programmatic smooth scrolling entirely. If nothing has
  // moved shortly after, jump — a button that does nothing is the worst case.
  setTimeout(() => {
    if (window.scrollY < from) return;                 // it is animating, leave it
    // "instant" overrides the CSS scroll-behavior, which would otherwise smooth
    // this call too — and smooth is exactly what did not work.
    window.scrollTo({top: 0, behavior: "instant"});
  }, 320);
});

/* Numbers count up the first time they come into view. */
const counters = document.querySelectorAll("[data-count]");
if (counters.length) {
  const countObserver = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      countObserver.unobserve(entry.target);
      const target = parseFloat(entry.target.dataset.count);
      if (!isFinite(target) || reduced) continue;
      const started = performance.now();
      const span = 1100;
      const step = (now) => {
        const progress = Math.min((now - started) / span, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        entry.target.textContent = Math.round(target * eased).toLocaleString();
        if (progress < 1) requestAnimationFrame(step);
        else entry.target.textContent = target.toLocaleString();
      };
      requestAnimationFrame(step);
    }
  }, {threshold: 0.4});
  counters.forEach(el => countObserver.observe(el));
}

/* "Open now", worked out in the visitor's own timezone from the printed hours. */
const flag = document.querySelector(".openflag");
if (flag && flag.dataset.week) {
  const week = JSON.parse(flag.dataset.week);
  const now = new Date();
  const today = ["sun","mon","tue","wed","thu","fri","sat"][now.getDay()];
  const span = week[today];
  const label = flag.querySelector("span");
  if (!span || span === "closed") {
    label.textContent = "Closed today";
    flag.style.opacity = ".75";
  } else {
    const [from, to] = span.split("-").map(v => parseInt(v, 10));
    const mins = now.getHours() * 100 + now.getMinutes();
    label.textContent = (mins >= from && mins <= to)
      ? "Open now" : "Closed right now";
  }
}
'''
