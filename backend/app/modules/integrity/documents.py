"""
Turn an uploaded question paper into what a model reads: page images or text.

- Photos (JPEG/PNG/WebP) → one image.
- PDF → per page: a born-digital page (enough *visible* text) is read from its own
  text layer; a scanned page is rendered to an image for the vision model. Scans
  often carry an invisible OCR text layer or a visible watermark line — neither
  counts, because OCR text is unreliable and a watermark is not the paper.
  A born-digital page that also has a picture (a figure) goes to the vision model
  together with its exact text.
- Word (.docx) → text, with tables as Markdown, equations as LaTeX and automatic
  list numbering written out, so the question numbers survive.

Nothing here is stored: the caller keeps only the extracted wording and a SHA-256.
"""
import io
import re
import zipfile
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
from PIL import Image, ImageOps, UnidentifiedImageError

PDF_TYPE = "application/pdf"
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp")
ACCEPTED_TYPES = (PDF_TYPE, DOCX_TYPE, *IMAGE_TYPES)

_BY_EXTENSION = {
    ".pdf": PDF_TYPE, ".docx": DOCX_TYPE, ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".webp": "image/webp",
}

# Long side in pixels: enough to read printed text, and keeps vision input bounded.
_MAX_SIDE = 1800
_PDF_RENDER_SCALE = 150 / 72  # 150 dpi
# A page with fewer visible letters than this is treated as a scan.
_MIN_VISIBLE_LETTERS = 150
# Pictures smaller than this (pixels per side) are logos or bullets, not figures.
_MIN_FIGURE_PX = 120
# Text sent to the model in one call; longer documents are split at page/paragraph breaks.
TEXT_CHUNK_CHARS = 8000
# Word documents larger than this when unzipped are refused (zip bombs).
_MAX_DOCX_XML_BYTES = 20 * 1024 * 1024


class UnreadablePaperError(ValueError):
    pass


class TooManyPagesError(ValueError):
    pass


@dataclass
class PreparedPage:
    """One model call's input: an image, text, or both (text then guides the wording)."""
    image: bytes | None = None
    text: str | None = None


@dataclass
class PreparedPaper:
    method: str  # VISION | TEXT_LAYER | DOCX | MIXED
    page_count: int | None  # None for Word documents
    pages: list[PreparedPage] = field(default_factory=list)

    @property
    def source_text(self) -> str:
        """All exact text the document gave us — used to check the model copied it faithfully."""
        return "\n".join(page.text for page in self.pages if page.text)


def normalize_content_type(content_type: str | None, filename: str | None) -> str:
    content_type = (content_type or "").split(";")[0].strip().lower()
    if content_type == "image/jpg":
        content_type = "image/jpeg"
    if content_type in ACCEPTED_TYPES:
        return content_type
    # Browsers sometimes send .docx (and others) as application/octet-stream.
    suffix = "." + (filename or "").rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""
    return _BY_EXTENSION.get(suffix, content_type)


def prepare(data: bytes, content_type: str, max_pages: int) -> PreparedPaper:
    if content_type == DOCX_TYPE:
        text = docx_text(data)
        if _letters(text) < 20:
            raise UnreadablePaperError("The Word document has no question text")
        return PreparedPaper(
            method="DOCX", page_count=None,
            pages=[PreparedPage(text=chunk) for chunk in chunk_text([text])],
        )
    if content_type == PDF_TYPE:
        return _prepare_pdf(data, max_pages)
    try:
        image = Image.open(io.BytesIO(data))
        # Phone photos store their rotation in EXIF rather than in the pixels.
        image = ImageOps.exif_transpose(image)
        return PreparedPaper(method="VISION", page_count=1, pages=[PreparedPage(image=_to_jpeg(image))])
    except (UnidentifiedImageError, OSError) as exc:
        raise UnreadablePaperError("The image could not be opened") from exc


# ── PDF ───────────────────────────────────────────────────────────────────────

def _prepare_pdf(data: bytes, max_pages: int) -> PreparedPaper:
    try:
        pdf = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as exc:
        raise UnreadablePaperError("The PDF could not be opened") from exc
    try:
        if len(pdf) == 0:
            raise UnreadablePaperError("The PDF has no pages")
        if len(pdf) > max_pages:
            raise TooManyPagesError(max_pages)
        pages: list[PreparedPage] = []
        kinds: set[str] = set()
        for index in range(len(pdf)):
            page = pdf[index]
            text = _visible_text(page)
            if _letters(text) < _MIN_VISIBLE_LETTERS:
                kinds.add("scan")
                pages.append(PreparedPage(image=_to_jpeg(page.render(scale=_PDF_RENDER_SCALE).to_pil())))
            elif _has_figure(page):
                kinds.add("figure")
                pages.append(PreparedPage(
                    image=_to_jpeg(page.render(scale=_PDF_RENDER_SCALE).to_pil()), text=text,
                ))
            else:
                kinds.add("text")
                pages.append(PreparedPage(text=text))
        page_count = len(pdf)
    finally:
        pdf.close()

    if kinds == {"text"}:
        method = "TEXT_LAYER"
        pages = [PreparedPage(text=chunk) for chunk in chunk_text([p.text or "" for p in pages])]
    elif "text" in kinds or "figure" in kinds:
        method = "MIXED" if "scan" in kinds else "TEXT_LAYER"
    else:
        method = "VISION"
    return PreparedPaper(method=method, page_count=page_count, pages=pages)


