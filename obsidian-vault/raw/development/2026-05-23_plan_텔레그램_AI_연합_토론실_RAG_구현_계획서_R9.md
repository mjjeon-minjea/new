← [[Development_Hub|개발 마스터 대시보드]]

# AI 멀티 에이전트 연합 토론실 (Joint Newsroom Multi-Agent Debate) 도입 계획서 (R9)

단순히 뉴스 기사를 기계적으로 1차원 요약하는 기존 방식에서 완전히 진화하여, 3대 전문 리포터 에이전트(국내경제, 글로벌매크로, 가상자산)들이 각자의 영역에서 수집한 1차 초안을 바탕으로 **서로 교차 지적(Peer Review / Critique)하고 토론하며, 이를 자율적으로 반영해 보고서의 깊이와 교차 결합력을 최상으로 끌어올리는 집단지성 멀티 에이전트 토론실(Joint Newsroom Multi-Agent Debate & Consensus System)**의 구현 계획서입니다.

---

## 1. User Review Required

> [!IMPORTANT]
> **집단지성 토론(Consensus & Peer Review)의 자율 구현**
> AI들이 백그라운드에서 지들끼리 1차 초안을 공유하여 서로 날카롭게 비판하는 피어 리뷰 회의(Debate Round)를 진행합니다. 서로의 지적과 수정 보완 과정을 거쳐 단일 관점의 왜곡을 방지하고 교차 검증된 명품 리포트를 완성합니다.

> [!TIP]
> **투명한 토론 로그 영속 보존**
> AI 지들끼리 서로 날카롭게 비난하고 수정 피드백을 수용했던 치열한 회의록 원본(Debate Log)을 `obsidian-vault/raw/development/` 내에 실물 파일로 영구 저장하여 사용자가 언제든 AI들의 토론 라이브 드라마를 읽을 수 있도록 아카이빙합니다.

---

## 2. Proposed Changes

### [Component 1] 멀티 에이전트 연합 토론실 엔진 이식

#### [NEW] [debate_room.py](file:///c:/Users/jmj/Desktop/안티그래비티/new/agents/debate_room.py)
* **주요 변경 사항**:
  1. `run_multi_agent_debate(raw_reports, financial_data)`:
     * 3대 리포터가 수집한 1차 요약 초안 리스트를 전달받아 합동 토론 세션을 엽니다.
     * **Round 1 (상호 비판 및 피어 크리틱)**: 각 에이전트의 페르소나를 입힌 gemma4 모델을 3회 순차 구동하여 타 에이전트의 리포트를 교차 분석하고 핵심 보완점/지적사항(Critique)을 생성합니다.
     * **Round 2 (피드백 수렴 및 최종 리팩토링)**: 각 에이전트가 동료 에이전트들이 제기한 크리틱 지침들을 컨텍스트로 전달받아, 자신의 1차 초안의 빈틈을 메우고 유기적으로 연계 융합한 **최종 집단지성 합의 보고서**를 생성해 냅니다.
     * **토론록(Debate Log) 실물 파일 영속화**: 이 치열했던 교차 발화 대화록 전문을 `obsidian-vault`와 `antigravity_report`에 예쁘게 포맷팅하여 실물 파일로 기록해 보존합니다.

#### [MODIFY] [chief_agent.py](file:///c:/Users/jmj/Desktop/안티그래비티/new/agents/chief_agent.py)
* **주요 변경 사항**:
  1. `run_relay()` 호출 시 3대 리포터 가동 후, `WikiManager`가 합성을 시작하기 전에 신설된 `debate_room.py`의 `run_multi_agent_debate` 프로세스를 중간에 오케스트레이션하여 소환합니다.
  2. 교차 토론 및 합의가 거쳐 완료된 리포트만을 최종 위키 점진적 합성 인풋으로 주입합니다.
  3. 요약 브리핑 메시지 맨 밑에 **"🤖 [AI 합동 뉴스룸 치열한 상호 토론 중계]"** 카드와 피어 리뷰 키워드를 텔레그램으로 함께 전송하여 투명성을 실시간 중계합니다.

---

## 3. 코드 사전 감사 및 Before / After 변경 계획

### [감사 대상 함수: ChiefAgent.run_relay 의 오케스트레이션 개편]

