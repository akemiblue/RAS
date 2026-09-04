#!/usr/bin/env python3
"""
横長の1枚絵を、Instagramのプロフィールグリッド用に分割するツール。

Instagramの仕様（2025年以降）:
  - フィード投稿として安全に使えるのは 4:5（1080 x 1350）
  - プロフィールのグリッドは 3:4 に切り抜かれる
  → 4:5 の画像は、グリッド上で左右が各 33.75px ずつ削られる

そのため単純に3等分すると、グリッド上で継ぎ目がズレる。
このスクリプトは「グリッドに表示される部分」を基準に分割し、
削られる分を隣の絵から借りて“塗り足し”として持たせる。

使い方:
    python3 slice_banner.py master.png out/ --cols 3
"""
import argparse, os
from PIL import Image

POST_W, POST_H = 1080, 1350          # 投稿サイズ 4:5
VISIBLE_W = POST_H * 3 / 4           # グリッドに映る幅 = 1012.5
BLEED = (POST_W - VISIBLE_W) / 2     # 片側の塗り足し = 33.75


def slice_banner(src_path, out_dir, cols=3, prefix='pin'):
    os.makedirs(out_dir, exist_ok=True)
    master = Image.open(src_path).convert('RGB')

    expected_w = round(VISIBLE_W * cols + BLEED * 2)
    if abs(master.width - expected_w) > 2:
        # 想定幅と違う場合は高さ1350に合わせて拡縮してから使う
        scale = POST_H / master.height
        master = master.resize((round(master.width * scale), POST_H), Image.LANCZOS)
        if abs(master.width - expected_w) > 2:
            raise SystemExit(
                '幅が合いません。高さ1350のとき幅 %d px の画像を用意してください（現在 %d px）。'
                % (expected_w, master.width))

    if master.height != POST_H:
        master = master.resize((master.width, POST_H), Image.LANCZOS)

    tiles = []
    for i in range(cols):
        left = round(i * VISIBLE_W)
        box = (left, 0, left + POST_W, POST_H)
        if box[2] > master.width:            # 右端のはみ出しを吸収
            box = (master.width - POST_W, 0, master.width, POST_H)
        tile = master.crop(box)
        path = os.path.join(out_dir, '%s_%02d.png' % (prefix, i + 1))
        tile.save(path)
        tiles.append((path, tile))
        print('書き出し:', path, tile.size)
    return tiles


def make_grid_preview(tiles, out_path, gutter=6, scale=0.32):
    """グリッド上での見え方（3:4に切り抜かれた状態）を並べて確認する画像"""
    crops = []
    for _, tile in tiles:
        x = round((tile.width - VISIBLE_W) / 2)
        crops.append(tile.crop((x, 0, x + round(VISIBLE_W), tile.height)))

    cw, ch = crops[0].size
    tw = cw * len(crops) + gutter * (len(crops) - 1)
    canvas = Image.new('RGB', (tw, ch), (255, 255, 255))
    for i, c in enumerate(crops):
        canvas.paste(c, (i * (cw + gutter), 0))
    canvas = canvas.resize((round(tw * scale), round(ch * scale)), Image.LANCZOS)
    canvas.save(out_path)
    print('グリッド確認用:', out_path, canvas.size)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('out_dir')
    ap.add_argument('--cols', type=int, default=3)
    ap.add_argument('--prefix', default='pin')
    args = ap.parse_args()

    tiles = slice_banner(args.src, args.out_dir, args.cols, args.prefix)
    make_grid_preview(tiles, os.path.join(args.out_dir, 'grid_preview.png'))
