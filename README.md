# web-lecture-notes

강의자료(PDF)와 강의 전사본으로 한국어 **학습노트**와 **연습문제**를 만드는 ChatGPT 웹 스킬이다. 한 번에 한 과목·한 주차를 다루며, 결과는 PDF가 아니라 편집할 수 있는 HTML·CSS·자산 묶음(편집본 ZIP)이다.

현재 버전은 **0.9.1**이다. 버전별 변경 내용은 커밋 기록에 있다.

> 개인 학습용으로 만든 작업 흐름이다. Google Drive 폴더 구조, 로컬 검토 단계 같은 전제가 이 사용 방식에 맞춰져 있다.

## 무엇을 목표로 하는가

처음 배우는 학부생이 개념과 그 이유, 중간 과정, 조건을 이해하고 새 문제에 적용할 수 있게 하는 것이 목표다. 평소에는 강의자료를 옆에 두고 대조하며 읽고, 시험 기간에는 노트만으로 복습할 수 있어야 한다.

- **핵심층과 펼침층으로 나눠 쓴다.** 핵심층은 강의자료의 내용과 교수가 그것을 풀어 준 설명이다. 분량은 숫자 목표 없이 교수가 둔 비중과 반복·보충 기준으로 정한다. 노트가 더한 보충, 수업 여담, 더 엄밀한 단서는 종류를 밝힌 펼침 블록에 둔다. 게시하는 학습노트 PDF는 펼침 블록을 숨긴 핵심판이고, 펼침 블록까지 보이는 전체판은 요청할 때만 만든다.
- **원자료의 의미를 지킨다.** 교수의 설명·이유·강조·예시를 교수 설명 단위로 파악해 본문에 반영하고, 교수가 강조한 것과 비중을 낮춘 것을 분량에 반영한다. 본문의 정정은 강의자료에 인쇄된 오류에만 붙인다. 원자료의 코드·의사코드는 원형 그대로 싣고, 오류가 확인된 경우에만 원형 뒤에 교정판을 따로 둔다.
- **역할에 맞게 표현한다.** 수식은 LaTeX로 적어 MathJax로 조판한다. 위치·방향·단계 관계를 보여 주는 원본 그림과 표는 필요한 영역을 잘라 그대로 쓰고, 시각적 설명을 숫자나 문장으로 대신하지 않는다.

## 작동 흐름

```
Google Drive 원자료 ─▶ ChatGPT 웹(Pro) 집필 ─▶ 편집본 ZIP ─▶ 로컬 검토·PDF 렌더 ─▶ 학습노트·연습문제 PDF
```

1. **집필(웹).** Pro가 이 저장소의 지침을 읽고 Drive의 원자료 전문을 읽은 뒤 학습노트·연습문제를 쓴다. 원자료 대조·계산·문장·이해의 네 가지를 자체 검토한 다음 편집본 ZIP 하나로 전달한다. 긴 작업 중 실행 환경이 초기화되는 경우에 대비해 단계마다 체크포인트를 Drive에 저장한다.
2. **검토와 PDF(로컬).** 받은 HTML을 WeasyPrint 70.0으로 렌더하고, 쪽마다 판독하면서 원자료와 다시 대조해 고친다. 이 단계의 도구와 절차는 이 저장소에 포함되어 있지 않다.

웹에서 PDF를 만들지 않는 이유는 대화마다 실행 환경이 달라 조판 결과를 보장할 수 없기 때문이다.

## 사용법

**준비물**

- GitHub와 Google Drive를 연결한 ChatGPT 웹
- Drive의 `대학교/<학기>/<과목>/` 아래에 `강의 자료`, `강의 녹음`(전사본), `강의 노트`, `빌드` 폴더
- Drive의 `대학교/웹 강의노트 스크립트/`에 버전별 실행용 ZIP(`web-lecture-notes-scripts-<버전>.zip`, 이 저장소의 `checkpoint.py`·`delivery.py`·`lecture.css`와 같은 바이트). ChatGPT 실행 환경이 GitHub에서 파일을 직접 받지 못해 Drive에서 받는다. 없으면 Pro가 저장소에서 가져와 쓴다

**요청**

1. 새 대화에 [`prompts/create-lecture-notes.md`](prompts/create-lecture-notes.md) 전체를 붙여 넣고 맨 위의 과목·주차·자료 범위를 채운다. 자료는 “02번 PDF ~p.18, 2주차 전사본 전체”처럼 평소 말로 적으면 된다.
2. 결과물인 `<과목명> <N>주차 편집본.zip`이 Drive의 `빌드/<N>주차/` 아래 이번 제작 폴더에 저장된다.
3. 응답이 전달 전에 끝나거나 ‘생각 실패’·연결 해제로 끊기면 **같은 대화에 ‘계속’만 보낸다.** Drive에 남은 마지막 단계 체크포인트에서 이어 간다. 새 대화로 처음부터 다시 시작하면 그동안의 작업을 쓰지 못한다.
4. 로컬 검토 요청은 [`prompts/review-lecture-notes.md`](prompts/review-lecture-notes.md)를 참고한다.

독자 수준과 학습 방식은 요청문의 기본값을 그대로 쓰면 된다. 이전 주차 학습노트를 `강의 노트/` 아래에 두면 선수지식을 확인하는 데 쓴다.

## 저장소 구성

| 파일 | 내용 |
|---|---|
| [`skills/lecture-notes-chat/SKILL.md`](skills/lecture-notes-chat/SKILL.md) | 입력, 작업 단계(S0–S5), Drive 체크포인트, 산출물, 완료 상태 |
| [`references/writing.md`](skills/lecture-notes-chat/references/writing.md) | 독자, 두 층과 분량, 원자료 의미 보존, 표현 선택, 정정, 문제의 타당성 |
| [`references/design.md`](skills/lecture-notes-chat/references/design.md) | 디자인 기준 v3.4: 시각 위계, 펼침 블록, 수식·표·그림 마크업, 조판 |
| [`references/delivery.md`](skills/lecture-notes-chat/references/delivery.md) | 편집본 ZIP 구성과 검사 |
| [`references/learning-contract.md`](skills/lecture-notes-chat/references/learning-contract.md) | 독자·선수지식·학습 방식·목표를 집필과 검토에 같게 전달하는 형식 |
| `assets/lecture.css`, `assets/layout-sample.*` | 기본 스타일과 합성 견본(HTML·PDF·그림) |
| `scripts/checkpoint.py`, `scripts/delivery.py` | 체크포인트 ZIP 생성·복원, 편집본 검사·포장. Python 표준 라이브러리만 쓰고 웹에서 쓰는 스크립트는 이 둘뿐이다 |
| `scripts/render.py`, `typeset.cjs` 외 | 로컬에서 PDF를 만드는 렌더러. LaTeX를 MathJax로 정적 SVG·MathML로 바꾼 뒤 WeasyPrint 70.0에 넘긴다(Python 의존성 `requirements.txt`, Node 18 이상 `package.json`) |
| `prompts/` | 웹 제작 요청문과 로컬 검토 안내 |

`.codex-plugin/plugin.json`과 `agents/openai.yaml`은 설치용 메타데이터다.

## 포함하지 않는 것

실제 강의자료·전사본·완성된 노트와 인증정보는 이 저장소에 넣지 않는다. 견본 HTML·PDF·그림은 모두 합성 자료다. 로컬 검토 도구도 포함하지 않는다.
