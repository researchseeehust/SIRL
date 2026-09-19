#!/usr/bin/env python3
"""Generates images/algorithm_diagram.svg.

Boxes are sized from measured text rather than hand-tuned numbers, because the
page's font stack (Google Sans -> Inter -> system-ui -> Helvetica) is not the
font any checker has locally, and Greek/maths glyphs come from a fallback face
that is wider than the Latin one. Measurement therefore uses DejaVu Sans, which
covers every glyph used here and is wider than Arial, so every box errs large.

Run:  python3 tools/gen_diagram.py [--preview out.png]
It also renders an optional PNG proof and asserts the geometry is sane.
"""
import re, sys, html, unicodedata
from PIL import Image, ImageDraw, ImageFont

REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
TOK = re.compile(r'([_^*])\{([^}]*)\}')
_fc = {}

def _f(path, size):
    k = (path, round(size * 4))
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, int(round(size * 4)))
    return _fc[k]

def _run_w(txt, size, bold):
    f = _f(BLD if bold else REG, size)
    w = 0.0
    for ch in txt:
        if unicodedata.combining(ch):
            w += 0.12 * size          # hats/dots overlay; small budget, not a full advance
            continue
        a = f.getlength(ch) / 4
        if ord(ch) > 0x24F:
            a = max(a, 0.62 * size)   # fallback faces run wide
        w += a
    return w

def measure(s, size, bold=False):
    w, i = 0.0, 0
    for m in TOK.finditer(s):
        w += _run_w(s[i:m.start()], size, bold)
        if m.group(1) == '*':
            w += _run_w(m.group(2), size, True)
        else:
            w += _run_w(m.group(2), size * 0.72, bold)
        i = m.end()
    return w + _run_w(s[i:], size, bold)

def runs(s, size):
    """(text, font-size, dy) chain. The shift back to the baseline rides on the
    next run that has content: an empty <tspan dy=..> is ignored by browsers."""
    out, i, pend = [], 0, 0.0
    def push(t, fs, extra, bold=False):
        nonlocal pend
        out.append((t, fs, pend + extra, bold)); pend = 0.0
    for m in TOK.finditer(s):
        if m.start() > i:
            push(s[i:m.start()], size, 0.0)
        if m.group(1) == '*':
            push(m.group(2), size, 0.0, True)
        else:
            sh = 0.30 * size if m.group(1) == '_' else -0.40 * size
            push(m.group(2), size * 0.72, sh)
            pend = -sh
        i = m.end()
    if i < len(s):
        push(s[i:], size, 0.0)
    return out

# ---------------------------------------------------------------- style ----
TITLE_FS, BODY_FS, TAG_FS, NOTE_FS = 16.0, 13.0, 11.5, 12.5
LINE_H, PAD_X, PAD_TOP, PAD_BOT = 25, 34, 32, 22
INK, MUTED, PLINE, PBG = "#10182a", "#5b667a", "#dfe5ee", "#fbfcfe"
C = {"leader": ("#c0607a", "#fdeff2"), "error": ("#2f6fb0", "#eaf2fb"),
     "critic": ("#7b4fb0", "#f3ecfa"), "bellman": ("#c07a1e", "#fdf3e6"),
     "adapt":  ("#1e8a72", "#e6f5f1"), "policy": ("#c0392b", "#fceae7"),
     "plant":  ("#2e8b3f", "#eaf6ec")}
FONT = ("'Google Sans', Inter, ui-sans-serif, system-ui, -apple-system, "
        "'Segoe UI', Helvetica, Arial, sans-serif")

def box_size(title, lines, tag=None):
    w = measure(title, TITLE_FS, True)
    for l in lines:
        w = max(w, measure(l, BODY_FS))
    if tag:
        w = max(w, measure(tag, TAG_FS, True) + 26)
    h = PAD_TOP + len(lines) * LINE_H + PAD_BOT + (28 if tag else 0)
    return w + 2 * PAD_X, h

class Scene:
    def __init__(s, w, h): s.w, s.h, s.it, s.pan = w, h, [], []
    def panel(s, x, y, w, h, t="", sub=None, dashed=False):
        s.pan.append(("panel", x, y, w, h, t, sub, dashed))
    def box(s, x, y, w, h, k, t, lines, tag=None):
        s.it.append(("box", x, y, w, h, k, t, lines, tag))
    def path(s, d, col="#46536b", dash=None, wd=2.0):
        s.it.append(("path", d, col, dash, wd))
    def flag(s, x, y, t, col="#46536b"):
        s.it.append(("flag", x, y, t, col))
    def note(s, x, y, t, col=MUTED, size=NOTE_FS, anchor="start"):
        s.it.append(("note", x, y, t, col, size, anchor))

