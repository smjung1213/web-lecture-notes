# web-lecture-notes

한국어 강의노트·연습문제의 집필, 정보 표현, 조판, 검토 기준. 관리 배포 패키지 버전은 **0.6.14**이다. 버전 문구나 파일 전달만으로 배포·활성화·외부 모델 실행을 완료했다고 하지 않는다. 실제 강의자료·전사본·학습노트·인증정보는 이 저장소에 넣지 않는다.

기본 목표는 처음 배우는 학부생이 강의자료 PDF를 옆에 두고, 이번 노트와 이전 주차 노트만으로 개념·이유·중간 과정·조건을 복습하고 새 문제에 적용하는 것이다. 현재 사용자 지정이 우선하며 독자·선수지식·학습 방식·목표를 집필과 검토에 같은 구조화 learning_contract로 전달한다. 후속 검토의 자유문자 지시는 이 계약의 독자·목표를 다시 정의하지 않는다. 페이지·토큰 목표로 필요한 설명을 줄이지 않는다. 목적 없는 전문 확장은 제한하되 현재 위치에서 이해·복습·적용을 돕는 반복 설명은 보존한다. 원자료 파일 보존, 학습 정보 보존, 결과 PDF의 표현 방식은 서로 다르다. 수식은 MathJax로 조판하고, 직관적 이해를 돕는 원본 그림·도식과 읽기 좋은 표는 추출·크롭해 활용한다. 재작성은 실제 개선 이유가 있을 때 선택하며, 위치·길이·방향·색 묶음·단계 관계의 시각적 설명을 숫자·문장으로 대체하지 않는다.

0.6.14는 실행 환경이 바뀌어도 웹이 PDF 렌더 도구를 스스로 준비하게 한다. 렌더 도구(WeasyPrint 70.0·MathJax 3.2.1·Noto CJK KR 글꼴)가 없는 환경에서는 `scripts/offline_runtime.py`가 빠진 것만 알려 주고, Pro가 Drive 고정 파일(CPython 3.12/3.13 wheel, MathJax node_modules, 서브셋 글꼴)을 받아 새 폴더에 설치한다(runtime.md). 2026-10-04 Codex 런타임(CPython 3.12, 렌더 도구 없음)에서 조판이 막힌 일이 계기다. 그 밖의 지침·CSS는 0.6.13과 같다.

0.6.13은 제작 요청문의 경로 칸(Google Drive 위치·과목 Drive 폴더·이전 주차 학습노트)을 없앤다. Pro가 Drive 구조(`대학교/<학기>/<과목>/` 아래 강의 자료·강의 녹음·강의 노트·빌드)에서 원자료와 이전 주차 노트를 찾고, 없는 폴더는 없음으로 진행한다(SKILL.md ‘입력과 권한의 경계’). 그 밖의 지침·도구·CSS는 0.6.12와 같다.

0.6.12는 지침 문서의 중복을 줄인다. 같은 규칙이 여러 문서에 반복되던 곳은 소유 문서 한 곳에만 두고 나머지는 링크로 바꿨다(렌더러 선택·wheel 확보는 runtime.md, 글꼴·각주는 design.md, 전달 세트는 delivery.md). production-note.md의 다섯 검사는 검사마다 상태 하나로 적는다. 웹 SKILL·README·요청문에 남아 있던 로컬 후속 검토의 옛 설명은 한 문장으로 줄였다. 집필 기준·도구·CSS는 0.6.11과 같다.

이전 버전의 변경 내역은 저장소 커밋 기록에 있다. 같은 고정 커밋의 지침·도구를 함께 사용하며 제작 메모에 버전과 커밋을 기록한다. 기존 PDF·영수증·편집본은 보존하고 새 후보를 실제로 확인한다. 로컬 검토 코드는 이 웹 저장소에 포함하지 않는다.

## 시작과 입력

[범용 제작 요청](prompts/create-lecture-notes.md)의 맨 위에서 과목·주차·자료 범위를 채운다. 원자료 입력의 기본은 사용자가 연결한 **Google Drive 플러그인**이다. 과목·주차·파일명과 범위를 평소 말하듯 적으면 된다. Drive는 `대학교/<학기>/<과목>/` 아래 `강의 자료`·`강의 녹음`·`강의 노트`·`빌드` 구조이며, 경로를 따로 적을 필요는 없다. 독자 수준은 비전공자 또는 해당 분야를 처음 배우는 학부생, 학습 방식은 강의자료 PDF를 옆에 두고 이번 노트와 이전 주차 노트로 복습·이해·적용하는 기본값(`source_parallel`)을 그대로 사용한다. 매번 이 두 항목을 작성할 필요는 없다. 단계 체크포인트와 편집본 ZIP은 과목 폴더의 `빌드/`에 저장한다(SKILL.md S0). 검토를 마친 이전 주차 학습노트 PDF는 `강의 노트/<N주차>/`에 두면 Pro가 찾아 읽는다. 현재 사용자 지정이 기본값보다 우선한다. 특정 과목·주차의 사례, 이전 대화, 견본을 새 주차의 원자료에 자동 포함하지 않는다.

