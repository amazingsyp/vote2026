#!/usr/bin/env python3
"""namu '제9회 지방선거/선거구 획정/{지역}' 페이지에서 선거구별 관할 행정동을 파싱.
출력: _workspace/namu_districts_raw.json = [{sido,sigungu,sdoGu,gichoGu,dongs:[...]}]
입력: /tmp/namu/*.html (curl로 받은 6개 지역 페이지)
주의: namu 표는 '제8회' 관할구역 기준 → 이후 후보 데이터와 선거구 집합 대조로 9회 일치 시군구만 채택.
"""
import json, os, re, html
from html.parser import HTMLParser

REGION_FILES = ["수도권", "충청권", "호남권", "대경권", "동남권", "강원·제주"]
SIDO_NAMES = ["서울특별시","부산광역시","대구광역시","인천광역시","광주광역시","대전광역시","울산광역시",
    "세종특별자치시","경기도","강원특별자치도","강원도","충청북도","충청남도","전북특별자치도","전라북도",
    "전라남도","경상북도","경상남도","제주특별자치도"]


class TableGrid(HTMLParser):
    """table을 rowspan/colspan 반영한 2D 그리드로 복원."""
    def __init__(self):
        super().__init__()
        self.tables=[]; self.cur=None; self.row=None; self.cell=None
        self.intd=False; self.pending={}  # col -> (text, remaining_rowspan)
        self.rowidx=0
        self._span=(1,1)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="table": self.cur=[]; self.pending={}; self.rowidx=0
        elif tag=="tr" and self.cur is not None:
            self.row=[]; self.colptr=0
        elif tag in ("td","th") and self.cur is not None and self.row is not None:
            self.intd=True; self.cell=[]
            rs=int(a.get("rowspan","1") or 1); cs=int(a.get("colspan","1") or 1)
            self._span=(rs,cs)
    def handle_data(self,d):
        if self.intd: self.cell.append(d)
    def handle_endtag(self,tag):
        if tag in ("td","th") and self.intd:
            txt=re.sub(r"\s+"," ",html.unescape("".join(self.cell))).strip()
            self.row.append((txt,self._span)); self.intd=False
        elif tag=="tr" and self.row is not None:
            self.cur_row=self.row; self.row=None
            if self.cur is not None: self.cur.append(self.cur_row)
        elif tag=="table" and self.cur is not None:
            self.tables.append(self.cur); self.cur=None


def expand(rows):
    """rowspan/colspan 반영해 직사각 그리드로 확장."""
    grid=[]; spans={}  # (r,c)->text via fill
    occupied={}
    maxc=0
    for r,row in enumerate(rows):
        c=0
        out={}
        # 이미 위에서 내려온 rowspan 칸 채우기
        while occupied.get((r,c)): out[c]=occupied[(r,c)]; c+=1
        for (txt,(rs,cs)) in row:
            while occupied.get((r,c)): out[c]=occupied[(r,c)]; c+=1
            for cc in range(cs):
                for rr in range(rs):
                    if rr==0: out[c+cc]=txt
                    else: occupied[(r+rr,c+cc)]=txt
            c+=cs
        maxc=max(maxc,c)
        grid.append(out)
    # dict -> list
    return [[g.get(i,"") for i in range(maxc)] for g in grid]


def parse_region(htmltext):
    p=TableGrid(); p.feed(htmltext)
    out=[]
    # 시도 헤딩 위치로 표↔시도 연결: 표 앞 텍스트에서 가장 가까운 시도명
    # 간단화: 전체 텍스트에서 표의 첫 셀(구 이름) 기준, 시도는 표 직전 헤딩에서 추정
    # 헤딩 추출
    plain=re.sub(r"<[^>]+>"," ",htmltext)
    for tbl in p.tables:
        grid=expand(tbl)
        if not grid or len(grid)<2: continue
        head=" ".join(grid[0])
        if "관할구역" not in head: continue  # 선거구 표만
        # 컬럼 인덱스: [구][시도의원][기초의원][관할구역][인구] 추정
        # 헤더에서 위치 찾기
        cols={}
        for i,c in enumerate(grid[0]):
            if "구·시·군" in c or "구.시.군" in c: cols["gu"]=i
            elif "광역의원" in c or "시·도의원" in c: cols.setdefault("sdo",i)
            elif "관할" in c: cols["dong"]=i
            elif "인구" in c: cols["pop"]=i
        # 표준 컬럼: gu=0, sido의원=1, 기초의원=2, 관할=3
        gu_i=cols.get("gu",0)
        dong_i=cols.get("dong",3)
        # 시도 추정: 표 안 구 이름으로 광역 판별은 어려워 → 지역파일+구 매칭에 위임(나중)
        for r in grid[1:]:
            if len(r)<=dong_i: continue
            gu=r[gu_i]; dongcell=r[dong_i]
            if not dongcell or "동" not in dongcell and "리" not in dongcell and "읍" not in dongcell and "면" not in dongcell:
                continue
            # 구 이름 정제: "종로구2" -> 종로구 (뒤 숫자 제거)
            gu=re.sub(r"\d+$","",gu).strip()
            # 시도의원 선거구 = col1, 기초의원 = col2 (정수숫자 뒤 제거)
            sdo=re.sub(r"\s*\d+$","",r[1]).strip() if len(r)>1 else ""
            gicho=re.sub(r"\s*\d+$","",r[2]).strip() if len(r)>2 else ""
            dongs=[d.strip() for d in re.split(r"[,，]", dongcell) if d.strip()]
            out.append({"sigungu":gu,"sdoGu":sdo,"gichoGu":gicho,"dongs":dongs})
    return out


def main():
    allrows=[]
    for r in REGION_FILES:
        fp=f"/tmp/namu/{r}.html"
        if not os.path.exists(fp):
            print("missing", fp); continue
        rows=parse_region(open(fp,encoding="utf-8").read())
        for x in rows: x["region"]=r
        allrows.extend(rows)
        print(f"{r}: {len(rows)} rows")
    os.makedirs("_workspace",exist_ok=True)
    json.dump(allrows, open("_workspace/namu_districts_raw.json","w",encoding="utf-8"), ensure_ascii=False)
    print("총", len(allrows), "rows ->","_workspace/namu_districts_raw.json")
    # 표본
    for x in allrows[:4]: print(" ", x["sigungu"], "|시도",x["sdoGu"],"|기초",x["gichoGu"],"|",x["dongs"][:4])


if __name__=="__main__":
    main()
