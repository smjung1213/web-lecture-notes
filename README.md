# web-lecture-notes

한국어 강의노트용 제작 지침·디자인·선택적 렌더링 도우미. 현재 배포 버전은 **0.4.0**이다. 웹 일반 Chat에서 사용자가 선택한 Pro가 최초 제작하고, Codex Astra Medium이 후속 검토·필요한 수정을 맡는다. 현재 사용자 지정 모델·추론 수준이 기본값보다 우선한다. 역할 분담이나 모델 수만으로 독립 검증·정확성을 보증하지 않는다. 강의자료·전사본·실제 학습노트·인증정보는 이 저장소에 포함하지 않는다.

0.4.0은 지정 시각자료·해설과 수식·유도를 모두 보존하고, 독자/범위 계약과 원자료 선행 목록을 추가한다. 부수 전문 확장과 반복만 줄이고 필요한 설명은 분량 목표로 축약하지 않는다. 공통 내용 기준은 `writing.md`, 실행·coverage는 웹 `SKILL.md`, 조판은 `design.md`, 후속 검토는 로컬 `lecture-week/SKILL.md`가 맡는다.

선택 읽기와 별도 응용·심화 문제는 자동 추가하지 않는다. 기본 문제에서도 이유·새 값 적용·조건 판단을 확인하며, 자체 제작 문항을 이유로 본문에 전문 내용을 늘리지 않는다. Codex 검토는 필요한 설명의 누락과 불필요한 확장·중복을 함께 판단하고 근거 있는 깊이 조절을 자동으로 되돌리지 않는다. 계산·정정의 정확성, 원자료 판독, 다섯 검사와 전 페이지 PDF 확인은 유지한다.

## Chat에서 파일 기반으로 사용

웹 Pro 대화에 Google Drive 앱/플러그인을 연결하고, 강의 PDF·전사본 TXT/MD가 있는 폴더 또는 파일 링크와 과목·주차·페이지 범위를 지정한다. [범용 제작 프롬프트](prompts/create-lecture-notes.md)를 함께 사용한다. 파일 링크 대신 과목·주차·파일명으로 대상을 명확히 지정해도 된다. 과목별 입력은 요청에 담고 공통 기준은 아래 소유 파일에서 읽는다. 실제 사용 모델과 도구는 실행 환경의 선택을 따르며 웹 표시명이나 내부 설정을 추측하지 않는다.

Drive에서 전사 전문과 PDF의 실제 페이지·표·그림을 읽고 원본 그림을 활용할 수 있는지 확인한다. 검색 결과나 추출 텍스트만 확보한 상태는 PDF 시각 확인 완료가 아니다. 같은 장애를 반복 호출하지 말고 접근 불가 파일·단계를 밝힌 뒤 그 파일만 직접 첨부한다. 사용자가 다른 입력을 명시하면 그 요청이 우선한다.

이 방식은 네이티브 스킬 설치가 아니라 사용자가 요청한 파일 기반 지침 적용이다. GitHub 연결은 모델이나 PDF 생성 도구를 추가하지 않는다. 강의 자료와 결과를 이 저장소에 쓰지 않는다.

프로젝트 안에서도 같은 방식을 사용한다. 과목·주차와 사용할 자료를 지정하고, 다른 주차의 소스와 이전 대화 내용을 이번 강의의 원자료로 자동 포함하지 않는다. 이미 접근 가능한 파일은 재업로드를 요구하지 않으며, 전문이나 표·그림을 읽을 수 없는 파일만 추가 제공을 요청한다. 프로젝트의 문체 지침은 함께 적용한다.

### 실제로 읽을 파일

먼저 SKILL.md를 읽고, 집필 전 writing.md, 조판 전 design.md와 CSS·HTML의 전문을 읽는다. 같은 리비전에서 이미 읽은 내용은 재사용한다. 경로는 저장소 루트 기준이다.