이전 공식본·채택 보완과 과목별 지시·미배포 기준 차이는 기본 입력란에 두지 않는다. 기존 노트 개정에 이전 보완을 이어받아야 하거나 공통 지침과 다른 특별 요청이 있을 때만 `추가 요청`에 관련 정보·지시를 적는다. 이를 별도로 지정하지 않은 새 제작에서 필수 입력으로 요구하지 않는다.

파일 목록·검색 발췌를 전문 읽기로 대신하지 않는다. 전사 전문과 지정 PDF의 실제 페이지·표·그림을 확보한다. 접근이 막힌 파일과 단계만 알리고 필요하면 그 파일의 직접 첨부를 요청한다. 이미 접근 가능한 파일의 재업로드, 같은 장애의 반복 호출, Chat 라이브러리로의 자동 전환은 요구하지 않는다. 막히지 않은 독립 작업은 계속한다.

GitHub 플러그인으로 기본 브랜치와 커밋을 확인한 뒤 그 커밋에서 아래 지침 문서의 전문을 읽는다. CSS·HTML 견본은 실제 사용할 구조·스타일·data-latex를 확인하며 파생 SVG/MathML 캐시의 전수 읽기는 요구하지 않는다. 잘린 응답은 이어 읽고 같은 리비전에서 이미 읽은 파일은 재사용한다. 확인한 커밋은 제작 메모에 한 번 기록한다. 필수 파일을 확보하지 못하면 그 파일에 의존하는 부분만 미확인으로 남기고 임의 재구성하지 않는다.

## 기준의 소유 파일

| 실제로 읽을 파일 | 담당 기준 |
|---|---|
| `skills/lecture-notes-chat/SKILL.md` | 입력·순서·source-inventory/coverage·산출물·완료 상태 |
| `skills/lecture-notes-chat/references/writing.md` | 독자·설명 깊이·원자료 의미 보존·표현 선택·정정·문제 타당성 |
| `skills/lecture-notes-chat/references/runtime.md` | 집필 전 환경·합성 PDF·격리 오프라인 설치·검증 한계 |
| `skills/lecture-notes-chat/references/design.md` | 시각 위계·수식/표/그림 마크업·조판·PDF 확인 |
| `skills/lecture-notes-chat/assets/lecture.css` | 재사용 기본 스타일. 주차별 변경은 `local.css` |
| `skills/lecture-notes-chat/assets/layout-sample.html` | 합성 구조·편집 가능한 LaTeX와 생성된 수식 캐시 |

`assets/layout-sample.pdf`, `sample-process.svg`, `sample-slide-crop.png`는 v3.4의 합성 견본이다. 원본 PDF 견본의 바이너리 접근이 안 되면 CSS/HTML로 진행하고 시각 확인 여부만 기록한다. 실제 생성한 PDF의 전 페이지 확인은 생략하지 않는다.

본격 집필 전 [runtime.md](skills/lecture-notes-chat/references/runtime.md)를 읽고 `scripts/preflight.py`로 현재 환경에서 합성 PDF를 만들어 두 페이지를 판독한다. 렌더러 선택과 런타임 준비(Drive 고정 파일)는 runtime.md를 따른다.

전달 직전 `references/delivery.md`, `scripts/delivery.py`, `scripts/delivery-requirements.txt`도 읽고 준비된 PDF를 한 번에 포장한다.

새 제작은 design.md의 디자인 기준 v3.4를 사용한다. 기존 노트·편집본은 동봉 lecture.css를 유지하며 새 CSS로 재조판·재출판하지 않는다.

관리 렌더러를 사용할 때는 `scripts/render.py`, `css_resources.py`, `typeset.cjs`, `package.json`, `package-lock.json`, `requirements.txt`도 읽는다. Python/WeasyPrint가 HTML 안의 JavaScript를 실행하는 경로가 아니다. 신뢰하는 Node 도우미가 LaTeX를 정적 SVG와 HTML용 MathML로 변환한 뒤 WeasyPrint에 넘긴다. 사용법·실제 검증 범위·검색/복사 및 접근성의 한계는 design.md를 따른다. 설치 설정 `.codex-plugin/plugin.json`, `agents/openai.yaml`은 배포 메타데이터이지 웹 대화의 모델·권한 변경 명령이 아니다.

