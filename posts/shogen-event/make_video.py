"""SHOGENトークイベント告知動画（縦型 1080x1920 / 30fps）を生成する。

使い方: python3 posts/shogen-event/make_video.py
出力:   posts/shogen-event/shogen_talk_1217.mp4
"""
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
FLYER = Image.open(HERE / "assets/flyer.png").convert("RGB")
# 電話番号は載せない: チラシ内の2か所（申込み欄・お問合せ欄）を白で隠す
_mask = ImageDraw.Draw(FLYER)
_mask.rectangle((748, 1836, 1125, 1906), fill=(255, 255, 255))
_mask.rectangle((488, 1918, 1190, 1972), fill=(255, 255, 255))
QR_CARD = Image.open(HERE / "assets/qr_card.png").convert("RGB")
OUT = HERE / "shogen_talk_1217.mp4"

W, H, FPS = 1080, 1920, 30
FONT = "/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"
WHITE, CREAM, GREEN, RED = (255, 255, 255), (255, 244, 214), (140, 205, 90), (226, 52, 52)
INK = (40, 40, 40)

FORM_URL = "forms.gle/mgworG3Q2kARK7Mz7"


def font(size):
    return ImageFont.truetype(FONT, size)


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def fade(t, start, dur=0.6):
    return ease((t - start) / dur)


# 背景: チラシの絵（海と子どもたち）をぼかして暗くした縦長画像
def make_bg():
    art = FLYER.crop((600, 430, 1414, 1170))  # 文字のない絵の部分だけ
    scale = H / art.height
    art = art.resize((int(art.width * scale), H), Image.LANCZOS)
    left = (art.width - W) // 2
    art = art.crop((left, 0, left + W, H)).filter(ImageFilter.GaussianBlur(18))
    shade = Image.new("RGB", (W, H), (10, 20, 45))
    return Image.blend(art, shade, 0.55)


BG = make_bg()
FLYER_FIT = FLYER.resize((int(W * 0.86), int(W * 0.86 * FLYER.height / FLYER.width)), Image.LANCZOS)
QR = QR_CARD.crop((128, 392, 1290, 1554)).resize((560, 560), Image.LANCZOS)


