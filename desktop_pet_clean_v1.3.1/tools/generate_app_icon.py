from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PNG_PATH = PROJECT_ROOT / "assets" / "app_icon.png"
ICO_PATH = PROJECT_ROOT / "assets" / "app_icon.ico"
SIZE = 1024


def _rounded_pen(width: float) -> QPen:
    pen = QPen(QColor("#111111"))
    pen.setWidthF(width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def _draw_heart(painter: QPainter) -> None:
    path = QPainterPath(QPointF(512, 275))
    path.cubicTo(370, 90, 85, 200, 130, 440)
    path.cubicTo(165, 630, 355, 760, 512, 875)
    path.cubicTo(670, 760, 860, 630, 895, 440)
    path.cubicTo(940, 200, 655, 90, 512, 275)
    path.closeSubpath()

    gradient = QLinearGradient(180, 140, 860, 840)
    gradient.setColorAt(0.0, QColor("#FF7F8D"))
    gradient.setColorAt(1.0, QColor("#FF6E8E"))
    painter.setPen(Qt.NoPen)
    painter.setBrush(gradient)
    painter.drawPath(path)


def _left_dog_path() -> tuple[QPainterPath, QPainterPath]:
    body = QPainterPath()
    body.moveTo(245, 720)
    body.cubicTo(180, 650, 165, 560, 215, 480)
    body.cubicTo(250, 420, 310, 390, 380, 395)
    body.cubicTo(455, 395, 515, 430, 545, 495)
    body.cubicTo(575, 560, 575, 650, 540, 725)
    body.cubicTo(505, 800, 355, 830, 245, 720)
    body.closeSubpath()

    head = QPainterPath()
    head.moveTo(235, 450)
    head.cubicTo(250, 315, 360, 255, 470, 290)
    head.cubicTo(535, 310, 575, 355, 595, 420)
    head.cubicTo(575, 500, 500, 545, 415, 540)
    head.cubicTo(315, 540, 240, 510, 235, 450)
    head.closeSubpath()
    return body, head


def _draw_left_dog(painter: QPainter) -> None:
    body, head = _left_dog_path()
    fill = QColor("#F8D873")
    accent = QColor("#FF8A8C")
    pen = _rounded_pen(18)

    painter.setPen(pen)
    painter.setBrush(fill)
    painter.drawPath(body)
    painter.drawPath(head)

    ear = QPainterPath()
    ear.moveTo(220, 460)
    ear.cubicTo(145, 500, 125, 565, 170, 610)
    ear.cubicTo(205, 645, 250, 638, 275, 595)
    ear.cubicTo(290, 550, 285, 495, 270, 455)
    ear.closeSubpath()
    painter.drawPath(ear)

    collar = QPainterPath()
    collar.moveTo(305, 560)
    collar.cubicTo(380, 585, 455, 585, 530, 562)
    collar.lineTo(530, 600)
    collar.cubicTo(455, 625, 378, 625, 302, 600)
    collar.closeSubpath()
    painter.setPen(Qt.NoPen)
    painter.setBrush(accent)
    painter.drawPath(collar)

    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawArc(QRectF(360, 640, 36, 110), 0 * 16, 180 * 16)
    painter.drawArc(QRectF(445, 640, 36, 110), 0 * 16, 180 * 16)
    painter.drawArc(QRectF(162, 745, 85, 55), 185 * 16, 145 * 16)

    painter.setBrush(QColor("#111111"))
    painter.drawEllipse(QRectF(332, 418, 28, 28))
    painter.drawEllipse(QRectF(456, 430, 24, 24))
    painter.drawEllipse(QRectF(406, 448, 24, 24))

    painter.setPen(_rounded_pen(12))
    smile = QPainterPath()
    smile.moveTo(372, 462)
    smile.cubicTo(390, 480, 420, 482, 440, 460)
    painter.drawPath(smile)


def _draw_right_dog(painter: QPainter) -> None:
    pen = _rounded_pen(18)
    fill = QColor("#F4F4F4")

    body = QPainterPath()
    body.moveTo(520, 720)
    body.cubicTo(495, 620, 515, 505, 585, 450)
    body.cubicTo(640, 405, 720, 395, 775, 430)
    body.cubicTo(835, 470, 865, 555, 870, 650)
    body.cubicTo(875, 735, 835, 810, 730, 820)
    body.cubicTo(640, 830, 565, 800, 520, 720)
    body.closeSubpath()

    head = QPainterPath()
    head.moveTo(520, 430)
    head.cubicTo(525, 330, 610, 285, 700, 300)
    head.cubicTo(780, 315, 830, 375, 825, 455)
    head.cubicTo(810, 520, 745, 555, 670, 548)
    head.cubicTo(595, 542, 525, 510, 520, 430)
    head.closeSubpath()

    painter.setPen(pen)
    painter.setBrush(fill)
    painter.drawPath(body)
    painter.drawPath(head)

    painter.setBrush(fill)
    for circle in (
        QRectF(520, 340, 62, 62),
        QRectF(560, 312, 66, 66),
        QRectF(620, 298, 70, 70),
        QRectF(690, 308, 68, 68),
        QRectF(748, 340, 60, 60),
    ):
        painter.drawEllipse(circle)

    painter.setBrush(QColor("#111111"))
    painter.drawEllipse(QRectF(610, 442, 24, 24))
    painter.drawEllipse(QRectF(705, 462, 22, 22))
    painter.drawEllipse(QRectF(660, 466, 22, 22))

    painter.setPen(_rounded_pen(12))
    smile = QPainterPath()
    smile.moveTo(625, 482)
    smile.cubicTo(646, 498, 675, 500, 695, 478)
    painter.drawPath(smile)

    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawArc(QRectF(612, 645, 34, 108), 0 * 16, 180 * 16)
    painter.drawArc(QRectF(695, 645, 34, 108), 0 * 16, 180 * 16)
    painter.drawArc(QRectF(838, 748, 74, 50), 185 * 16, 145 * 16)

    paw = QPainterPath()
    paw.moveTo(775, 535)
    paw.cubicTo(815, 555, 842, 595, 846, 640)
    painter.drawPath(paw)


def build_icon(size: int = SIZE) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

    _draw_heart(painter)
    _draw_left_dog(painter)
    _draw_right_dog(painter)

    painter.end()
    return image


def _normalize_icon_image(source_image: QImage, *, size: int = SIZE) -> QImage:
    if source_image.isNull():
        raise RuntimeError("Source icon image is empty or unreadable.")

    canvas = QImage(size, size, QImage.Format_ARGB32)
    canvas.fill(Qt.transparent)

    fitted = source_image.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    x = int((size - fitted.width()) / 2)
    y = int((size - fitted.height()) / 2)
    painter.drawImage(x, y, fitted)
    painter.end()
    return canvas


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate app icon PNG/ICO assets.")
    parser.add_argument(
        "source",
        nargs="?",
        help="Optional source image path. When provided, the image is normalized and exported as PNG/ICO.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    PNG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if args.source:
        source_path = Path(args.source).expanduser().resolve()
        image = _normalize_icon_image(QImage(str(source_path)))
    else:
        image = build_icon()
    if not image.save(str(PNG_PATH)):
        raise RuntimeError(f"Failed to save PNG icon: {PNG_PATH}")
    if not image.save(str(ICO_PATH)):
        raise RuntimeError(f"Failed to save ICO icon: {ICO_PATH}")
    print(f"Generated icon files:\n- {PNG_PATH}\n- {ICO_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
