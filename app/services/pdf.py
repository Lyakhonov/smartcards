import fitz


def extract_text_from_pdf(file: bytes) -> str:
    doc = fitz.open(stream=file, filetype="pdf")
    text = ""

    for page in doc:
        text += page.get_text()

    return text