def text_layer(lines, alpha, y_shift=0):
    """lines: [(text, size, color, y)] を中央揃えで描く。"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(255 * alpha)
    for text, size, color, y in lines:
        f = font(size)
        w = d.textlength(text, font=f)
        x = (W - w) / 2
        d.text((x + 4, y + y_shift + 5), text, font=f, fill=(0, 0, 0, int(a * 0.6)))
        d.text((x, y + y_shift), text, font=f, fill=color + (a,),
               stroke_width=max(1, size // 40), stroke_fill=color + (a,))
    return layer


def paste_alpha(base, layer):
    base.paste(layer, (0, 0), layer)


def bg_zoom(t, total):
    s = 1 + 0.06 * (t / total)
    img = BG.resize((int(W * s), int(H * s)), Image.BILINEAR)
    ox, oy = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((ox, oy, ox + W, oy + H))


def rounded_panel(size, fill, radius=36):
    p = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(p).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=fill)
    return p


# ---------- シーン ----------
def scene_intro(t):
    """0–7s: いつか、ではなく、いま、伝えたいこと。"""
    img = bg_zoom(t, 7).convert("RGBA")
    a1 = fade(t, 0.4) * (1 - fade(t, 6.4))
    a2 = fade(t, 2.4) * (1 - fade(t, 6.4))
    paste_alpha(img, text_layer([("いつか、ではなく", 96, CREAM, 720)], a1, (1 - fade(t, 0.4)) * 30))
    paste_alpha(img, text_layer([("いま、", 150, WHITE, 900),
                                 ("伝えたいこと。", 120, WHITE, 1080)], a2, (1 - fade(t, 2.4)) * 30))
    return img


def scene_title(t):
    """7–12s: タイトル"""
    img = bg_zoom(t + 7, 30).convert("RGBA")
    a = fade(t, 0.1) * (1 - fade(t, 4.4))
    paste_alpha(img, text_layer([("ペンキ画家", 80, CREAM, 560),
                                 ("SHOGEN", 190, WHITE, 680),
                                 ("トークイベント", 104, WHITE, 900)], a))
    a2 = fade(t, 1.4) * (1 - fade(t, 4.4))
    paste_alpha(img, text_layer([("「今日、誰のために生きる？」", 64, CREAM, 1140)], a2))
    a3 = fade(t, 2.4) * (1 - fade(t, 4.4))
    paste_alpha(img, text_layer([("12.17", 150, WHITE, 1290),
                                 ("宮城県 大郷町", 72, GREEN, 1470)], a3))
    return img


def scene_flyer(t, dur=8):
    """12–20s: チラシ全体 → 日時・会場へゆっくりズーム"""
    img = bg_zoom(t + 12, 30).convert("RGBA")
    a = fade(t, 0.0, 0.8) * (1 - fade(t, dur - 0.6))
    z = 1 + 0.45 * ease(max(0, (t - 3.2) / (dur - 3.8)))
    fw, fh = int(FLYER_FIT.width * z), int(FLYER_FIT.height * z)
    fl = FLYER_FIT.resize((fw, fh), Image.BILINEAR)
    # ズームの焦点: チラシ下部の日時〜料金欄（縦 60% あたり、横 30% あたり）
    k = ease(max(0, (t - 3.2) / (dur - 3.8)))
    fx = (W - fw) / 2 + k * (fw * (0.5 - 0.3))
    fy = (H - fh) / 2 + 40 * (1 - fade(t, 0, 0.8)) + k * (fh * (0.5 - 0.74))
    card = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow = rounded_panel((fw, fh), (0, 0, 0, 120), 8).filter(ImageFilter.GaussianBlur(20))
    card.paste(shadow, (int(fx) + 12, int(fy) + 18), shadow)
    card.paste(fl, (int(fx), int(fy)))
    card.putalpha(card.getchannel("A").point(lambda v: int(v * a)))
    paste_alpha(img, card)
    return img


def scene_info(t, dur=6):
    """20–26s: 開催概要"""
    img = bg_zoom(t + 20, 30).convert("RGBA")
    a = fade(t, 0.1) * (1 - fade(t, dur - 0.6))
    panel = rounded_panel((920, 980), (255, 255, 255, int(235 * a)))
    img.paste(panel, (80, 380), panel)
    rows = [
        ("日時", "2026.12.17（木）", "19:00〜20:30（開場18:30）"),
        ("会場", "大郷町文化会館", "宮城県黒川郡大郷町中村字屋鋪8-19"),
        ("料金", "大人 4,000円", "中高生 1,500円／小学生 500円\n未就学児 無料"),
        ("定員", "限定 350名", ""),
    ]
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    y = 450
    for i, (label, main, sub) in enumerate(rows):
        ra = int(255 * a * fade(t, 0.3 + i * 0.35))
        d.rounded_rectangle((130, y, 290, y + 84), 42, fill=GREEN + (ra,))
        lf = font(48)
        d.text((210 - d.textlength(label, font=lf) / 2, y + 16), label, font=lf, fill=WHITE + (ra,),
               stroke_width=1, stroke_fill=WHITE + (ra,))
        d.text((320, y + 8), main, font=font(62), fill=INK + (ra,), stroke_width=1, stroke_fill=INK + (ra,))
        sy = y + 100
        for line in sub.split("\n") if sub else []:
            d.text((320, sy), line, font=font(36), fill=(90, 90, 90, ra))
            sy += 50
        y = max(sy, y + 110) + 60
    paste_alpha(img, layer)
    paste_alpha(img, text_layer([("SHOGENさんの話を聞けば", 52, WHITE, 1470),
                                 ("生き方が変わります。", 52, WHITE, 1545)], a * fade(t, 1.8)))
    return img


def scene_apply(t, dur=8):
    """26–34s: 申込み（QR・URL）"""
    img = bg_zoom(t + 26, 30).convert("RGBA")
    a = fade(t, 0.1)
    paste_alpha(img, text_layer([("お申込みはこちら", 96, WHITE, 230)], a))
    panel = rounded_panel((680, 680), (255, 255, 255, int(255 * a)), 40)
    img.paste(panel, (200, 420), panel)
    q = QR.copy().convert("RGBA")
    q.putalpha(int(255 * a))
    img.paste(q, (260, 480), q)
    paste_alpha(img, text_layer([(FORM_URL, 58, CREAM, 1160)], fade(t, 0.6)))
    paste_alpha(img, text_layer([("締切 12月16日（水）", 72, (255, 220, 80), 1290)], fade(t, 1.0)))
    paste_alpha(img, text_layer([("主催：はんずあっぷ", 42, (220, 220, 220), 1500)], fade(t, 1.4)))
    return img


SCENES = [(scene_intro, 7), (scene_title, 5), (scene_flyer, 8), (scene_info, 6), (scene_apply, 8)]


def main():
    total = sum(d for _, d in SCENES)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-t", str(total), "-i", "anullsrc=r=44100:cl=stereo",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(OUT)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fn, dur in SCENES:
        for i in range(int(dur * FPS)):
            proc.stdin.write(fn(i / FPS).convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()
    print(OUT, f"{total}s")


if __name__ == "__main__":
    main()