def _visible_text(page: pdfium.PdfPage) -> str:
    """The page's text, leaving out invisible text (the OCR layer scanner apps add)."""
    textpage = page.get_textpage()
    try:
        chars = []
        for i in range(textpage.count_chars()):
            obj = pdfium_c.FPDFText_GetTextObject(textpage.raw, i)
            if obj and pdfium_c.FPDFTextObj_GetTextRenderMode(obj) == pdfium_c.FPDF_TEXTRENDERMODE_INVISIBLE:
                continue
            chars.append(chr(pdfium_c.FPDFText_GetUnicode(textpage.raw, i)))
    finally:
        textpage.close()
    text = "".join(chars).replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t ]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def _has_figure(page: pdfium.PdfPage) -> bool:
    for obj in page.get_objects(filter=(pdfium_c.FPDF_PAGEOBJ_IMAGE,), max_depth=10):
        try:
            width, height = obj.get_px_size()
        except pdfium.PdfiumError:
            continue
        if width >= _MIN_FIGURE_PX and height >= _MIN_FIGURE_PX:
            return True
    return False


def _letters(text: str) -> int:
    return sum(ch.isalpha() for ch in text)


def _to_jpeg(image: Image.Image) -> bytes:
    image = image.convert("RGB")
    image.thumbnail((_MAX_SIDE, _MAX_SIDE))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def chunk_text(parts: list[str], limit: int = TEXT_CHUNK_CHARS) -> list[str]:
    """Join pages into chunks of at most `limit` characters, splitting long ones at blank lines."""
    pieces: list[str] = []
    for part in parts:
        if len(part) <= limit:
            pieces.append(part)
            continue
        current = ""
        for paragraph in part.split("\n"):
            if current and len(current) + len(paragraph) + 1 > limit:
                pieces.append(current)
                current = ""
            current = f"{current}\n{paragraph}" if current else paragraph
        if current:
            pieces.append(current)
    chunks: list[str] = []
    for piece in pieces:
        if chunks and len(chunks[-1]) + len(piece) + 2 <= limit:
            chunks[-1] = f"{chunks[-1]}\n\n{piece}"
        else:
            chunks.append(piece)
    return [chunk for chunk in chunks if chunk.strip()]


# ── Word (.docx) ──────────────────────────────────────────────────────────────

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
_MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"


def docx_text(data: bytes) -> str:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise UnreadablePaperError("The Word document could not be opened") from exc
    with archive:
        document = _read_xml(archive, "word/document.xml", required=True)
        numbering = _Numbering(_read_xml(archive, "word/numbering.xml", required=False))
    body = document.find(f"{_W}body")
    if body is None:
        raise UnreadablePaperError("The Word document has no body")
    blocks = []
    for child in body:
        if child.tag == f"{_W}p":
            blocks.append(_paragraph(child, numbering))
        elif child.tag == f"{_W}tbl":
            blocks.append(_table(child, numbering))
    return "\n".join(block for block in blocks if block.strip())


def _read_xml(archive: zipfile.ZipFile, name: str, *, required: bool) -> ET.Element | None:
    try:
        info = archive.getinfo(name)
    except KeyError as exc:
        if required:
            raise UnreadablePaperError("The file is not a Word document") from exc
        return None
    if info.file_size > _MAX_DOCX_XML_BYTES:
        raise UnreadablePaperError("The Word document is too large to read")
    raw = archive.read(info)
    # Word never writes DTDs; refusing them rules out entity-expansion attacks.
    if b"<!DOCTYPE" in raw[:4096] or b"<!ENTITY" in raw[:4096]:
        raise UnreadablePaperError("The Word document could not be read")
    try:
        return ET.fromstring(raw)
    except ET.ParseError as exc:
        raise UnreadablePaperError("The Word document is damaged") from exc


def _paragraph(p: ET.Element, numbering: "_Numbering") -> str:
    text = _inline(p).strip()
    number = numbering.label_for(p)
    if number and text:
        return f"{number} {text}"
    return text


