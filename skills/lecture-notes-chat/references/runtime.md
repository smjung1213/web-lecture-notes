# 집필 전 조판 환경 확인

본격 집필에 들어가기 전에 현재 실행 환경과 작은 합성 PDF를 확인한다. 환경 검사가 막혀도 원자료 확보·범위 계약·inventory 등 독립 작업은 계속한다. 다만 조판 미확인을 숨긴 채 첫 PDF 완성을 약속하지 않는다. 이미 검증한 같은 환경·도구·CSS·글꼴을 그대로 쓰면 결과 경로·해시를 production-note.md에 연결해 재사용한다. 환경이나 해당 입력이 바뀌면 새 경로에서 다시 시험한다.

## 렌더러 선택

공식 PDF의 렌더러는 WeasyPrint 70.0이다. 로컬 lecture-week가 최종본을 70.0으로 다시 렌더하고 저장하므로, 웹 PDF는 첫 전달용이다. 웹은 실제로 관측한 환경으로 다음 순서에 따라 고른다.

1. 현재 환경의 preflight가 공식 모드로 통과하면 그대로 쓴다.
2. 미리 설치된 68.0 환경이면 설치하지 않고 `--draft-renderer` preflight를 시도한다. 통과하면 초안 모드로 진행한다(영수증 `renderer_mode: draft`). 68.0은 70.0보다 수식(SVG)이 작고 줄바꿈이 조금 다를 수 있다. 쪽별 판독은 실제 초안 PDF로 하고 최종 배치는 로컬 70.0에서 다시 본다.
3. 그 밖의 경우는 아래 ‘Drive 고정 파일로 런타임 준비’로 70.0 런타임을 스스로 준비한다. WeasyPrint·MathJax·Noto 글꼴 중 하나라도 없거나, 70.0이 다른 패키지 버전 차이(`RENDERER_VERSION_MISMATCH`, `PREFLIGHT_DEPENDENCY_MISMATCH`)로 막히는 경우가 여기에 든다.

그 밖의 버전으로 자동 전환하지 않는다. 고른 렌더러·모드와 이유를 production-note.md에 적는다.

## 현재 환경을 먼저 사용

같은 고정 Git 커밋의 scripts와 assets를 실제 파일로 확보한다. GitHub 문서 읽기 성공은 스크립트·PNG·ZIP의 바이트 전달 성공을 보장하지 않는다. preflight의 합성 그림 sample-slide-crop.png를 실제 이미지 바이트로 받지 못하면 preflight가 같은 구성의 합성 그림을 직접 그리고 결과에 `sample_png: generated`로 남긴다. 이 그림 때문에 첨부를 요청하지 않는다. Drive나 대화에 남은 이전 버전의 소스 ZIP·스크립트를 지침·도구로 쓰지 않는다. 현재 Python 실행 파일·플랫폼·Python/WeasyPrint 버전·glibc, Noto Serif CJK KR·Noto Sans CJK KR·Noto Sans Mono CJK KR, Node 18+·MathJax 3.2.1의 실제 상태를 확인한다. MathJax가 이미 다른 위치에 있으면 실제 확인한 디렉터리만 MATHJAX_MODULE_ROOT로 지정한다.

```sh
# python은 이번 작업에서 관측한 동일 실행 파일의 절대 경로로 바꾼다.
python -B scripts/preflight.py --output /새/조판시험
# 기본 환경이 68.0이면(초안 모드): python -B scripts/preflight.py --output /새/조판시험 --draft-renderer
```

