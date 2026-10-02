# 집필 전 조판 환경 확인

본격 집필에 들어가기 전에 현재 실행 환경과 작은 합성 PDF를 확인한다. 환경 검사가 막혀도 원자료 확보·범위 계약·inventory 등 독립 작업은 계속한다. 다만 조판 미확인을 숨긴 채 첫 PDF 완성을 약속하지 않는다. 이미 검증한 같은 환경·도구·CSS·글꼴을 그대로 쓰면 결과 경로·해시를 production-note.md에 연결해 재사용한다. 환경이나 해당 입력이 바뀌면 새 경로에서 다시 시험한다.

## 렌더러 선택

공식 PDF의 렌더러는 WeasyPrint 70.0이다. 로컬 lecture-week가 최종본을 70.0으로 다시 렌더하고 저장하므로, 웹 PDF는 첫 전달용이다. 웹은 실제로 관측한 버전으로 다음 순서에 따라 고른다.

1. 현재 환경이 70.0이면 그대로 쓴다(공식 모드).
2. 미리 설치된 68.0이면 설치하지 않고 초안 렌더러로 쓴다. preflight.py·render.py에 `--draft-renderer`를 붙인다. 영수증에 `renderer_mode: draft`가 남는다. 68.0은 70.0보다 수식(SVG)이 작게 나오고 줄바꿈이 조금 달라질 수 있다. 쪽별 판독은 실제로 만든 초안 PDF로 하고, 최종 배치는 로컬 70.0 렌더에서 다시 확인한다.
3. 둘 다 아니면 아래 오프라인 설치로 70.0을 준비한다.

그 밖의 버전으로 자동 전환하지 않는다. 고른 렌더러·모드와 이유를 production-note.md에 적는다.

## 현재 환경을 먼저 사용

같은 고정 Git 커밋의 scripts와 assets를 실제 파일로 확보한다. GitHub 문서 읽기 성공은 스크립트·PNG·wheel·ZIP의 바이트 전달 성공을 보장하지 않는다. preflight의 합성 그림 sample-slide-crop.png를 실제 이미지 바이트로 받지 못하면 preflight가 같은 구성의 합성 그림을 직접 그리고 결과에 `sample_png: generated`로 남긴다. 이 그림 때문에 첨부를 요청하지 않는다. Drive나 대화에 남은 이전 버전의 소스 ZIP·스크립트를 지침·도구로 쓰지 않는다. wheel ZIP은 위 3번에서만 필요하다. 아래 고정 Google Drive 파일을 연결된 Drive 도구로 실제 내려받고, 막힌 경우에만 직접 첨부를 요청한다. 현재 Python 실행 파일·플랫폼·아키텍처·Python/WeasyPrint 버전·glibc, Noto Serif CJK KR·Noto Sans CJK KR·Noto Sans Mono CJK KR, Node 18+·MathJax 3.2.1의 실제 상태를 확인한다. 폰트·Node/MathJax·Pango/Fontconfig는 아래 Python wheel 묶음에 없으며 자동 설치하지 않는다. MathJax가 이미 다른 위치에 있으면 실제 확인한 디렉터리만 MATHJAX_MODULE_ROOT로 지정한다.

```sh
# python은 이번 작업에서 관측한 동일 실행 파일의 절대 경로로 바꾼다.
python -B scripts/preflight.py --output /새/조판시험
# 기본 환경이 68.0이면(초안 모드): python -B scripts/preflight.py --output /새/조판시험 --draft-renderer
# 필요할 때만: MATHJAX_MODULE_ROOT=/실제/node_modules/mathjax-full
```

preflight.py는 설치하지 않는다. 실제 WeasyPrint import(공식 70.0, 초안 모드는 68.0도), 필수 Python 버전, 네이티브 라이브러리·글꼴·MathJax, 캐시 재생성 비교를 검사하고 assets/preflight.html과 관리 CSS·그림을 새 폴더에 복사하여 synthetic.pdf 2쪽을 만든다. 두 페이지에는 수식·두 줄 물결·그림·표·코드와 페이지 하단 정정 두 개가 있다. PDF 본문의 정정 문장·호출과 같은 쪽·배치·링크 영역도 구조적으로 검사한다. 실패는 preflight-result.json의 INCOMPLETE와 오류로 남으며 기존 출력 경로를 덮어쓰지 않는다. require_renderer는 메타데이터와 실제 WeasyPrint import를 검사하고 요구 버전 불일치를 PDF 생성 전에 차단한다.