1. `skills/lecture-notes-chat/SKILL.md`: 작업 범위, 내용 대조, 산출물.
2. `skills/lecture-notes-chat/references/writing.md`: 이해 중심 집필, 보충의 필요·중단 기준, 정정과 문제 타당성.
3. `skills/lecture-notes-chat/references/design.md`: 조판과 실제 PDF 확인 기준.
4. `skills/lecture-notes-chat/assets/lecture.css`: 출력에 재사용할 기본 스타일.
5. `skills/lecture-notes-chat/assets/layout-sample.html`: 재사용할 구조 예시. 합성 본문을 강의 내용으로 쓰지 않는다.

Python+WeasyPrint로 렌더링할 때는 `skills/lecture-notes-chat/scripts/render.py`와 `scripts/requirements.txt`(같은 스킬 폴더 아래)를 추가로 가져온다. 기존 환경을 우선 사용하며 특정 렌더러 설치를 반복하지 않는다. 설치용 `.codex-plugin/plugin.json`과 `agents/openai.yaml`은 일반 Chat 제작에 필요한 읽기 대상이 아니다.

### 접근과 작업의 경계

- 파일 목록이나 검색 발췌는 전문 읽기를 대신하지 않는다. 잘린 응답은 제공되는 행 범위/파일 읽기 기능으로 끝까지 이어 읽는다. 필수 파일을 끝내 확보하지 못하면 해당 파일의 직접 첨부를 요청하고 임의로 지침을 재구성하지 않는다.
- 읽은 리비전을 제공 도구로 확인할 수 있으면 짧은 제작 메모에 한 번 기록하고 같은 리비전을 사용한다. 확인할 수 없는 값을 추측하지 않는다. 지침 전체의 별도 해시 보고서·원문 회수 ZIP·접근성 인증서를 중복 생성할 필요는 없다. 원자료 식별·독자·범위는 input-contract.json에 기록한다.
- `assets/layout-sample.pdf`는 선택적 견본이다. GitHub의 바이너리 접근이 불가능하면 반복 다운로드를 시도하지 말고 확보한 CSS·HTML과 디자인 지침으로 진행한다. 견본을 시각적으로 확인하지 못했다는 사실만 메모하고, 실제 생성한 PDF는 직접 확인한다.
- 원자료·계획·본문 대조와 문항 및 PDF 확인은 유지한다. 웹 최초 제작에 로컬 검증 엔진·대형 provenance 체계·모든 문자 빈도 일치 검사·이유 없는 복수 렌더러 반복을 강제하지 않는다. input-contract/source-inventory와 후속 로컬 결과 계약은 별도 역할이다. 관찰된 문제를 수정하고 영향받은 부분을 다시 확인하면 된다.
- 학습에 필요한 조건은 본문에, 환경·실행·검증 이력은 제작 메모에 둔다. 짧은 안내만 남는 꼬리 페이지와 해설 분리는 레이아웃 조정으로 줄이고, 이를 위해 필요한 이유·조건·풀이를 삭제하지 않는다. 불필요한 확장·반복의 축소는 writing.md에 따른다.

## 배포 파일 목록

- `.codex-plugin/plugin.json`
- `skills/lecture-notes-chat/SKILL.md`
- `skills/lecture-notes-chat/agents/openai.yaml`
- `skills/lecture-notes-chat/references/writing.md`
- `skills/lecture-notes-chat/references/design.md`
- `skills/lecture-notes-chat/assets/lecture.css`
- `skills/lecture-notes-chat/assets/layout-sample.html`
- `skills/lecture-notes-chat/assets/layout-sample.pdf`
- `skills/lecture-notes-chat/scripts/render.py`
- `skills/lecture-notes-chat/scripts/requirements.txt`

PDF 견본은 합성 디자인 자료이지 실제 강의 원자료가 아니다. 파일 바이트 획득, 지침 전문 읽기, PDF 시각 확인, 지침을 따른 제작은 서로 다른 검증 항목이다. 권한·파일 도구 제한을 우회하기 위해 인증정보를 요청하거나 공개 저장소로 전환하지 않는다.

## 후속 검토와 두 심화 개념

