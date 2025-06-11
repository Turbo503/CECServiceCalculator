"""Minimal PDF generation utilities."""
from __future__ import annotations

from typing import Iterable, Tuple


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def simple_pdf(lines: Iterable[str], path: str) -> None:
    """Write lines of text to *path* as a simple one-page PDF."""
    escaped = [_escape(line) for line in lines]
    stream_lines = ["BT", "/F1 12 Tf", "72 760 Td"]
    for line in escaped:
        stream_lines.append(f"({line}) Tj")
        stream_lines.append("0 -14 Td")
    stream_lines.append("ET")
    stream = "\n".join(stream_lines)

    objects: list[str] = []
    offsets: list[int] = []

    def add(obj: str) -> None:
        offsets.append(len("%PDF-1.4\n") + sum(len(o) for o in objects))
        objects.append(obj)

    add("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    add("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    add(
        "3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        "/MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n"
    )
    add("4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n")
    stream_bytes = stream.encode("utf-8")
    add(
        f"5 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n{stream}\nendstream\nendobj\n"
    )

    xref_pos = len("%PDF-1.4\n") + sum(len(o) for o in objects)
    xref_entries = ["0000000000 65535 f "] + [f"{o:010} 00000 n " for o in offsets]
    xref = "xref\n0 6\n" + "\n".join(xref_entries) + "\n"
    trailer = f"trailer\n<< /Root 1 0 R /Size 6 >>\nstartxref\n{xref_pos}\n%%EOF\n"

    with open(path, "wb") as fh:
        fh.write("%PDF-1.4\n".encode("utf-8"))
        for obj in objects:
            fh.write(obj.encode("utf-8"))
        fh.write(xref.encode("utf-8"))
        fh.write(trailer.encode("utf-8"))


def simple_pdf_table(rows: Iterable[Tuple[str, str]], path: str) -> None:
    """Write two-column rows to *path* as a simple one-page PDF."""
    escaped_rows = [(_escape(l), _escape(r)) for l, r in rows]
    stream_lines = ["BT", "/F1 12 Tf", "72 760 Td"]
    for left, right in escaped_rows:
        stream_lines.append(f"({left}) Tj")
        if right:
            stream_lines.append("250 0 Td")
            stream_lines.append(f"({right}) Tj")
            stream_lines.append("-250 0 Td")
        stream_lines.append("0 -14 Td")
    stream_lines.append("ET")
    stream = "\n".join(stream_lines)

    objects: list[str] = []
    offsets: list[int] = []

    def add(obj: str) -> None:
        offsets.append(len("%PDF-1.4\n") + sum(len(o) for o in objects))
        objects.append(obj)

    add("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    add("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    add(
        "3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R>> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n"
    )
    add("4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n")
    stream_bytes = stream.encode("utf-8")
    add(f"5 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n{stream}\nendstream\nendobj\n")

    xref_pos = len("%PDF-1.4\n") + sum(len(o) for o in objects)
    xref_entries = ["0000000000 65535 f "] + [f"{o:010} 00000 n " for o in offsets]
    xref = "xref\n0 6\n" + "\n".join(xref_entries) + "\n"
    trailer = f"trailer\n<< /Root 1 0 R /Size 6 >>\nstartxref\n{xref_pos}\n%%EOF\n"

    with open(path, "wb") as fh:
        fh.write("%PDF-1.4\n".encode("utf-8"))
        for obj in objects:
            fh.write(obj.encode("utf-8"))
        fh.write(xref.encode("utf-8"))
        fh.write(trailer.encode("utf-8"))
