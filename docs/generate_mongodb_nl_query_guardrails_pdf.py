"""Generate a professional one-page PDF explaining MongoDB NL query guardrails.

This script avoids external PDF dependencies and writes a standards-compliant PDF
using built-in Type1 fonts (Helvetica + Courier).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import textwrap


PAGE_WIDTH = 595
PAGE_HEIGHT = 842

MARGIN_X = 40
CONTENT_TOP = 720
CONTENT_BOTTOM = 60

FONT_REG = "F1"  # Helvetica
FONT_BOLD = "F2"  # Helvetica-Bold
FONT_CODE = "F3"  # Courier

COLOR_BRAND_DARK = (0.00, 0.25, 0.35)
COLOR_BRAND_LIGHT = (0.00, 0.73, 0.45)
COLOR_TEXT = (0.13, 0.17, 0.22)
COLOR_MUTED = (0.32, 0.37, 0.42)
COLOR_CODE_BG = (0.95, 0.97, 0.99)
COLOR_CODE_BORDER = (0.82, 0.87, 0.92)


@dataclass
class PDFBuilder:
    commands: list[str]
    y: float

    def cmd(self, text: str) -> None:
        self.commands.append(text)

    def set_fill(self, rgb: tuple[float, float, float]) -> None:
        self.cmd(f"{rgb[0]:.4f} {rgb[1]:.4f} {rgb[2]:.4f} rg")

    def rect_fill(self, x: float, y: float, w: float, h: float) -> None:
        self.cmd(f"{x:.1f} {y:.1f} {w:.1f} {h:.1f} re f")

    def rect_stroke(self, x: float, y: float, w: float, h: float) -> None:
        self.cmd(f"{x:.1f} {y:.1f} {w:.1f} {h:.1f} re S")

    def set_stroke(self, rgb: tuple[float, float, float], width: float = 1) -> None:
        self.cmd(f"{rgb[0]:.4f} {rgb[1]:.4f} {rgb[2]:.4f} RG")
        self.cmd(f"{width:.1f} w")

    def text(self, x: float, y: float, value: str, font: str, size: int, color: tuple[float, float, float]) -> None:
        escaped = value.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        self.cmd(f"/{font} {size} Tf")
        self.set_fill(color)
        self.cmd(f"1 0 0 1 {x:.1f} {y:.1f} Tm")
        self.cmd(f"({escaped}) Tj")

    def write_wrapped(self, x: float, text: str, font: str, size: int, color: tuple[float, float, float],
                      width_chars: int, line_height: int = 15, gap_after: int = 2) -> None:
        for line in textwrap.wrap(text, width=width_chars, break_long_words=False, replace_whitespace=False):
            self.text(x, self.y, line, font, size, color)
            self.y -= line_height
        self.y -= gap_after

    def section_title(self, value: str) -> None:
        self.text(MARGIN_X, self.y, value, FONT_BOLD, 13, COLOR_TEXT)
        self.y -= 18

    def bullet(self, value: str) -> None:
        self.text(MARGIN_X + 4, self.y, "-", FONT_BOLD, 12, COLOR_BRAND_DARK)
        self.write_wrapped(MARGIN_X + 16, value, FONT_REG, 10, COLOR_TEXT, width_chars=84, line_height=14, gap_after=1)

    def code_block(self, title: str, code_lines: list[str]) -> None:
        block_width = PAGE_WIDTH - (2 * MARGIN_X)
        line_height = 12
        block_height = 22 + (len(code_lines) * line_height) + 12
        y_bottom = self.y - block_height + 6

        self.set_fill(COLOR_CODE_BG)
        self.rect_fill(MARGIN_X, y_bottom, block_width, block_height)
        self.set_stroke(COLOR_CODE_BORDER, width=1)
        self.rect_stroke(MARGIN_X, y_bottom, block_width, block_height)

        self.text(MARGIN_X + 10, self.y - 10, title, FONT_BOLD, 10, COLOR_MUTED)

        code_y = self.y - 26
        for line in code_lines:
            self.text(MARGIN_X + 10, code_y, line, FONT_CODE, 9, COLOR_TEXT)
            code_y -= line_height

        self.y = y_bottom - 14


def build_pdf_bytes(content_stream: str) -> bytes:
    objects: list[bytes] = []

    def add(obj: str) -> None:
        objects.append(obj.encode("latin-1"))

    add("<< /Type /Catalog /Pages 2 0 R >>")
    add("<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    add(
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        "/Resources << /Font << /F1 5 0 R /F2 6 0 R /F3 7 0 R >> >> "
        "/Contents 4 0 R >>"
    )

    content_bytes = content_stream.encode("latin-1")
    stream_obj = b"<< /Length " + str(len(content_bytes)).encode("ascii") + b" >>\nstream\n" + content_bytes + b"\nendstream"
    objects.append(stream_obj)

    add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    add("<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

    chunks: list[bytes] = [b"%PDF-1.4\n"]
    offsets = [0]
    cursor = len(chunks[0])

    for idx, obj in enumerate(objects, start=1):
        offsets.append(cursor)
        block = f"{idx} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"
        chunks.append(block)
        cursor += len(block)

    xref_pos = cursor
    xref = [f"xref\n0 {len(objects) + 1}\n".encode("ascii"), b"0000000000 65535 f \n"]
    for off in offsets[1:]:
        xref.append(f"{off:010d} 00000 n \n".encode("ascii"))

    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode("ascii")

    return b"".join(chunks + xref + [trailer])


def generate() -> None:
    b = PDFBuilder(commands=[], y=CONTENT_TOP)

    # Header bars
    b.set_fill(COLOR_BRAND_DARK)
    b.rect_fill(0, 742, PAGE_WIDTH, 100)
    b.set_fill(COLOR_BRAND_LIGHT)
    b.rect_fill(0, 736, PAGE_WIDTH, 8)

    b.text(40, 792, "MongoDB Flow: Natural Language to Trusted Results", FONT_BOLD, 23, (1, 1, 1))
    b.text(40, 766, "Natural Language -> Query Generation -> Guardrails -> Result", FONT_REG, 12, (0.78, 1.0, 0.9))

    b.section_title("1) Natural Language Input")
    b.write_wrapped(
        MARGIN_X,
        "A user asks a business question in plain English. The agent extracts intent, entities, time windows, and required metrics.",
        FONT_REG,
        10,
        COLOR_TEXT,
        width_chars=96,
    )

    b.code_block(
        "Example user prompt",
        [
            "\"Show Scope 1 emissions for semiconductor companies in 2024,",
            "sorted by highest emissions and limited to 25 records.\"",
        ],
    )

    b.section_title("2) Query Generation")
    b.bullet("The agent maps business phrases to the approved collection schema and legal MongoDB operators.")
    b.bullet("Output is deterministic and machine-checkable before any database execution.")

    b.code_block(
        "Generated MQL plan (pre-guardrails)",
        [
            "{",
            "  \"collection\": \"esg_emissions\",",
            "  \"query\": {\"company.sector\": \"Semiconductors\", \"reporting_year\": 2024},",
            "  \"projection\": {\"company.ticker\": 1, \"scope1_emissions\": 1, \"_id\": 0},",
            "  \"sort\": {\"scope1_emissions\": -1},",
            "  \"limit\": 25",
            "}",
        ],
    )

    b.section_title("3) Guardrails")
    b.bullet("Field allowlist: blocks unknown or policy-restricted fields.")
    b.bullet("Index coverage: requires indexed filter paths to avoid collection scans.")
    b.bullet("Safety injection: enforces maxTimeMS and hard result limits.")

    b.code_block(
        "Blocked response shape",
        [
            "{",
            "  \"success\": false,",
            "  \"guardrail\": \"index_coverage\",",
            "  \"error\": \"No indexed filter field found\",",
            "  \"details\": {\"required\": [\"company.ticker\", \"reporting_year\"]}",
            "}",
        ],
    )

    b.section_title("4) Trusted Result")
    b.bullet("Only validated queries execute against MongoDB.")
    b.bullet("Results include clear user-facing output plus traceable guardrail context.")

    b.text(MARGIN_X, 46, "Outcome: faster insight with governance, reliability, and predictable performance.", FONT_BOLD, 10, COLOR_BRAND_DARK)

    # Build content stream in text mode with one graphics-state block.
    content = "q\n" + "\n".join(b.commands) + "\nQ"

    pdf = build_pdf_bytes(content)
    out_path = Path("docs/mongodb_nl_query_guardrails_result.pdf")
    out_path.write_bytes(pdf)
    print(f"Wrote {out_path} ({len(pdf)} bytes)")


if __name__ == "__main__":
    generate()