# ------------------------------------------------------------------ svg ----
def _tspans(s, size):
    o = []
    for t, fs, dy, bd in runs(s, size):
        a = f' dy="{dy:.2f}"' if abs(dy) > 1e-9 else ''
        f = f' font-size="{fs:.1f}"' if abs(fs - size) > 1e-9 else ''
        b = ' font-weight="700"' if bd else ''
        o.append(f'<tspan{a}{f}{b}>{html.escape(t)}</tspan>')
    return ''.join(o)

def _t(x, y, s, size, weight, fill, anchor="middle", italic=False):
    st = ' font-style="italic"' if italic else ''
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}"{st}>{_tspans(s, size)}</text>')

def to_svg(sc):
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {sc.w} {sc.h}" '
         f'width="{sc.w}" height="{sc.h}" font-family="{FONT}">', '<defs>']
    for mid, col in (("ah", "#46536b"), ("ah-red", "#c0392b"), ("ah-grey", "#7a8494")):
        o.append(f'<marker id="{mid}" markerWidth="10" markerHeight="10" refX="7.5" '
                 f'refY="3.6" orient="auto"><path d="M0,0 L8,3.6 L0,7.2 Z" fill="{col}"/></marker>')
    o.append('<filter id="soft" x="-14%" y="-30%" width="128%" height="160%">'
             '<feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#103154" '
             'flood-opacity="0.10"/></filter></defs>')
    o.append(f'<rect width="{sc.w}" height="{sc.h}" fill="#ffffff"/>')
    for it in sc.pan + sc.it:
        k = it[0]
        if k == "panel":
            _, x, y, w, h, t, sub, dashed = it
            extra = ' stroke-dasharray="5,4"' if dashed else ''
            fill = "#ffffff" if dashed else PBG
            o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                     f'rx="16" ry="16" fill="{fill}" stroke="{"#c3ccda" if dashed else PLINE}" '
                     f'stroke-width="1.6"{extra}/>')
            if t:   o.append(_t(x + 28, y + 38, t, 16, 700, "#2b3542", "start"))
            if sub: o.append(_t(x + 28, y + 62, sub, NOTE_FS, 400, MUTED, "start", True))
        elif k == "box":
            _, x, y, w, h, key, t, lines, tag = it
            st, fl = C[key]
            o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                     f'rx="13" ry="13" fill="{fl}" stroke="{st}" stroke-width="1.7" '
                     f'filter="url(#soft)"/>')
            cx = x + w / 2
            o.append(_t(cx, y + 30, t, TITLE_FS, 700, INK))
            for n, ln in enumerate(lines):
                o.append(_t(cx, y + 30 + (n + 1) * LINE_H, ln, BODY_FS, 400, "#3a4552"))
            if tag:
                tw = measure(tag, TAG_FS, True) + 24
                o.append(f'<rect x="{cx-tw/2:.1f}" y="{y+h-28:.1f}" width="{tw:.1f}" '
                         f'height="20" rx="10" ry="10" fill="{st}" opacity="0.13"/>')
                o.append(_t(cx, y + h - 13.5, tag, TAG_FS, 600, st))
        elif k == "path":
            _, d, col, dash, wd = it
            mk = {"#46536b": "ah", "#c0392b": "ah-red", "#7a8494": "ah-grey"}[col]
            ds = f' stroke-dasharray="{dash}"' if dash else ''
            o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{wd}"{ds} '
                     f'marker-end="url(#{mk})"/>')
        elif k == "flag":
            _, x, y, t, col = it
            w_ = measure(t, NOTE_FS) + 18
            o.append(f'<rect x="{x-w_/2:.1f}" y="{y-14:.1f}" width="{w_:.1f}" height="21" '
                     f'rx="7" ry="7" fill="{PBG}" opacity="0.97"/>')
            o.append(_t(x, y + 1.5, t, NOTE_FS, 500, col, "middle", True))
        elif k == "note":
            _, x, y, t, col, size, anchor = it
            o.append(_t(x, y, t, size, 400, col, anchor, True))
    o.append('</svg>')
    return '\n'.join(o)

