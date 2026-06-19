# 기안문 초안을 HWPX 템플릿에 주입해 새 파일을 생성하는 모듈
import io
import shutil
import zipfile
from copy import deepcopy
from pathlib import Path
from lxml import etree

TEMPLATE = Path(__file__).parent / "기안문.hwpx"

HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS = {"hp": HP}

# paraPrIDRef 값 (템플릿에서 확인)
PARA_PR_BODY = "21"   # 본문 들여쓰기 단락
PARA_PR_BLANK = "20"  # 빈 줄
PARA_PR_DEFAULT = "0" # 제목·구분선


def _make_para(text: str, para_pr: str, char_pr: str = "8") -> etree._Element:
    """hp:p 요소를 생성합니다. linesegarray 없이."""
    p = etree.Element(f"{{{HP}}}p", attrib={
        "id": "0",
        "paraPrIDRef": para_pr,
        "styleIDRef": "0",
        "pageBreak": "0",
        "columnBreak": "0",
        "merged": "0",
    })
    run = etree.SubElement(p, f"{{{HP}}}run", attrib={"charPrIDRef": char_pr})
    if text:
        t = etree.SubElement(run, f"{{{HP}}}t")
        t.text = text
    return p


def write_hwpx(draft: dict, output_path: str) -> str:
    """
    draft: {"title": str, "body_lines": [str], "attachment": str}
    output_path: 저장할 경로 (.hwpx)
    반환값: 저장된 파일 경로
    """
    # 템플릿 복사 후 수정
    shutil.copy2(TEMPLATE, output_path)

    buf = io.BytesIO()
    with zipfile.ZipFile(TEMPLATE, "r") as zin, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        # mimetype은 반드시 첫 번째, STORED
        zout.writestr(zipfile.ZipInfo("mimetype"), zin.read("mimetype"), compress_type=zipfile.ZIP_STORED)

        for item in zin.infolist():
            if item.filename == "mimetype":
                continue
            if item.filename == "Contents/section0.xml":
                new_xml = _build_section(draft, zin.read(item.filename))
                zout.writestr(item.filename, new_xml)
            else:
                zout.writestr(item, zin.read(item.filename))

    Path(output_path).write_bytes(buf.getvalue())
    return output_path


def _build_section(draft: dict, original_xml: bytes) -> bytes:
    root = etree.fromstring(original_xml)
    paras = root.findall(f"{{{HP}}}p")

    # 원본에서 첫 3개 단락(제목, 구분선, 빈줄)과 secPr를 가져온 뒤 나머지 제거
    # secPr는 paras[0]의 run 안에 있음 — 그대로 유지
    keep = paras[:3]  # [0]=제목, [1]=구분선, [2]=빈줄

    # 제목 텍스트 교체
    title_t = keep[0].find(f".//{{{HP}}}t")
    if title_t is not None:
        title_t.text = f"제목 : {draft['title']}"
    # linesegarray 제거
    for p in keep:
        _strip_linesegarray(p)

    # 기존 단락 모두 제거
    for p in paras:
        root.remove(p)

    # keep 단락 다시 추가
    for p in keep:
        root.append(p)

    # 본문 줄 추가
    for line in draft.get("body_lines", []):
        root.append(_make_para(line, PARA_PR_BODY))

    # 빈 줄
    root.append(_make_para("", PARA_PR_BLANK))

    # 붙임
    attachment = draft.get("attachment", "해당없음")
    if attachment and attachment != "해당없음":
        root.append(_make_para(f"붙임  {attachment} 1부.  끝.", PARA_PR_BODY))
    else:
        root.append(_make_para("끝.", PARA_PR_BODY))

    return etree.tostring(root, encoding="UTF-8", xml_declaration=True, standalone=True)


def _strip_linesegarray(p: etree._Element):
    for lsa in p.findall(f"{{{HP}}}linesegarray"):
        p.remove(lsa)