자동 검사 통과 후 **새 PDF 두 페이지를 각각 판독**해 한글·수식·물결 간격·그림/캡션·표/코드·각주·잘림/겹침을 확인한다. preflight-result.json의 NOT_PERFORMED는 자동 도구가 시각 판독을 하지 않았다는 뜻이다. production-note.md에 결과 해시, 실제 판독 페이지와 판정·미확인을 별도로 남긴다. 기존 증거 파일의 플래그를 고쳐 완료로 만들지 않는다. 성공 후 같은 Python 실행 경로와 환경 변수, 같은 모드(초안이면 `--draft-renderer`)로 실제 원고를 렌더한다. 합성 시험은 강의 내용 검토나 최종 PDF 전 페이지 검토를 대신하지 않는다.

## 필요한 경우의 오프라인 설치

공통 도구 scripts/offline_runtime.py는 필요한 네 Python 패키지가 이미 요구 버전이면 재설치 없이 위 시험을 실행한다. 실제 import·합성 시험에 실패하면 미완료로 끝난다. 설치가 필요한 경우에만 Linux / x86_64 / CPython 3.13인지 실제 관측하고, wheel 조건인 glibc 2.28 이상을 확인한다. 이는 설치 후보 조건이며 다른 Linux 배포판·Python 패치·glibc에서 성공을 인증하지 않는다. 현재 성공 증거는 **Linux x86_64, CPython 3.13.5, glibc 2.41**에 한정된다. macOS·ARM·다른 Python에서는 이 wheel 묶음을 설치하지 않는다.

웹의 확보 경로는 사용자가 연결한 Google Drive의 고정 파일이다. `weasyprint70-linux-x86_64-cp313-wheels-r01.zip` (17개 공식 wheel, 17,520,667바이트):

- Drive 파일 ID `1Jdrsbfcy-pUU_uO_t_MdNRJOCERE_XUg`
- `SHA-256 497860db0a228e6dff7c93e7a04c220150bb1bd3d4d30786b85dbd5bf500f984`

파일 ID로 직접 가져오고 Drive 전체나 과목 폴더를 탐색하지 않는다. 2026-09-30 시험에서 성공한 호출은 Drive 도구의 원본 파일 다운로드(`fetch`의 `download_raw_file=true`)였다. 도구 이름·인수는 환경마다 다를 수 있으므로 실제 제공된 원본 파일 다운로드 기능을 쓴다. 파일 목록·메타데이터·미리보기·검색 발췌·링크 확보는 바이너리 확보가 아니다. 실행 환경의 실제 파일 경로·크기·SHA-256을 확인했을 때만 확보로 기록하며, 이번 단계 전에 있던 파일을 새로 받은 것으로 기록하지 않는다. 다운로드가 막히면 관측한 오류를 한 번 기록하고 이 ZIP만 직접 첨부하도록 요청한다. 같은 실패 반복, 공개 공유 전환, 토큰·쿠키 요구, 다른 서비스 우회, PyPI 온라인 설치 성공의 전제는 하지 않는다.

