# 업로드 파일에서 텍스트를 추출하는 모듈 (PDF, HWPX, DOCX, TXT)
import zipfile
from pathlib import Path
from lxml import etree


def extract_text(file_path: str) -> str:
    path = Path(file_path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _from_pdf(path)
    elif suffix == ".hwpx":
        return _from_hwpx(path)
    elif suffix in (".docx", ".doc"):
        return _from_docx(path)
    elif suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")
    else:
        raise ValueError(f"지원하지 않는 파일 형식: {suffix}")


def _from_pdf(path: Path) -> str:
    from pypdf import PdfReader
    pages = []
    reader = PdfReader(path)
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


def _from_hwpx(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        # PrvText.txt는 미리보기 텍스트로 빠르게 추출 가능
        if "Preview/PrvText.txt" in z.namelist():
            raw = z.read("Preview/PrvText.txt")
            return raw.decode("utf-8", errors="replace")
        # 없으면 section0.xml에서 직접 파싱
        xml = z.read("Contents/section0.xml")
    root = etree.fromstring(xml)
    ns = {"hp": "http://www.hancom.co.kr/hwpml/2011/paragraph"}
    lines = []
    for p in root.findall(".//hp:p", ns):
        text = "".join(t.text or "" for t in p.findall(".//hp:t", ns))
        lines.append(text)
    return "\n".join(lines)


def _from_docx(path: Path) -> str:
    from docx import Document
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)
