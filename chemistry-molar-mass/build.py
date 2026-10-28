"""Build 5 Instagram slides (1080x1350) for the molar-mass post as editable SVGs
in the style of the 'Хімія' samples (white bg, coral headings, black-outlined cards)."""
import base64, os, html, math
from PIL import ImageFont
import matplotlib
matplotlib.rcParams['mathtext.fontset'] = 'cm'
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)

W, H = 1080, 1350
CORAL = '#F35A52'
STAR = '#FDDEDC'
BLACK = '#000000'
INK = '#111111'
ML = 76  # left margin
MR = 76

FONT_FILES = {
    400: '/usr/share/fonts/opentype/inter/Inter-Regular.otf',
    500: '/usr/share/fonts/opentype/inter/Inter-Medium.otf',
    600: '/usr/share/fonts/opentype/inter/Inter-SemiBold.otf',
    700: '/usr/share/fonts/opentype/inter/Inter-Bold.otf',
    800: '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf',
}
_fc = {}
def font(weight, size):
    k = (weight, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FONT_FILES[weight], size)
    return _fc[k]

def tw(text, weight, size, ls=0):
    if text.startswith('\x01'):
        return font(weight, round(size * 0.62)).getlength(text[1:])
    return font(weight, size).getlength(text) + ls * size * len(text)

def emoji_href(code):
    with open(os.path.join(HERE, 'emoji', code + '.png'), 'rb') as f:
        return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()

def esc(s):
    return html.escape(s, quote=False)

# ---------- rich text ----------
# run = (text, weight, color)

def wrap_runs(runs, size, maxw, ls=0):
    """Greedy word wrap over styled runs. '\n' in text forces a break."""
    tokens = []  # (word, weight, color) ; word may be '\n'
    for text, wgt, col in runs:
        parts = text.split('\n')
        for pi, part in enumerate(parts):
            if pi > 0:
                tokens.append(('\n', wgt, col))
            buf = ''
            for ch in part:
                buf += ch
                if ch == ' ':
                    tokens.append((buf, wgt, col)); buf = ''
            if buf:
                tokens.append((buf, wgt, col))
    lines, cur, curw = [], [], 0.0
    for word, wgt, col in tokens:
        if word == '\n':
            lines.append(cur); cur, curw = [], 0.0; continue
        ww = tw(word.rstrip(' '), wgt, size, ls)
        if cur and curw + ww > maxw:
            lines.append(cur); cur, curw = [], 0.0
            if word.strip() == '':
                continue
        cur.append((word, wgt, col))
        curw += tw(word, wgt, size, ls)
    if cur:
        lines.append(cur)
    # merge adjacent same-style, strip trailing spaces
    out = []
    for ln in lines:
        m = []
        for word, wgt, col in ln:
            if m and m[-1][1] == wgt and m[-1][2] == col and not word.startswith('\x01') and not m[-1][0].startswith('\x01'):
                m[-1] = (m[-1][0] + word, wgt, col)
            else:
                m.append((word, wgt, col))
        if m:
            m[-1] = (m[-1][0].rstrip(' '), m[-1][1], m[-1][2])
        out.append(m)
    return out

def line_width(line, size, ls=0):
    return sum(tw(t, w, size, ls) for t, w, _ in line)

def text_block(runs, x, y_top, size, maxw, lh, anchor='start', ls=0, upper=False, name=None):
    """Returns (svg, height, lines, last_line_width). y_top = top of first line box."""
    if upper:
        runs = [(t.upper(), w, c) for t, w, c in runs]
    lines = wrap_runs(runs, size, maxw, ls)
    # baseline: center cap-ish glyphs in the line box
    asc = size * 0.727  # Inter cap height
    parts = []
    for i, ln in enumerate(lines):
        base = y_top + i * lh + (lh + asc) / 2
        lw = line_width(ln, size, ls)
        lx = x if anchor == 'start' else (x - lw / 2 if anchor == 'middle' else x - lw)
        spans = ''
        for t, w, c in ln:
            if t.startswith('\x01'):  # subscript run
                sub = round(size * 0.62); sh = round(size * 0.22)
                spans += (f'<tspan font-weight="{w}" fill="{c}" font-size="{sub}" dy="{sh}">{esc(t[1:])}</tspan>'
                          f'<tspan dy="{-sh}"></tspan>')
            else:
                spans += f'<tspan font-weight="{w}" fill="{c}">{esc(t)}</tspan>'
        parts.append(f'<tspan x="{lx:.1f}" y="{base:.1f}">{spans}</tspan>')
    lsattr = f' letter-spacing="{ls*size:.2f}"' if ls else ''
    nm = f' id="{esc(name)}"' if name else ''
    svg = (f'<text{nm} font-family="Inter" font-size="{size}"{lsattr} xml:space="preserve">'
           + ''.join(parts) + '</text>')
    return svg, len(lines) * lh, lines, (line_width(lines[-1], size, ls) if lines else 0)