# -------------------------------------------------------------- preview ----
S = 2
_fd = {}
def _pf(path, size):
    """font at preview scale (the measuring fonts are 4x and must not be reused)"""
    k = (path, round(size * S, 1))
    if k not in _fd:
        _fd[k] = ImageFont.truetype(path, max(1, int(round(size * S))))
    return _fd[k]

def _draw(d, x, y, s, size, bold, fill, anchor):
    pen = x - measure(s, size, bold) / 2 if anchor == "middle" else x
    cy = y
    for t, fs, dy, bd in runs(s, size):
        cy += dy
        d.text((pen * S, cy * S), t, font=_pf(BLD if (bold or bd) else REG, fs),
               fill=fill, anchor="ls")
        pen += measure(t, fs, bold or bd)

def to_png(sc, path):
    im = Image.new("RGB", (sc.w * S, sc.h * S), "white"); d = ImageDraw.Draw(im)
    for it in sc.pan + sc.it:
        k = it[0]
        if k == "panel":
            _, x, y, w, h, t, sub, dashed = it
            d.rounded_rectangle([x*S, y*S, (x+w)*S, (y+h)*S], 16*S,
                                fill="#ffffff" if dashed else PBG,
                                outline="#c3ccda" if dashed else PLINE, width=2)
            if t:   _draw(d, x+28, y+38, t, 16, True, "#2b3542", "start")
            if sub: _draw(d, x+28, y+62, sub, NOTE_FS, False, MUTED, "start")
        elif k == "box":
            _, x, y, w, h, key, t, lines, tag = it
            st, fl = C[key]
            d.rounded_rectangle([x*S, y*S, (x+w)*S, (y+h)*S], 13*S, fill=fl, outline=st, width=3)
            cx = x + w/2
            _draw(d, cx, y+30, t, TITLE_FS, True, INK, "middle")
            for n, ln in enumerate(lines):
                _draw(d, cx, y+30+(n+1)*LINE_H, ln, BODY_FS, False, "#3a4552", "middle")
            if tag:
                tw = measure(tag, TAG_FS, True) + 24
                d.rounded_rectangle([(cx-tw/2)*S,(y+h-28)*S,(cx+tw/2)*S,(y+h-8)*S],10*S,fill="#e9edf4")
                _draw(d, cx, y+h-13.5, tag, TAG_FS, True, st, "middle")
        elif k == "path":
            _, dd, col, dash, wd = it
            n = [float(v) for v in re.findall(r'-?\d+\.?\d*', dd)]
            if ' C ' in dd:
                p=[(n[0],n[1]),(n[2],n[3]),(n[4],n[5]),(n[6],n[7])]; pts=[]
                for q in range(41):
                    tt=q/40; u=1-tt
                    pts.append(((u**3*p[0][0]+3*u*u*tt*p[1][0]+3*u*tt*tt*p[2][0]+tt**3*p[3][0])*S,
                                (u**3*p[0][1]+3*u*u*tt*p[1][1]+3*u*tt*tt*p[2][1]+tt**3*p[3][1])*S))
                d.line(pts, fill=col, width=int(wd*S))
            else:
                d.line([n[0]*S,n[1]*S,n[2]*S,n[3]*S], fill=col, width=int(wd*S))
        elif k == "flag":
            _, x, y, t, col = it
            w_ = measure(t, NOTE_FS) + 18
            d.rounded_rectangle([(x-w_/2)*S,(y-14)*S,(x+w_/2)*S,(y+7)*S], 7*S, fill=PBG)
            _draw(d, x, y+1.5, t, NOTE_FS, False, col, "middle")
        elif k == "note":
            _, x, y, t, col, size, anchor = it
            _draw(d, x, y, t, size, False, col, anchor)
    im.save(path)

# =========================================================== the diagram ====
A1 = [("leader", "Virtual leader + graph G",
       ["q_{0}(t),  η_{0}(t)", "neighbours j ∈ ℕ_{i},  link b_{i}"], None),
      ("error", "Neighbourhood error",
       ["δ_{i} = [δ_{pi} ; δ_{ηi}] ∈ ℝ^{5}"], None),
      ("critic", "Critic NN",
       ["φ_{i}(δ_{i}) ∈ ℝ^{15},  ∇φ_{i}", "quadratic bases, eq. (25)"], "detail in (b)"),
      ("bellman", "IRL Bellman residual Ψ_{i}",
       ["Ψ_{i} = Δφ_{i}^{T} Ŵ_{i} + ϱ_{i}", "T-window + experience replay"], None)]
