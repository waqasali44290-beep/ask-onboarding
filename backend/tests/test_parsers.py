"""PDF / Markdown / TXT parsing, unsupported types and empty files."""
import pytest

from app.ingestion.parsers import ParsedDocument, ParseError, parse_file


def test_markdown_and_txt_are_decoded_with_unix_line_endings():
    parsed = parse_file("pto.md", b"# PTO\r\n\r\nYou get 25 days.")
    assert parsed.text == "# PTO\n\nYou get 25 days."
    assert parsed.page_for_offset(5) is None


def test_unsupported_extension_is_rejected():
    with pytest.raises(ParseError, match="Unsupported file type"):
        parse_file("slides.pptx", b"anything")


def test_empty_file_is_rejected():
    with pytest.raises(ParseError, match="no readable text"):
        parse_file("empty.txt", b"  \n ")


def test_page_for_offset_maps_characters_to_pdf_pages():
    # Three pages starting at characters 0, 100 and 250.
    parsed = ParsedDocument(text="x" * 300, page_starts=[0, 100, 250])
    assert parsed.page_for_offset(0) == 1
    assert parsed.page_for_offset(99) == 1
    assert parsed.page_for_offset(100) == 2
    assert parsed.page_for_offset(299) == 3


def make_pdf(pages: list[str]) -> bytes:
    """Build a minimal valid PDF with one line of Helvetica text per page."""
    font_id = 3 + 2 * len(pages)
    objects = [
        "<</Type/Catalog/Pages 2 0 R>>",
        "<</Type/Pages/Kids[{}]/Count {}>>".format(
            " ".join(f"{3 + 2 * i} 0 R" for i in range(len(pages))), len(pages)
        ),
    ]
    for i, text in enumerate(pages):
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
        objects.append(
            f"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
            f"/Resources<</Font<</F1 {font_id} 0 R>>>>/Contents {4 + 2 * i} 0 R>>"
        )
        objects.append(f"<</Length {len(stream)}>>stream\n{stream}\nendstream")
    objects.append("<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>")

    out = "%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    out += "".join(f"{offset:010d} 00000 n \n" for offset in offsets)
    out += f"trailer<</Size {len(objects) + 1}/Root 1 0 R>>\nstartxref\n{xref_at}\n%%EOF\n"
    return out.encode("latin-1")


def test_pdf_text_is_extracted_with_page_numbers():
    parsed = parse_file("benefits.pdf", make_pdf(["Health insurance starts day one.", "Pension match is 5 percent."]))
    assert "Health insurance starts day one." in parsed.text
    second_page_at = parsed.text.index("Pension match")
    assert parsed.page_for_offset(0) == 1
    assert parsed.page_for_offset(second_page_at) == 2


def test_broken_pdf_gives_a_readable_error():
    with pytest.raises(ParseError, match="Could not read the PDF"):
        parse_file("handbook.pdf", b"this is not a pdf")