웹 일반 Chat의 Pro는 원자료 검토·집필·문제·첫 PDF·편집본을 만든다. 이후 사용자가 강의 PDF·전사본·결과 PDF 두 개·편집 HTML/CSS/이미지·input-contract.json·source-inventory.md를 Codex에 전달하면 Astra Medium 부모가 대조·수정·최종 확인을 책임진다. 외부 검토를 사용하는 로컬 구성에서는 검증된 Claude Code 또는 Gemini를 사용하는 AGY가 원자료만의 목록 작성 → 원고 대조 → 수정 부분 재확인을 맡고, Codex가 근거와 최종 판단을 책임진다. 기본은 검증기 1개이며 중요한 미해결 충돌 등에만 대체·추가 검증기를 사용한다. 이용 가능한 검증기가 없으면 Codex가 직접 검토하고 외부 검토 미실시를 기록한다. 실행·결과 정리는 별도 코드가 맡고 Codex에는 최종 결과와 필요한 근거만 전달한다. 이 웹 지침 배포는 로컬 실행기를 설치·검증·활성화하지 않는다. 외부 검토의 접근 제한·모델·시각 판독 등이 검증되지 않은 구성은 비활성 상태로 유지한다. 웹 지침 ZIP에는 로컬 실행기·인증·원자료를 넣지 않는다. [Codex 검토 요청](prompts/review-lecture-notes.md)은 일반적인 한 문장 요청을 위한 상세 기준도 담는다. 해당 로컬 프로젝트의 lecture-week 스킬이 필요한 수정·PDF 확인·완성본 저장까지 처리한다. “검토만” 또는 “수정하지 마”라고 명시하면 읽기와 보고만 한다. 원자료와 편집본은 첨부하거나 이미 접근 가능한 경로에 있어야 한다.

내용 기준 `writing.md`는 본문에 필요한 깊이를 정하고, 선택 읽기와 별도 응용·심화 구역은 필요할 때만 허용한다. 제공한 기본/강의 범위 응용 문항은 선택 읽기에 의존하지 않는다. 범위 내 원자료 시각자료와 실제 값·관계·설명을 모두 보존한다. 설명에서 대표값을 선택할 수 있지만 원본 표의 일부만 남기는 뜻은 아니다. 새 전문 확장·반복의 축소는 목적과 이유를 coverage.md에 기록한다.

로컬 관리 원본은 웹 스킬 폴더와 배포 README/prompts다. 저장소와 배포 ZIP은 관리 원본에서 동기화하며 저장소 쓰기는 사용자가 허용한 작업 범위에서 수행한다. 웹 Chat은 다운로드할 첫 산출물을 제공하고 사용자 컴퓨터의 공식 저장 위치를 변경했다고 주장하지 않는다. Codex의 후보 전달·공식 저장 범위는 현재 요청과 로컬 프로젝트 지침을 따른다. 후보 전달까지만 요청되면 PREPARED로 남기고, 공식 저장까지 허용된 경우에는 기존 PDF와 최신 편집 ZIP을 보존·해시 확인한 뒤 같은 revision으로 갱신한다. 이미 허용된 저장을 재승인받도록 요구하지 않는다. PDF 두 개와 편집 ZIP의 대응·이전본 보존을 확인하며, 파일 도우미의 복사·추출·검사·렌더·포장 기능은 계속 사용한다. 이전의 대형 다중 모델·원장 엔진을 다시 가동하는 뜻은 아니다.

지침 정리 근거는 OpenAI의 [Astra 프롬프팅 안내](https://developers.openai.com/api/docs/guides/latest-model/gpt-6-astra.md#prompting-best-practices)와 [추론 모델 프롬프팅 기준](https://developers.openai.com/api/docs/guides/reasoning-best-practices#how-to-prompt-reasoning-models-effectively)다. API 전용 설정을 웹 Chat·Codex의 실행 설정으로 옮기지 않으며, 공식 문서의 일반 권고가 이 프로젝트의 필수 원자료·PDF 검사를 대체하지 않는다.