A2 = [("plant", "WMR plant",
       ["ṗ_{i} = H_{i}(p_{i}) η_{i}", "driven by û_{i}, ϑ̂_{i}, Itô noise"], None),
      ("policy", "H∞ policy",
       ["û_{i}   eq. (32)", "ϑ̂_{i}   eq. (33)"], None),
      ("adapt", "Adaptive law",
       ["dŴ_{i}/dt = −α_{i}(⋯)Ψ_{i} + ξ_{i}Θ_{i}", "eq. (35)"], "model-free in (c)")]
B1 = [("critic", "φ_{i}(δ_{i})", ["quadratic bases, eq. (25)"], None),
      ("critic", "Δφ_{i}(t)", ["φ_{i}(t) − φ_{i}(t−T)"], None)]
C1 = [("policy", "Behaviour signal", ["u_{j} = û_{j} + e_{j}", "bounded probe e_{j}"], None),
      ("adapt", "Target policy", ["û_{j},  ϑ̂_{j}", "actor NN, current weights"], None)]

def sizes(specs): return [box_size(t, l, g) for (_, t, l, g) in specs]

def build():
    # --- panel (a): row 2 sits directly under boxes 2..4 of row 1, so the loop
    #     closes as a rectangle instead of a tangle of diagonals.
    s1, s2 = sizes(A1), sizes(A2)
    gap = 48
    while True:
        cent = []
        x = 0.0
        for w, _ in s1:
            cent.append(x + w / 2); x += w + gap
        ok = all((cent[i + 2] - cent[i + 1]) - (s2[i][0] + s2[i + 1][0]) / 2 >= 34
                 for i in range(len(s2) - 1))
        if ok or gap > 200: break
        gap += 4
    row1_w = sum(w for w, _ in s1) + gap * (len(s1) - 1)
    h1, h2 = max(h for _, h in s1), max(h for _, h in s2)

    PAW = row1_w + 180
    W = PAW + 48
    ax, ay = 24, 24
    x0 = ax + (PAW - row1_w) / 2
    cent = []
    x = x0
    for w, _ in s1:
        cent.append(x + w / 2); x += w + gap

    chip_y, chip_h = 78, 38
    r1y = chip_y + chip_h + 30
    r2y = r1y + h1 + 74
    PAH = (r2y + h2 + 34) - ay

    pw = (PAW - 40) / 2
    bx, cx_ = ax, ax + pw + 40
    py = ay + PAH + 30

    sc = Scene(int(W), 10)
    sc.panel(ax, ay, PAW, PAH, "(a)  Per-agent online critic-only IRL / H∞ control loop")

    r1 = []
    for (k, t, l, g), (w, _), c in zip(A1, s1, cent):
        sc.box(c - w / 2, r1y, w, h1, k, t, l, g); r1.append((c - w / 2, r1y, w, h1))
    r2 = []
    for (k, t, l, g), (w, _), c in zip(A2, s2, cent[1:]):
        sc.box(c - w / 2, r2y, w, h2, k, t, l, g); r2.append((c - w / 2, r2y, w, h2))

    ymid1, ymid2 = r1y + h1 / 2, r2y + h2 / 2
    for a, b in zip(r1, r1[1:]):
        sc.path(f"M {a[0]+a[2]:.1f} {ymid1:.1f} L {b[0]-7:.1f} {ymid1:.1f}")

    nb = "neighbour data:   δ_{j}, ∇φ_{j} → Θ_{i}       û_{j}, ϑ̂_{j} → ϱ_{i}"
    nw = measure(nb, NOTE_FS) + 52
    sc.panel(cent[3] - nw / 2, chip_y, nw, chip_h, dashed=True)
    sc.note(cent[3], chip_y + 24, nb, MUTED, NOTE_FS, "middle")
    sc.path(f"M {cent[3]:.1f} {chip_y+chip_h:.1f} L {cent[3]:.1f} {r1y-7:.1f}",
            "#7a8494", "5,4", 1.8)

    sc.path(f"M {cent[3]:.1f} {r1y+h1:.1f} L {cent[3]:.1f} {r2y-7:.1f}")
    sc.flag(cent[3] + 104, (r1y + h1 + r2y) / 2, "Ψ_{i},  history stack Z_{i}")

    for a, b, lab in ((r2[2], r2[1], "Ŵ_{i}"), (r2[1], r2[0], "û_{i}, ϑ̂_{i}")):
        sc.path(f"M {a[0]:.1f} {ymid2:.1f} L {b[0]+b[2]+7:.1f} {ymid2:.1f}")
        sc.flag((a[0] + b[0] + b[2]) / 2, ymid2 - 20, lab)

    sc.path(f"M {cent[1]:.1f} {r2y:.1f} L {cent[1]:.1f} {r1y+h1+7:.1f}", "#c0392b")
    sc.flag(cent[1] - 118, (r1y + h1 + r2y) / 2, "state feedback  p_{i}, η_{i}", "#c0392b")

    # --- panel (b)
    sb = sizes(B1); gb = 44
    rbw = sum(w for w, _ in sb) + gb; hb = max(h for _, h in sb)
    rby = py + 96
    x = bx + (pw - rbw) / 2
    rb = []
    for (k, t, l, g), (w, _) in zip(B1, sb):
        sc.box(x, rby, w, hb, k, t, l, g); rb.append((x, rby, w, hb)); x += w + gb
    sc.path(f"M {rb[0][0]+rb[0][2]:.1f} {rby+hb/2:.1f} L {rb[1][0]-7:.1f} {rby+hb/2:.1f}")

    hs_t = "History stack  Z_{i}"
    hs_l = ["Z_{i} = { Δφ̄_{i}^{1}, …, Δφ̄_{i}^{l} },   rank(Z_{i}) = L = 15",
            "l = 20 > L stored samples", "replaces persistence of excitation"]
    hw, hh = box_size(hs_t, hs_l); hw = max(hw, pw - 72)
    hy = rby + hb + 62
    sc.path(f"M {rb[1][0]+rb[1][2]/2:.1f} {rby+hb:.1f} L {rb[1][0]+rb[1][2]/2:.1f} {hy-7:.1f}")
    sc.note(rb[1][0] + rb[1][2] / 2 + 12, hy - 26, "recorded", MUTED, 12, "start")
    sc.box(bx + (pw - hw) / 2, hy, hw, hh, "bellman", hs_t, hs_l)
    nb_y = hy + hh + 34
    sc.note(bx + (pw - hw) / 2, nb_y, "Checkable on the recorded data — not an a-priori", MUTED)
    sc.note(bx + (pw - hw) / 2, nb_y + 20, "requirement on the trajectory.", MUTED)

    # --- panel (c)
    scz = sizes(C1); gc = 44
    rcw = sum(w for w, _ in scz) + gc; hc = max(h for _, h in scz)
    rcy = rby
    x = cx_ + (pw - rcw) / 2
    rc = []
    for (k, t, l, g), (w, _) in zip(C1, scz):
        sc.box(x, rcy, w, hc, k, t, l, g); rc.append((x, rcy, w, hc)); x += w + gc

    ob_t = "Off-policy Bellman equation"
    ob_l = ["Λ_{i}(t)^{T} *{Z}_{i} + ϱ_{i}(t) = ε_{Bi}(t)    eq. (48)",
            "g_{i}, k_{i} lumped into *{Z}_{i}", "drift f_{ei} and diffusion Σ_{i} cancel"]
    ow, oh = box_size(ob_t, ob_l); ow = max(ow, pw - 96)
    oy = rcy + hc + 62
    ox = cx_ + (pw - ow) / 2
    for b, frac in ((rc[0], 0.30), (rc[1], 0.70)):
        bc = b[0] + b[2] / 2; tx = ox + ow * frac
        sc.path(f"M {bc:.1f} {b[1]+b[3]:.1f} C {bc:.1f} {b[1]+b[3]+24:.1f}, "
                f"{tx:.1f} {oy-26:.1f}, {tx:.1f} {oy-7:.1f}")
    sc.box(ox, oy, ow, oh, "bellman", ob_t, ob_l)

    mf_t = "Model-free residual  Ψ_{i}^{mf}"
    mf_l = ["drop-in inside the same adaptive law, eq. (35)"]
    mw, mh = box_size(mf_t, mf_l); mw = max(mw, ow - 90)
    my = oy + oh + 54
    sc.path(f"M {ox+ow/2:.1f} {oy+oh:.1f} L {ox+ow/2:.1f} {my-7:.1f}")
    sc.box(cx_ + (pw - mw) / 2, my, mw, mh, "plant", mf_t, mf_l)

    ph = max(nb_y + 20, my + mh) + 34 - py
    sc.panel(bx, py, pw, ph, "(b)  Critic regressor & history stack",
             "expands the Critic NN → residual path of (a)")
    sc.panel(cx_, py, pw, ph, "(c)  Model-free off-policy extension",
             "swaps Δφ_{i} → Λ_{i},  Ŵ_{i} → *{Z}_{i},  Θ_{i} → Θ_{i}^{mf}  in eq. (35)")
    sc.h = int(py + ph + 24)
    return sc

