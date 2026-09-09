#!/usr/bin/env python3
"""
プロフィールグリッド12マス（文字タイル × 写真タイルの市松）を書き出すスクリプト。

    python3 make_grid.py            # 全パレット（sage / meishi / ras）
    python3 make_grid.py ras        # パレットを指定

各パレットについて次を出力する:
    <palette>/tile_01.png .. tile_12.png   投稿用 1080x1350（4:5）
    <palette>/sheet.html / sheet.png       文字タイル6枚の元データ
    <palette>/grid_preview.png             グリッド（3列×4行）での見え方
    compare.png                            2パレットの並べ比べ
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
HERE = os.path.dirname(os.path.abspath(__file__))

POST_W, POST_H = 1080, 1350          # 投稿サイズ 4:5
VISIBLE_W = POST_H * 3 / 4           # グリッドに映る幅 = 1012.5
COLS, ROWS = 3, 4
SLACK = 160                          # headless chromium の表示領域不足を吸収する余白

# --------------------------------------------------------------------------
# 文字タイルの文言。参考にした構成（見出しだけの静かなタイル）をRAS®の内容に置換。
# 位置は 01,03,05,07,09,11（奇数マス）。
# --------------------------------------------------------------------------
COPY = [
    dict(pos=1,  main='思い込みの<br>ほどき方',            sub='vol.01'),
    dict(pos=3,  main='我慢を<br>ゆるめる<br>3つの問い',   sub=''),
    dict(pos=5,  main='ご一緒に<br>できること',            sub='SESSION MENU'),
    dict(pos=7,  main='かつてあなたを<br>守っていた<br>我慢という癖', sub=''),
    dict(pos=9,  main='わたしについて',                    sub='ABOUT'),
    dict(pos=11, main='あなたが自分に<br>ついている嘘',    sub=''),
]

# 写真タイルの位置と、そこに置く写真の想定。README の一覧と対応している。
PHOTO = [
    dict(pos=2,  label='手のひら・指先（筋反射テストの手元）'),
    dict(pos=4,  label='窓辺の光／カーテン'),
    dict(pos=6,  label='東北の風景（田・海・雪）'),
    dict(pos=8,  label='机まわり（ノート・ペン・シート）'),
    dict(pos=10, label='後ろ姿／横顔（顔出しは任意）'),
    dict(pos=12, label='湯呑み・お茶などの静物'),
]

# --------------------------------------------------------------------------
# パレット。tones は文字タイルの背景色で、上から順に繰り返して使う。
# inks は tones と1対1で対応する文字色。
# --------------------------------------------------------------------------
PALETTES = {
    # A案: 参考画像の配色をそのまま踏襲した、セージ／ベージュ系
    'sage': dict(
        tones=['#ECEEEC', '#D3DDD7', '#E4DCC3'],
        inks=['#7A827D', '#5F6E66', '#7C6F55'],
        wash='#D8DCD5',      # 写真に薄くかける色。グリッド全体の色味を揃える
        wash_amount=0.14,
        label='A案 sage（参考画像の配色）',
    ),
    # B案: 名刺の実配色。背景グラデ #ebdede→#caaa99、見出し #8b5031、本文 #444342 から起こした。
    #      3トーンは名刺のグラデーション上を淡い側から拾っている。
    'meishi': dict(
        tones=['#F3EAE6', '#EBDEDE', '#DAC4BC'],
        inks=['#8B5031', '#444342', '#5F4033'],   # 3つ目は見出し色を濃いトーン用に沈めたもの
        wash='#DAC4BC',      # 名刺グラデの中間色。写真も名刺と同じ空気になる
        wash_amount=0.16,
        label='B案 meishi（名刺の実配色）',
    ),
    # C案: RASロゴの臙脂・朱・橙に寄せた配色
    'ras': dict(
        tones=['#F4EDEA', '#EBD9D3', '#F3E3CE'],
        inks=['#8C4A55', '#A03A3F', '#98652F'],
        wash='#E5CFC6',
        wash_amount=0.16,
        label='C案 ras（ロゴ配色）',
    ),
}


# --------------------------------------------------------------------------
# 文字タイル: 6枚を横一列のシートとして描き、1080pxごとに切り出す。
# 背景が単色なので塗り足しは不要。1回のレンダリングで6枚そろう。
# --------------------------------------------------------------------------
def build_sheet_html(p):
    tiles = []
    for i, c in enumerate(COPY):
        tone = p['tones'][i % len(p['tones'])]
        ink = p['inks'][i % len(p['inks'])]
        sub = '<div class="sub">%s</div>' % c['sub'] if c['sub'] else ''
        tiles.append(
            '<div class="tile" style="background:%s;color:%s">'
            '<div class="main">%s</div>%s</div>' % (tone, ink, c['main'], sub))

    return f"""<!doctype html><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{POST_W * len(COPY)}px;height:{POST_H}px;overflow:hidden}}
body{{font-family:'IPAPMincho','IPAMincho','IPAPGothic',serif}}
.sheet{{display:flex}}
.tile{{width:{POST_W}px;height:{POST_H}px;display:flex;flex-direction:column;
  align-items:center;justify-content:center;text-align:center;padding:0 150px}}
.main{{font-size:76px;line-height:1.95;letter-spacing:.18em;text-indent:.18em}}
.sub{{margin-top:52px;font-size:30px;line-height:1.8;letter-spacing:.34em;
  text-indent:.34em;opacity:.72;font-family:'Liberation Serif',serif}}
