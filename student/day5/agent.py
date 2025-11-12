# -*- coding: utf-8 -*-
"""
Day5: RAG 도구 에이전트 (개선 버전)
- 역할: Day5 RAG 본체 호출 → 결과 렌더 → 저장(envelope) → 응답
- 개선: 에러 핸들링, 결과 검증, 통계 정보 추가
"""

from __future__ import annotations
from typing import Dict, Any
import os
import logging

from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse

from student.day5.impl.rag import Day5Agent
from student.common.writer import render_day5, render_enveloped
from student.common.schemas import Day5Plan
from student.common.fs_utils import save_markdown

logger = logging.getLogger(__name__)

MODEL = LiteLlm(model="openai/gpt-4o-mini")


def _handle(query: str) -> Dict[str, Any]:
    """공모전 RAG 검색 처리"""
    index_dir = os.getenv("DAY5_INDEX_DIR", "indices/day5")
    
    if not os.path.exists(index_dir):
        raise FileNotFoundError(f"인덱스 디렉토리가 없습니다: {index_dir}")
    
    logger.info(f"[Day5] 검색 시작: {query[:50]}...")
    
    plan = Day5Plan(
        index_dir=index_dir,
        min_score=0.15,
        min_mean_topk=0.2,
        return_draft_when_enough=True,
        force_rag_only=False,
        top_k=10,
        max_context=2000,
    )
    
    agent = Day5Agent()
    payload = agent.handle(query, plan)
    
    # 통계 추가
    contexts = payload.get("contexts", [])
    if contexts:
        avg_score = sum(float(c.get('score', 0)) for c in contexts) / len(contexts)
        payload["stats"] = {
            "total_results": len(contexts),
            "avg_score": avg_score,
            "search_method": "hybrid"
        }
        logger.info(f"[Day5] 검색 완료: {len(contexts)}개, 평균 점수: {avg_score:.3f}")
    
    return payload


def before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
    **kwargs,
) -> LlmResponse | None:
    """RAG 검색 및 결과 렌더링"""
    try:
        last = llm_request.contents[-1]
        if last.role != "user":
            return None
            
        query = last.parts[0].text.strip()
        
        # 유효성 검사
        if not query:
            return LlmResponse(
                content=types.Content(
                    parts=[types.Part(text="❌ 검색 질의를 입력해주세요.")],
                    role="model",
                )
            )
        
        if len(query) > 500:
            return LlmResponse(
                content=types.Content(
                    parts=[types.Part(text="❌ 질의가 너무 깁니다. 500자 이내로 입력해주세요.")],
                    role="model",
                )
            )
        
        # RAG 검색
        payload = _handle(query)
        
        # 결과 확인
        contexts = (payload or {}).get("contexts", [])
        if not contexts:
            return LlmResponse(
                content=types.Content(
                    parts=[types.Part(text=f"🔍 '{query}'에 대한 공모전을 찾지 못했습니다.\n\n다른 키워드로 검색해보세요.")],
                    role="model",
                )
            )

        # 렌더링 및 저장
        body_md = render_day5(query, payload)
        saved = save_markdown(query=query, route="day5", markdown=body_md)
        md = render_enveloped(kind="day5", query=query, payload=payload, saved_path=saved)

        return LlmResponse(
            content=types.Content(
                parts=[types.Part(text=md)],
                role="model",
            )
        )
        
    except FileNotFoundError as e:
        return LlmResponse(
            content=types.Content(
                parts=[types.Part(text=f"❌ 인덱스 파일을 찾을 수 없습니다: {e}\n\n인덱스가 생성되었는지 확인해주세요.")],
                role="model",
            )
        )
    except Exception as e:
        logger.error(f"[Day5] 에러: {e}", exc_info=True)
        return LlmResponse(
            content=types.Content(
                parts=[types.Part(text=f"❌ Day5 에러: {e}")],
                role="model",
            )
        )
    
    return None


day5_rag_agent = Agent(
    name="Day5RagAgent",
    model=MODEL,
    
    description="""공모전 검색 및 추천 전문 에이전트.

[기능] 벡터 인덱스 기반 공모전 검색, 매칭도 분석, 순위화 추천
[사용 시점] 공모전 찾기, 특정 분야/주제 공모전 추천 요청 시
[출력] 추천 목록(표), 상위 3개 상세 정보, 검색 통계""",
    
    instruction="""공모전 추천 전문가로서 동작합니다.

검색 결과는 이미 구조화된 마크다운으로 제공됩니다.
- 제공된 결과를 그대로 사용
- 필요시 간단한 코멘트만 추가 (예: "1, 2번 추천", "마감 임박 주의")
- 추가 질문이 있을 때만 상세 답변

주의사항:
- 검색 결과 재구성 금지
- 표 형식 유지
- 없는 정보 추가 금지""",
    
    tools=[],
    before_model_callback=before_model_callback,
)