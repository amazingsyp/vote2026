---
name: vote-helper-orchestrator
description: 제9회 전국동시지방선거 투표 도우미(단일 HTML, 정치성향 진단→주소→후보 일치도) 제작·갱신·배포를 에이전트 팀으로 조율하는 오케스트레이터. "투표 도우미 만들어/빌드/배포", "지방선거 도우미", "성향 테스트+후보 매칭", "후보 데이터 갱신", "설문 보강", "다시 빌드/재배포", "결과 개선", "선거구 보완" 등 이 프로젝트 관련 작업 시 사용. 단순 질문은 직접 응답 가능.
---

# vote-helper-orchestrator — 투표 도우미 제작 오케스트레이터

제9회 지방선거 투표 도우미를 5인 에이전트 팀으로 만든다. 각 에이전트는 "누가", 각 스킬은 "어떻게", 이 오케스트레이터는 "누가 언제 어떤 순서로"를 정의한다. 데이터 계약은 `references/data-contract.md`(단일 진실 공급원).

## 실행 모드: 에이전트 팀(기본) + 하이브리드
- 기본은 에이전트 팀(TeamCreate + SendMessage + TaskCreate, 자체 조율).
- **데이터 수집 단계**는 지역(시도) 병렬이 이득이면 서브 에이전트 팬아웃 가능(하이브리드). 그 외는 팀.
- 모든 Agent/팀원 호출에 `model: "opus"`.

## Phase 0: 컨텍스트 확인 (먼저 실행)
1. `_workspace/` 존재 여부와 `index.html` 존재를 확인.
2. 분기:
   - `_workspace/` 없음 → **초기 빌드**(Phase 1~5 전체).
   - 있음 + 사용자가 부분 수정 요청(예: "설문만", "후보 갱신만") → **부분 재실행**(해당 에이전트만).
   - 있음 + 새 데이터/키 제공 → **새 실행**(기존 `_workspace/`를 `_workspace_prev/`로 이동 후 진행).
3. data.go.kr 서비스 키 보유 여부 확인. 없으면 사용자에게 요청하거나 샘플 모드로 진행할지 확인.

## Phase 1: 데이터 수집 (data-engineer)
- `nec-data-pipeline`로 후보·공약·정당·선거구 JSON 수집·정규화 → `_workspace/01_data_*.json`.
- 산출: candidates / parties(명단) / districts / report(통계·누락).
- 키 없으면 대표 시도 샘플 목업으로 폴백(보고서에 명시).

## Phase 2: 분석 + 설문 (병렬: policy-analyst ∥ quiz-designer)
- policy-analyst: 단체장·교육감 공약 점수화 + 정당 프로파일 → `02_analyst_*.json`.
- quiz-designer: 16~20문항 설문 + 채점식 → `03_quiz_*.json`.
- 두 에이전트는 5축 부호 규약을 SendMessage로 동기화.

## Phase 3: 구현 (frontend-builder)
- `single-html-builder`로 quiz/candidates/parties/districts 임베드한 단일 `index.html` 생성.
- 매칭·레이더·주소검색·결과·요약 화면.

## Phase 4: 검증 (qa-integrator, 점진적)
- 각 Phase 산출 직후 점진 검증 + 최종 통합 검증(경계면 교차 비교, 채점·매칭 실행, 헤드리스 동작).
- 버그는 책임 에이전트에 수정 요청 → 재검증.

## Phase 5: 배포 (qa-integrator)
- 검증 통과 + **사용자 승인** 후 GitHub Pages 배포. URL 보고.

## 데이터 전달 프로토콜
- **태스크 기반**(TaskCreate/Update): 진행·의존 관리.
- **파일 기반**(`_workspace/{phase}_{agent}_{artifact}.json`): 모든 산출물. 최종만 레포 루트(`index.html`).
- **메시지 기반**(SendMessage): 축 부호 동기화, 경계면 버그 수정 요청 등 실시간 조율.

## 에러 핸들링
- API/스크립트 1회 재시도 후 실패 → 해당 범위 누락 기록하고 진행(중단 금지), 보고서 명시.
- 상충/불확실 데이터는 삭제하지 않고 출처·lowConfidence 병기.
- 키 미제공 → 샘플 모드 폴백. 검증 미통과 → 배포 금지.
- 경계면 버그 → 필드·라인 지정해 책임 에이전트에 수정 요청, 수정 후 재검증.

## 팀 구성 (5인, 대규모)
data-engineer · policy-analyst · quiz-designer · frontend-builder · qa-integrator(general-purpose).
리더(오케스트레이터)는 TeamCreate로 구성, TaskCreate로 의존 포함 작업 할당, 진행 모니터링·종합.

## 테스트 시나리오
- **정상 흐름**: 키 제공 → 전국 수집 → 분석∥설문 → HTML → 검증 통과(경계면·채점·매칭·헤드리스) → 승인 후 배포 → URL.
- **에러 흐름 1(키 없음)**: Phase 1에서 키 부재 → 샘플 모드로 대표 시도만 수집 → 동일 파이프라인 → 검증 시 "샘플 데이터" 한계 명시 → 배포는 사용자 판단.
- **에러 흐름 2(경계면 버그)**: frontend가 `candidate.photo` 사용하나 데이터는 `photoUrl` → QA가 교차 비교로 적발 → frontend 수정 → 재검증 통과.
- **부분 재실행**: "설문만 보강" → quiz-designer만 호출 → frontend 임베드 갱신 → QA 채점 검산 → 재배포.
