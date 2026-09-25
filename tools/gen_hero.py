#!/usr/bin/env python3
"""Generates images/hero_overview.svg - the figure at the top of the page.

Geometry is reconstructed from the paper rather than traced from a render:

  leader      x0(t)=0.1+0.3t, y0(t)=-0.6+sin(pi t/10)      (Sec. Results)
  offsets     p_i = p_0 - Delta_i, Delta = [0,-.5],[.5,-1],[-.5,-1]
  starts      q1=[.5,-.5]  q2=[-.5,-.5]  q3=[1,-.5]  q0=[.1,-.6]
  graph       0->1, 1->2, 1->3, 3->2                       (Fig. communication graph)

The follower transient is a fitted envelope, not logged data: the error holds
through the first ~3 s while the nonholonomic vehicles align, then decays so the
snapshot positions land where Fig. "quy dao" puts them (converged by ~25 s, agent 2
slowest), settling into the documented 0.00-0.05 m residual band.

Axes are equal-scale on purpose - a formation figure that stretches one axis
misreports the shape it exists to show.

Run:  python3 tools/gen_hero.py
"""
import math
import pathlib

# -- palette: slots 1-3 of the data-viz reference palette (validated all-pairs,
# light mode, white surface: worst normal dE 24.0, worst CVD dE 9.2). The leader
# is deliberately NOT a categorical slot - it is a reference path, so it wears
# neutral ink plus a dash pattern.
INK, MUTED, GRID = "#10182a", "#5b667a", "#e6ecf3"
LEADER = "#10182a"
SERIES = {1: "#2a78d6", 2: "#eb6834", 3: "#1baf7a"}

OFFSET = {1: (0.0, 0.5), 2: (-0.5, 1.0), 3: (0.5, 1.0)}
START = {1: (0.5, -0.5), 2: (-0.5, -0.5), 3: (1.0, -0.5)}
TAU = {1: 9.5, 2: 11.0, 3: 8.5}          # agent 2 is the slow one (coupled to both)
HOLD, SHAPE_P = 3.0, 1.386               # alignment delay, envelope exponent
RESID = {1: (0.025, 0.7), 2: (0.030, 2.1), 3: (0.022, 4.0)}   # amp (m), phase
EDGES = [(0, 1), (1, 2), (1, 3), (3, 2)]
SNAPS = [5, 15, 25, 35]
T_END = 50.0

# -- plot frame (equal scale on both axes) -------------------------------------
PPM = 66.0
XMIN, XMAX = -1.05, 16.35
YMIN, YMAX = -2.25, 2.05
ML, MR, MT, MB = 58, 132, 46, 52
PW, PH = (XMAX - XMIN) * PPM, (YMAX - YMIN) * PPM

# -- formation strip: the same snapshots, drawn leader-relative and magnified,
# because the deviations that matter (metres early, centimetres late) are
# invisible at the scale the whole 15 m run has to be drawn at.
STRIP_T = SNAPS + [int(T_END)]
STRIP_PPM, STRIP_R = 48.0, 1.30          # px/m inside a glyph, half-extent (m)
GLYPH = 2 * STRIP_R * STRIP_PPM
STRIP_TOP, STRIP_LAB = 30, 26
W = ML + PW + MR
H = MT + PH + MB + STRIP_TOP + GLYPH + STRIP_LAB


def leader(t):
    return 0.1 + 0.3 * t, -0.6 + math.sin(math.pi * t / 10.0)


def agent(i, t):
    lx, ly = leader(t)
    ox, oy = OFFSET[i]
    tx, ty = lx + ox, ly + oy
    sx, sy = START[i]
    e0x, e0y = sx - (0.1 + ox), sy - (-0.6 + oy)
    k = math.exp(-((max(0.0, t - HOLD) / TAU[i]) ** SHAPE_P))
    amp, ph = RESID[i]
    wob = amp * math.sin(0.9 * t + ph) * (1.0 - k)
    return tx + e0x * k, ty + e0y * k + wob


def pos(which, t):
    return leader(t) if which == 0 else agent(which, t)


def sx(x):
    return ML + (x - XMIN) * PPM


def sy(y):
    return MT + (YMAX - y) * PPM


def path(fn, t0=0.0, t1=T_END, n=900):
    pts = [fn(t0 + (t1 - t0) * k / n) for k in range(n + 1)]
    d = [f"M {sx(pts[0][0]):.1f} {sy(pts[0][1]):.1f}"]
    d += [f"L {sx(x):.1f} {sy(y):.1f}" for x, y in pts[1:]]
    return " ".join(d)


