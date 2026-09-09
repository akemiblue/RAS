#!/usr/bin/env python3
"""
プロフィール固定用の「3枚でつながる1枚絵」を、テーマ違いで書き出すスクリプト。

    python3 make_banner.py rose indigo sumi

各テーマについて次を出力する:
    <theme>/pin_01.png .. pin_03.png   投稿用 1080x1350
    <theme>/grid_preview.png           グリッドでの見え方
"""
import os, subprocess, sys
from slice_banner import slice_banner, make_grid_preview, POST_H, VISIBLE_W, BLEED

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
COLS = 3
MASTER_W = round(VISIBLE_W * COLS + BLEED * 2)   # 3106

# 3枚に載せる文言。テーマを変えても中身は共通にして、見え方だけ比べられるようにする
COPY = [
    dict(n='01', main='思い込みを、<br>手放す。',
         sub='<span class="en">Release &amp; Awakening System</span><br>キネシオロジー × 眼球筋運動',
         foot='RAS<sup>®</sup> × 東北'),
    dict(n='02', main='我慢を、<br>ほどく。',
         sub='「私さえ我慢すれば」<br>そう言ってきた あなたへ',
         foot='宮城県大郷町'),
    dict(n='03', main='<span class="sm">体験・無料相談</span><br>受付中',
         sub='オンライン / 対面<br>プロフィールのリンクから',
         foot='ファシリテーター AKEMI'),
]

RINGS = """
  <g fill="none" stroke="{ring}" stroke-opacity="{ringop}" stroke-width="26" filter="url(#soft)">
    <circle cx="871"  cy="{cy}" r="196"/><circle cx="1223" cy="{cy}" r="196"/>
    <circle cx="1884" cy="{cy}" r="196"/><circle cx="2236" cy="{cy}" r="196"/>
  </g>"""

# 3枚の境界をまたいで流れる1本の曲線。継ぎ目を figure にしてしまう
WAVE = """
  <path d="M -40 1055 C 520 1000, 990 1110, 1553 1055 S 2590 1000, 3150 1055"
        fill="none" stroke="{ring}" stroke-opacity="{ringop}" stroke-width="5"/>"""

THEMES = {
    # 現行案。淡いピンク + 明朝
    'rose': dict(
        bg='linear-gradient(180deg,#FDF4F1 0%,#F9EAE5 55%,#F6E3DE 100%)',
        edge='#F6E3DE', ink='#2A2523', kicker='#C1697A', sub='#7C6B66',
        foot='#B08C88', rule='#C9737F', ruleop='.34',
        deco=RINGS.format(ring='#C9737F', ringop='.30', cy=690),
        band='', main_size=112, main_top=100, pad_top=250,
    ),
    # ロゴの青紫に寄せた案。3枚を横断する大きな英文が「つなぎ」そのものになる
    'indigo': dict(
        bg='linear-gradient(135deg,#EEF2FB 0%,#E9E9F7 50%,#F4EEF9 100%)',
        edge='#F4EEF9', ink='#232A45', kicker='#5B6BC0', sub='#5F6580',
        foot='#8D93B4', rule='#5B6BC0', ruleop='.30',
        deco=RINGS.format(ring='#7B7FD0', ringop='.20', cy=760),
        band=dict(text='RELEASE &amp; AWAKENING SYSTEM', top=312, size=112,
                  ls='.20em', color='#3A44 7A'.replace(' ', ''), op='.16'),
        main_size=104, main_top=250, pad_top=250,
    ),
    # 墨色。白抜き文字に細い曲線が横断する、静かで濃い案
    'sumi': dict(
        bg='linear-gradient(180deg,#22262E 0%,#2C2F38 55%,#343642 100%)',
        edge='#343642', ink='#F4F1EC', kicker='#C9A97A', sub='#B4AEA6',
        foot='#8A857E', rule='#C9A97A', ruleop='.42',
        deco=(RINGS.format(ring='#C9A97A', ringop='.22', cy=690)
              + WAVE.format(ring='#C9A97A', ringop='.30')),
        band='', main_size=112, main_top=100, pad_top=250,
    ),
}