preflight.py는 설치하지 않는다. 실제 WeasyPrint import(공식 70.0, 초안 모드는 68.0도), 필수 Python 버전, 네이티브 라이브러리·글꼴·MathJax, 캐시 재생성 비교를 검사하고 assets/preflight.html과 관리 CSS·그림을 새 폴더에 복사하여 synthetic.pdf 2쪽을 만든다. 두 페이지에는 수식·두 줄 물결·그림·표·코드와 페이지 하단 정정 두 개가 있다. PDF 본문의 정정 문장·호출과 같은 쪽·배치·링크 영역도 구조적으로 검사한다. 실패는 preflight-result.json의 INCOMPLETE와 오류로 남으며 기존 출력 경로를 덮어쓰지 않는다. require_renderer는 메타데이터와 실제 WeasyPrint import를 검사하고 요구 버전 불일치를 PDF 생성 전에 차단한다.

자동 검사 통과 후 **새 PDF 두 페이지를 각각 판독**해 한글·수식·물결 간격·그림/캡션·표/코드·각주·잘림/겹침을 확인한다. preflight-result.json의 NOT_PERFORMED는 자동 도구가 시각 판독을 하지 않았다는 뜻이다. production-note.md에 결과 해시, 실제 판독 페이지와 판정·미확인을 별도로 남긴다. 기존 증거 파일의 플래그를 고쳐 완료로 만들지 않는다. 성공 후 같은 Python 실행 경로와 환경 변수, 같은 모드(초안이면 `--draft-renderer`)로 실제 원고를 렌더한다. 합성 시험은 강의 내용 검토나 최종 PDF 전 페이지 검토를 대신하지 않는다.

## Drive 고정 파일로 런타임 준비

실행 환경이 바뀌어도 웹이 스스로 70.0 런타임을 만든다. 필요한 파일은 사용자의 Google Drive에 고정 파일로 있고, 파일명·크기·SHA-256·Drive 파일 ID는 관리 원본 `scripts/offline/`의 JSON(`attachment.json`, `cp312/attachment.json`, `mathjax.json`, `fonts.json`)에 있다.

| 파일 | 내용 |
|---|---|
| `weasyprint70-linux-x86_64-cp313-wheels-r01.zip` | CPython 3.13용 공식 wheel 17개 |
| `weasyprint70-linux-x86_64-cp312-wheels-r01.zip` | CPython 3.12용 공식 wheel 17개 |
| `mathjax-3.2.1-node-modules-r01.zip` | `package-lock.json`대로 설치한 MathJax 3.2.1 node_modules |
| `noto-cjk-kr-subset-fonts-r01.zip` | Noto Serif·Sans·Sans Mono CJK KR 서브셋(OFL) |

1. 인수 없이 먼저 실행한다. 이미 있는 것은 다시 받지 않도록, 결과의 `required_files`에 이 환경에서 빠진 파일만 나온다.

   ```sh
   python -B scripts/offline_runtime.py --output /새/런타임-1
   ```

2. 나온 파일만 연결된 Drive 도구의 원본 파일 다운로드(예: `fetch`의 `download_raw_file=true`)로 파일 ID에서 직접 받는다. Drive 전체나 과목 폴더를 탐색하지 않는다. 파일 목록·메타데이터·미리보기는 바이너리 확보가 아니다. 실제 파일의 크기·SHA-256을 확인했을 때만 확보로 기록한다.
3. 새 출력 폴더로 다시 실행한다. `node`가 PATH에 없으면 관측한 Node 18+ 실행 파일을 `--node`로 준다.

   ```sh
   python -B scripts/offline_runtime.py --output /새/런타임-2 \
     --archive /받은/weasyprint70-…-wheels-r01.zip \
     --mathjax-archive /받은/mathjax-3.2.1-node-modules-r01.zip \
     --fonts-archive /받은/noto-cjk-kr-subset-fonts-r01.zip
   ```

4. `result.json`이 `AUTOMATED_CHECKS_PASSED_VISUAL_REVIEW_REQUIRED`이면 합성 PDF 두 쪽을 위와 같이 판독한다. 이후 렌더·전달 명령에는 `runtime_command_prefix`(설치했으면 `python -B -S`)와 `runtime_environment`(`PYTHONPATH`, `MATHJAX_MODULE_ROOT`, `FONTCONFIG_FILE`, 필요하면 `PATH`)를 그대로 붙인다. 일반 python으로 돌아가면 기본 패키지를 읽는다.

   ```sh
   PYTHONPATH=… MATHJAX_MODULE_ROOT=… FONTCONFIG_FILE=… /실제/python -B -S scripts/render.py /작업/notes.html /새/notes.pdf
   ```

