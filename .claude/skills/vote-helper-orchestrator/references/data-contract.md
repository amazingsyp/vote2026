# 데이터 계약 (Data Contract) — 제9회 지방선거 투표 도우미

모든 에이전트와 스킬이 공유하는 **단일 진실 공급원**. 데이터 shape이 바뀌면 이 파일을 먼저 고치고, 소비하는 쪽(frontend, qa)에 전파한다. QA의 경계면 검증은 이 계약을 기준으로 수행한다.

## 1. 정치 성향 축 (Political Axes)

5축. 각 축은 `-100 .. +100` 정수. 0이 중도.

| key | 이름 | -100 극 | +100 극 |
|-----|------|---------|---------|
| `econ` | 경제 | 분배·복지·규제 | 시장·성장·감세 |
| `social` | 사회·문화 | 진보·다양성 | 보수·전통 |
| `security` | 대북·안보 | 화해·협력 | 강경·억지 |
| `env` | 환경·개발 | 환경보호 | 개발·성장 |
| `gov` | 정부역할 | 큰 정부·공공 | 작은 정부·민영 |

성향 벡터 타입: `AxisVector = { econ:number, social:number, security:number, env:number, gov:number }`

## 2. 설문 (Quiz)

```jsonc
// quiz.json
{
  "axes": [ {"key":"econ","name":"경제","leftLabel":"분배·복지","rightLabel":"시장·성장"}, ... ],
  "questions": [
    {
      "id": "q1",
      "text": "문항 텍스트(서술형 입장 진술)",
      "axis": "econ",            // 주 축
      "weight": 1.0,             // 이 문항이 축에 기여하는 가중치
      "direction": 1,            // +1: 동의가 +축 방향, -1: 동의가 -축 방향
      "options": [               // 5점 리커트 고정
        {"label":"매우 동의","score":2},
        {"label":"동의","score":1},
        {"label":"중립","score":0},
        {"label":"반대","score":-1},
        {"label":"매우 반대","score":-2}
      ]
    }
  ],
  "scoring": "각 축 점수 = Σ(option.score × weight × direction) 를 축별로 합산 후 -100..100 정규화"
}
```

문항 수 16~20. 각 축 최소 3문항.

## 3. 후보자 (Candidates)

```jsonc
// candidates.json
{
  "meta": { "election": "제9회 전국동시지방선거", "voteDate": "2026-06-03", "builtAt": "<빌드시 스탬프>", "source": "data.go.kr (15040587 선거공약, 15000908 후보자)" },
  "candidates": [
    {
      "id": "sgId-sgTypecode-num",   // 고유키
      "sgTypecode": 3,                // 선거종류코드 (아래 표)
      "electionName": "서울특별시장",
      "districtCode": "1100",          // 선거구 코드 (행정구역/선거구 매핑 키)
      "districtName": "서울특별시",
      "num": 1,                        // 기호
      "name": "홍길동",
      "party": "○○당",
      "photoUrl": "https://... 또는 null",
      "pledges": [                      // 단체장·교육감만 채워짐. 의원은 [] 
        {"title":"공약 제목","body":"공약 내용 요약"}
      ],
      "axisVector": { "econ":40, "social":-20, "security":60, "env":-10, "gov":30 },
      "axisSource": "pledge" | "party",  // pledge=공약 개별분석, party=정당 성향 대체
      "matchableBy": "pledge" | "party"
    }
  ]
}
```

### 선거종류코드 (sgTypecode) — data-engineer가 API 문서로 최종 확인
- 3: 시도지사(광역단체장) · 4: 구시군의 장(기초단체장) · 11: 교육감 → **공약 개별 분석**
- 5: 시도의원(지역구) · 6: 구시군의원(지역구) · 7: 비례 시도의원 · 8: 비례 구시군의원 → **정당 성향 대체**

> 공약 문서 제출 선거는 시도지사·구시군장·교육감(+대통령)뿐. 의원은 `pledges:[]`, `axisSource:"party"`.

## 4. 정당 성향 (Party Profiles)

```jsonc
// parties.json
{ "parties": [ { "name":"○○당", "axisVector": {...}, "rationale":"성향 근거 1~2문장" } ] }
```
의원 후보의 `axisVector`는 소속 정당 프로파일에서 상속한다.

## 5. 주소 → 선거구 매핑 (District Lookup)

```jsonc
// districts.json — 읍면동 단위 행정코드 → 각 선거 선거구 코드
{
  "byEmd": {
    "<법정동코드 또는 시도/시군구/읍면동 조합>": {
      "sido": "서울특별시",
      "sigungu": "종로구",
      "emd": "청운효자동",
      "districts": { "3":"1100", "4":"1111", "11":"1100", "5":"1111-01", "6":"1111-가" }
      // sgTypecode → districtCode
    }
  }
}
```
Kakao 우편번호 서비스가 반환하는 `sido/sigungu/bname`로 이 표를 조회해 사용자의 모든 선거 선거구를 해석한다. 의원 선거구 매핑이 가장 어려움 — 선관위 선거구획정 자료로 구축, 미해결 읍면동은 단체장/교육감만 노출하고 의원은 "선거구 확인 필요"로 처리.

## 6. 매칭 결과 (Frontend 계산, 런타임)
- 사용자 `AxisVector` u, 후보 `AxisVector` c.
- 일치도 = `round( (1 - 정규화거리(u,c)) × 100 )`. 정규화거리 = 유클리드거리 / 최대거리(√(5×200²)).
- 각 후보 카드에 일치도 %, 레이더 차트(u vs c 오버레이), 일치/불일치 축 Top 근거 표시.

## 파일 산출 위치
- 중간 산출물: `_workspace/{phase}_{agent}_{artifact}.json`
- 최종 임베드 데이터: 빌드 시 `index.html`에 인라인(`<script type="application/json">`) 또는 `data.json` 동봉.
