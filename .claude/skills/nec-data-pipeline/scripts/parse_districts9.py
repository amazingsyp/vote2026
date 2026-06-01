#!/usr/bin/env python3
"""namu 9회 지선 선거구 '획정 예시(가칭)' 표만 파싱 (8회 표 제외).
두 형식 지원:
  A) [시의회선거구][구의회선거구][관할구역][인구][국회]  (예: 종로구의회 가 선거구)
  B) [시의회(구의회)통합선거구][관할구역][인구][국회]     (예: 은평구 제1(구의회 가(4))선거구)
출력: _workspace/namu_districts_raw.json = [{region,sigungu,sdoGu,gichoGu,dongs:[...]}]
주의: namu 9회는 '가칭/예시' → 이후 선관위 후보 데이터와 선거구 집합 대조로 최종 일치 시군구만 채택.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from parse_districts import TableGrid, expand  # 동일 그리드 복원 재사용

REGION_FILES = ["수도권", "충청권", "호남권", "대경권", "동남권", "강원·제주"]
LETTERS = "가나다라마바사아자차카타파하거너더러머버서어저처커터퍼허"


def gu_of(s):
    m = re.match(r"\s*([가-힣]+?[구시군])", s)
    return m.group(1) if m else ""


def giho_letter(s):
    # "...의회 가 선거구", "(구의회 가(4))", "구의회 가선거구" 등에서 기초 선거구 문자 추출
    m = re.search(r"(?:구의회|군의회|의회)\s*([" + LETTERS + r"])\s*\)?\s*선거구", s)
    if not m:
        m = re.search(r"(?:구의회|군의회)\s*([" + LETTERS + r"])\s*\(", s)
    return m.group(1) if m else ""


def sdo_no(s):
    m = re.search(r"제\s*(\d+)\s*\(?선거구", s) or re.search(r"제\s*(\d+)", s)
    return m.group(1) if m else ""


def parse_region(htmltext):
    tabs = re.findall(r"<table.*?</table>", htmltext, re.S)
    out = []
    for t in tabs:
        if "9회 지선" not in t or "관할구역" not in t:
            continue
        p = TableGrid(); p.feed(t)
        if not p.tables:
            continue
        g = expand(p.tables[0])
        if len(g) < 3:
            continue
        hdr = g[1] if "관할" in " ".join(g[1]) else g[0]
        dong_i = next((i for i, c in enumerate(hdr) if "관할" in c), None)
        if dong_i is None:
            continue
        fmtA = dong_i == 2  # 시의회+구의회 분리
        for r in g:
            if len(r) <= dong_i:
                continue
            dongcell = r[dong_i]
            if "동" not in dongcell and "리" not in dongcell and "읍" not in dongcell and "면" not in dongcell:
                continue
            if "관할" in dongcell:
                continue
            if fmtA:
                sdocell, gichocell = r[0], r[1]
            else:
                sdocell = gichocell = r[0]
            gu = gu_of(gichocell) or gu_of(dongcell) or gu_of(sdocell)
            if not gu:
                continue
            letter = giho_letter(gichocell)
            no = sdo_no(sdocell)
            gicho = f"{gu}{letter}선거구" if letter else ""
            sdo = f"{gu}제{no}선거구" if no else (f"{gu}선거구" if "전 지역" in sdocell or "전지역" in sdocell else "")
            # 동: 구 접두 제거 후 분리
            dc = re.sub(r"^[가-힣]+[구시군]\s+", "", dongcell)
            dongs = [d.strip() for d in re.split(r"[,，]", dc) if d.strip() and "선거구" not in d]
            if gicho or sdo:
                out.append({"sigungu": gu, "sdoGu": sdo.replace(gu, "", 1), "gichoGu": gicho.replace(gu, "", 1), "dongs": dongs})
    return out


def main():
    allrows = []
    for r in REGION_FILES:
        fp = f"/tmp/namu/{r}.html"
        if not os.path.exists(fp):
            print("missing", fp); continue
        rows = parse_region(open(fp, encoding="utf-8").read())
        for x in rows:
            x["region"] = r
        allrows.extend(rows)
        print(f"{r}: {len(rows)} rows")
    json.dump(allrows, open("_workspace/namu_districts_raw.json", "w", encoding="utf-8"), ensure_ascii=False)
    print("총", len(allrows), "-> _workspace/namu_districts_raw.json")
    for x in allrows[:5]:
        print(" ", x["sigungu"], "|시도", x["sdoGu"], "|기초", x["gichoGu"], "|", x["dongs"][:4])


if __name__ == "__main__":
    main()