## 제작과 후속 검토

웹에서 현재 선택된 Pro가 원자료 읽기 → 원자료 요소·학습 질문 파악 → 실제 환경·합성 PDF 확인 → 표현 선택과 설명·문제 집필 → 첫 PDF·편집본 → 다섯 자체 검사를 수행한다. 수식 재조판·표 재작성·의미 있는 통합은 coverage에 처리 유형, 원자료/최종 위치, 보존 대상과 짧은 대조 근거를 남긴다. 수식 재조판과 시각자료 보존은 따로 확인한다. 같은 숫자·식이 남아도 그림의 시각적 설명이 사라졌으면 완전 대응이 아니다.

이후 원자료·노트/문제집 PDF·편집 ZIP을 로컬 프로젝트에 두고 Claude Code에 ‘[과목] [주차] 검토해’라고 요청한다([로컬 검토 요청](prompts/review-lecture-notes.md)). 후속 검토·수정·공식 저장의 실행 계약은 로컬 `lecture-week`가 소유하며, 이 저장소는 CLI·계정·외부 모델을 설치하거나 사용 가능하다고 보증하지 않는다.

## 전달·보존·배포

웹 전달물은 [전달 도우미](skills/lecture-notes-chat/references/delivery.md)가 검증한 같은 새 폴더에서 제공하고, Drive에는 편집본 ZIP 하나만 올린다.

웹 전달물은 `<과목명> <N>주차 학습노트.pdf`, `<과목명> <N>주차 연습문제.pdf`, 같은 내용의 `<과목명> <N>주차 편집본.zip`이다. 표시 과목명의 띄어쓰기를 유지하고 N에는 앞자리 0을 붙이지 않는다. ZIP에는 HTML 두 개·CSS·사용 자산·input-contract.json·source-inventory.md·coverage.md·production-note.md 및 실제 재생성 방법을 넣는다. 수식이 있으면 LaTeX와 정적 캐시, 재생성 도우미·버전/의존성 안내도 포함한다. 폰트 파일·node_modules·원시 외부 로그·실제 강의 원자료를 지침 배포에 넣지 않는다.

원자료·받은 산출물·기존 공식본은 보존하며 새 수정 사본에서 작업한다. 웹은 다운로드 파일을 제공할 뿐 사용자 컴퓨터나 GitHub의 활성 파일을 갱신했다고 하지 않는다. 후속 로컬 검토의 공식 저장은 현재 요청과 로컬 저장 규칙을 따른다. 검토만/저장 금지 요청은 지키고, 이미 허용된 적용을 통상적인 구현 선택마다 재승인받지 않는다. 공식 갱신 전 이전 PDF/편집본을 보존·바이트 확인하고 두 PDF와 최신 편집 ZIP의 대응을 확인한다.

관리 원본은 `스킬/web-lecture-notes/`의 웹 스킬·메타데이터와 `웹 Chat 배포/GitHub/`의 README/prompts다. 관리 경로는 이 README와 웹 스킬의 링크로 확인한다. 과거 검토 패키지의 path-map.json은 당시 경로 대응을 설명하는 역사 자료다. 새 웹 자산·스크립트도 같은 소유 경로에 둔다. `스킬/제작 엔진/tools/package_web.py`의 명시적 허용 목록으로 지침만 배포하며, 렌더러는 로컬 도우미에서 관리 웹 원본을 재사용한다. 관리 원본·저장소·배포 ZIP의 바이트를 확인하고 과거 대형 다중 모델·원장 엔진을 다시 활성화하지 않는다.

로컬 관리자 검사는 작업공간에서 `스킬/제작 엔진/pyproject.toml`의 의존 환경을 사용한다. `python "스킬/web-lecture-notes/skills/lecture-notes-chat/scripts/render.py" <HTML> --check --ready`는 편집 자산·수식 캐시를 검사하고, `python -m lecture_tools pack <편집 폴더> <새 ZIP>`은 새 편집 ZIP을 검사·작성한다. 로컬 회귀는 `python -m pytest "스킬/제작 엔진/tests"`로 실행한다. 웹 지침 후보 포장은 `python "스킬/제작 엔진/tools/package_web.py" <새 staging> <새 ZIP>`이며 GitHub 게시와 별개다. 이 명령들은 웹 대화 작성자에게 로컬 파일 권한이 생겼다는 뜻이 아니다.