같은 바이너리의 관리 보관 원본은 비공개 [고정 GitHub Release](https://github.com/smjung1213/web-lecture-notes/releases/tag/weasyprint70-wheels-r01)다. GitHub main에는 관리 도구·잠금·해시·출처·라이선스 정보를 둔다. 웹 실행 환경은 이 Release를 내려받지 못했으므로(아래 ‘증거와 한계’) 웹에서는 Release 다운로드를 시도하지 않는다. Drive 사본과 Release의 파일명·크기·SHA-256은 같고 scripts/offline/attachment.json에 함께 적는다. `latest` 링크로 다른 버전을 자동 선택하지 않는다.

다운로드·첨부 ZIP은 관리 도구가 전체 크기·SHA-256, 정확한 내부 파일 목록·종류, 각 wheel 크기·해시를 확인한 뒤 새 폴더에만 푼다. ZIP 안의 코드는 실행하지 않는다. 준비된 환경이면 아래 설치 도우미는 ZIP을 다시 풀거나 설치하지 않고 합성 시험만 수행한다.

```sh
python -B scripts/offline_runtime.py --archive /다운로드/weasyprint70-linux-x86_64-cp313-wheels-r01.zip \
  --output /새/격리환경 --mathjax-root /실제/node_modules/mathjax-full
```

설치 전 별도로 다운로드 파일만 검증·압축 해제하려면 다음을 사용한다. 이 명령은 Python 패키지를 설치하지 않는다.

```sh
python -B scripts/fetch_runtime.py --archive /다운로드/weasyprint70-linux-x86_64-cp313-wheels-r01.zip --output /새/묶음검증
python -B scripts/offline_runtime.py --verify-only --wheels /새/묶음검증/wheels
```

`fetch_runtime.py --download --output /새/묶음다운로드`는 고정 Release URL에 HTTPS 요청을 한 번 보내는 관리용 별도 옵션이며 웹 확보 경로가 아니다. 브라우저 인증을 가져오거나 자격 증명을 전달하지 않으므로 현재 비공개 Release의 인증된 다운로드를 대신하지 못한다. 401/403/404는 RELEASE_ACCESS_REQUIRED로 기록하며, 네트워크 실패·해시 불일치는 설치로 넘어가지 않는다. `fetch-result.json`과 실패한 새 폴더를 보존한다. 성공한 압축 해제 결과만 설치의 `--wheels`로 넘긴다.

검증 기준은 관리 scripts/offline/wheel-sources.json과 requirements-offline.txt다. 모든 전이 의존성의 버전·공식 PyPI URL·SHA-256·wheel 내부 라이선스 경로를 보존한다. 첨부의 임의 manifest나 스크립트를 신뢰하지 않는다. 도구는 `--no-index --only-binary=:all: --require-hashes --ignore-installed --target`으로 새 site-packages에만 설치한다. pip 캐시·bytecode 생성을 끄고 stdout/stderr와 설치 보고서를 보존한다. 같은 Python에 `-B -S`와 별도 PYTHONPATH를 적용해 기본 site-packages를 제외하며 17개 배포판과 실제 모듈 경로를 검사한다. 기본 환경의 대상 17개 패키지와 pip, Python 실행 파일의 전후 버전·위치·파일 해시를 비교한다. 전체 OS나 모든 프로그램의 호환성 인증은 아니다. 실패한 새 폴더도 증거로 남기며 재시도는 새 이름에서 한다.

성공한 설치 결과의 result.json에 기록된 실행 파일·PYTHONPATH를 이후 렌더와 전달 명령에도 사용한다. 격리 설치 후 일반 python 명령으로 돌아가면 기본 68.0을 읽을 수 있다.

```sh
PYTHONPATH=/새/격리환경/site-packages /실제/python -B -S scripts/render.py /작업/notes.html /새/notes.pdf
PYTHONPATH=/새/격리환경/site-packages /실제/python -B -S scripts/delivery.py /작업/준비원고 /새/전달폴더 --notes-pdf /검토한/notes.pdf --workbook-pdf /검토한/workbook.pdf --revision handoff-01 --file-prefix '과목명 1주차'
```

필요한 MathJax 경로도 위와 동일하게 유지한다. wheel ZIP은 Python 의존성용이며 편집 ZIP에 자동 동봉하지 않는다. 제작 메모에는 Python·MathJax 실행 경로, 격리 여부, 버전·해시와 이 첨부 이름을 기록한다. 편집본 재생성에서도 기존 환경을 먼저 확인하고, 부족한 의존성만 실제 접근 가능한 경로로 준비한다.

## 증거와 한계

2026-09-30 웹 시험에서는 위 17개 wheel의 격리 설치·실제 70.0 import·MathJax 캐시 비교·관리 렌더러의 2쪽 합성 PDF 생성이 성공했다. 기본 68.0과 검사 대상 18개 패키지의 1,356개 파일은 보존됐다. 설치 stderr의 camelot-py/moviepy에 대한 pypdf/Pillow 충돌 경고는 숨기지 않는다. 이 두 프로그램은 격리 런타임에 없었으며 해당 프로그램과의 호환성은 시험하지 않았다. 68.0 최초 설치 주체는 미확인이다. 앞선 온라인 설치 실패에서 관측한 원인은 PyPI DNS 이름 해석 실패였고 70.0 미지원 근거가 아니었다. 68.0의 `://` 기준 프로토콜 판별은 file/data 제한에서 물결 SVG data URI를 거부했지만 70.0에서는 성공했다.

2026-09-30 별도 새 대화의 0.6.3 시험에서 첨부 없는 GitHub 단계는 Release를 내려받지 못해(URL 사전 조회 조건 오류, 브라우저 열기 비활성, github.com 이름 해석 실패, GitHub 커넥터는 메타데이터만 제공) 설치·PDF 없이 미완료였다. HTTP 401/403/404는 관측되지 않았다. 같은 대화의 Drive 단계에서는 파일 ID로 소스 ZIP·wheel ZIP·manifest를 실제로 받아 해시가 일치했고, 17개 wheel 격리 설치, 2쪽 PDF 3개 생성·판독, 관리 전달 ZIP 포장, 부정 검사 11개 통과를 웹이 보고했다. 요청문에 없던 manifest의 SHA-256(`982d5ecb…be64d`, 820바이트)이 로컬 원본과 일치해 Drive 바이트 확보는 로컬에서 따로 확인됐다. 증거 ZIP·PDF는 Chat 다운로드 실패로 로컬 검증하지 못했다. 한 세션의 결과를 모든 세션·계정의 성공 보장으로 확대하지 않는다.

첫 웹 증거는 승격 전 설치 경로·동일 wheel과 합성 입력을, Drive 단계는 0.6.3 관리 도구의 웹 실행을 보고한다. 0.6.5의 준비 HTML 고정점 수정은 로컬에서만 검증했다. 로컬 검증과 웹 보고를 구분한다. 실제 Chat PDF 뷰어의 클릭·검색/복사·접근성 시험은 미완료다. 0.6.3 시험의 컨테이너 Chromium은 root 실행 제한으로 시작하지 못했으며 이를 Chat 뷰어의 제한으로 보지 않는다. 구조 검사와 실제 뷰어 검사를 구분하며 별도 우회 작업을 요구하지 않는다.

2026-10-02 로컬(macOS)에서 보관된 68.0 사본으로 관리 렌더러를 시험했다. 고치기 전에는 위의 data URI 거부로 실패했고, render.py가 file/data 스킴을 직접 검사하도록 바꾼 뒤에는 견본 9쪽, preflight 2쪽, 4주차 노트 49쪽·연습문제 30쪽이 70.0과 같은 쪽수와 같은 페이지 하단 정정 배치로 만들어졌다. 차이는 수식 SVG가 작게 나오는 것과 일부 줄바꿈(노트 1쪽)이었다. 웹 Linux의 68.0 초안 모드는 이 시험 뒤에 처음 쓰며, 그 결과는 별도로 확인한다.

물결 간격의 기존 v3.4 기준은 Poppler 300dpi, 빨강 R>130·R>1.5G·G<130·B<130, 어두운 글자 max(RGB)<120으로 검출한 픽셀 행 중심 간 거리다. 이번 웹 PDF를 같은 방식으로 재측정한 위 간격은 0.4233/0.3387mm, 주기는 13.7994/13.8001pt로 기존 검사를 통과했다. 웹 보고서의 600dpi 빈 픽셀 수 기준 0.25–0.30mm와 직접 비교하지 않는다. 해상도·색 임계값·거리 정의를 함께 기록하며 연속적인 실제 경계 간격을 확정하거나 이 차이만으로 CSS를 바꾸지 않는다.
