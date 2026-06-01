# 제9회 전국동시지방선거 투표 도우미

정치 성향을 진단하고, 주소지 후보와의 성향 일치도를 보여주는 단일 HTML 웹앱.

- 선거일: 2026-06-03
- 백엔드 없음 · 모바일 우선 · 모든 계산은 브라우저 내에서 수행(주소·응답 미전송)

## 기능

1. 18문항으로 5개 축(경제·사회·안보·환경·정부역할) 정치 성향 측정 → 레이더 차트
2. 주소 검색(Kakao) → 행정동 기준으로 해당 선거구 후보 자동 표시
3. 후보별 일치도(%)·레이더 비교·근거 축·실제 공약 표시

성향 산출:
- 시·도지사, 시·군·구청장, 교육감: 제출 공약을 5개 축으로 분석
- 지방의원: 공약 미제출 선거이므로 소속 정당 성향으로 대체(배지 표기)
- 무소속·정보 없음: 분석 불가 사유를 카드에 표시

## 데이터 출처

- 중앙선거관리위원회 OpenAPI (data.go.kr): 후보자 정보(15000908), 선거공약 정보(15040587)
- 선거구–행정동 매핑: 공직선거법·시도 조례 기반 정리 자료

후보 성향 점수는 공약·정당 정책에 근거한 추정치이며 참고용이다.

## 빌드

`index.html`은 `template.html`에 데이터를 주입해 생성한다. 데이터 갱신 시:

```bash
KEY=data.go.kr_서비스키   # 후보자·선거공약 API 활용신청 후 발급

python3 .claude/skills/nec-data-pipeline/scripts/fetch_nec.py --key "$KEY"        # 후보자
python3 .claude/skills/nec-data-pipeline/scripts/fetch_pledges.py --key "$KEY"     # 공약
python3 build_site.py                                                              # index.html 생성
```

## 배포

`index.html` 한 파일만 정적 호스팅하면 동작한다.

```bash
git add index.html README.md LICENSE
git commit -m "deploy"
git push
# GitHub 저장소 Settings → Pages → Source: main / root
```

Kakao 지도 SDK는 도메인 제한 JavaScript 키를 사용한다. 배포 도메인을 [Kakao Developers](https://developers.kakao.com) 콘솔의 Web 플랫폼에 등록해야 한다.

## 구조

```
index.html        배포물(데이터 임베드, 단일 파일)
template.html     앱 템플릿
build_site.py     빌드 스크립트
.claude/          제작용 에이전트·스킬·데이터 파이프라인(배포 불필요)
```

## 라이선스

Apache License 2.0 — [LICENSE](LICENSE) 참조.

선거 데이터의 저작권은 중앙선거관리위원회 등 원저작자에 있으며, 본 라이선스는 코드에 적용된다.
