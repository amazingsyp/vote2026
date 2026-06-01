#!/usr/bin/env python3
"""공약 보유 단체장·교육감을 점수화 배치로 추출.
출력: _workspace/score_batch_{n}.json  (정책분석 에이전트 입력)
사용: python3 extract_batches.py [--size 50]
"""
import argparse, json, os

WS = "_workspace"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=50)
    args = ap.parse_args()
    cands = {c["huboid"]: c for c in json.load(open(f"{WS}/01_data_candidates.json", encoding="utf-8"))["candidates"]}
    pledges = json.load(open(f"{WS}/01b_pledges.json", encoding="utf-8"))

    rows = []
    for hid, pls in pledges.items():
        if not pls:
            continue
        c = cands.get(hid)
        if not c:
            continue
        rows.append({
            "huboid": hid,
            "name": c["name"],
            "party": c["party"],
            "sgTypecode": c["sgTypecode"],
            "election": c["electionName"],
            "region": c["sggName"] or c["sdName"],
            "pledges": [{"realm": p.get("realm", ""), "title": p.get("title", ""),
                          "body": p.get("body", "")[:500]} for p in pls],
        })
    # 교육감 먼저(우선순위), 그다음 시도지사, 구청장
    order = {11: 0, 3: 1, 4: 2}
    rows.sort(key=lambda r: order.get(r["sgTypecode"], 9))

    n = 0
    for i in range(0, len(rows), args.size):
        batch = rows[i:i + args.size]
        with open(f"{WS}/score_batch_{n}.json", "w", encoding="utf-8") as f:
            json.dump(batch, f, ensure_ascii=False)
        n += 1
    print(f"총 {len(rows)}명 -> {n}개 배치 (배치당 ~{args.size}명)")
    print("교육감:", sum(1 for r in rows if r["sgTypecode"] == 11),
          "시도지사:", sum(1 for r in rows if r["sgTypecode"] == 3),
          "구청장:", sum(1 for r in rows if r["sgTypecode"] == 4))


if __name__ == "__main__":
    main()