# ---------- math (formula as vector paths, Computer Modern like the source image) ----------

def math_path(tex, size):
    tp = TextPath((0, 0), tex, size=size, prop=FontProperties())
    verts, codes = tp.vertices, tp.codes
    d, i = [], 0
    while i < len(codes):
        c = codes[i]
        if c == Path.MOVETO:
            x, y = verts[i]; d.append(f'M{x:.2f} {-y:.2f}'); i += 1
        elif c == Path.LINETO:
            x, y = verts[i]; d.append(f'L{x:.2f} {-y:.2f}'); i += 1
        elif c == Path.CURVE3:
            (x1, y1), (x2, y2) = verts[i], verts[i + 1]
            d.append(f'Q{x1:.2f} {-y1:.2f} {x2:.2f} {-y2:.2f}'); i += 2
        elif c == Path.CURVE4:
            (x1, y1), (x2, y2), (x3, y3) = verts[i], verts[i + 1], verts[i + 2]
            d.append(f'C{x1:.2f} {-y1:.2f} {x2:.2f} {-y2:.2f} {x3:.2f} {-y3:.2f}'); i += 3
        elif c == Path.CLOSEPOLY:
            d.append('Z'); i += 1
        else:
            i += 1
    ext = tp.get_extents()
    return ' '.join(d), ext.x0, -ext.y1, ext.width, ext.height  # bbox in svg coords

# ---------- decorations ----------

def star(cx, cy, r_out, r_in, rot=0, sw=16, pts=5, wobble=None):
    """Hand-drawn-ish outline star like the samples."""
    coords = []
    for k in range(pts * 2):
        r = r_out if k % 2 == 0 else r_in
        if wobble:
            r *= wobble[k % len(wobble)]
        a = math.radians(rot + k * 180 / pts - 90)
        coords.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d = 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in coords) + ' Z'
    return (f'<path d="{d}" fill="none" stroke="{STAR}" stroke-width="{sw}" '
            f'stroke-linejoin="round" stroke-linecap="round"/>')

def card(x, y, w, h, r=28, sw=2):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="#FFFFFF" '
            f'stroke="{BLACK}" stroke-width="{sw}"/>')

def emoji(code, x, y, s):
    return f'<image x="{x:.1f}" y="{y:.1f}" width="{s}" height="{s}" href="{emoji_href(code)}"/>'

def badge(label, x, y, s=112):
    """Element tile in place of an emoji (H, O), Apple-emoji-like rounded square."""
    fs = 64 if len(label) == 1 else 50
    return (f'<rect x="{x}" y="{y}" width="{s}" height="{s}" rx="26" fill="{CORAL}"/>'
            f'<text font-family="Inter" font-weight="700" font-size="{fs}" fill="#FFFFFF" '
            f'text-anchor="middle" x="{x + s/2:.1f}" y="{y + s/2 + fs*0.727/2:.1f}">{esc(label)}</text>')