</style>
<div class="sheet">{''.join(tiles)}</div>
"""


def render_text_tiles(name, p, out_dir):
    html_path = os.path.join(out_dir, 'sheet.html')
    sheet_png = os.path.join(out_dir, 'sheet.png')
    with open(html_path, 'w') as f:
        f.write(build_sheet_html(p))

    subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
                    '--hide-scrollbars', '--force-device-scale-factor=1',
                    '--window-size=%d,%d' % (POST_W * len(COPY), POST_H + SLACK),
                    '--screenshot=' + sheet_png,
                    'file://' + os.path.abspath(html_path)],
                   check=True, capture_output=True)

    # headless の表示領域は指定より少し低く出るため、余裕をもたせて撮り、上から切る
    sheet = Image.open(sheet_png).convert('RGB').crop(
        (0, 0, POST_W * len(COPY), POST_H))
    out = {}
    for i, c in enumerate(COPY):
        tile = sheet.crop((i * POST_W, 0, (i + 1) * POST_W, POST_H))
        path = os.path.join(out_dir, 'tile_%02d.png' % c['pos'])
        tile.save(path)
        out[c['pos']] = tile
        print('文字タイル:', path)
    return out


# --------------------------------------------------------------------------
# 写真タイル: 差し替え前のプレースホルダ。
# どのマスに何の写真を入れるかが、グリッドを見るだけで分かるようにしておく。
# --------------------------------------------------------------------------
def jp_font(size):
    for path in ('/usr/share/fonts/opentype/ipafont-mincho/ipamp.ttf',
                 '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf',
                 '/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf'):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def hex_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def make_placeholder(p, spec, out_path):
    """縦のグラデーション＋用途ラベル。実写に差し替える前提の仮タイル。"""
    top = hex_rgb(p['wash'])
    bottom = tuple(min(255, round(v * 0.86)) for v in top)

    tile = Image.new('RGB', (POST_W, POST_H))
    draw = ImageDraw.Draw(tile)
    for y in range(POST_H):
        t = y / (POST_H - 1)
        draw.line([(0, y), (POST_W, y)],
                  fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))

    ink = tuple(round(v * 0.55) for v in bottom)
    draw.text((POST_W / 2, POST_H / 2 - 70), 'PHOTO', font=jp_font(38), fill=ink,
              anchor='mm')
    draw.line([(POST_W / 2 - 70, POST_H / 2 - 16), (POST_W / 2 + 70, POST_H / 2 - 16)],
              fill=ink, width=2)

    # 括弧の前で折り返す。1行に収まらないラベルだけ2行になる
    font = jp_font(34)
    for i, line in enumerate(spec['label'].replace('（', '\n（').split('\n')):
        draw.text((POST_W / 2, POST_H / 2 + 24 + i * 56), line, font=font,
                  fill=ink, anchor='mm')

    tile.save(out_path)
    print('写真タイル（仮）:', out_path)
    return tile


# --------------------------------------------------------------------------
# グリッドでの見え方: 4:5 の画像は 3:4 に切り抜かれて並ぶ
# --------------------------------------------------------------------------
def make_grid_preview(tiles, out_path, gutter=6, scale=0.30):
    crops = []
    for pos in range(1, COLS * ROWS + 1):
        tile = tiles[pos]
        x = round((tile.width - VISIBLE_W) / 2)
        crops.append(tile.crop((x, 0, x + round(VISIBLE_W), tile.height)))

    cw, ch = crops[0].size
    canvas = Image.new('RGB',
                       (cw * COLS + gutter * (COLS - 1),
                        ch * ROWS + gutter * (ROWS - 1)), (255, 255, 255))
    for i, c in enumerate(crops):
        canvas.paste(c, ((i % COLS) * (cw + gutter), (i // COLS) * (ch + gutter)))

    canvas = canvas.resize((round(canvas.width * scale), round(canvas.height * scale)),
                           Image.LANCZOS)
    canvas.save(out_path)
    print('グリッド確認用:', out_path, canvas.size)
    return canvas


def make_compare(previews, out_path, gap=48, pad=48, caption_h=62):
    font = jp_font(30)
    w = sum(p.width for _, p in previews) + gap * (len(previews) - 1) + pad * 2
    h = max(p.height for _, p in previews) + pad * 2 + caption_h
    canvas = Image.new('RGB', (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    x = pad
    for label, prev in previews:
        canvas.paste(prev, (x, pad + caption_h))
        draw.text((x + prev.width / 2, pad + caption_h / 2), label,
                  font=font, fill=(60, 60, 60), anchor='mm')
        x += prev.width + gap

    canvas.save(out_path)
    print('比較用:', out_path, canvas.size)


def build(name, out_root=HERE):
    p = PALETTES[name]
    out_dir = os.path.join(out_root, name)
    os.makedirs(out_dir, exist_ok=True)

    tiles = render_text_tiles(name, p, out_dir)
    for spec in PHOTO:
        path = os.path.join(out_dir, 'tile_%02d.png' % spec['pos'])
        tiles[spec['pos']] = make_placeholder(p, spec, path)

    preview = make_grid_preview(tiles, os.path.join(out_dir, 'grid_preview.png'))
    return p['label'], preview


if __name__ == '__main__':
    names = sys.argv[1:] or list(PALETTES)
    previews = []
    for name in names:
        print('=== %s ===' % name)
        previews.append(build(name))
    if len(previews) > 1:
        make_compare(previews, os.path.join(HERE, 'compare.png'))