def main():
    o = []
    add = o.append
    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H:.0f}" '
        f'width="{W:.0f}" height="{H:.0f}" font-family="Google Sans, Inter, system-ui, '
        f'Helvetica, Arial, sans-serif" role="img" aria-labelledby="ttl">')
    add('<title id="ttl">Three wheeled mobile robots converge to a rigid formation '
        'while tracking a serpentine virtual leader over 50 seconds.</title>')
    add(f'<rect width="{W:.0f}" height="{H:.0f}" fill="#ffffff"/>')

    # -- grid: recessive, 2 m major ------------------------------------------
    g = [f'<g stroke="{GRID}" stroke-width="1">']
    x = -0.0
    while x <= 16.01:
        g.append(f'<line x1="{sx(x):.1f}" y1="{MT}" x2="{sx(x):.1f}" y2="{MT + PH:.1f}"/>')
        x += 2
    y = -2.0
    while y <= 2.01:
        g.append(f'<line x1="{ML}" y1="{sy(y):.1f}" x2="{ML + PW:.1f}" y2="{sy(y):.1f}"/>')
        y += 1
    g.append('</g>')
    add("".join(g))

    # -- axes ----------------------------------------------------------------
    add(f'<g stroke="{MUTED}" stroke-width="1.2" stroke-opacity=".55" fill="none">'
        f'<line x1="{ML}" y1="{MT + PH:.1f}" x2="{ML + PW:.1f}" y2="{MT + PH:.1f}"/>'
        f'<line x1="{ML}" y1="{MT}" x2="{ML}" y2="{MT + PH:.1f}"/></g>')
    t = [f'<g fill="{MUTED}" font-size="12.5">']
    x = 0.0
    while x <= 16.01:
        t.append(f'<text x="{sx(x):.1f}" y="{MT + PH + 19:.1f}" text-anchor="middle">{x:.0f}</text>')
        x += 2
    y = -2.0
    while y <= 2.01:
        t.append(f'<text x="{ML - 10}" y="{sy(y) + 4.3:.1f}" text-anchor="end">{y:.0f}</text>')
        y += 1
    t.append(f'<text x="{ML + PW / 2:.1f}" y="{MT + PH + 41:.1f}" text-anchor="middle" '
             f'font-size="13" font-weight="600">x (m)</text>')
    t.append(f'<text transform="translate({ML - 40},{MT + PH / 2:.1f}) rotate(-90)" '
             f'text-anchor="middle" font-size="13" font-weight="600">y (m)</text>')
    t.append('</g>')
    add("".join(t))

    # -- snapshot linkages: the communication graph, drawn faintly ------------
    for ts in SNAPS:
        seg = []
        for a, b in EDGES:
            ax, ay = pos(a, ts)
            bx, by = pos(b, ts)
            seg.append(f'<line x1="{sx(ax):.1f}" y1="{sy(ay):.1f}" '
                       f'x2="{sx(bx):.1f}" y2="{sy(by):.1f}"/>')
        add(f'<g stroke="{MUTED}" stroke-width="1.25" stroke-opacity=".45" '
            f'stroke-dasharray="3 3">{"".join(seg)}</g>')

    # -- trajectories ---------------------------------------------------------
    add(f'<path d="{path(leader)}" fill="none" stroke="{LEADER}" stroke-width="2" '
        f'stroke-opacity=".55" stroke-dasharray="7 5" stroke-linecap="round"/>')
    for i in (1, 2, 3):
        add(f'<path d="{path(lambda t, i=i: agent(i, t))}" fill="none" '
            f'stroke="{SERIES[i]}" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round"/>')

    # -- start markers (hollow) and snapshot dots -----------------------------
    for i in (0, 1, 2, 3):
        c = LEADER if i == 0 else SERIES[i]
        x0, y0 = pos(i, 0.0)
        add(f'<circle cx="{sx(x0):.1f}" cy="{sy(y0):.1f}" r="4.5" fill="#ffffff" '
            f'stroke="{c}" stroke-width="2"/>')
        for ts in SNAPS:
            px, py = pos(i, ts)
            add(f'<circle cx="{sx(px):.1f}" cy="{sy(py):.1f}" r="3.4" fill="{c}" '
                f'fill-opacity=".85" stroke="#ffffff" stroke-width="1.4"/>')

    # -- snapshot time labels, placed on whichever side has the free space ----
    for ts in SNAPS:
        xs = [pos(i, ts) for i in (0, 1, 2, 3)]
        cx = sum(p[0] for p in xs) / 4
        lo, hi = min(p[1] for p in xs), max(p[1] for p in xs)
        ly = sy(lo) + 21 if (lo + hi) / 2 < 0 else sy(hi) - 13
        add(f'<text x="{sx(cx):.1f}" y="{ly:.1f}" text-anchor="middle" '
            f'font-size="12" font-weight="700" fill="{MUTED}">{ts} s</text>')
    add(f'<text x="{sx(pos(2, 0)[0]) - 12:.1f}" y="{sy(pos(2, 0)[1]) + 5:.1f}" '
        f'text-anchor="end" font-size="12" font-weight="700" fill="{MUTED}">0 s</text>')

    # -- the locked formation at 50 s: bold edges, then filled marks ----------
    seg = []
    for a, b in EDGES:
        ax, ay = pos(a, T_END)
        bx, by = pos(b, T_END)
        seg.append(f'<line x1="{sx(ax):.1f}" y1="{sy(ay):.1f}" '
                   f'x2="{sx(bx):.1f}" y2="{sy(by):.1f}"/>')
    tri = " ".join(f"{sx(pos(i, T_END)[0]):.1f},{sy(pos(i, T_END)[1]):.1f}" for i in (2, 1, 3))
    add(f'<polygon points="{tri}" fill="{INK}" fill-opacity=".05"/>')
    add(f'<g stroke="{INK}" stroke-width="1.8" stroke-opacity=".5">{"".join(seg)}</g>')
    for i in (0, 1, 2, 3):
        c = LEADER if i == 0 else SERIES[i]
        px, py = pos(i, T_END)
        add(f'<circle cx="{sx(px):.1f}" cy="{sy(py):.1f}" r="5.6" fill="{c}" '
            f'stroke="#ffffff" stroke-width="2"/>')

    # -- direct labels: colour rides the swatch, the text stays ink -----------
    # Connectors leave each mark on a short horizontal stub before turning, so
    # they never cut across the locked formation they are pointing at.
    ends = sorted(((pos(i, T_END)[1], i) for i in (0, 1, 2, 3)), reverse=True)
    lab_x = ML + PW + 34
    top = MT + PH / 2 - (len(ends) - 1) * 22 / 2 - 18
    for k, (_, i) in enumerate(ends):
        c = LEADER if i == 0 else SERIES[i]
        px, py = pos(i, T_END)
        ly = top + k * 22
        x0, y0 = sx(px) + 8, sy(py)
        add(f'<path d="M {x0:.1f} {y0:.1f} H {x0 + 9:.1f} L {lab_x - 15:.1f} {ly - 4:.1f} '
            f'H {lab_x - 12:.1f}" fill="none" stroke="{c}" stroke-width="1.5" '
            f'stroke-opacity=".45" stroke-linejoin="round"/>')
        add(f'<circle cx="{lab_x - 7:.1f}" cy="{ly - 4:.1f}" r="3.6" fill="{c}"/>')
        name = "Leader" if i == 0 else f"Agent {i}"
        add(f'<text x="{lab_x + 1:.1f}" y="{ly:.1f}" font-size="12.5" font-weight="650" '
            f'fill="{INK}">{name}</text>')

    # -- legend: colour in the swatch, never in the type ---------------------
    lx = ML + 2
    add(f'<g font-size="12.5" fill="{MUTED}">')
    add(f'<line x1="{lx}" y1="{MT - 18}" x2="{lx + 22}" y2="{MT - 18}" stroke="{LEADER}" '
        f'stroke-width="2" stroke-opacity=".55" stroke-dasharray="7 5"/>')
    add(f'<text x="{lx + 28}" y="{MT - 14}">Virtual leader (reference)</text>')
    lx += 178
    for i in (1, 2, 3):
        add(f'<line x1="{lx}" y1="{MT - 18}" x2="{lx + 22}" y2="{MT - 18}" '
            f'stroke="{SERIES[i]}" stroke-width="2"/>')
        add(f'<text x="{lx + 28}" y="{MT - 14}">Agent {i}</text>')
        lx += 96
    add(f'<line x1="{lx}" y1="{MT - 18}" x2="{lx + 22}" y2="{MT - 18}" stroke="{MUTED}" '
        f'stroke-width="1.1" stroke-opacity=".45" stroke-dasharray="3 3"/>')
    add(f'<text x="{lx + 28}" y="{MT - 14}">Communication graph</text>')
    add('</g>')

    # -- formation strip ------------------------------------------------------
    # Same snapshots, leader-relative and magnified ~2.3x, each against the
    # target shape: what the main panel cannot show is a centimetre error at
    # 15 m scale, and that is exactly the quantity converging.
    sy0 = MT + PH + MB + STRIP_TOP
    add(f'<line x1="{ML}" y1="{sy0 - STRIP_TOP + 10:.1f}" x2="{ML + PW:.1f}" '
        f'y2="{sy0 - STRIP_TOP + 10:.1f}" stroke="{GRID}" stroke-width="1"/>')
    add(f'<text x="{ML}" y="{sy0 - 6:.1f}" font-size="12" font-weight="700" '
        f'fill="{MUTED}">Formation shape, leader-relative '
        f'<tspan font-weight="450">(dashed = target; magnified)</tspan></text>')

    n = len(STRIP_T)
    step = PW / n
    for k, ts in enumerate(STRIP_T):
        cx = ML + step * (k + 0.5)
        cy = sy0 + GLYPH / 2 + 6
        lx0, ly0 = pos(0, ts)
        final = ts == int(T_END)
        add(f'<rect x="{cx - GLYPH / 2:.1f}" y="{sy0:.1f}" width="{GLYPH:.1f}" '
            f'height="{GLYPH:.1f}" rx="16" fill="{"#eef5ff" if final else "#f6f9fc"}" '
            f'stroke="{"#cfe0f5" if final else GRID}" stroke-width="1"/>')

        def gx(x):
            return cx + (x - lx0) * STRIP_PPM

        def gy(y):
            return cy - (y - ly0) * STRIP_PPM

        # realised shape first, target outline over it: once converged the two
        # coincide, and drawing the target on top is what makes that readable
        # instead of looking like the reference vanished.
        seg = []
        for a, b in EDGES:
            ax, ay = pos(a, ts)
            bx, by = pos(b, ts)
            seg.append(f'<line x1="{gx(ax):.1f}" y1="{gy(ay):.1f}" '
                       f'x2="{gx(bx):.1f}" y2="{gy(by):.1f}"/>')
        add(f'<g stroke="{INK}" stroke-width="1.5" stroke-opacity=".4">{"".join(seg)}</g>')
        tgt = " ".join(f"{gx(lx0 + OFFSET[i][0]):.1f},{gy(ly0 + OFFSET[i][1]):.1f}"
                       for i in (2, 1, 3))
        add(f'<polygon points="{tgt}" fill="none" stroke="{MUTED}" stroke-width="1.3" '
            f'stroke-opacity=".7" stroke-dasharray="4 3"/>')
        for i in (0, 1, 2, 3):
            c = LEADER if i == 0 else SERIES[i]
            px, py = pos(i, ts)
            r = 4.6 if i else 3.6
            add(f'<circle cx="{gx(px):.1f}" cy="{gy(py):.1f}" r="{r}" fill="{c}" '
                f'stroke="#ffffff" stroke-width="1.6"/>')
        add(f'<text x="{cx:.1f}" y="{sy0 + GLYPH + STRIP_LAB - 8:.1f}" '
            f'text-anchor="middle" font-size="12" font-weight="700" '
            f'fill="{INK if ts == int(T_END) else MUTED}">{ts} s</text>')

    add('</svg>')

    out = pathlib.Path(__file__).resolve().parent.parent / "images" / "hero_overview.svg"
    out.write_text("\n".join(o), encoding="utf-8")

    # -- geometry assertions: the figure must not quietly drift off the paper --
    assert abs(leader(50)[0] - 15.1) < 1e-9 and abs(leader(50)[1] + 0.6) < 1e-9
    for i in (1, 2, 3):
        ex, ey = agent(i, T_END)
        tx = leader(50)[0] + OFFSET[i][0]
        ty = leader(50)[1] + OFFSET[i][1]
        assert math.hypot(ex - tx, ey - ty) < 0.05, f"agent {i} outside residual band"
        assert math.hypot(*[a - b for a, b in zip(agent(i, 0.0), START[i])]) < 1e-9
    print(f"wrote {out}  ({W:.0f}x{H:.0f}, {PPM:g} px/m, equal aspect)")


if __name__ == "__main__":
    main()
