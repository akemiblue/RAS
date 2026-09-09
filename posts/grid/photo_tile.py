#!/usr/bin/env python3
"""
手持ちの写真を、グリッドの色調に合わせた写真タイル（1080x1350）に変換する。

    python3 photo_tile.py 手元.jpg ras 02
    python3 photo_tile.py 窓辺.jpg ras 04 --focus top --strength 0.22
    python3 photo_tile.py 風景.jpg ras 06 --preview     # 変換後にグリッドを作り直す

やっていること:
  1. 4:5（1080x1350）に切り抜く（はみ出す側を等分に落とす）
  2. 彩度をわずかに下げる（写真ごとの色の差を抑える）
  3. パレットの色を薄くかける（文字タイルと写真タイルの色味を揃える）

3の「薄くかける」が、グリッド全体を1つの作品に見せる要になっている。
写真をそのまま並べると、1枚1枚の色がばらついて統一感が出ない。
"""
import argparse
import os

from PIL import Image, ImageEnhance

from make_grid import (COLS, PALETTES, PHOTO, POST_H, POST_W, ROWS,
                       hex_rgb, make_grid_preview)

FOCUS = {'top': 0.0, 'center': 0.5, 'bottom': 1.0}


def cover_crop(im, focus='center'):
    """縦横比を保ったまま 1080x1350 を埋める。余る側を focus の位置で切る。"""
    scale = max(POST_W / im.width, POST_H / im.height)
    im = im.resize((max(POST_W, round(im.width * scale)),
                    max(POST_H, round(im.height * scale))), Image.LANCZOS)

    f = FOCUS[focus]
    left = round((im.width - POST_W) * 0.5)          # 横は常に中央
    top = round((im.height - POST_H) * f)
    return im.crop((left, top, left + POST_W, top + POST_H))


def tone(im, palette, strength=None, saturation=0.82, brightness=1.03):
    p = PALETTES[palette]
    amount = p['wash_amount'] if strength is None else strength

    im = ImageEnhance.Color(im).enhance(saturation)
    im = ImageEnhance.Brightness(im).enhance(brightness)

    wash = Image.new('RGB', im.size, hex_rgb(p['wash']))
    return Image.blend(im, wash, amount)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src', help='元の写真')
    ap.add_argument('palette', choices=sorted(PALETTES), help='パレット名')
    ap.add_argument('pos', type=int, choices=[s['pos'] for s in PHOTO],
                    help='グリッドの何マス目に置くか（偶数マス）')
    ap.add_argument('--focus', default='center', choices=sorted(FOCUS),
                    help='縦に余ったときにどこを残すか（既定: center）')
    ap.add_argument('--strength', type=float,
                    help='パレット色をかける強さ 0〜1（既定: パレットの設定値）')
    ap.add_argument('--saturation', type=float, default=0.82)
    ap.add_argument('--preview', action='store_true',
                    help='変換後に grid_preview.png を作り直す')
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(here, args.palette)
    out_path = os.path.join(out_dir, 'tile_%02d.png' % args.pos)

    im = Image.open(args.src).convert('RGB')
    tile = tone(cover_crop(im, args.focus), args.palette, args.strength,
                args.saturation)
    tile.save(out_path)
    print('書き出し:', out_path, tile.size)

    if args.preview:
        tiles = {pos: Image.open(os.path.join(out_dir, 'tile_%02d.png' % pos)).convert('RGB')
                 for pos in range(1, COLS * ROWS + 1)}
        make_grid_preview(tiles, os.path.join(out_dir, 'grid_preview.png'))


if __name__ == '__main__':
    main()