도구는 각 ZIP의 크기·SHA-256을 관리 값과 대조한 뒤에만 새 폴더에 푼다. wheel은 관리 해시로 다시 검사하고 `--no-index --only-binary=:all: --require-hashes --target`으로 새 site-packages에만 설치한다. 글꼴은 새 폴더의 `fonts.conf`로만 보이게 하며 시스템 글꼴 설정과 기본 Python은 바꾸지 않는다(설치 전후 비교를 result.json에 남긴다). ZIP 안의 코드를 실행하지 않는다. 지원 범위는 Linux x86_64, CPython 3.12/3.13, glibc 2.28 이상, 시스템 Pango·Fontconfig가 있는 환경이다. 그 밖이면 `TARGET_MISMATCH` 등 관측 오류를 기록하고 조판을 미완료로 둔다.

다운로드가 막힌 파일만 관측한 오류를 한 번 기록하고 그 파일의 직접 첨부를 요청한다. 같은 실패 반복, 공개 공유 전환, 토큰·쿠키 요구, PyPI·npm 온라인 설치, 다른 서비스 우회는 하지 않는다. 응답 도중 런타임 폴더가 사라지면 남은 ZIP으로(없으면 다시 받아) 새 폴더에서 같은 절차를 반복한다.

서브셋 글꼴은 로컬 공식 렌더가 쓰는 같은 KR 글꼴에서 한글·라틴·기호·KS X 1001 한자 범위만 남긴 것이다. 글꼴 이름·굵기·글자 폭은 같다(2026-10-04 2주차 원고 렌더에서 쪽수와 단어 위치가 전체 글꼴과 일치). 이 범위 밖의 드문 문자는 빈 상자로 보일 수 있으므로 PDF 판독에서 발견하면 표시 결함으로 기록한다. Serif Medium·SemiBold는 묶음에 없어 500·600 굵기가 Regular·Bold로 표시될 수 있다. 이는 웹 초안의 차이이며 로컬 70.0에서 다시 확인한다.

GitHub의 비공개 Release(`weasyprint70-wheels-r01`)는 cp313 wheel ZIP의 관리 보관 원본이며 웹 실행 환경에서는 내려받지 못한다(아래 ‘증거와 한계’). `fetch_runtime.py --download`는 그 Release에 HTTPS 요청을 한 번 보내는 관리용 옵션이며 웹 확보 경로가 아니다. wheel·MathJax·글꼴 ZIP은 편집 ZIP에 동봉하지 않는다. 제작 메모에는 Python·MathJax·글꼴 경로, 격리 여부, 버전·해시와 사용한 고정 파일 이름을 기록한다.

## 증거와 한계

2026-09-30 웹 시험에서는 위 17개 wheel의 격리 설치·실제 70.0 import·MathJax 캐시 비교·관리 렌더러의 2쪽 합성 PDF 생성이 성공했다. 기본 68.0과 검사 대상 18개 패키지의 1,356개 파일은 보존됐다. 설치 stderr의 camelot-py/moviepy에 대한 pypdf/Pillow 충돌 경고는 숨기지 않는다. 이 두 프로그램은 격리 런타임에 없었으며 해당 프로그램과의 호환성은 시험하지 않았다. 68.0 최초 설치 주체는 미확인이다. 앞선 온라인 설치 실패에서 관측한 원인은 PyPI DNS 이름 해석 실패였고 70.0 미지원 근거가 아니었다. 68.0의 `://` 기준 프로토콜 판별은 file/data 제한에서 물결 SVG data URI를 거부했지만 70.0에서는 성공했다.

