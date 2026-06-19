# LLM API를 호출해 기안문 구조화 초안을 생성하는 모듈
import json

import anthropic
from openai import OpenAI

SYSTEM_PROMPT = """당신은 한국 공공기관의 기안문(품의서) 작성 전문가입니다.
사용자가 제공한 원문 내용을 분석하여 기안문 형식으로 변환합니다.

반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요.

{
  "title": "안건명 (간결하고 행동 지향적으로)",
  "body_lines": [
    "1. 배경 및 목적 문장.",
    "2. 주요 내용은 다음과 같습니다.",
    "  가. 항목명: 내용",
    "  나. 항목명: 내용",
    "3. 후속 조치 요청 문장."
  ],
  "attachment": "붙임 파일명 또는 '해당없음'"
}

작성 원칙:
- 제목: 구체적이고 행동 지향적 (예: "○○ 사업 추진 품의")
- 본문: 1~3개 항목, 핵심만 간결하게
- 세부 내용(표, 일정, 예산)은 attachment에 명시하고 본문에서 제외
- body_lines 각 항목은 완결된 문장으로 작성
"""

def generate_draft(
    source_text: str,
    api_key: str,
    provider: str = "openai",
    model: str | None = None,
    base_url: str | None = None,
) -> dict:
    """원문 텍스트를 받아 기안문 구조 딕셔너리를 반환합니다."""
    api_key = api_key.strip()
    if provider == "anthropic":
        raw = _generate_with_anthropic(source_text, api_key, model=model)
    elif provider == "openai":
        raw = _generate_with_openai(source_text, api_key, model=model, base_url=base_url)
    else:
        raise ValueError(f"지원하지 않는 LLM 제공자: {provider}")
    return _parse_json(raw)


def _generate_with_anthropic(source_text: str, api_key: str, model: str | None = None) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model or "claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"다음 내용을 기안문으로 작성해주세요:\n\n{source_text[:8000]}",
            }
        ],
    )
    return message.content[0].text.strip()


def _generate_with_openai(
    source_text: str,
    api_key: str,
    model: str | None = None,
    base_url: str | None = None,
) -> str:
    client = OpenAI(api_key=api_key, base_url=base_url or None)
    response = client.chat.completions.create(
        model=model or "solar-1-mini-chat",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": f"다음 내용을 기안문으로 작성해주세요:\n\n{source_text[:8000]}",
            },
        ],
    )
    raw = response.choices[0].message.content.strip()
    if not raw:
        raise ValueError("OpenAI 응답에서 텍스트를 찾지 못했습니다.")
    return raw


def _parse_json(raw: str) -> dict:
    # JSON 블록이 감싸져 있을 경우 제거
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
