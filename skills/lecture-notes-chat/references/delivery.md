# 웹 편집본의 전달 세트

이 절차는 웹에서 로컬 검토로 넘기는 편집본 ZIP 하나를 만든다. 웹은 PDF를 만들지 않는다. 로컬 lecture-week가 이 ZIP의 HTML을 WeasyPrint 70.0으로 처음 렌더해 기준 PDF로 쓴다. 전달 세트는 내용 검토·PDF 판독·공식 저장의 승인이 아니다.

## 실행

웹 제작에서는 S5에서 전달 세트를 만든다(SKILL.md ‘응답 하나로 끝까지 하고 단계마다 Drive에 저장한다’). 재개용 체크포인트(`checkpoint.py`)는 전달 세트가 아니다. `delivery.py`는 Python 표준 라이브러리만 쓰고 다른 스크립트 파일 없이 실행된다. HTML 검사 코드는 로컬 렌더러(`render.py`·`css_resources.py`)의 것과 같은 사본이다. WeasyPrint·BeautifulSoup·pypdf·MathJax는 필요 없다. 받은 묶음의 스크립트를 실행하지 않는다.

```sh
python scripts/delivery.py /작업/원고 /전달/handoff-01 \
  --revision 'W4-handoff-01' --file-prefix '수치해석 4주차' --status draft
```

출력 폴더는 새 경로이며 원고 폴더 밖에 둔다. `draft`는 내용 검토 미완료, `web-reviewed`는 웹 자체 검토 수행 상태다. 후자는 작성자가 실제 수행한 경우에만 선택하며 자동 내용 인증이나 로컬 검토 통과를 뜻하지 않는다.

입력은 `notes.html`, `workbook.html`, `lecture.css`, `input-contract.json`, `source-inventory.md`, `coverage.md`, `production-note.md`다. 선택 `local.css`, 자산 `assets/`, 실습 `practice/`, qa-summary/resume-note 및 자산·계산 기록을 함께 넣는다. 본문에서 참조하는 추가 실습 파일 등이 표준 위치 밖에 있으면 `--include practice_week4.py`처럼 원고 폴더 안 상대 파일을 명시한다. 추가 파일은 실행하지 않고 바이트 그대로 포함한다. PDF는 받지 않으며 `assets/`나 `--include`에 PDF가 있으면 멈춘다.

## 도구가 확인하는 것

- 두 HTML의 중복 ID, 문서 내부 링크, `<script>` 같은 능동 요소, 참조한 CSS·그림(CSS 안의 참조 포함)이 원고 폴더 안에 실제로 있는지. 결과의 `html_checks`에 자산 수와 `data-latex` 수식 수가 남는다.
- 새 ZIP을 다시 읽었을 때 모든 파일의 해시가 `delivery-manifest.json`(handoff_version 2)과 같은지.

페이지 하단 정정의 배치, 수식 변환, 글꼴, 실제 쪽은 로컬 렌더에서 확인한다. 이 도구의 통과를 그 확인으로 쓰지 않는다. ZIP 밖 `delivery.json`에는 ZIP의 SHA-256·크기와 HTML 검사 결과를 기록한다. 기존 입력 manifest는 덮어쓰지 않는다. 과거 PDF·원시 로그·판독용 이미지는 세트에 섞지 않는다.

## 올리기와 보고

성공한 새 전달 폴더의 편집본 ZIP만 Drive 이번 제작 폴더에 새 파일로 올린다. 전달 완료 판정과 최종 보고는 SKILL.md ‘전달과 후속 검토’를 따른다. 안내에는 전달 번호와 내용 검토 상태를 한 줄로 표시한다. 수정 후에는 새 전달 번호·폴더로 다시 만든다. 파일명은 과목·주차 규칙을 유지한다.

포장 이후 파일을 수정했다면 그 전달은 무효이며 새 폴더로 다시 만든다. 내용이 바뀌지 않은 포장 재검사 때문에 전체 내용 검토를 반복하지 않는다. 파일 일치는 원고의 정확성·설명 충분성·시각 가독성을 승인하지 않는다.