def _table(tbl: ET.Element, numbering: "_Numbering") -> str:
    rows = []
    for tr in tbl.findall(f"{_W}tr"):
        cells = []
        for tc in tr.findall(f"{_W}tc"):
            parts = []
            for child in tc:
                if child.tag == f"{_W}p":
                    parts.append(_paragraph(child, numbering))
                elif child.tag == f"{_W}tbl":
                    parts.append(_table(child, numbering).replace("\n", " "))
            cells.append(" <br> ".join(part for part in parts if part).replace("|", "\\|"))
        if any(cells):
            rows.append("| " + " | ".join(cells) + " |")
    if not rows:
        return ""
    width = rows[0].count(" | ") + 1
    return "\n".join([rows[0], "|" + " --- |" * width, *rows[1:]])


def _inline(element: ET.Element) -> str:
    out = []
    for child in element:
        tag = child.tag
        if tag == f"{_W}t":
            out.append(child.text or "")
        elif tag in (f"{_W}tab", f"{_W}ptab"):
            out.append(" ")
        elif tag in (f"{_W}br", f"{_W}cr"):
            out.append("\n")
        elif tag == f"{_M}oMathPara":
            out.append(" " + " ".join(f"${_math(m)}$" for m in child.iter(f"{_M}oMath")) + " ")
        elif tag == f"{_M}oMath":
            out.append(f" ${_math(child)}$ ")
        elif tag == f"{_MC}AlternateContent":
            # The same content in several forms; use the first only.
            choice = next(iter(child), None)
            if choice is not None:
                out.append(_inline(choice))
        elif tag in (f"{_W}drawing", f"{_W}pict", f"{_W}object"):
            boxes = list(child.iter(f"{_W}txbxContent"))
            if boxes:
                out.append(" ".join(_inline(p) for box in boxes for p in box.iter(f"{_W}p")))
            else:
                out.append(" [image] ")
        elif tag in (f"{_W}delText", f"{_W}instrText", f"{_W}rPr", f"{_W}pPr", f"{_W}del"):
            continue
        else:
            out.append(_inline(child))
    return re.sub(r"[ \t]+", " ", "".join(out))


# Office Math (OMML) → LaTeX, for the constructs exam papers use.
_NARY = {"∑": r"\sum", "∏": r"\prod", "∫": r"\int", "∬": r"\iint", "∭": r"\iiint", "∮": r"\oint"}
_SYMBOLS = {
    "×": r"\times ", "÷": r"\div ", "≤": r"\le ", "≥": r"\ge ", "≠": r"\ne ", "±": r"\pm ",
    "→": r"\to ", "∞": r"\infty ", "α": r"\alpha ", "β": r"\beta ", "γ": r"\gamma ",
    "δ": r"\delta ", "θ": r"\theta ", "λ": r"\lambda ", "μ": r"\mu ", "π": r"\pi ",
    "σ": r"\sigma ", "ω": r"\omega ", "Δ": r"\Delta ", "∂": r"\partial ", "√": r"\sqrt ",
    "≈": r"\approx ", "∈": r"\in ", "·": r"\cdot ",
}


def _math(element: ET.Element) -> str:
    return "".join(_math_node(child) for child in element).strip()


def _arg(element: ET.Element, name: str) -> str:
    found = element.find(f"{_M}{name}")
    return _math(found) if found is not None else ""


def _math_node(node: ET.Element) -> str:
    tag = node.tag.removeprefix(_M)
    if tag == "r":
        text = "".join(t.text or "" for t in node.iter(f"{_M}t"))
        return "".join(_SYMBOLS.get(ch, ch) for ch in text)
    if tag == "f":
        return rf"\frac{{{_arg(node, 'num')}}}{{{_arg(node, 'den')}}}"
    if tag == "sSup":
        return f"{{{_arg(node, 'e')}}}^{{{_arg(node, 'sup')}}}"
    if tag == "sSub":
        return f"{{{_arg(node, 'e')}}}_{{{_arg(node, 'sub')}}}"
    if tag == "sSubSup":
        return f"{{{_arg(node, 'e')}}}_{{{_arg(node, 'sub')}}}^{{{_arg(node, 'sup')}}}"
    if tag == "rad":
        degree = _arg(node, "deg")
        return rf"\sqrt[{degree}]{{{_arg(node, 'e')}}}" if degree else rf"\sqrt{{{_arg(node, 'e')}}}"
    if tag == "nary":
        chr_el = node.find(f"{_M}naryPr/{_M}chr")
        symbol = chr_el.get(f"{_M}val") if chr_el is not None else "∫"
        command = _NARY.get(symbol, symbol)
        sub, sup = _arg(node, "sub"), _arg(node, "sup")
        limits = (f"_{{{sub}}}" if sub else "") + (f"^{{{sup}}}" if sup else "")
        return f"{command}{limits} {_arg(node, 'e')}"
    if tag == "d":
        pr = node.find(f"{_M}dPr")
        beg = end = None
        if pr is not None:
            beg_el, end_el = pr.find(f"{_M}begChr"), pr.find(f"{_M}endChr")
            beg = beg_el.get(f"{_M}val") if beg_el is not None else None
            end = end_el.get(f"{_M}val") if end_el is not None else None
        inner = ", ".join(_math(e) for e in node.findall(f"{_M}e"))
        return f"{beg if beg is not None else '('}{inner}{end if end is not None else ')'}"
    if tag == "func":
        return f"\\{_arg(node, 'fName').strip()} {_arg(node, 'e')}"
    if tag == "m":
        rows = [" & ".join(_math(e) for e in mr.findall(f"{_M}e")) for mr in node.findall(f"{_M}mr")]
        return r"\begin{matrix} " + r" \\ ".join(rows) + r" \end{matrix}"
    if tag in ("acc", "bar", "box", "borderBox", "groupChr", "limLow", "limUpp", "eqArr", "e"):
        return " ".join(_math(child) for child in node if not child.tag.endswith("Pr"))
    if tag.endswith("Pr"):
        return ""
    return _math(node)


