#!/usr/bin/env python3
"""단일 HTML 빌드: 후보·정당·설문 데이터를 결합해 template.html에 임베드 -> index.html.

- 후보 axisVector = (공약 분석 있으면 그것, 없으면) 소속 정당 프로파일 상속.
- 교육감·무소속 등 정당/공약 모두 없으면 axisVector=null (프론트가 '분석 대기'로 표시).
사용: python3 build_site.py
"""
import json, os, re

WS = "_workspace"
AXES = ["econ", "social", "security", "env", "gov"]


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    cands = load(f"{WS}/01_data_candidates.json")
    parties = load(f"{WS}/02_analyst_parties.json")
    quiz = load(f"{WS}/03_quiz_quiz.json")
    # 공약(huboid -> [{realm,title,body}]) 결합
    pledges = {}
    pp = f"{WS}/01b_pledges.json"
    if os.path.exists(pp):
        pledges = load(pp)
    # 동→선거구 매핑(검증된 시군구만). 키 "시도canon|시군구|동" -> {"5":sgg,"6":sgg}
    districts = {}
    dp = f"{WS}/districts.json"
    if os.path.exists(dp):
        districts = load(dp)
    # 공약 분석 결과가 있으면 우선 사용
    scored = {}
    sp = f"{WS}/02_analyst_candidates_scored.json"
    if os.path.exists(sp):
        for c in load(sp).get("candidates", []):
            if c.get("axisVector"):
                scored[c["id"]] = c

    pmap = {p["name"]: p for p in parties["parties"]}

    # 공약 기반 점수(채점 에이전트 산출, scored_batch_*.json) huboid별 병합
    pscore = {}
    import glob
    for bf in glob.glob(f"{WS}/scored_batch_*.json"):
        for s in load(bf).get("scores", []):
            if s.get("axisVector"):
                pscore[s["huboid"]] = s

    out = []
    n_pledge = n_party = n_none = 0
    n_haspl = 0
    for c in cands["candidates"]:
        cpl = pledges.get(c.get("huboid"), []) or c.get("pledges", [])
        if cpl:
            n_haspl += 1
        av, asrc, low, am = None, "none", False, None
        sc = pscore.get(c.get("huboid"))
        mask = [k for k in sc.get("axMask", []) if k in AXES] if sc else []
        if sc and mask:  # 공약 기반 점수 (axMask가 비어있지 않을 때만)
            av, asrc, low = sc["axisVector"], "pledge", bool(sc.get("lowConfidence"))
            if len(mask) < len(AXES):
                am = [AXES.index(k) for k in mask]
            n_pledge += 1
        else:            # 빈 axMask 또는 점수 없음 → 정당 성향 폴백
            p = pmap.get(c["party"])
            if p and p.get("axisVector"):
                av, asrc, low = p["axisVector"], "party", bool(p.get("lowConfidence"))
                n_party += 1
            else:
                n_none += 1
        av_arr = [av[k] for k in AXES] if av else None
        rec = {
            "id": c["id"],
            "t": c["sgTypecode"],
            "e": c["electionName"],
            "sd": c["sdName"],
            "sgg": c["sggName"],
            "wiw": c["wiwName"],
            "n": c["num"],
            "nm": c["name"],
            "p": c["party"],
            "job": (c.get("job") or "")[:30],
            "car": (c.get("career1") or "")[:60],
            "av": av_arr,
            "as": asrc,
            "lc": low,
            "pl": [{"title": (p.get("realm") and f"[{p['realm']}] " or "") + p.get("title", ""),
                    "body": re.sub(r"\s+", " ", p.get("body", "")).strip()[:240]} for p in cpl],
        }
        if am:
            rec["am"] = am
        out.append(rec)

    app = {
        "meta": cands["meta"],
        "axes": quiz["axes"],
        "options": quiz["options"],
        "questions": quiz["questions"],
        "scoring": quiz.get("scoring", ""),
        "parties": parties["parties"],
        "districts": districts,
        "candidates": out,
    }

    with open("template.html", encoding="utf-8") as f:
        tpl = f.read()
    payload = json.dumps(app, ensure_ascii=False, separators=(",", ":"))
    html = tpl.replace("/*__APPDATA__*/", payload)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    size = os.path.getsize("index.html") / 1024 / 1024
    print(f"index.html 생성: {size:.2f} MB, 후보 {len(out)}명")
    print(f"  성향 출처 — 공약:{n_pledge}  정당:{n_party}  없음(교육감·무소속):{n_none}")
    print(f"  실제 공약 보유 후보: {n_haspl}명")


if __name__ == "__main__":
    main()
