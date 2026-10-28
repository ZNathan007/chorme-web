"""Split each slide SVG into a shapes-only SVG + a native-text spec for Figma.

Figma's SVG import flattens multi-line <text>, so shapes go in via
figma.createNodeFromSvg() and text is rebuilt as editable Inter text layers.
Emoji <image>s become named placeholders ("emoji <code>") that get image fills.

Usage: python3 figma_split.py out <dst_dir>
"""
import re, sys, json
import xml.etree.ElementTree as ET
NS = '{http://www.w3.org/2000/svg}'
ASC, LINE = 0.96875, 1.2109  # Inter hhea ascender / (asc+desc) in em
EMOJI = {2: ['1f50d', '1f4a7', '1f4a1'], 3: ['1f4d6', '269b-fe0f', '1f4a1'],
         4: ['1f9ee', '1f3af', '1f4a1'], 5: ['1f9ea']}

def top_of(baseline, s, lh):
    return baseline - (((lh - LINE * s) / 2 + ASC * s) if lh else ASC * s)

def gen(i, src):
    s = open(src, encoding='utf-8').read()
    texts = []
    for m in re.finditer(r'<text\b[^>]*>.*?</text>', s, re.S):
        el = ET.fromstring(m.group(0).replace('<text', f'<text xmlns="http://www.w3.org/2000/svg"', 1))
        size = float(el.get('font-size'))
        ls = float(el.get('letter-spacing') or 0)
        lines = [c for c in el if c.tag == NS + 'tspan']
        d = {'s': size}
        if el.get('id'): d['n'] = el.get('id')
        if ls: d['ls'] = ls
        if el.get('fill-opacity'): d['op'] = float(el.get('fill-opacity'))
        if el.get('text-anchor') == 'middle': d['a'] = 'm'
        if not lines:
            d['x'], b = float(el.get('x')), float(el.get('y'))
            d['r'] = [[el.text, int(el.get('font-weight')), el.get('fill')]]
            d['y'] = round(top_of(b, size, None), 1)
        else:
            ys = [float(l.get('y')) for l in lines]
            lh = round(ys[1] - ys[0], 1) if len(ys) > 1 else None
            if lh is None:  # single line: same box as the builder used
                lh = {80: 96, 44: 60 if i != 5 else 56, 34: 46, 38: 50, 40: 54}.get(int(size))
            d['lh'] = lh
            d['x'] = float(lines[0].get('x'))
            d['y'] = round(top_of(ys[0], size, lh), 1)
            runs = []
            for li, l in enumerate(lines):
                if li: runs.append(['\n', None, None])
                for r in l:
                    t = r.text or ''
                    if not t: continue
                    if r.get('dy') and r.get('font-size'):  # subscript run (A_r)
                        t = {'r': 'ᵣ'}.get(t, t)
                    runs.append([t, int(r.get('font-weight')), r.get('fill')])
            # merge newline into previous run, merge same-style runs
            out = []
            for t, w, c in runs:
                if w is None: out[-1][0] += t; continue
                if out and out[-1][1] == w and out[-1][2] == c: out[-1][0] += t
                else: out.append([t, w, c])
            d['r'] = out
        d['x'] = round(d['x'], 1)
        texts.append(d)
    shapes = re.sub(r'<text\b[^>]*>.*?</text>', '', s, flags=re.S)
    shapes = re.sub(r'<title>.*?</title>', '', shapes)
    it = iter(EMOJI.get(i, []))
    def img(m):
        x, y, w = re.search(r'x="([\d.]+)" y="([\d.]+)" width="(\d+)"', m.group(0)).groups()
        return f'<rect id="emoji {next(it)}" x="{x}" y="{y}" width="{w}" height="{w}" fill="#EEEEEE"/>'
    shapes = re.sub(r'<image [^>]*?/>', img, shapes)
    return shapes, texts

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    for i in range(1, 6):
        shapes, texts = gen(i, f'{src}/slide{i}.svg')
        open(f'{dst}/shapes{i}.svg', 'w', encoding='utf-8').write(shapes)
        open(f'{dst}/texts{i}.json', 'w', encoding='utf-8').write(json.dumps(texts, ensure_ascii=False, separators=(',', ':')))
        print(i, len(shapes), len(json.dumps(texts, ensure_ascii=False)))
