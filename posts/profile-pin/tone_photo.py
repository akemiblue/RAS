#!/usr/bin/env python3
"""
写真を、参考デザインの色調（彩度を落とした、少し暖かいマット調）に揃えるツール。

グリッド全体の統一感は、文字タイルより「写真の色が揃っているか」で決まる。
撮った写真をそのまま上げると、ここだけ浮く。

    python3 tone_photo.py 写真.jpg out.jpg
    python3 tone_photo.py 写真.jpg out.jpg --strength 0.7
"""
import argparse
from PIL import Image, ImageEnhance

CREAM = (226, 218, 187)   # #E2DABB 参考デザインのベージュ


def tone(img, strength=1.0):
    """strength 0=元のまま 1=標準 それ以上で更に淡く"""
    img = img.convert('RGB')

    # 1. 彩度を落とす
    img = ImageEnhance.Color(img).enhance(1 - 0.42 * strength)

    # 2. コントラストを少し弱めて、マットな質感にする
    img = ImageEnhance.Contrast(img).enhance(1 - 0.14 * strength)

    # 3. ベージュを薄くかぶせて色味を寄せる
    overlay = Image.new('RGB', img.size, CREAM)
    img = Image.blend(img, overlay, 0.13 * strength)

    # 4. 黒を少し持ち上げる（フィルム調の締まりすぎない黒）
    lift = int(14 * strength)
    img = img.point(lambda v: lift + v * (255 - lift) // 255)

    # 5. わずかに明るく
    return ImageEnhance.Brightness(img).enhance(1 + 0.03 * strength)


def fit_tile(img, w=1080, h=1350):
    """4:5に切り抜く（中央基準）"""
    src_ratio, dst_ratio = img.width / img.height, w / h
    if src_ratio > dst_ratio:
        nw = round(img.height * dst_ratio)
        img = img.crop(((img.width - nw) // 2, 0, (img.width + nw) // 2, img.height))
    else:
        nh = round(img.width / dst_ratio)
        img = img.crop((0, (img.height - nh) // 2, img.width, (img.height + nh) // 2))
    return img.resize((w, h), Image.LANCZOS)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('dst')
    ap.add_argument('--strength', type=float, default=1.0)
    ap.add_argument('--crop', action='store_true', help='4:5(1080x1350)に切り抜く')
    a = ap.parse_args()
    im = Image.open(a.src)
    if a.crop:
        im = fit_tile(im)
    tone(im, a.strength).save(a.dst, quality=95)
    print('書き出し:', a.dst)
