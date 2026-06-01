#!/usr/bin/env python3
"""제9회 전국동시지방선거 후보자 전량 수집 (data.go.kr 중앙선관위 후보자정보 API).

사용: python3 fetch_nec.py --key <서비스키> [--out <dir>] [--pledge-key <공약API키>]
- 후보자 정보: PofelcddInfoInqireService/getPofelcddRegistSttusInfoInqire
- 17개 시도 × 7개 선거종류(3,4,5,6,7,8,11)를 sdName 기준 페이지네이션 수집.
- 산출: <out>/01_data_candidates.json, 01_data_parties.json, 01_data_report.md
데이터 계약: .claude/skills/vote-helper-orchestrator/references/data-contract.md
"""
import argparse, json, os, sys, time, urllib.parse, urllib.request

CAND_EP = "https://apis.data.go.kr/9760000/PofelcddInfoInqireService/getPofelcddRegistSttusInfoInqire"
SG_ID = "20260603"  # 제9회 전국동시지방선거

# sgTypecode (서울 실증으로 확정): 3 시도지사 / 4 구시군장 / 11 교육감 -> 공약 개별분석 대상
#   5 시도의원 지역구 / 6 구시군의원 지역구 / 8 비례 시도의원 / 9 비례 구시군의원 -> 정당 성향 대체
#   (7=빈 데이터, 1/2/10=해당 선거 없음)
SG_TYPES = {
    "3": "시도지사", "4": "구시군의 장", "11": "교육감",
    "5": "시도의원", "6": "구시군의원", "8": "비례대표시도의원", "9": "비례대표구시군의원",
}
PLEDGE_TYPES = {"3", "4", "11"}

SIDO = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시", "대전광역시",
    "울산광역시", "세종특별자치시", "경기도", "강원특별자치도", "충청북도", "충청남도",
    "전북특별자치도", "전라남도", "경상북도", "경상남도", "제주특별자치도",
]


def call(ep, params, retries=2):
    qs = urllib.parse.urlencode(params)
    url = f"{ep}?{qs}"
    last = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=40) as r:
                raw = r.read().decode("utf-8")
            data = json.loads(raw)
            return data
        except Exception as e:  # noqa
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"call failed: {ep} {params.get('sgTypecode')} {params.get('sdName')}: {last}")


def fetch_type_sido(key, sgType, sdName):
    """한 (선거종류, 시도)의 모든 후보를 페이지네이션 수집. API는 numOfRows를 100으로 캡한다."""
    out, page, num = [], 1, 100
    while True:
        d = call(CAND_EP, {
            "serviceKey": key, "pageNo": page, "numOfRows": num,
            "sgId": SG_ID, "sgTypecode": sgType, "sdName": sdName, "resultType": "json",
        })
        body = d.get("response", {}).get("body", {})
        items = (body.get("items") or {}).get("item") or []
        if isinstance(items, dict):
            items = [items]
        out.extend(items)
        total = int(body.get("totalCount") or 0)
        if len(out) >= total or not items:
            break
        page += 1
        time.sleep(0.2)
    return out


def norm(raw, sgType):
    district = (raw.get("sggName") or raw.get("sdName") or "").strip()
    cid = f"{SG_ID}-{sgType}-{raw.get('huboid')}"
    return {
        "id": cid,
        "huboid": raw.get("huboid"),
        "sgTypecode": int(sgType),
        "electionName": SG_TYPES[sgType],
        "sdName": raw.get("sdName", ""),
        "sggName": raw.get("sggName", ""),
        "wiwName": raw.get("wiwName", ""),
        "districtName": district,
        "num": (raw.get("giho") or "").strip(),
        "name": raw.get("name", ""),
        "party": (raw.get("jdName") or "").strip() or "무소속",
        "job": raw.get("job", ""),
        "edu": raw.get("edu", ""),
        "career1": raw.get("career1", ""),
        "career2": raw.get("career2", ""),
        "status": raw.get("status", ""),
        "photoUrl": None,            # 후보자 API에 사진 없음 -> 프론트 이니셜 아바타
        "pledges": [],               # 공약 API 수집 시 채움(단체장·교육감만)
        "axisVector": None,          # policy-analyst가 채움
        "axisSource": "pledge" if sgType in PLEDGE_TYPES else "party",
        "matchableBy": "pledge" if sgType in PLEDGE_TYPES else "party",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--pledge-key", default=None)
    ap.add_argument("--out", default="_workspace")
    ap.add_argument("--types", default=",".join(SG_TYPES.keys()))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    cands, counts, errors = [], {}, []
    for sgType in args.types.split(","):
        sgType = sgType.strip()
        if sgType not in SG_TYPES:
            continue
        for sd in SIDO:
            try:
                raws = fetch_type_sido(args.key, sgType, sd)
            except Exception as e:  # noqa
                errors.append(str(e))
                print(f"  ! ERROR {SG_TYPES[sgType]} {sd}: {e}", file=sys.stderr)
                continue
            for r in raws:
                cands.append(norm(r, sgType))
            counts[f"{sgType}:{SG_TYPES[sgType]}:{sd}"] = len(raws)
            print(f"  {SG_TYPES[sgType]:12s} {sd:10s} {len(raws):5d}")
            time.sleep(0.15)

    parties = sorted({c["party"] for c in cands if c["party"]})
    meta = {
        "election": "제9회 전국동시지방선거", "voteDate": "2026-06-03", "sgId": SG_ID,
        "source": "data.go.kr 9760000 PofelcddInfoInqireService", "total": len(cands),
    }
    with open(os.path.join(args.out, "01_data_candidates.json"), "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "candidates": cands}, f, ensure_ascii=False)
    with open(os.path.join(args.out, "01_data_parties.json"), "w", encoding="utf-8") as f:
        json.dump({"parties": [{"name": p, "axisVector": None, "rationale": ""} for p in parties]},
                  f, ensure_ascii=False, indent=2)

    by_type = {}
    for c in cands:
        by_type[c["electionName"]] = by_type.get(c["electionName"], 0) + 1
    lines = ["# 01 데이터 수집 보고", "", f"- 총 후보: **{len(cands)}**", f"- 정당 수: {len(parties)}", ""]
    lines.append("## 선거종류별 후보 수")
    for k, v in by_type.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append(f"## 정당 목록 ({len(parties)})")
    lines.append(", ".join(parties))
    if errors:
        lines += ["", f"## 수집 오류 {len(errors)}건", *[f"- {e}" for e in errors]]
    with open(os.path.join(args.out, "01_data_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nDONE: {len(cands)} candidates, {len(parties)} parties -> {args.out}/")
    if errors:
        print(f"  with {len(errors)} errors (see report)")


if __name__ == "__main__":
    main()
