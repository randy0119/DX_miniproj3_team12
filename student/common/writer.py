# -*- coding: utf-8 -*-
from typing import Dict, Any
from textwrap import dedent

# --------- 본문 렌더러들 ---------
def render_day1(query: str, payload: Dict[str, Any]) -> str:
    web = payload.get("web_top", []) or []
    prices = payload.get("prices", []) or []
    profile = (payload.get("company_profile") or "").strip()
    profile_sources = payload.get("profile_sources") or []

    lines = [f"# 웹 리서치 리포트", f"- 질의: {query}", ""]

    # 1) 시세 스냅샷
    if prices:
        lines.append("## 시세 스냅샷")
        for p in prices:
            sym = p.get("symbol", "")
            cur = f" {p.get('currency')}" if p.get("currency") else ""
            if p.get("price") is not None:
                lines.append(f"- **{sym}**: {p['price']}{cur}")
            else:
                lines.append(f"- **{sym}**: (가져오기 실패) — {p.get('error','')}")
        lines.append("")

    # 2) 기업 정보 요약(발췌 + 출처)
    if profile:
        # 500자 정도로 길이 제한(가독)
        short = profile[:500].rstrip()
        if len(profile) > 500:
            short += "…"
        lines.append("## 기업 정보 요약")
        lines.append(short)
        if profile_sources:
            lines.append("")
            lines.append("**출처(기업 정보):**")
            for u in profile_sources[:3]:
                lines.append(f"- {u}")
        lines.append("")

    # 3) 상위 웹 결과(타이틀 + 메타 + 2줄 발췌)
    if web:
        lines.append("## 관련 링크 & 발췌")
        for r in web[:5]:
            title = r.get("title") or r.get("url") or "link"
            src = r.get("source") or ""
            date = r.get("published_date") or r.get("date") or ""
            url = r.get("url", "")
            tail = f" — {src}" + (f" ({date})" if date else "")
            lines.append(f"- [{title}]({url}){tail}")

            # 2줄 발췌: content > snippet > '' 우선순위
            raw = (r.get("content") or r.get("snippet") or "").strip().replace("\n", " ")
            if raw:
                excerpt = raw[:280].rstrip()
                if len(raw) > 280:
                    excerpt += "…"
                lines.append(f"  > {excerpt}")
        lines.append("")

    # 웹 결과가 전혀 없을 때 힌트
    if not (web or profile or prices):
        lines.append("_참고: 결과가 비어있습니다. 쿼리/도메인 제한/키워드 설정을 확인하세요._")
        lines.append("")

    return "\n".join(lines)


def render_day2(query: str, payload: dict) -> str:
    # 기존 요약/머리말 생성부는 유지
    lines = []
    lines.append(f"# Day2 – RAG 요약")
    lines.append("")
    lines.append(f"**질의:** {query}")
    lines.append("")

    # ── 추가: 초안(answer) 표시
    answer = (payload or {}).get("answer") or ""
    if answer:
        lines.append("## 초안 요약")
        lines.append("")
        lines.append(answer.strip())
        lines.append("")

    # ── 추가: 근거 상위 K 표
    contexts = (payload or {}).get("contexts") or []
    if contexts:
        lines.append("## 근거(Top-K)")
        lines.append("")
        lines.append("| rank | score | path | chunk_id | excerpt |")
        lines.append("|---:|---:|---|---:|---|")
        for i, c in enumerate(contexts, 1):
            score = f"{float(c.get('score', 0.0)):.3f}"
            path = str(c.get("path") or c.get("meta", {}).get("path") or "")

            # excerpt 후보(우선순위: text > chunk > content)
            raw = (
                c.get("text")
                or c.get("chunk")
                or c.get("content")
                or ""
            )
            excerpt = (str(raw).replace("\n", " ").strip())[:200]

            # chunk_id 후보(우선순위: id > meta.chunk > chunk_id > chunk_index)
            chunk_id = (
                c.get("id")
                or c.get("meta", {}).get("chunk")
                or c.get("chunk_id")
                or c.get("chunk_index")
                or ""
            )

            lines.append(f"| {i} | {score} | {path} | {chunk_id} | {excerpt} |")
        lines.append("")

    return "\n".join(lines)

def render_day3(query: str, payload: Dict[str, Any]) -> str:
    items = payload.get("items", [])
    lines = [f"# 공고 탐색 결과", f"- 질의: {query}", ""]
    if items:
        lines.append("| 출처 | 제목 | 기관 | 접수 마감 | 예산 | URL | 점수 |")
        lines.append("|---|---|---|---:|---:|---|---:|")
        for it in items[:10]:
            src = it.get('source','-')
            title = it.get('title','-')
            agency = it.get('agency','-')
            close = it.get('close_date','-')
            budget = it.get('budget','-')
            url = it.get('url','-')
            score = it.get('score',0)
            lines.append(f"| {src} | {title} | {agency} | {close or '-'} | {budget or '-'} | {url} | {score:.3f} |")
    else:
        lines.append("관련 공고를 찾지 못했습니다.")
        
    has_atts = any(it.get("attachments") for it in items)
    if has_atts:
        lines.append("\n## 첨부파일 요약")
        for i, it in enumerate(items[:10], 1):
            atts = it.get("attachments") or []
            if not atts: 
                continue
            lines.append(f"- **{i}. {it.get('title','(제목)')}**")
            for a in atts[:5]:
                lines.append(f"  - {a}")
    return "\n".join(lines)

