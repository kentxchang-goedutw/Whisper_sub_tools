from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets"
PNG_PATH = ASSETS_DIR / "app_icon.png"
ICO_PATH = ASSETS_DIR / "app_icon.ico"


def rounded_rectangle_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def vertical_gradient(size: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGB", (size, size), top)
    pixels = image.load()
    for y in range(size):
        ratio = y / (size - 1)
        color = tuple(round(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(3))
        for x in range(size):
            pixels[x, y] = color
    return image


def make_icon(size: int = 1024) -> Image.Image:
    scale = size / 1024
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    pad = int(72 * scale)
    shadow_draw.rounded_rectangle(
        (pad, int(84 * scale), size - pad, size - int(52 * scale)),
        radius=int(214 * scale),
        fill=(32, 42, 74, 86),
    )
    image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(int(34 * scale))))

    tile = vertical_gradient(size, (22, 126, 236), (45, 205, 190)).convert("RGBA")
    mask = rounded_rectangle_mask(size, int(214 * scale))
    tile.putalpha(mask)
    image.alpha_composite(tile)

    draw = ImageDraw.Draw(image)

    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse(
        (int(92 * scale), int(70 * scale), int(778 * scale), int(724 * scale)),
        fill=(255, 255, 255, 36),
    )
    image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(int(22 * scale))))

    screen_box = (
        int(172 * scale),
        int(228 * scale),
        int(852 * scale),
        int(678 * scale),
    )
    draw.rounded_rectangle(screen_box, radius=int(80 * scale), fill=(255, 255, 255, 245))

    play = [
        (int(438 * scale), int(348 * scale)),
        (int(438 * scale), int(558 * scale)),
        (int(610 * scale), int(453 * scale)),
    ]
    draw.polygon(play, fill=(246, 75, 136, 255))

    line_y = [int(744 * scale), int(822 * scale)]
    line_specs = [
        (int(198 * scale), int(826 * scale), (255, 255, 255, 244)),
        (int(266 * scale), int(758 * scale), (255, 255, 255, 214)),
    ]
    for y, (left, right, color) in zip(line_y, line_specs, strict=True):
        draw.rounded_rectangle(
            (left, y, right, y + int(42 * scale)),
            radius=int(21 * scale),
            fill=color,
        )

    sparkle = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    sparkle_draw = ImageDraw.Draw(sparkle)
    cx, cy = int(770 * scale), int(214 * scale)
    points = [
        (cx, cy - int(64 * scale)),
        (cx + int(18 * scale), cy - int(18 * scale)),
        (cx + int(64 * scale), cy),
        (cx + int(18 * scale), cy + int(18 * scale)),
        (cx, cy + int(64 * scale)),
        (cx - int(18 * scale), cy + int(18 * scale)),
        (cx - int(64 * scale), cy),
        (cx - int(18 * scale), cy - int(18 * scale)),
    ]
    sparkle_draw.polygon(points, fill=(255, 241, 135, 238))
    image.alpha_composite(sparkle)

    return image


def main() -> None:
    ASSETS_DIR.mkdir(exist_ok=True)
    icon = make_icon()
    icon.save(PNG_PATH)
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon.save(ICO_PATH, sizes=sizes)
    print(f"Wrote {PNG_PATH}")
    print(f"Wrote {ICO_PATH}")


if __name__ == "__main__":
    main()
