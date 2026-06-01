#!/usr/bin/env python3
"""namu 파싱 결과를 선관위 9회 후보 데이터와 대조해 검증된 동→선거구 매핑 구축.
- 시군구별 namu 선거구 집합 == 후보데이터 선거구 집합일 때만 채택(8회/9회 불일치 차단 + 시도 확정).
- 출력: _workspace/districts.json = {"시도canon|시군구|동": {"5":시도의원sgg,"6":기초의원sgg}}
"""
import json, re

WS = "_workspace"
REGION_SIDO = {
    "수도권": ["서울특별시","인천광역시","경기도"],
    "충청권": ["대전광역시","세종특별자치시","충청북도","충청남도"],
    "호남권": ["광주광역시","전북특별자치도","전라남도"],
    "대경권": ["대구광역시","경상북도"],
    "동남권": ["부산광역시","울산광역시","경상남도"],
    "강원·제주": ["강원특별자치도","제주특별자치도"],
}
SIDO_CANON = {"서울특별시":"서울","인천광역시":"인천","경기도":"경기","대전광역시":"대전","세종특별자치시":"세종",
    "충청북도":"충북","충청남도":"충남","광주광역시":"광주","전북특별자치도":"전북","전라남도":"전남",
    "대구광역시":"대구","경상북도":"경북","부산광역시":"부산","울산광역시":"울산","경상남도":"경남",
    "강원특별자치도":"강원","제주특별자치도":"제주"}
def canon(s): return SIDO_CANON.get(s, s)
def nz(s): return re.sub(r"\s","",s or "")
def nd(s): return re.sub(r"[\s·.]","",s or "")  # 동 키 정규화(점·가운뎃점 제거)


def main():
    cands = json.load(open(f"{WS}/01_data_candidates.json", encoding="utf-8"))["candidates"]
    namu = json.load(open(f"{WS}/namu_districts_raw.json", encoding="utf-8"))

    # 후보 데이터: (시도, 시군구) -> {5:set(sgg), 6:set(sgg)}
    # 일반시(안양시동안구 등)는 시 단위로도 합집합 인덱스 구축(시 = 행정구 접미 제거)
    cand = {}
    for c in cands:
        if c["sgTypecode"] in (5, 6):
            wn = nz(c["wiwName"])
            for key in {(c["sdName"], wn), (c["sdName"], re.sub(r"(시).*$", r"\1", wn))}:
                cand.setdefault(key, {5: set(), 6: set()})[c["sgTypecode"]].add(nz(c["sggName"]))

    # namu: region+시군구 -> rows
    bysgg = {}
    for r in namu:
        bysgg.setdefault((r["region"], nz(r["sigungu"])), []).append(r)

    mapping = {}
    stats = {"assigned": 0, "nomatch": 0, "dongs": 0}
    nomatch = []
    for (region, sgg), rows in bysgg.items():
        namu_gicho = {nz(sgg + r["gichoGu"]) for r in rows if r["gichoGu"]}
        namu_sdo = {nz(sgg + r["sdoGu"]) for r in rows if r["sdoGu"]}
        # 시도 배정: 같은 시군구명 후보 중 선거구명 겹침이 가장 큰 시도(거부 없음, 최대 채움)
        best_sido, best_ov = None, 0
        for sido in REGION_SIDO.get(region, []):
            cd = cand.get((sido, sgg))
            if not cd:
                continue
            ov = len(namu_gicho & cd[6]) + len(namu_sdo & cd[5])
            if ov > best_ov:
                best_ov, best_sido = ov, sido
        # 겹침 0이어도 후보에 그 시군구가 유일하게 있으면 배정
        if not best_sido:
            cands_sido = [s for s in REGION_SIDO.get(region, []) if (s, sgg) in cand]
            best_sido = cands_sido[0] if len(cands_sido) == 1 else None
        if not best_sido:
            stats["nomatch"] += 1; nomatch.append(f"{region}/{sgg}"); continue
        matched_sido = best_sido
        stats["assigned"] += 1
        # 동 -> 선거구 매핑 (행정동 이름 기준). sgg 유효성은 후처리(parse_final)에서 후보 대조로 필터.
        for r in rows:
            t5 = nz(sgg + r["sdoGu"]) if r["sdoGu"] else None
            t6 = nz(sgg + r["gichoGu"]) if r["gichoGu"] else None
            for d in r["dongs"]:
                d = d.strip()
                # 일반시 dong 셀의 행정구 접두 제거: "동안구 평촌동" -> "평촌동"
                d = re.sub(r"^[가-힣]+[구시군]\s+", "", d)
                if not d:
                    continue
                key = f"{canon(matched_sido)}|{sgg}|{nd(d)}"
                ent = {}
                if t5: ent["5"] = t5
                if t6: ent["6"] = t6
                if ent:
                    mapping[key] = ent
                    stats["dongs"] += 1

    json.dump(mapping, open(f"{WS}/districts.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(f"시군구 배정: {stats['assigned']} | 미배정: {stats['nomatch']} | 동 {len(mapping)}")
    print("미배정 예시:", nomatch[:8])


if __name__ == "__main__":
    main()
