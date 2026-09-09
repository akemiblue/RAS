#!/usr/bin/env python3
"""
参考デザイン（hanburydesignco.com の britylyn 風）に寄せた、無地の文字タイルを作る。

特徴:
  ・無地の落ち着いた色。飾りなし
  ・明朝体を大きめの字間で、中央に、低いコントラストで置く
  ・下に小さな英字を1行
グリッド全体の統一感は「同じ組み方を繰り返すこと」で作る。

    python3 make_tiles.py
"""
import os, subprocess

CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
W, H = 1080, 1350                 # 投稿サイズ 4:5
VISIBLE = H * 3 / 4               # グリッドに映る幅 1012.5
SIDE = (W - VISIBLE) / 2          # 左右で削られる 33.75px

# 参考画像から抽出した3色
PALETTE = {
    'stone': dict(bg='#F2F2F0', ink='#6E736C', en='#9AA096'),   # 淡いグレー
    'sage':  dict(bg='#D7DDD9', ink='#5B6660', en='#899690'),   # セージグリーン
    'cream': dict(bg='#E2DABB', ink='#6B6449', en='#9A9376'),   # ベージュ
}

# プロフィール固定用の3枚。3色を1周させる
PINNED = [
    dict(name='pin_01', tone='stone', jp='RAS<sup>®</sup>　とは', en='RELEASE &amp; AWAKENING SYSTEM'),
    dict(name='pin_02', tone='sage',  jp='こんな方へ',           en='WHO IT IS FOR'),
    dict(name='pin_03', tone='cream', jp='体験・無料相談',        en='BOOK A SESSION'),
]

# 通常投稿用のストック。写真と交互に並べるとグリッドが整う
POSTS = [
    dict(name='post_01', tone='cream', jp='我慢を、<br>ほどく',        en='LET IT GO'),
    dict(name='post_02', tone='stone', jp='「私さえ<br>我慢すれば」',   en='THE STORY YOU TELL'),
    dict(name='post_03', tone='sage',  jp='本当は<br>どうしたい？',     en='WHAT DO YOU WANT'),
    dict(name='post_04', tone='stone', jp='眠れない<br>夜のこと',       en='ON SLEEPLESS NIGHTS'),
    dict(name='post_05', tone='sage',  jp='がんばり方を<br>変える',     en='A DIFFERENT WAY'),
    dict(name='post_06', tone='cream', jp='私について',                en='ABOUT ME'),
]


def html(spec, jp_size=86):
    c = PALETTE[spec['tone']]
    return f"""<!doctype html><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{W}px;height:{H}px;overflow:hidden;background:{c['bg']}}}
.wrap{{width:{W}px;height:{H}px;display:flex;flex-direction:column;
  align-items:center;justify-content:center;padding:0 {SIDE+110}px}}
.jp{{font-family:'IPAPMincho','IPAMincho',serif;font-size:{jp_size}px;line-height:2.05;
  letter-spacing:.30em;text-indent:.30em;color:{c['ink']};text-align:center}}
.jp sup{{font-size:.42em;vertical-align:.9em;letter-spacing:0}}
.en{{margin-top:76px;font-family:'Liberation Serif',serif;font-size:25px;
  letter-spacing:.44em;text-indent:.44em;color:{c['en']};text-align:center;white-space:nowrap}}
</style>
<div class="wrap"><div class="jp">{spec['jp']}</div><div class="en">{spec['en']}</div></div>
"""


def render(spec, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.abspath(os.path.join(out_dir, spec['name'] + '.html'))
    open(p, 'w').write(html(spec))
    png = os.path.join(out_dir, spec['name'] + '.png')
    subprocess.run([CHROME, '--headless', '--no-sandbox', '--disable-gpu',
                    '--hide-scrollbars', '--force-device-scale-factor=1',
                    '--window-size=%d,%d' % (W, H), '--screenshot=' + png,
                    'file://' + p], check=True, capture_output=True)
    os.remove(p)
    print('書き出し:', png)
    return png


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    for s in PINNED:
        render(s, os.path.join(here, 'natural'))
    for s in POSTS:
        render(s, os.path.join(here, 'natural', 'stock'))