def _letters_for(n: int) -> str:
    out = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def _roman(n: int) -> str:
    values = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
              (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = ""
    for value, numeral in values:
        while n >= value:
            out += numeral
            n -= value
    return out


_FORMATS = {
    "decimal": str,
    "lowerLetter": lambda n: _letters_for(n).lower(),
    "upperLetter": _letters_for,
    "lowerRoman": lambda n: _roman(n).lower(),
    "upperRoman": _roman,
}


class _Numbering:
    """Writes out Word's automatic list numbers ("1.", "(a)", "ii)") — question labels often are one."""

    def __init__(self, root: ET.Element | None) -> None:
        self._levels: dict[str, dict[int, tuple[str, str, int]]] = {}  # numId → ilvl → (fmt, text, start)
        self._counters: dict[str, dict[int, int]] = {}
        if root is None:
            return
        abstract = {}
        for an in root.findall(f"{_W}abstractNum"):
            levels = {}
            for lvl in an.findall(f"{_W}lvl"):
                levels[int(lvl.get(f"{_W}ilvl", "0"))] = (
                    _val(lvl.find(f"{_W}numFmt"), "decimal"),
                    _val(lvl.find(f"{_W}lvlText"), ""),
                    int(_val(lvl.find(f"{_W}start"), "1")),
                )
            abstract[an.get(f"{_W}abstractNumId")] = levels
        for num in root.findall(f"{_W}num"):
            levels = dict(abstract.get(_val(num.find(f"{_W}abstractNumId"), ""), {}))
            for override in num.findall(f"{_W}lvlOverride"):
                start = override.find(f"{_W}startOverride")
                ilvl = int(override.get(f"{_W}ilvl", "0"))
                if start is not None and ilvl in levels:
                    fmt, text, _ = levels[ilvl]
                    levels[ilvl] = (fmt, text, int(_val(start, "1")))
            self._levels[num.get(f"{_W}numId")] = levels

    def label_for(self, p: ET.Element) -> str | None:
        num_pr = p.find(f"{_W}pPr/{_W}numPr")
        if num_pr is None:
            return None
        num_id = _val(num_pr.find(f"{_W}numId"), "")
        ilvl = int(_val(num_pr.find(f"{_W}ilvl"), "0"))
        levels = self._levels.get(num_id)
        if not levels or ilvl not in levels:
            return None
        fmt, text, start = levels[ilvl]
        counters = self._counters.setdefault(num_id, {})
        counters[ilvl] = counters.get(ilvl, start - 1) + 1
        for deeper in [k for k in counters if k > ilvl]:
            del counters[deeper]
        if fmt in ("bullet", "none") or not text:
            return None

        def render(match: re.Match) -> str:
            level = int(match.group(1)) - 1
            level_fmt, _, level_start = levels.get(level, ("decimal", "", 1))
            value = counters.get(level, level_start)
            return _FORMATS.get(level_fmt, str)(value)

        return re.sub(r"%(\d)", render, text)


def _val(element: ET.Element | None, default: str) -> str:
    if element is None:
        return default
    return element.get(f"{_W}val", default)


# ── Labels ────────────────────────────────────────────────────────────────────

def normalize_label(label: str) -> str:
    """'Q1(a)', '1 (a)', '1.a' and 'q1a' all become '1a'."""
    label = label.strip().lower()
    label = re.sub(r"^(question|ques|qn|q)\s*\.?\s*", "", label)
    return re.sub(r"[^0-9a-z]", "", label)
