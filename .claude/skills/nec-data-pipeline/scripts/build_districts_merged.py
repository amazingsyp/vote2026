#!/usr/bin/env python3
"""최종 동→선거구 매핑 병합.
- t5(시도의원): namu '/선거구' 최종 확정본(권위). 선관위 후보 데이터로 sgg 검증.
- t6(기초의원): 8회 검증맵(_workspace/districts.json, set 일치=9회최종 미변경 구).
출력(덮어쓰기): _workspace/districts.json = {"시도canon|시군구|동": {"5":sgg,"6":sgg}}
"""
import json, os, re

WS = "_workspace"
CANON = {"서울특별시":"서울","인천광역시":"인천","경기도":"경기","대전광역시":"대전","세종특별자치시":"세종",
    "충청북도":"충북","충청남도":"충남","광주광역시":"광주","전북특별자치도":"전북","전라남도":"전남",
    "대구광역시":"대구","경상북도":"경북","부산광역시":"부산","울산광역시":"울산","경상남도":"경남",
    "강원특별자치도":"강원","제주특별자치도":"제주"}
def canon(s): return CANON.get(s, s)
def nz(s): return re.sub(r"\s","",s or "")
def nd(s):  # 동 정규화: 공백·가운뎃점·마침표 제거(종로1·2·3·4가동 == 종로1.2.3.4가동)
    return re.sub(r"[\s·.]","",s or "")


def main():
    cands = json.load(open(f"{WS}/01_data_candidates.json", encoding="utf-8"))["candidates"]
    final = json.load(open(f"{WS}/final_districts_raw.json", encoding="utf-8"))
    base = json.load(open(f"{WS}/districts.json", encoding="utf-8"))  # 8회 검증맵(t5+t6)

    # 후보 데이터 t5 검증셋: (시도, 시군구 or 시) -> set(sgg)
    cand5 = {}
    for c in cands:
        if c["sgTypecode"] == 5:
            wn = nz(c["wiwName"])
            for k in {(c["sdName"], wn), (c["sdName"], re.sub(r"(시).*$", r"\1", wn))}:
                cand5.setdefault(k, set()).add(nz(c["sggName"]))

    # base의 동 키를 nd 정규화로 재키잉(t6 보존)
    merged = {}
    for k, v in base.items():
        sido, sg, d = k.split("|")
        merged[f"{sido}|{sg}|{nd(d)}"] = dict(v)

    added5 = valid5 = rej5 = 0
    for row in final:
        sido, sg, sgg = row["sido"], nz(row["sigungu"]), nz(row["sgg"])
        # 검증: sgg가 후보 데이터 t5 집합에 존재(시군구 또는 시 단위)
        ok = any(sgg in cand5.get((sido, key), set())
                 for key in {sg, re.sub(r"(시).*$", r"\1", sg)})
        if not ok:
            rej5 += 1; continue
        valid5 += 1
        for d in row["dongs"]:
            key = f"{canon(sido)}|{sg}|{nd(d)}"
            ent = merged.setdefault(key, {})
            if "5" not in ent: added5 += 1
            ent["5"] = sgg

    json.dump(merged, open(f"{WS}/districts.json", "w", encoding="utf-8"), ensure_ascii=False)
    has5 = sum(1 for v in merged.values() if "5" in v)
    has6 = sum(1 for v in merged.values() if "6" in v)
    print(f"병합 동 키: {len(merged)} | t5 보유 {has5} | t6 보유 {has6}")
    print(f"최종본 t5: 검증통과 {valid5} 행(거부 {rej5}), 신규 동 t5 {added5}")


if __name__ == "__main__":
    main()