2026-09-30 별도 새 대화의 0.6.3 시험에서 첨부 없는 GitHub 단계는 Release를 내려받지 못해(URL 사전 조회 조건 오류, 브라우저 열기 비활성, github.com 이름 해석 실패, GitHub 커넥터는 메타데이터만 제공) 설치·PDF 없이 미완료였다. HTTP 401/403/404는 관측되지 않았다. 같은 대화의 Drive 단계에서는 파일 ID로 소스 ZIP·wheel ZIP·manifest를 실제로 받아 해시가 일치했고, 17개 wheel 격리 설치, 2쪽 PDF 3개 생성·판독, 관리 전달 ZIP 포장, 부정 검사 11개 통과를 웹이 보고했다. 요청문에 없던 manifest의 SHA-256(`982d5ecb…be64d`, 820바이트)이 로컬 원본과 일치해 Drive 바이트 확보는 로컬에서 따로 확인됐다. 증거 ZIP·PDF는 Chat 다운로드 실패로 로컬 검증하지 못했다. 한 세션의 결과를 모든 세션·계정의 성공 보장으로 확대하지 않는다.

첫 웹 증거는 승격 전 설치 경로·동일 wheel과 합성 입력을, Drive 단계는 0.6.3 관리 도구의 웹 실행을 보고한다. 0.6.5의 준비 HTML 고정점 수정은 로컬에서만 검증했다. 로컬 검증과 웹 보고를 구분한다. 실제 Chat PDF 뷰어의 클릭·검색/복사·접근성 시험은 미완료다. 0.6.3 시험의 컨테이너 Chromium은 root 실행 제한으로 시작하지 못했으며 이를 Chat 뷰어의 제한으로 보지 않는다. 구조 검사와 실제 뷰어 검사를 구분하며 별도 우회 작업을 요구하지 않는다.

2026-10-02 로컬(macOS)에서 보관된 68.0 사본으로 관리 렌더러를 시험했다. 고치기 전에는 위의 data URI 거부로 실패했고, render.py가 file/data 스킴을 직접 검사하도록 바꾼 뒤에는 견본 9쪽, preflight 2쪽, 4주차 노트 49쪽·연습문제 30쪽이 70.0과 같은 쪽수와 같은 페이지 하단 정정 배치로 만들어졌다. 차이는 수식 SVG가 작게 나오는 것과 일부 줄바꿈(노트 1쪽)이었다. 웹 Linux의 68.0 초안 모드는 이 시험 뒤에 처음 쓰며, 그 결과는 별도로 확인한다.

물결 간격의 기존 v3.4 기준은 Poppler 300dpi, 빨강 R>130·R>1.5G·G<130·B<130, 어두운 글자 max(RGB)<120으로 검출한 픽셀 행 중심 간 거리다. 이번 웹 PDF를 같은 방식으로 재측정한 위 간격은 0.4233/0.3387mm, 주기는 13.7994/13.8001pt로 기존 검사를 통과했다. 웹 보고서의 600dpi 빈 픽셀 수 기준 0.25–0.30mm와 직접 비교하지 않는다. 해상도·색 임계값·거리 정의를 함께 기록하며 연속적인 실제 경계 간격을 확정하거나 이 차이만으로 CSS를 바꾸지 않는다.

2026-10-04 시스템 프로그래밍 2주차 웹 제작은 Codex 런타임(`/opt/codex/runtimes/codex-primary-runtime`, CPython 3.12.14, glibc 2.39, Node v24.19.0)에서 실행됐다. 이 환경에는 WeasyPrint·MathJax·Noto 글꼴이 없었고 cp313 wheel만으로는 설치할 수 없어 조판이 미완료였다. 이 때문에 cp312 wheel·MathJax·글꼴 고정 파일을 추가했다. 새 경로의 Linux 실제 설치는 웹 시험으로 확인한다. 로컬(macOS)에서는 MathJax·글꼴 설치와 합성 PDF, cp312/cp313 해시 고정 의존성 해석만 확인했다.
