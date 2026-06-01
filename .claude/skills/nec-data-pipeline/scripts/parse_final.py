#!/usr/bin/env python3
"""namu '제9회 지방선거/선거구'(최종 확정본) 단일 페이지에서 시도의원(t5)+기초의원(t6) 동 매핑 추출.
게이팅 없이 namu 최종본을 신뢰. 출력: _workspace/districts.json = {"시도canon|시군구|동":{"5":sgg,"6":sgg}}
표 형식(혼재):
  - 시의회/도의회: [선거구(제N)][관할]
  - 구·군의회 분리: [시의회 제N][구·군의회 가][관할]
  - 통합: [제1선거구/가 선거구(n)][관할]
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from parse_districts import TableGrid, expand

CANON = {"서울특별시":"서울","인천광역시":"인천","경기도":"경기","대전광역시":"대전","세종특별자치시":"세종",
    "충청북도":"충북","충청남도":"충남","광주광역시":"광주","전북특별자치도":"전북","전라남도":"전남",
    "대구광역시":"대구","경상북도":"경북","부산광역시":"부산","울산광역시":"울산","경상남도":"경남",
    "강원특별자치도":"강원","제주특별자치도":"제주"}
HEAD_SIDO = {"서울특별시":"서울특별시","인천광역시":"인천광역시","경기도":"경기도","부산광역시":"부산광역시",
    "울산광역시":"울산광역시","경상남도":"경상남도","대구광역시":"대구광역시","경상북도":"경상북도",
    "전남광주통합특별시":"광주광역시","광주광역시":"광주광역시","전라남도":"전라남도","전북특별자치도":"전북특별자치도",
    "대전광역시":"대전광역시","세종특별자치시":"세종특별자치시","충청북도":"충청북도","충청남도":"충청남도",
    "강원특별자치도":"강원특별자치도","제주특별자치도":"제주특별자치도"}
LETTERS = "가나다라마바사아자차카타파하거너더러머버서어저처커터퍼허고노도로모보소오조초코토포호"
def canon(s): return CANON.get(s, s)
def nz(s): return re.sub(r"\s", "", s or "")
def nd(s): return re.sub(r"[\s·.]", "", s or "")
def gu_of(s):
    m = re.match(r"\s*([가-힣]+?[구시군])(?![가-힣])", s.strip())
    return m.group(1) if m else ""


def main():
    h = open("/tmp/namu_sgg.html", encoding="utf-8").read()
    tokens = []
    for m in re.finditer(r"<h[23][^>]*>(.*?)</h[23]>", h, re.S):
        txt = re.sub(r"<[^>]+>", "", m.group(1)); txt = re.sub(r"&#91;.*?&#93;", "", txt)
        tokens.append((m.start(), "head", txt))
    for m in re.finditer(r"<table.*?</table>", h, re.S):
        tokens.append((m.start(), "table", m.group(0)))
    tokens.sort(key=lambda x: x[0])

    cur = None
    # 8회-검증맵을 베이스로 로드(t6 보강용). 최종본이 우선 덮어씀.
    base_path = "_workspace/districts.json"
    mapping = json.load(open(base_path, encoding="utf-8")) if os.path.exists(base_path) else {}
    base_n = len(mapping)
    rows_used = 0
    for _, typ, payload in tokens:
        if typ == "head":
            for k, v in HEAD_SIDO.items():
                if k in nz(payload):
                    cur = v; break
            continue
        if "관할구역" not in payload or not cur:
            continue
        p = TableGrid(); p.feed(payload)
        if not p.tables:
            continue
        g = expand(p.tables[0])
        hdr = next((r for r in g[:3] if "관할" in " ".join(r)), None)
        if not hdr:
            continue
        dong_i = next(i for i, c in enumerate(hdr) if "관할" in c)
        for r in g:
            if len(r) <= dong_i:
                continue
            dongcell = r[dong_i]
            if not re.search(r"[동리읍면]", dongcell) or "관할" in dongcell:
                continue
            sgtext = " ".join(r[:dong_i])
            gu = gu_of(sgtext) or gu_of(dongcell)
            if not gu:
                continue
            t5 = t6 = None
            m5 = re.search(r"제\s*(\d+)\s*선거구", sgtext)
            if m5:
                t5 = f"{gu}제{m5.group(1)}선거구"
            elif "전 지역" in sgtext or "전지역" in sgtext:
                t5 = f"{gu}선거구"
            m6 = re.search(r"(?:^|[\s/(])([" + LETTERS + r"])\s*선거구", sgtext)
            if m6:
                t6 = f"{gu}{m6.group(1)}선거구"
            if not (t5 or t6):
                continue
            rows_used += 1
            dc = re.sub(r"^[가-힣]+[구시군]\s+", "", dongcell)
            for d in re.split(r"[,，]", dc):
                d = d.strip()
                if not d or "선거구" in d:
                    continue
                key = f"{canon(cur)}|{nz(gu)}|{nd(d)}"
                ent = mapping.setdefault(key, {})
                if t5: ent["5"] = t5
                if t6: ent["6"] = t6

    cands = json.load(open("_workspace/01_data_candidates.json", encoding="utf-8"))["candidates"]
    # 제주·세종: 시도의원 선거구명에 관할 동이 들어있음("서귀포시 대천동·중문동·예래동선거구")
    # → 후보 데이터에서 직접 파생(namu 불필요).
    derived = 0
    for c in cands:
        if c["sgTypecode"] != 5 or c["sdName"] not in ("제주특별자치도", "세종특별자치시"):
            continue
        body = re.sub(r"^\s*" + re.escape(c["sdName"]), "", c["sggName"]).strip()
        m = re.match(r"(\S+?[시군구])?\s*(.+?)선거구$", body)
        if not m:
            continue
        sigungu = nz(m.group(1) or c.get("wiwName") or c["sdName"])
        for d in re.split(r"[·,]", m.group(2)):
            d = d.strip()
            if not d:
                continue
            key = f"{canon(c['sdName'])}|{sigungu}|{nd(d)}"
            mapping.setdefault(key, {})["5"] = nz(c["sggName"])
            derived += 1
    print(f"제주·세종 파생 동: {derived}")

    # 후처리 필터: 후보 데이터에 없는 선거구명 제거(선택 불가한 phantom 차단 → 자동선택 항상 유효)
    cset = {"5": set(), "6": set()}
    for c in cands:
        if c["sgTypecode"] in (5, 6):
            cset[str(c["sgTypecode"])].add(nz(c["sggName"]))
    dropped = 0
    for k in list(mapping.keys()):
        v = mapping[k]
        for t in ("5", "6"):
            if t in v and v[t] not in cset[t]:
                del v[t]; dropped += 1
        if not v:
            del mapping[k]

    json.dump(mapping, open("_workspace/districts.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(f"phantom 선거구 제거: {dropped}")
    has5 = sum(1 for v in mapping.values() if "5" in v)
    has6 = sum(1 for v in mapping.values() if "6" in v)
    sgus = len({"|".join(k.split("|")[:2]) for k in mapping})
    print(f"동 키 {len(mapping)}(베이스 {base_n}) | t5 {has5} | t6 {has6} | 시군구 {sgus} | 최종본 행 {rows_used}")


if __name__ == "__main__":
    main()
