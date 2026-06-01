#!/usr/bin/env python3
"""단체장·교육감(sgTypecode 3,4,11) 후보 공약 전량 수집.
사용: python3 fetch_pledges.py --key <서비스키> [--out _workspace]
입력: <out>/01_data_candidates.json  출력: <out>/01b_pledges.json {huboid:[{realm,title,body}]}
"""
import argparse, json, os, time, urllib.parse, urllib.request

EP = "https://apis.data.go.kr/9760000/ElecPrmsInfoInqireService/getCnddtElecPrmsInfoInqire"
SG_ID = "20260603"
PLEDGE_TYPES = {3, 4, 11}


def call(params, retries=2):
    url = f"{EP}?{urllib.parse.urlencode(params)}"
    last = None
    for a in range(retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa
            last = e; time.sleep(1.2 * (a + 1))
    raise RuntimeError(str(last))


def parse(item):
    out = []
    cnt = int(item.get("prmsCnt") or 0) or 10
    for i in range(1, 11):
        title = (item.get(f"prmsTitle{i}") or "").strip()
        body = (item.get(f"prmmCont{i}") or "").strip()
        realm = (item.get(f"prmsRealmName{i}") or "").strip()
        if title or body:
            out.append({"realm": realm, "title": title, "body": body})
        if i >= cnt and not title:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    ap.add_argument("--out", default="_workspace")
    args = ap.parse_args()
    with open(os.path.join(args.out, "01_data_candidates.json"), encoding="utf-8") as f:
        cands = json.load(f)["candidates"]
    targets = [c for c in cands if c["sgTypecode"] in PLEDGE_TYPES]
    print(f"공약 수집 대상: {len(targets)}명 (단체장·교육감)")

    pledges, n_have, errors = {}, 0, []
    for idx, c in enumerate(targets, 1):
        hid = c["huboid"]
        try:
            d = call({"serviceKey": args.key, "numOfRows": 10, "sgId": SG_ID,
                      "sgTypecode": c["sgTypecode"], "cnddtId": hid, "resultType": "json"})
            body = d.get("response", {}).get("body", {})
            it = (body.get("items") or {}).get("item") or []
            if isinstance(it, dict):
                it = [it]
            pl = parse(it[0]) if it else []
        except Exception as e:  # noqa
            errors.append(f"{hid} {c['name']}: {e}"); pl = []
        pledges[hid] = pl
        if pl:
            n_have += 1
        if idx % 100 == 0:
            print(f"  {idx}/{len(targets)} ... 공약보유 {n_have}")
        time.sleep(0.12)

    with open(os.path.join(args.out, "01b_pledges.json"), "w", encoding="utf-8") as f:
        json.dump(pledges, f, ensure_ascii=False)
    print(f"DONE: {len(pledges)}명 중 공약보유 {n_have}명, 오류 {len(errors)}건 -> {args.out}/01b_pledges.json")
    if errors:
        print("  오류 예:", errors[:3])


if __name__ == "__main__":
    main()
