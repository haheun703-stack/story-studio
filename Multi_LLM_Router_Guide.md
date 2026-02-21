# 🔥 Multi-LLM Router 구조 가이드 (바이브코딩용)

## 📌 개요

이 문서는 바이브코딩 프로젝트에서 GPT, Claude, Gemini를 함께 사용하는
멀티 LLM Router 구조를 설명합니다.

------------------------------------------------------------------------

## 📁 권장 프로젝트 구조

    futures_vs_python/
    │
    ├── main.py
    ├── llm_router.py
    ├── openai_client.py
    ├── claude_client.py
    ├── gemini_client.py
    └── .env

------------------------------------------------------------------------

## 📄 llm_router.py

``` python
from openai_client import call_openai
from claude_client import call_claude
from gemini_client import call_gemini

def call_llm(model, prompt):
    if model == "gemini":
        return call_gemini(prompt)
    elif model == "gpt":
        return call_openai(prompt)
    elif model == "claude":
        return call_claude(prompt)
    else:
        raise ValueError("Unknown model")
```

------------------------------------------------------------------------

## 📄 main.py

``` python
from llm_router import call_llm

response = call_llm("gemini", "페로브스카이트 최신 뉴스 요약해줘")
print(response)
```

------------------------------------------------------------------------

## 📄 .env 예시

    OPENAI_API_KEY=your_openai_key
    CLAUDE_API_KEY=your_claude_key
    GEMINI_API_KEY=your_gemini_key

------------------------------------------------------------------------

## 🎯 확장 아이디어

### 1️⃣ 자동 분기 Router

``` python
def smart_router(prompt):
    if "코드" in prompt:
        return call_llm("gpt", prompt)
    elif "논리" in prompt:
        return call_llm("claude", prompt)
    else:
        return call_llm("gemini", prompt)
```

### 2️⃣ 자동매매 시스템 연결 구조

사용자 입력 → 뉴스 분석 → LLM 판단 → 매매 신호 생성 → 주문 API 호출

------------------------------------------------------------------------

## 🚀 전략 활용

  목적             추천 모델
  ---------------- -----------
  코드 생성        GPT
  논리/추론        Claude
  뉴스/검색/요약   Gemini

------------------------------------------------------------------------

이 구조를 바이브코딩 메인 엔진에 붙이면\
자동으로 모델을 바꿔가며 사용 가능합니다.