def molecule(cx, cy, scale=1.0, flip=False):
    """Chrome ball-and-stick H2O model, grayscale like the sample-3 render."""
    s = scale
    ang = math.radians(104.5 / 2)
    L = 300 * s
    sgn = -1 if flip else 1
    o = (cx, cy)
    h1 = (cx - L * math.sin(ang) * sgn, cy + L * math.cos(ang))
    h2 = (cx + L * math.sin(ang) * sgn, cy + L * math.cos(ang))
    ro, rh = 150 * s, 100 * s
    out = ['<defs>'
           '<radialGradient id="ball" cx="0.35" cy="0.3" r="0.75">'
           '<stop offset="0" stop-color="#FFFFFF"/><stop offset="0.25" stop-color="#E4E4E4"/>'
           '<stop offset="0.65" stop-color="#8E8E8E"/><stop offset="0.9" stop-color="#3A3A3A"/>'
           '<stop offset="1" stop-color="#5A5A5A"/></radialGradient>'
           '<radialGradient id="ballc" cx="0.35" cy="0.3" r="0.75">'
           '<stop offset="0" stop-color="#FFFFFF"/><stop offset="0.25" stop-color="#FCD3D0"/>'
           '<stop offset="0.65" stop-color="#F35A52"/><stop offset="0.9" stop-color="#9E2722"/>'
           '<stop offset="1" stop-color="#B8322C"/></radialGradient>'
           '<linearGradient id="stick" x1="0" y1="0" x2="1" y2="0">'
           '<stop offset="0" stop-color="#4A4A4A"/><stop offset="0.45" stop-color="#F2F2F2"/>'
           '<stop offset="1" stop-color="#555555"/></linearGradient>'
           '</defs>']
    for hx, hy in (h1, h2):
        dx, dy = hx - o[0], hy - o[1]
        ln = math.hypot(dx, dy)
        a = math.degrees(math.atan2(dy, dx)) - 90
        out.append(f'<rect x="{-22*s:.1f}" y="0" width="{44*s:.1f}" height="{ln:.1f}" rx="{10*s:.1f}" '
                   f'fill="url(#stick)" transform="translate({o[0]:.1f} {o[1]:.1f}) rotate({a:.2f})"/>')
    for hx, hy in (h1, h2):
        out.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{rh:.1f}" fill="url(#ball)"/>')
        out.append(f'<text font-family="Inter" font-weight="700" font-size="{70*s:.0f}" fill="#1A1A1A" '
                   f'fill-opacity="0.75" text-anchor="middle" x="{hx:.1f}" y="{hy + 26*s:.1f}">H</text>')
    out.append(f'<circle cx="{o[0]:.1f}" cy="{o[1]:.1f}" r="{ro:.1f}" fill="url(#ballc)"/>')
    out.append(f'<text font-family="Inter" font-weight="700" font-size="{100*s:.0f}" fill="#FFFFFF" '
               f'text-anchor="middle" x="{o[0]:.1f}" y="{o[1] + 36*s:.1f}">O</text>')
    return '<g id="H2O molecule">' + ''.join(out) + '</g>'

def page(name, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'<title>{esc(name)}</title>'
            f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>' + body + '</svg>')

# ---------- building blocks for "post 2" (cards) layout ----------

HEAD_SIZE, HEAD_LH = 80, 96
SUB_SIZE, SUB_LH = 44, 60
CARD_X, CARD_W = 200, 804
EMO_X, EMO_S = 70, 112
CARD_TXT = 34
CARD_LH = 46
CARD_PAD_X, CARD_PAD_Y = 44, 40

def header(step_title, subtitle, sub_emoji, y=96):
    svg, h, lines, lastw = text_block([(step_title, 700, CORAL)], ML, y, HEAD_SIZE, W - ML - MR, HEAD_LH, upper=True)
    y2 = y + h + 22
    s2, h2, l2, lw2 = text_block([(subtitle, 500, BLACK)], ML, y2, SUB_SIZE, W - ML - MR - 70, SUB_LH, upper=True)
    out = svg + s2
    if sub_emoji:
        es = 56
        out += emoji(sub_emoji, ML + lw2 + 12, y2 + h2 - SUB_LH + (SUB_LH - es) / 2 - 2, es)
    return out, y2 + h2

def card_row(y, runs, icon=None, kind='emoji', min_h=0):
    tsvg, th, _, _ = text_block(runs, CARD_X + CARD_PAD_X, 0, CARD_TXT, CARD_W - 2 * CARD_PAD_X, CARD_LH)
    ch = max(min_h, th + 2 * CARD_PAD_Y)
    ty = y + (ch - th) / 2
    tsvg, _, _, _ = text_block(runs, CARD_X + CARD_PAD_X, ty, CARD_TXT, CARD_W - 2 * CARD_PAD_X, CARD_LH)
    out = card(CARD_X, y, CARD_W, ch) + tsvg
    if icon:
        iy = y + (ch - EMO_S) / 2
        out += badge(icon, EMO_X, iy) if kind == 'badge' else emoji(icon, EMO_X, iy, EMO_S)
    return out, ch

def plain(y, runs, size=CARD_TXT, lh=CARD_LH, x=ML, maxw=W - ML - MR):
    s, h, _, _ = text_block(runs, x, y, size, maxw, lh)
    return s, h

def stack(y, items, gap):
    out = ''
    for it in items:
        if isinstance(it, int):
            y += it; continue
        s, h = it(y)
        out += s
        y += h + gap
    return out, y - gap

R, B, C = 400, 700, CORAL

def run(t, w=R, c=BLACK):
    return (t, w, c)

# ================= slides =================
slides = {}

# ---- Slide 1 (post-1 style) ----
def slide1():
    body = star(1010, 140, 230, 95, rot=8, wobble=[1, 1.05, .95, 1.1, 1, .9, 1.05, 1, .95, 1.08])
    body += star(70, 1250, 210, 85, rot=-12, wobble=[1, .95, 1.08, 1, .92, 1.05, 1, 1.1, .97, 1])
    # logo (bars + name) like the sample
    lx, ly = ML, 70
    body += (f'<g id="logo"><rect x="{lx}" y="{ly+14}" width="7" height="20" fill="{BLACK}"/>'
             f'<rect x="{lx+11}" y="{ly+6}" width="7" height="28" fill="{BLACK}"/>'
             f'<rect x="{lx+22}" y="{ly}" width="7" height="34" fill="{BLACK}"/>'
             f'<rect x="{lx+33}" y="{ly+10}" width="7" height="24" fill="{BLACK}"/>'
             f'<text font-family="Inter" font-weight="700" font-size="22" fill="{BLACK}" '
             f'x="{lx+52}" y="{ly+33}">TURBO CHEMISTRY</text></g>')
    body += molecule(840, 1010, scale=0.95)
    hs, hlh = 112, 118
    s, h, _, _ = text_block([run('Як швидко\nвизначити\nмолярну\nмасу', 800, C)], ML - 4, 190, hs, 900, hlh,
                            upper=True, ls=-0.02, name='title')
    body += s
    y = 190 + h + 28
    # black label box like "СКІЛЬКИ ЧАСУ НА ЦЕ ПІДЕ?"
    bs = 64
    lab = 'СПОЛУКИ?'
    bw = tw(lab, 700, bs) + 2 * 30
    bh = 96
    body += (f'<rect x="{ML}" y="{y}" width="{bw:.0f}" height="{bh}" fill="{BLACK}"/>'
             f'<text font-family="Inter" font-weight="700" font-size="{bs}" fill="#FFFFFF" '
             f'x="{ML+30}" y="{y + (bh + bs*0.727)/2:.1f}">{lab}</text>')
    y += bh + 60
    s, h, _, _ = text_block([run('3 кроки', B), run(' — і ти впораєшся із завданням на НМТ без зайвих обчислень')],
                            ML, y, 40, 470, 54)
    body += s
    return page('Слайд 1', body)

# ---- Slide 2 ----
def slide2():
    body = star(1000, 110, 200, 82, rot=12, wobble=[1, 1.06, .94, 1.1, 1, .9, 1.04, 1, .96, 1.08])
    hs, y = header('Крок 1 —', 'Знайди формулу\nсполуки', '1f50d')
    body += hs
    items = [
        lambda yy: card_row(yy, [run('Наприклад, вода — '), run('H₂O', B, C)], '1f4a7', min_h=132),
        lambda yy: plain(yy + 6, [run('Подивись, які атоми входять до складу молекули та скільки їх:')], maxw=W - ML - MR - 40),
        lambda yy: card_row(yy, [run('H — '), run('2 атоми', B, C)], 'H', 'badge', min_h=132),
        lambda yy: card_row(yy, [run('O — '), run('1 атом', B, C)], 'O', 'badge', min_h=132),
        lambda yy: card_row(yy, [run('Маленька цифра внизу показує '), run('кількість атомів', B, C),
                                 run('. Якщо цифри немає — атом один')], '1f4a1'),
    ]
    s, end = stack(y + 80, items, 44)
    return page('Слайд 2', body + s), end

# ---- Slide 3 ----
def slide3():
    body = star(1000, 110, 200, 82, rot=-6, wobble=[1, .95, 1.07, 1, .92, 1.06, 1, 1.1, .96, 1])
    hs, y = header('Крок 2 —', 'Знайди відносні\nатомні маси', '1f4d6')
    body += hs
    def ar(el, val):
        # A with subscript r, as in Ar(H)
        return [('A', R, BLACK), ('\x01r', R, BLACK), (f'({el}) = ', R, BLACK), (val, B, C)]
    items = [
        lambda yy: card_row(yy, [run('Для цього використовуй '), run('періодичну таблицю', B, C), run(':')],
                            '269b-fe0f', min_h=150),
        lambda yy: card_row(yy, ar('H', '1'), 'H', 'badge', min_h=150),
        lambda yy: card_row(yy, ar('O', '16'), 'O', 'badge', min_h=150),
        lambda yy: card_row(yy, [run('Не потрібно вчити напам’ять маси всіх елементів — навчися '),
                                 run('швидко знаходити їх у таблиці', B, C)], '1f4a1'),
    ]
    s, end = stack(y + 90, items, 56)
    return page('Слайд 3', body + s), end

# ---- Slide 4 ----
def slide4():
    body = star(1000, 110, 200, 82, rot=20, wobble=[1, 1.04, .95, 1.08, 1, .92, 1.06, 1, .95, 1.1])
    hs, y = header('Крок 3 —', 'Помнож і додай!', '1f9ee')
    body += hs

    def formula(yy):
        lab, lh = plain(yy, [run('Для H₂O:', B)], size=38, lh=50)
        fy = yy + lh + 18
        d, bx, by, bw, bh = math_path(r'$M(\mathrm{H_2O}) = 2\cdot 1 + 16 = 18$', 100)
        boxh = 280
        sc = min(1.0, (W - 2 * ML - 100) / bw)
        ox = W / 2 - (bx + bw / 2) * sc
        oy = fy + boxh / 2 - (by + bh / 2) * sc
        svg = lab + card(ML, fy, W - 2 * ML, boxh, r=32, sw=3)
        svg += (f'<path id="formula M(H2O) = 2·1 + 16 = 18" d="{d}" fill="{BLACK}" '
                f'transform="translate({ox:.1f} {oy:.1f}) scale({sc:.4f})"/>')
        return svg, lh + 18 + boxh

    items = [
        formula,
        lambda yy: card_row(yy, [run('Отже, '), run('M(H₂O) = 18 г/моль', B, C)], '1f3af', min_h=150),
        lambda yy: card_row(yy, [run('Запам’ятай алгоритм: '),
                                 run('кількість атомів × їхні атомні маси → сума всіх результатів', B, C)],
                            '1f4a1'),
    ]
    s, end = stack(y + 100, items, 76)
    return page('Слайд 4', body + s), end

# ---- Slide 5 (post-3 style) ----
def slide5():
    body = star(40, 720, 240, 100, rot=-10, wobble=[1, .95, 1.08, 1, .92, 1.05, 1, 1.1, .97, 1])
    body += star(1040, 1250, 170, 70, rot=15, sw=14)
    hs, hlh = 88, 102
    s, h, lines, lastw = text_block([run('Хочеш розбирати\nтакі завдання\nбез плутанини?', 800, C)],
                                    ML, 100, hs, W - ML - MR, hlh, upper=True, ls=-0.01, name='title')
    body += s
    body += emoji('1f9ea', ML + lastw + 14, 100 + h - hlh + (hlh - 76) / 2, 76)
    body += molecule(250, 880, scale=0.86, flip=True)
    rx = 560
    y = 540
    s, h, _, _ = text_block([run('Підписуйся та пиши мені кодове слово', B)], rx, y, 44, W - rx - MR, 56)
    body += s
    y += h + 30
    bs, bh = 72, 116
    lab = 'РЕАКТИВ'
    bw = tw(lab, 800, bs) + 2 * 34
    body += (f'<rect x="{rx}" y="{y}" width="{bw:.0f}" height="{bh}" rx="10" fill="{BLACK}"/>'
             f'<text font-family="Inter" font-weight="800" font-size="{bs}" fill="{C}" '
             f'x="{rx+34}" y="{y + (bh + bs*0.727)/2:.1f}">{lab}</text>')
    y += bh + 30
    s, h, _, _ = text_block([run('підберемо план підготовки до НМТ з хімії для тебе')], rx, y, 40, W - rx - MR, 54)
    body += s
    return page('Слайд 5', body)

results = {
    'slide1': slide1(),
    'slide2': slide2(),
    'slide3': slide3(),
    'slide4': slide4(),
    'slide5': slide5(),
}
for name, val in results.items():
    svg, end = (val if isinstance(val, tuple) else (val, None))
    if end is not None:
        print(name, 'content bottom =', round(end))
    with open(os.path.join(OUT, f'{name}.svg'), 'w', encoding='utf-8') as f:
        f.write(svg)
print('ok')
