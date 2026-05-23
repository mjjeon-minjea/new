import time
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from agents.shared.config import WIKI_DIR, SESSIONS_DIR, ROOT_DIR
from agents.shared.protocols import AgentResult
from agents.db_manager import DBManager
from agents.korea_reporter import KoreaReporter
from agents.global_reporter import GlobalReporter
from agents.bitcoin_reporter import BitcoinReporter
from agents.wiki_manager import WikiManager

# 5선 전략분석 에이전트군 임포트
from agents.macro_signal_analyst import MacroSignalAnalyst
from agents.onchain_signal_analyst import OnchainSignalAnalyst
from agents.risk_assessor import RiskAssessor
from agents.chief_strategy_analyst import ChiefStrategyAnalyst

class ChiefAgent:
    """총괄팀장 에이전트: 동기식 릴레이 협업 제어 및 wiki/log.md 성적 영속 로깅 오케스트레이터"""
    
    def __init__(self):
        self.agent_name = "ChiefAgent"
        
    def run_relay(self) -> str:
        """
        [전체 릴레이 구동 진입점]
        0선(DB) ➡️ 1선(국내) ➡️ 2선(해외) ➡️ 3선(비트코인) ➡️ 3.5선(데스크) ➡️ 4선(Wiki)의 릴레이 실행 조율.
        종료 시 타임스탬프 기반 세션 격리 아카이빙을 수행하고 요약 브리핑을 반환합니다.
        """
        start_time = time.time()
        print("\n" + "👑 "*15)
        print("[*] 총괄팀장 ChiefAgent 릴레이 파이프라인 구동 개시...")
        print("👑 "*15 + "\n")
        
        # R4 반영: 실행 타임스탬프 기반 세션 디렉토리 개설
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M")
        session_dir = SESSIONS_DIR / timestamp
        session_dir.mkdir(parents=True, exist_ok=True)
        
        results: List[AgentResult] = []
        financial_data = None
        
        # ---------------------------------------------
        # [0선: DB 관리자 - 실시간 금융 지표 선행 수집]
        # ---------------------------------------------
        db_agent = DBManager()
        db_res = db_agent.collect()
        results.append(db_res)
        
        if db_res.success:
            financial_data = db_res.payload
            print(f"[*] [0선 DB관리자] 선행 수집 완료 (김프: {financial_data.get('kimchi_premium', 0):+.2f}%)")
            
            # R4 반영: 수집된 원천 계량 수치 JSON 백업
            db_meta_path = session_dir / "db_manager.json"
            try:
                with open(db_meta_path, "w", encoding="utf-8") as f:
                    json.dump(financial_data, f, ensure_ascii=False, indent=2)
                print(f"[+] 0선 정량 금융 지표 세션 아카이브 백업 성공: {db_meta_path.name}")
            except Exception as e:
                print(f"[!] 0선 금융 지표 JSON 세션 저장 실패: {e}")
        else:
            print("[!] [0선 DB관리자] 선행 수집 실패 또는 부분 에러. 기본값으로 후행 에이전트를 가동합니다.")
            
        # ---------------------------------------------
        # [1선 ~ 3선: 3대 리포터 가동]
        # ---------------------------------------------
        reporters = [
            KoreaReporter(),
            GlobalReporter(),
            BitcoinReporter()
        ]
        
        reporter_results: List[AgentResult] = []
        for reporter in reporters:
            rep_res = reporter.collect(financial_data)
            results.append(rep_res)
            reporter_results.append(rep_res)
            print(f"[*] [{reporter.agent_name}] 처리 성공 여부: {rep_res.success} | 수집 기사 수: {rep_res.collected_count}개")
            
        # ---------------------------------------------
        # [3.5선: AI 합동 언론 데스크 & 레드팀 크리틱 파이프라인]
        # ⚠️  editorial_result는 results 리스트에 추가하지 않는다.
        #     _build_briefing_report()가 results[0]~[4]를 하드코딩으로 참조하기 때문이다.
        # ---------------------------------------------
        print("\n" + "📰 "*15)
        print("[*] [Joint Editorial Board] 합동 언론 데스크 & 레드팀 파이프라인 가동...")
        print("📰 "*15 + "\n")

        from agents.editorial_desk import run_editorial_board
        editorial_result = run_editorial_board(reporter_results, financial_data, session_dir)

        editorial_column = ""
        if editorial_result and editorial_result.success:
            editorial_column = editorial_result.payload.get("final_column", "")
            # 최종 칼럼을 세션 디렉토리에 별도 저장
            editorial_col_path = session_dir / "editorial_column.md"
            try:
                editorial_col_path.write_text(editorial_column, encoding="utf-8")
                print(f"[+] [3.5선 편집장] 최종 종합 칼럼 세션 아카이브 저장: {editorial_col_path.name}")
            except Exception as e:
                print(f"[!] [3.5선 편집장] 칼럼 세션 저장 실패: {e}")
        else:
            print("[!] [3.5선 편집장] 편집 데스크 실패 또는 건너뜀. 4선 Wiki 정상 진행합니다.")

        # ---------------------------------------------
        # [4선: Wiki 관리자 - 지식 융합 및 누적 컴파운딩]
        # ---------------------------------------------
        wiki_agent = WikiManager()
        wiki_res = wiki_agent.run_compounding(financial_data)
        results.append(wiki_res)
        print(f"[*] [4선 Wiki관리자] 위키 누적 합성 성공 여부: {wiki_res.success} | 갱신된 파일 수: {wiki_res.collected_count}개")
        
        # ---------------------------------------------
        # [5선: 전략분석 에이전트 군 구동 (Wiki 이후 순차 배치)]
        # ⚠️ results 리스트에 추가하지 않고 editorial_desk처럼 별도 격리 처리
        # ---------------------------------------------
        print("\n" + "🎯 "*15)
        print("[*] [5선 전략분석 에이전트단] 수석/거시/온체인 분석 및 리스크 평가 가동...")
        print("🎯 "*15 + "\n")
        
        strategy_results: List[AgentResult] = []
        
        # (1) 5선 거시 신호 분석가 기동
        try:
            macro_analyst = MacroSignalAnalyst()
            macro_res = macro_analyst.analyze(financial_data, session_dir)
            strategy_results.append(macro_res)
            print(f"[*] [5선 Macro] 분석 성공: {macro_res.success} | 파일: {len(macro_res.files_created)}개")
        except Exception as e:
            print(f"[!] [5선 Macro] 기동 실패: {e}")
            strategy_results.append(AgentResult(agent_name="MacroSignalAnalyst", success=False, errors=[str(e)]))
            
        # (2) 5선 온체인 신호 분석가 기동
        try:
            onchain_analyst = OnchainSignalAnalyst()
            onchain_res = onchain_analyst.analyze(financial_data, session_dir)
            strategy_results.append(onchain_res)
            print(f"[*] [5선 Onchain] 분석 성공: {onchain_res.success} | 파일: {len(onchain_res.files_created)}개")
        except Exception as e:
            print(f"[!] [5선 Onchain] 기동 실패: {e}")
            strategy_results.append(AgentResult(agent_name="OnchainSignalAnalyst", success=False, errors=[str(e)]))
            
        # (3) 5선 리스크 평가가 기동
        try:
            risk_assessor = RiskAssessor()
            risk_res = risk_assessor.assess(financial_data, session_dir)
            strategy_results.append(risk_res)
            print(f"[*] [5선 Risk] 평가 성공: {risk_res.success} | 파일: {len(risk_res.files_created)}개")
        except Exception as e:
            print(f"[!] [5선 Risk] 기동 실패: {e}")
            strategy_results.append(AgentResult(agent_name="RiskAssessor", success=False, errors=[str(e)]))
            
        # (4) 5선 수석 전략 분석가 최종 종합 기동
        chief_strat_column = ""
        chief_strat_res = None
        try:
            chief_analyst = ChiefStrategyAnalyst()
            chief_strat_res = chief_analyst.generate_strategy(strategy_results, financial_data, session_dir)
            if chief_strat_res and chief_strat_res.success:
                chief_strat_column = chief_strat_res.payload.get("strategy_column", "")
                
                # R4 반영: 최종 전략 기안문 세션 저장
                strat_col_path = session_dir / "strategy_column.md"
                strat_col_path.write_text(chief_strat_column, encoding="utf-8")
                print(f"[+] [5선 수석전략가] 최종 종합 투자 전략 아카이브 완료: {strat_col_path.name}")
        except Exception as e:
            print(f"[!] [5선 수석전략가] 종합 전략 도출 실패: {e}")
            chief_strat_res = AgentResult(agent_name="ChiefStrategyAnalyst", success=False, errors=[str(e)])
            
        # R4 반영: 5선 전략에이전트군 상세 구동 내역 세션 저장
        strategy_log_path = session_dir / "strategy_analysis.md"
        try:
            strat_log_content = self._build_strategy_log_content(strategy_results, chief_strat_res, timestamp)
            strategy_log_path.write_text(strat_log_content, encoding="utf-8")
            print(f"[+] 5선 전략 분석 성적 아카이브 완료: {strategy_log_path.name}")
        except Exception as e:
            print(f"[!] 5선 세션 로그 저장 실패: {e}")
            
        # ---------------------------------------------
        # [6선: 릴레이 통계/성적 정밀 영속 기록 및 최종 보고서 작성]
        # ---------------------------------------------
        total_elapsed = time.time() - start_time
        
        # 기존 log.md 성적표 작성
        self._write_relay_performance_log(results, total_elapsed)
        
        # R4 반영: chief_agent 실행 통계 로그 백업 (chief_agent.md)
        chief_log_path = session_dir / "chief_agent.md"
        try:
            chief_log_content = self._build_chief_log_content(results, total_elapsed, timestamp)
            chief_log_path.write_text(chief_log_content, encoding="utf-8")
            print(f"[+] 총괄 에이전트 실행 통계 세션 아카이브 백업 성공: {chief_log_path.name}")
        except Exception as e:
            print(f"[!] 총괄 에이전트 실행 통계 저장 실패: {e}")
        
        # 최종 브리핑 리포트 구성 (5선 분석 결과물도 명시적으로 전달)
        briefing = self._build_briefing_report(
            results, 
            total_elapsed, 
            financial_data, 
            editorial_column=editorial_column,
            strategy_results=strategy_results,
            chief_strat_res=chief_strat_res
        )
        
        # R4 반영: 최종 브리핑 전문 세션 아카이브 저장 (_report.md)
        report_path = session_dir / "_report.md"
        try:
            report_path.write_text(briefing, encoding="utf-8")
            print(f"[+] 최종 브리핑 전문 세션 아카이브 백업 성공: {report_path.name}")
        except Exception as e:
            print(f"[!] 최종 브리핑 전문 저장 실패: {e}")
            
        # R4 반영: wiki_manager 상세 로그 백업 (wiki_manager.md)
        wiki_log_path = session_dir / "wiki_manager.md"
        try:
            wiki_log_content = f"# Wiki Manager 세션 합성 결과\n- 성공 여부: {wiki_res.success}\n- 갱신 파일 수: {wiki_res.collected_count}개\n- 생성 파일 목록: {wiki_res.files_created}\n- 발생 에러: {wiki_res.errors}\n"
            wiki_log_path.write_text(wiki_log_content, encoding="utf-8")
            print(f"[+] Wiki Manager 상세 로그 백업 성공: {wiki_log_path.name}")
        except Exception as e:
            print(f"[!] wiki_manager 세션 로그 저장 실패: {e}")
            
        return briefing

    def _build_strategy_log_content(self, results: List[AgentResult], chief_res: Optional[AgentResult], timestamp: str) -> str:
        """5선 전략분석 에이전트단 전용 실행 통계 구성"""
        content = f"# 🎯 5선 전략 분석 에이전트 세션 실행 결과표\n"
        content += f"- **실행 세션 ID**: `{timestamp}`\n\n"
        content += "| 에이전트명 | 상태 | 생성 파일 | 에러 및 경고 내용 | 소요 시간 |\n"
        content += "| :--- | :---: | :--- | :--- | :---: |\n"
        
        for res in results:
            status = "✅ 성공" if res.success else "⚠️ 경고"
            files = ", ".join([Path(f).name for f in res.files_created]) if res.files_created else "-"
            errs = ", ".join(res.errors) if res.errors else "-"
            content += f"| {res.agent_name} | {status} | `{files}` | {errs} | {res.elapsed_seconds:.1f}초 |\n"
            
        if chief_res:
            status = "✅ 성공" if chief_res.success else "⚠️ 경고"
            files = ", ".join([Path(f).name for f in chief_res.files_created]) if chief_res.files_created else "-"
            errs = ", ".join(chief_res.errors) if chief_res.errors else "-"
            content += f"| {chief_res.agent_name} | {status} | `{files}` | {errs} | {chief_res.elapsed_seconds:.1f}초 |\n"
            
        return content

    def _build_chief_log_content(self, results: List[AgentResult], total_elapsed: float, timestamp: str) -> str:
        """총괄 에이전트 실행 요약 마크다운 내용 구성"""
        content = f"# Chief Agent 실행 통계 기록\n"
        content += f"- **실행 세션 ID**: `{timestamp}`\n"
        content += f"- **총 소요 시간**: `{total_elapsed:.2f}초`\n\n"
        content += "## 에이전트별 상세 구동 정보\n"
        for idx, res in enumerate(results):
            content += f"### {idx}선 - {res.agent_name}\n"
            content += f"- **성공 여부**: {res.success}\n"
            content += f"- **소요 시간**: {res.elapsed_seconds:.2f}초\n"
            content += f"- **수집/처리 건수**: {res.collected_count}개\n"
            content += f"- **에러 목록**: {res.errors if res.errors else '없음'}\n\n"
        return content

    def _write_relay_performance_log(self, results: List[AgentResult], total_elapsed: float):
        """[v3.0 신설] 각 에이전트의 AgentResult 성적과 오류 상세를 wiki/log.md 하단에 자동 덧붙임 로깅"""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        success_count = sum(1 for r in results if r.success)
        total_steps = len(results)
        
        log_file = WIKI_DIR / "log.md"
        
        # 마크다운 성적표 양식 조립
        perf_log = f"\n## 📊 [{now_str}] 릴레이 실행 결과표 | 총 {total_steps}단계 완료 (성공: {success_count}/{total_steps}, 총 소요: {total_elapsed:.1f}초)\n\n"
        perf_log += "| 단계 | 에이전트명 | 상태 | 처리/수집 건수 | 생성 및 갱신 파일 | 에러 및 경고 내용 | 소요 시간 |\n"
        perf_log += "| :---: | :--- | :---: | :---: | :--- | :--- | :---: |\n"
        
        for idx, res in enumerate(results):
            status_emoji = "✅ 성공" if res.success else "⚠️ 경고"
            files_str = ", ".join([f"`{Path(f).name}`" for f in res.files_created[:3]])
            if len(res.files_created) > 3:
                files_str += f" 외 {len(res.files_created)-3}건"
            if not files_str:
                files_str = "-"
                
            errs_str = ", ".join(res.errors[:2])
            if len(res.errors) > 2:
                errs_str += f" 외 {len(res.errors)-2}건"
            if not errs_str:
                errs_str = "-"
                
            perf_log += f"| {idx}선 | {res.agent_name} | {status_emoji} | {res.collected_count}개 | {files_str} | {errs_str} | {res.elapsed_seconds:.1f}초 |\n"
            
        perf_log += "\n"
        
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(perf_log)
            print(f"[+] log.md 에 릴레이 실행 성적표를 무결하게 덧붙임 기록 완료.")
        except Exception as e:
            print(f"[!] log.md 실행 성능 기록 덧붙임 실패: {e}")

    def _build_briefing_report(
        self, 
        results: List[AgentResult], 
        total_elapsed: float, 
        financial_data: Dict[str, Any], 
        editorial_column: str = "",
        strategy_results: List[AgentResult] = None,
        chief_strat_res: AgentResult = None
    ) -> str:
        """최종 릴레이 수행 결과 요약 브리핑(마크다운 고가독성 카드형) 빌더"""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 각 에이전트별 수치 확보
        db_res = results[0]
        kor_res = results[1]
        glb_res = results[2]
        btc_res = results[3]
        wiki_res = results[4]
        
        # 금융 실시간 지표 정리
        fin_card = ""
        if financial_data:
            btc_krw = financial_data.get("btc_krw", 0)
            btc_krw_change = financial_data.get("btc_krw_change", 0)
            btc_usd = financial_data.get("btc_usd", 0)
            exchange_rate = financial_data.get("exchange_rate", 0)
            bok_rate = financial_data.get("bok_rate", 0)
            kimchi_premium = financial_data.get("kimchi_premium", 0)
            
            kimp_sign = "+" if kimchi_premium > 0 else ""
            btc_sign = "+" if btc_krw_change > 0 else ""
            
            fin_card = f"""📊 *[오늘의 실시간 금융/크립토 주요 지표]*
• 🪙 *Bitcoin (Upbit)*: `{btc_krw:,.0f}원` ({btc_sign}{btc_krw_change:.2f}%)
• ⚡ *김치 프리미엄 (Premium)*: `{kimp_sign}{kimchi_premium:.2f}%`
• 💵 *원/달러 환율 (USD/KRW)*: `{exchange_rate:,.2f}원`
• 🇰🇷 *한국 기준금리 (BOK Rate)*: `{bok_rate:.2f}%`
• 🕒 *지표 갱신시*: `{financial_data.get('updated_at', '')}`
"""

        # 에러 총합 모음
        total_errors = []
        for r in results:
            if r.errors:
                total_errors.extend(r.errors)
                
        err_report = ""
        if total_errors:
            err_report = f"\n⚠️ *[실행 중 특이사항/에러 목록]*\n"
            for err in total_errors[:3]:
                err_report += f"- {err}\n"
            if len(total_errors) > 3:
                err_report += f"- 그 외 {len(total_errors)-3}건의 사소한 피드 지연/경고 존재 (활동 로그 log.md 참고)\n"

        editorial_section = ""
        if editorial_column:
            # 500자 내외의 미리보기 발췌문 구성
            preview_text = editorial_column[:500].strip()
            if len(editorial_column) > 500:
                preview_text += "..."
            
            editorial_section = f"""
📰 *[Joint Editorial Board — AI 종합 사설 미리보기]*
{preview_text}
"""

        briefing = f"""🤖 *[Antigravity AI 비서 릴레이 파이프라인 브리핑]*

👑 *총괄팀장 ChiefAgent 보고*:
전체 0선~4선 릴레이 실행이 성공적으로 완료되었습니다! 

{fin_card}
📈 *[에이전트별 수집 및 지식 합성 성적]*
- 💾 *0선 DB관리자*: `{db_res.collected_count}개` 주요 수치 동기화 {"✅" if db_res.success else "⚠️"}
- 🇰🇷 *1선 국내경제*: 신규 `{kor_res.collected_count}건` 수집 완료 {"✅" if kor_res.success else "⚠️"}
- 🌍 *2선 해외경제*: 신규 `{glb_res.collected_count}건` 수집 완료 {"✅" if glb_res.success else "⚠️"}
- 🪙 *3선 비트코인*: 신규 `{btc_res.collected_count}건` 수집 완료 {"✅" if btc_res.success else "⚠️"}
- 🧠 *4선 Wiki관리*: `{wiki_res.collected_count}개` 마스터 지식 위키 누적 합성(Compounding) 완료 {"✅" if wiki_res.success else "⚠️"}

🎯 *[5선 전략 분석 및 리스크 진단 성적]*
- 📈 *5선 거시 신호*: {"✅ 분석 완료" if strategy_results and strategy_results[0].success else "⚠️ 지연"}
- 🔗 *5선 온체인 신호*: {"✅ 분석 완료" if strategy_results and strategy_results[1].success else "⚠️ 지연"}
- 🚨 *5선 리스크 평가*: {"✅ 진단 완료" if strategy_results and strategy_results[2].success else "⚠️ 지연"}
- 👑 *5선 수석 전략가*: {"✅ 마스터 투자 전략서 완성" if chief_strat_res and chief_strat_res.success else "⚠️ 실패"}
{editorial_section}{err_report}
⏱️ *총 소요 시간*: `{total_elapsed:.1f}초`
🕒 *브리핑 생성 시각*: `{now_str}`

💡 *Tip*: 수집된 뉴스 원본들과 마스터 지식 위키는 옵시디언 볼트에서 실시간 크로스링크(`[[Bitcoin]]`, `[[US-Fed]]`, `[[Korea-Economy]]`) 형태로 편리하게 브라우징하여 살펴보실 수 있습니다.
"""
        return briefing

if __name__ == "__main__":
    agent = ChiefAgent()
    brief = agent.run_relay()
    print("\n" + "="*55)
    print("릴레이 실행 최종 브리핑 출력:")
    print("="*55)
    print(brief)