def render_day5(query: str, payload: dict) -> str:
    """
    Day5 공모전 RAG 검색 결과 렌더링
    - 사용자 질의 표시
    - 추천 공모전 표 형식 (실제 컬럼 구조 반영)
    - 상세 정보 섹션
    """
    lines = []
    lines.append("# 🎯 Day5 – 공모전 추천 결과")
    lines.append("")
    lines.append(f"**검색 질의:** {query}")
    lines.append("")

    # ── 초안 요약 (있는 경우)
    answer = (payload or {}).get("answer") or ""
    if answer:
        lines.append("## 💡 추천 요약")
        lines.append("")
        lines.append(answer.strip())
        lines.append("")

    # ── 공모전 추천 목록 (Top-K)
    contexts = (payload or {}).get("contexts") or []
    if contexts:
        lines.append("## 📋 추천 공모전 목록")
        lines.append("")
        lines.append("| 순위 | 공모전명 | 주최 | 분야 | 참가자격 | 마감일 | 매칭도 | 추천 근거 |")
        lines.append("|:---:|----------|------|------|----------|--------|:------:|-----------|")
        
        for i, c in enumerate(contexts, 1):
            # 매칭 점수
            score = float(c.get('score', 0.0))
            match_pct = f"{score*100:.1f}%"
            
            # 원본 텍스트에서 공모전 정보 파싱
            raw_text = (
                c.get("text")
                or c.get("chunk")
                or c.get("content")
                or ""
            )
            
            # 텍스트에서 각 필드 추출
            def extract_field(text: str, field_name: str) -> str:
                """[필드명]: 형식에서 값 추출"""
                import re
                pattern = rf'\[{field_name}\]:\s*(.+?)(?=\n\[|$)'
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    return match.group(1).strip().replace('\n', ' ')[:50]
                return "-"
            
            contest_name = extract_field(raw_text, "공모전명")
            host = extract_field(raw_text, "주최")
            field = extract_field(raw_text, "분야")
            eligibility = extract_field(raw_text, "참가 자격")
            deadline = extract_field(raw_text, "마감일")
            
            # 추천 근거: 상세 내용 또는 전공 우대 부분
            detail = extract_field(raw_text, "상세 내용")
            if len(detail) > 80:
                detail = detail[:80] + "..."
            
            lines.append(
                f"| {i} | {contest_name} | {host} | {field} | {eligibility} | {deadline} | {match_pct} | {detail} |"
            )
        lines.append("")

    # ── 상위 추천 공모전 상세 (Top 3)
    if contexts and len(contexts) > 0:
        lines.append("## 📌 상위 추천 공모전 상세")
        lines.append("")
        
        for i, c in enumerate(contexts[:3], 1):
            score = float(c.get('score', 0.0))
            
            # 원본 텍스트
            raw_text = (
                c.get("text")
                or c.get("chunk")
                or c.get("content")
                or ""
            )
            
            # 필드 추출 함수 (상세용)
            def extract_field_detail(text: str, field_name: str) -> str:
                """[필드명]: 형식에서 값 추출 (전체)"""
                import re
                pattern = rf'\[{field_name}\]:\s*(.+?)(?=\n\[|$)'
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    return match.group(1).strip()
                return "-"
            
            contest_name = extract_field_detail(raw_text, "공모전명")
            host = extract_field_detail(raw_text, "주최")
            field = extract_field_detail(raw_text, "분야")
            eligibility = extract_field_detail(raw_text, "참가 자격")
            team_size = extract_field_detail(raw_text, "팀 규모")
            deadline = extract_field_detail(raw_text, "마감일")
            prize = extract_field_detail(raw_text, "상금 및 혜택")
            preferred_major = extract_field_detail(raw_text, "전공 우대")
            detail = extract_field_detail(raw_text, "상세 내용")
            
            lines.append(f"### {i}. {contest_name}")
            lines.append("")
            lines.append(f"**매칭도:** {score*100:.1f}% | **마감일:** {deadline}")
            lines.append("")
            
            # 핵심 정보 표
            lines.append("| 항목 | 내용 |")
            lines.append("|------|------|")
            lines.append(f"| 주최 | {host} |")
            lines.append(f"| 분야 | {field} |")
            lines.append(f"| 참가 자격 | {eligibility} |")
            lines.append(f"| 팀 규모 | {team_size} |")
            lines.append(f"| 상금 및 혜택 | {prize} |")
            lines.append(f"| 전공 우대 | {preferred_major} |")
            lines.append("")
            
            # 상세 내용
            if detail and detail != "-":
                lines.append("**📝 상세 내용**")
                lines.append("")
                lines.append(detail)
                lines.append("")
            
            lines.append("---")
            lines.append("")

    # ── 검색 통계
    if contexts:
        lines.append("## 📊 검색 통계")
        lines.append("")
        lines.append(f"- **검색된 공모전 수:** {len(contexts)}개")
        avg_score = sum(float(c.get('score', 0)) for c in contexts) / len(contexts) if contexts else 0
        lines.append(f"- **평균 매칭도:** {avg_score*100:.1f}%")
        lines.append("")

    return "\n".join(lines)

# --------- Envelope(머리말/푸터) ---------
def _compose_envelope(kind: str, query: str, body_md: str, saved_path: str) -> str:
    header = dedent(f"""\
    ---
    output_schema: v1
    type: markdown
    route: {kind}
    saved: {saved_path}
    query: "{query.replace('"','\\\"')}"
    ---

    """)
    footer = dedent(f"""\n\n---\n> 저장 위치: `{saved_path}`\n""")
    return header + body_md.strip() + footer

def render_enveloped(kind: str, query: str, payload: Dict[str, Any], saved_path: str) -> str:
    if kind == "day1":
        body = render_day1(query, payload)
    elif kind == "day2":
        body = render_day2(query, payload)
    elif kind == "day3":
        body = render_day3(query, payload)
    elif kind == "day5":
        body = render_day5(query, payload)
    else:
        body = f"### 결과\n\n(알 수 없는 kind: {kind})"
    return _compose_envelope(kind, query, body, saved_path)