# ============================================================== checks =====
def _bez(p, t):
    u = 1 - t
    return (u**3*p[0][0] + 3*u*u*t*p[1][0] + 3*u*t*t*p[2][0] + t**3*p[3][0],
            u**3*p[0][1] + 3*u*u*t*p[1][1] + 3*u*t*t*p[2][1] + t**3*p[3][1])

def check(sc):
    errs = []
    boxes = [(i[1], i[2], i[3], i[4], i[6]) for i in sc.it if i[0] == "box"]
    panels = [(i[1], i[2], i[3], i[4]) for i in sc.pan if not i[7]]
    for a in range(len(boxes)):
        for b in range(a + 1, len(boxes)):
            x1,y1,w1,h1,n1 = boxes[a]; x2,y2,w2,h2,n2 = boxes[b]
            if x1 < x2+w2 and x1+w1 > x2 and y1 < y2+h2 and y1+h1 > y2:
                errs.append(f"hop chong nhau: {n1} / {n2}")
    for x,y,w,h,n in boxes:
        if not any(x>=px-.5 and y>=py-.5 and x+w<=px+pw+.5 and y+h<=py+ph+.5
                   for px,py,pw,ph in panels):
            errs.append(f"hop ra ngoai panel: {n}")
    for it in sc.it:
        if it[0] != "path": continue
        n = [float(v) for v in re.findall(r'-?\d+\.?\d*', it[1])]
        pts = ([_bez([(n[0],n[1]),(n[2],n[3]),(n[4],n[5]),(n[6],n[7])], q/60) for q in range(61)]
               if ' C ' in it[1] else
               [(n[0]+(n[2]-n[0])*q/60, n[1]+(n[3]-n[1])*q/60) for q in range(61)])
        for x,y,w,h,nm in boxes:
            for q,(px,py) in enumerate(pts):
                if 0.06 < q/60 < 0.94 and x+3 < px < x+w-3 and y+3 < py < y+h-3:
                    errs.append(f"mui ten xuyen hop {nm}"); break
    # text inside its box, and baseline returns to zero
    for it in sc.it:
        if it[0] != "box": continue
        _, x, y, w, h, key, t, lines, tag = it
        for s_, fs, bold in [(t, TITLE_FS, True)] + [(l, BODY_FS, False) for l in lines]:
            if measure(s_, fs, bold) > w - 16:
                errs.append(f"chu tran hop {t!r}: {s_[:30]!r}")
            cum = 0.0
            for _tx, f_, dy, _bd in runs(s_, fs):
                cum += dy
                if abs(f_ - fs) < 1e-9 and abs(cum) > 1e-6:
                    errs.append(f"lech baseline trong {t!r}")
    for it in sc.pan:
        if it[5]:
            for s_, fs in ((it[5], 16), (it[6] or "", NOTE_FS)):
                if s_ and measure(s_, fs, fs == 16) > it[3] - 50:
                    errs.append(f"tieu de panel tran: {s_[:34]!r}")
    return errs

if __name__ == "__main__":
    sc = build()
    errs = check(sc)
    out = "/home/vm-khanhtx2/paper/SIRL_webpage/images/algorithm_diagram.svg"
    open(out, "w").write(to_svg(sc))
    if "--preview" in sys.argv:
        to_png(sc, sys.argv[sys.argv.index("--preview") + 1])
    print(f"canvas {sc.w} x {sc.h}")
    print("KIEM TRA:", "sach" if not errs else "")
    for e in dict.fromkeys(errs):
        print("  !", e)
