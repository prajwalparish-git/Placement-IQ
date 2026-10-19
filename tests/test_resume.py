from io import BytesIO

import pytest
from docx import Document

from piq.resume import MAX_BYTES, ResumeError, extract_text

TEXT = "Test Student\nSkills: Python, Django, SQL, Data Structures\nProject: Attendance tracker"


def _pdf(text: str) -> bytes:
    """A minimal valid one-page PDF with `text` drawn in Helvetica."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode() if text else b""
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = BytesIO(b"%PDF-1.4\n"), []
    for i, o in enumerate(objs, 1):
        out.seek(0, 2)
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n%s\nendobj\n" % (i, o))
    xref = out.tell()
    out.write(b"xref\n0 6\n0000000000 65535 f \n")
    out.write(b"".join(b"%010d 00000 n \n" % off for off in offsets))
    out.write(b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % xref)
    return out.getvalue()


def test_txt_and_uppercase_extension():
    assert "Django" in extract_text("cv.txt", TEXT.encode())
    assert "Django" in extract_text("CV.TXT", TEXT.encode())


def test_docx_paragraphs_and_tables():
    doc = Document()
    doc.add_paragraph("Test Student — resume")
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Skills"
    table.cell(0, 1).text = "Python, Django, SQL, Data Structures, Algorithms"
    buf = BytesIO()
    doc.save(buf)
    text = extract_text("cv.docx", buf.getvalue())
    assert "Test Student" in text and "Algorithms" in text


def test_pdf_text_is_extracted():
    text = extract_text("cv.pdf", _pdf("Skills Java SQL Data Structures Algorithms Git Docker"))
    assert "Data Structures" in text


def test_pdf_without_text_layer_is_rejected():
    with pytest.raises(ResumeError, match="scanned PDFs"):
        extract_text("scan.pdf", _pdf(""))


@pytest.mark.parametrize(
    ("name", "size", "message"),
    [
        ("cv.png", 100, "Unsupported file type"),
        ("cv", 100, "Unsupported file type"),
        ("cv.txt", 9, "Could not read text"),
        ("cv.txt", MAX_BYTES + 1, "larger than 5 MB"),
    ],
    ids=["png", "no-extension", "too-short", "too-large"],
)
def test_bad_input_is_rejected(name, size, message):
    with pytest.raises(ResumeError, match=message):
        extract_text(name, b"x" * size)


@pytest.mark.parametrize(
    "data",
    [b"%PDF-1.4\n" + b"\x00garbage" * 40, _pdf("Skills Java SQL Data Structures")[:200]],
    ids=["garbage", "truncated"],
)
def test_damaged_pdf_is_rejected_with_a_message(data):
    with pytest.raises(ResumeError, match="Could not open this PDF"):
        extract_text("cv.pdf", data)


def test_damaged_docx_is_rejected_with_a_message():
    with pytest.raises(ResumeError, match="Could not open this DOCX"):
        extract_text("cv.docx", b"PK\x03\x04 not really a zip archive" * 10)