#### [Before] `chief_agent.py` (라인 65-83)
```python
        # ---------------------------------------------
        # [1선 ~ 3선: 3대 리포터 가동 (금융 데이터 인메모리 주입 연계)]
        # ---------------------------------------------
        reporters = [
            KoreaReporter(),
            GlobalReporter(),
            BitcoinReporter()
        ]
        
        for reporter in reporters:
            rep_res = reporter.collect(financial_data)
            results.append(rep_res)
            print(f"[*] [{reporter.agent_name}] 처리 성공 여부: {rep_res.success} | 수집 기사 수: {rep_res.collected_count}개")
            
        # ---------------------------------------------
        # [4선: Wiki 관리자 - 지식 융합 및 누적 컴파운딩]
        # ---------------------------------------------
        wiki_agent = WikiManager()
        wiki_res = wiki_agent.run_compounding(financial_data)
        results.append(wiki_res)
```

#### [After] `chief_agent.py` (토론방 소환 및 RAG 피드백 브릿지 연계)
```python
        # ---------------------------------------------
        # [1선 ~ 3선: 3대 리포터 가동 (금융 데이터 인메모리 주입 연계)]
        # ---------------------------------------------
        reporters = [
            KoreaReporter(),
            GlobalReporter(),
            BitcoinReporter()
        ]
        
        raw_reports = {}
        for reporter in reporters:
            rep_res = reporter.collect(financial_data)
            results.append(rep_res)
            # 수집된 1차 마크다운 리포트들의 텍스트 내용 확보
            raw_reports[reporter.agent_name] = rep_res
            print(f"[*] [{reporter.agent_name}] 처리 성공 여부: {rep_res.success} | 수집 기사 수: {rep_res.collected_count}개")
            
        # ---------------------------------------------
        # [R9 신설: AI 멀티 에이전트 연합 토론실 가동 (Consensus Debate)]
        # ---------------------------------------------
        print("\n💬 "*10)
        print("[*] AI 멀티 에이전트 연합 토론실(Joint Newsroom Debate)을 긴급 개설합니다...")
        print("💬 "*10 + "\n")
        
        from agents.debate_room import run_multi_agent_debate
        debate_result = run_multi_agent_debate(raw_reports, financial_data, timestamp)
        
        # ---------------------------------------------
        # [4선: Wiki 관리자 - 지식 융합 및 누적 컴파운딩]
        # (토론을 통해 검증 합의 완료된 명품 리포트를 인풋으로 삼아 합성 진행)
        # ---------------------------------------------
        wiki_agent = WikiManager()
        # wiki_agent에 토론 합의 데이터 전달
        wiki_res = wiki_agent.run_compounding(financial_data, debate_result)
        results.append(wiki_res)
```

---

## 4. Known Unknowns (자기완성도 선언 배제)

> [!WARNING]
> **다자간 토론 시 Ollama의 순차 통신 연산 부하**
> 3개 에이전트가 각자 2라운드씩 총 6번 이상의 LLM 호출을 백그라운드에서 연속으로 처리하므로, 릴레이 소요 시간이 기존 10초 내외에서 약 40~90초까지 늘어날 수 있습니다. 사용자의 대기 피로감을 덜기 위해 텔레그램 화면에 `💬 지들끼리 1차 초안을 두고 비평 및 교차 토론 회의를 치열하게 진행 중...` 메시지를 단계별로 자세하게 중계합니다.
> 
> **토론 수렴 안정성**
> AI들이 서로 지적한 뒤 합의하는 과정에서, 드물게 피드백이 너무 난잡하여 융합 보고서 포맷이 꼬일 예외가 있을 수 있습니다. 이를 방지하기 위해 엄격한 마크다운 규격 템플릿과 보완 지침을 Debate System Prompt에 주입하여 안정성을 보장합니다.

---

## 5. Verification Plan

### Integration Tests
- `/update` 명령어 가동 시, 로그에 `[Joint Newsroom Debate]` 관련 1차 초안 스캔 ➡️ Round 1 피어 리뷰 지적 ➡️ Round 2 집단지성 합의본 개정 로그가 콘솔에 아름다운 라이브 드라마처럼 기록되는지 점검합니다.
- 토론 세션 완료 후 `obsidian-vault/raw/development/` 내에 `2026-05-23_AI_Joint_Newsroom_Debate_R0.md` 파일이 치열한 교차 대화 내용과 함께 생성되는지 실물 파일 I/O를 확인합니다.
- 텔레그램 브리핑 메시지 하단에 토론 중계 요약 및 동료 에이전트 간의 주요 크리틱 키워드가 가독성 높게 표시되는지 확인합니다.
