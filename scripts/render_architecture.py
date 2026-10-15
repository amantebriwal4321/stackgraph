"""Draw docs/architecture.png. Pillow is only needed to regenerate the picture."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "docs" / "architecture.png"
W, H = 1400, 820
paper = (243, 239, 230)
ink = (28, 25, 20)
green = (29, 106, 69)
card = (255, 250, 243)
line = (90, 84, 74)


def font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def box(draw, xy, title, lines, fill=card):
    draw.rounded_rectangle(xy, radius=18, fill=fill, outline=ink, width=2)
    x, y, _, _ = xy
    draw.text((x + 18, y + 16), title, font=font(22, True), fill=ink)
    cursor = y + 52
    for line_text in lines:
        draw.text((x + 18, cursor), line_text, font=font(16), fill=line)
        cursor += 24


def arrow(draw, start, end, label):
    draw.line([start, end], fill=green, width=3)
    ex, ey = end
    draw.polygon([(ex, ey), (ex - 12, ey - 6), (ex - 12, ey + 6)], fill=green)
    face = font(14, True)
    lx = (start[0] + end[0]) // 2 - 30
    ly = (start[1] + end[1]) // 2 - 22
    box = draw.textbbox((lx, ly), label, font=face)
    draw.rectangle((box[0] - 4, box[1] - 2, box[2] + 4, box[3] + 2), fill=paper)
    draw.text((lx, ly), label, font=face, fill=green)


def main():
    image = Image.new("RGB", (W, H), paper)
    draw = ImageDraw.Draw(image)
    draw.text((48, 36), "Stackgraph", font=font(36, True), fill=ink)
    draw.text(
        (48, 84),
        "FalkorDB is the only store. Advisor and scout share it. Memory is a graph per user.",
        font=font(18),
        fill=line,
    )
    box(draw, (48, 160, 360, 360), "Browser", ["Chat, Cypher, and the path.", "Served by FastAPI.", "No model key required."])
    box(draw, (470, 150, 860, 390), "Advisor", ["Rule router, or a model", "with tool calls if a key", "is set. Reads the", "ecosystem graph. Writes", "the user memory graph."])
    box(draw, (470, 450, 860, 690), "Scout", ["Counts DEPENDS_ON", "reach, 1 to 3 hops.", "Writes Signal nodes", "the advisor reads back."])
    box(
        draw,
        (980, 180, 1350, 660),
        "FalkorDB",
        [
            "Graph: ecosystem",
            "Tool, Category,",
            "Maintainer, Signal",
            "",
            "Graph: mem_<user>",
            "User, Session,",
            "Question, Answer",
            "Tool refs, USED_PATH",
            "",
            "Append only file",
            "on the data volume.",
        ],
        fill=(232, 241, 234),
    )
    arrow(draw, (360, 250), (470, 250), "question")
    arrow(draw, (860, 240), (980, 280), "Cypher")
    arrow(draw, (860, 560), (980, 480), "signals")
    image.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
