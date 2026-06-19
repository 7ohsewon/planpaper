# 기안문 자동 생성 Streamlit 앱 진입점
import os
import tempfile
from pathlib import Path

import streamlit as st

from extractor import extract_text
from draft import generate_draft
from hwpx_writer import write_hwpx

st.set_page_config(page_title="기안문 자동 생성", page_icon="📄", layout="centered")
st.title("📄 기안문 자동 생성")
st.caption("PDF · HWPX · DOCX · TXT 파일을 업로드하면 AI가 기안문(.hwpx)을 만들어 드립니다.")

# LLM 설정 입력 (환경변수 우선)
provider_options = {
    "openai": "OpenAI 호환",
    "anthropic": "Anthropic Claude",
}
default_provider = os.environ.get("LLM_PROVIDER", "openai").lower()
if default_provider not in provider_options:
    default_provider = "openai"

provider = st.selectbox(
    "LLM 제공자",
    options=list(provider_options.keys()),
    index=list(provider_options.keys()).index(default_provider),
    format_func=lambda key: provider_options[key],
)

if provider == "openai":
    default_api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    default_model = os.environ.get("LLM_MODEL") or os.environ.get("OPENAI_MODEL", "gpt-5.5")
    default_base_url = os.environ.get("OPENAI_BASE_URL", "")
    api_label = "API Access Token"
    api_placeholder = "sk-... (공식 OpenAI API 키)"
else:
    default_api_key = os.environ.get("LLM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
    default_model = os.environ.get("LLM_MODEL") or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    default_base_url = ""
    api_label = "Anthropic API Key"
    api_placeholder = "sk-ant-..."

api_key = st.text_input(api_label, type="password", value=default_api_key, placeholder=api_placeholder).strip()
if provider == "openai":
    st.info("공식 OpenAI API는 platform.openai.com에서 발급한 API 키를 사용합니다. `AQ...` 형식 토큰은 직접 동작하지 않을 수 있습니다.")
model = st.text_input("모델", value=default_model)
base_url = ""
if provider == "openai":
    base_url = st.text_input(
        "Base URL (선택)",
        value=default_base_url,
        help="OpenAI 공식 API가 아닌 게이트웨이 토큰이라면 해당 엔드포인트를 입력하세요.",
        placeholder="https://api.openai.com/v1",
    )

uploaded = st.file_uploader(
    "원문 파일 업로드",
    type=["pdf", "hwpx", "docx", "txt"],
    help="기안문으로 변환할 원본 문서를 올려주세요.",
)

if uploaded and api_key:
    if st.button("기안문 생성", type="primary"):
        with st.spinner("파일에서 텍스트 추출 중..."):
            with tempfile.NamedTemporaryFile(suffix=Path(uploaded.name).suffix, delete=False) as tmp:
                tmp.write(uploaded.read())
                tmp_path = tmp.name
            try:
                source_text = extract_text(tmp_path)
            except Exception as e:
                st.error(f"텍스트 추출 실패: {e}")
                st.stop()
            finally:
                os.unlink(tmp_path)

        st.success(f"추출 완료 — {len(source_text):,}자")

        with st.spinner(f"{provider_options[provider]} 모델이 기안문 초안을 작성 중..."):
            try:
                draft = generate_draft(
                    source_text,
                    api_key,
                    provider=provider,
                    model=model.strip() or None,
                    base_url=base_url.strip() or None,
                )
            except Exception as e:
                st.error(f"초안 생성 실패: {e}")
                st.stop()

        st.subheader("생성된 기안문 미리보기")
        st.markdown(f"**제목:** {draft.get('title', '')}")
        for line in draft.get("body_lines", []):
            st.text(line)
        attachment = draft.get("attachment", "")
        if attachment and attachment != "해당없음":
            st.text(f"\n붙임  {attachment} 1부.  끝.")
        else:
            st.text("\n끝.")

        with st.spinner("HWPX 파일 생성 중..."):
            out_path = tempfile.mktemp(suffix=".hwpx")
            try:
                write_hwpx(draft, out_path)
            except Exception as e:
                st.error(f"HWPX 생성 실패: {e}")
                st.stop()

        with open(out_path, "rb") as f:
            st.download_button(
                label="⬇️ 기안문 다운로드 (.hwpx)",
                data=f,
                file_name="기안문_작성본.hwpx",
                mime="application/octet-stream",
            )
        os.unlink(out_path)

elif uploaded and not api_key:
    st.warning("API 토큰을 입력해주세요.")