def build_html(t):
    band = ''
    if t['band']:
        b = t['band']
        band = ('<div class="band" style="top:%dpx;font-size:%dpx;letter-spacing:%s;'
                'color:%s;opacity:%s">%s</div>' %
                (b['top'], b['size'], b['ls'], b['color'], b['op'], b['text']))

    cols = ''.join(
        '<div class="col"><div class="kicker">%s</div><div class="main">%s</div>'
        '<div class="sub">%s</div><div class="foot">%s</div></div>'
        % (c['n'], c['main'], c['sub'], c['foot']) for c in COPY)

    return f"""<!doctype html><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
html{{width:{MASTER_W}px;height:{POST_H}px;background:{t['edge']}}}
body{{width:{MASTER_W}px;height:{POST_H}px;overflow:hidden;background:{t['bg']};
  font-family:'IPAPGothic','IPAGothic',sans-serif;color:{t['ink']}}}
.deco{{position:absolute;top:0;left:0;display:block}}
.band{{position:absolute;left:{BLEED}px;width:{VISIBLE_W*COLS}px;text-align:center;
  font-family:'Liberation Serif',serif;white-space:nowrap}}
.stage{{position:absolute;top:0;left:{BLEED}px;width:{VISIBLE_W*COLS}px;height:{POST_H}px;display:flex}}
.col{{width:{VISIBLE_W}px;height:{POST_H}px;position:relative;text-align:center;
  padding:{t['pad_top']}px 100px 112px 100px;display:flex;flex-direction:column}}
.kicker{{font-size:36px;letter-spacing:.42em;text-indent:.42em;font-weight:700;color:{t['kicker']}}}
.main{{margin-top:{t['main_top']}px;font-family:'IPAPMincho','IPAMincho',serif;
  font-size:{t['main_size']}px;line-height:1.52;letter-spacing:.06em}}
.main .sm{{font-size:{round(t['main_size']*0.7)}px}}
.sub{{margin-top:76px;font-size:38px;line-height:2.0;letter-spacing:.09em;color:{t['sub']}}}
.foot{{margin-top:auto;line-height:1.6;font-size:30px;letter-spacing:.24em;
  text-indent:.24em;color:{t['foot']}}}
.en{{font-family:'Liberation Serif',serif;letter-spacing:.16em}}
sup{{font-size:.62em;vertical-align:.5em}}
</style>
<svg class="deco" width="{MASTER_W}" height="{POST_H}" viewBox="0 0 {MASTER_W} {POST_H}">
 <defs><filter id="soft" x="-25%" y="-25%" width="150%" height="150%">
   <feGaussianBlur stdDeviation="17"/></filter></defs>
 {t['deco']}
 <line x1="0" y1="1140" x2="{MASTER_W}" y2="1140" stroke="{t['rule']}"
       stroke-opacity="{t['ruleop']}" stroke-width="4"/>
</svg>
{band}
<div class="stage">{cols}</div>
"""


def render(theme, out_root='.'):
    t = THEMES[theme]
    d = os.path.join(out_root, theme)
    os.makedirs(d, exist_ok=True)
    html_path = os.path.abspath(os.path.join(d, 'master.html'))
    open(html_path, 'w').write(build_html(t))

    subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
                    '--hide-scrollbars', '--force-device-scale-factor=1',
                    '--window-size=%d,%d' % (MASTER_W, POST_H),
                    '--screenshot=' + os.path.join(d, 'master.png'),
                    'file://' + html_path],
                   check=True, capture_output=True)

    tiles = slice_banner(os.path.join(d, 'master.png'), d, COLS, 'pin')
    make_grid_preview(tiles, os.path.join(d, 'grid_preview.png'))
    return d


if __name__ == '__main__':
    for name in (sys.argv[1:] or list(THEMES)):
        print('=== %s ===' % name)
        render(name)
