# 집필 계약과 후단 검토 입력

후단 `lecture_tools.review_contract.learning_schema()`의 검토 입력은 `reader` 문자열, `prior_knowledge` 문자열 배열, `study_mode` (`notes_primary` 또는 `source_parallel`), `goal` 문자열의 정확히 네 키다. 빈 문자열과 알 수 없는 추가 키는 거부된다. 웹 입력은 아래 변환을 거쳐 네 키가 된다. `goal`은 한 문장으로 축소하지 않는다. 주차 목표 여러 개를 번호 붙인 한 문자열로 담아 의미와 검토 범위를 보존한다.

웹 집필 계약에서 선수지식을 `allowed`/`not_assumed`로 나눴다면 각각 `허용:`/`가정하지 않음:` 접두어를 붙여 배열로 옮긴다. 미지정 선수지식을 빈 배열로 바꾸지 말고 계약을 확정할 때까지 미확인으로 남긴다. 원 집필 계약과 변환본을 함께 보존하고, 후단에는 변환본만 전달한다.

study_mode의 기본값은 `source_parallel`(강의자료 PDF를 옆에 두고 이번 노트와 이전 주차 노트로 복습·이해·적용)이다. 노트의 필요한 설명·조건·풀이를 줄인다는 뜻이 아니다. `notes_primary`는 사용자가 노트만으로 공부한다고 지정할 때 쓴다. 이전 주차 학습노트로 확인한 개념은 변환 뒤 `허용: 같은 과목 N–M주차 학습노트에서 다룬 개념 — 개념, 개념, …` 한 항목이 되게 적는다(allowed 배열에는 `허용:` 없이). 예: `허용: 같은 과목 1–3주차 학습노트에서 다룬 개념 — 비트와 바이트, 16진수, 2의 보수`. 이전 주차 노트가 없으면 이 항목을 두지 않는다. 복습 방식은 writing.md ‘이전 주차 개념’, goal 작성은 writing.md ‘목표·독자·깊이’를 따른다.

원자료의 페이지 표기는 PDF 첫 장을 1로 세는 물리 쪽수다. 인쇄 번호가 다르면 함께 적고 혼용하지 않는다.


새 입력의 `lecture_tools.review_contract.learning_contract`는 웹 형식도 직접 받아 결정적으로 변환한다. `prior_knowledge` 객체는 정확히 allowed/not_assumed 배열을 가지며 순서를 보존한다. goal 배열은 순서대로 `1. …`와 LF로 연결한다. `contract_conversion`은 원형·변환본·양쪽 SHA-256·변환 버전 `web-learning-contract-v2`을 반환하며 units/Claude 새 준비는 웹 원형을 받으면 이 기록도 남긴다. CLI `review_files.py convert-contract CONFIG OUTPUT`으로 변환 기록을 먼저 고정할 수 있다. 과거 네 키 계약과 digest 계산은 소급 변경하지 않는다. 변환 기록은 내용 검토 완료가 아니다.

지원하는 웹 입력은 위 네 키에 선택 문자열 `study_mode_description`을 더한 형태다. `reader`와 `study_mode`는 그대로 두고 `prior_knowledge`는 문자열 배열 또는 정확히 allowed/not_assumed인 객체, `goal`은 문자열 또는 비어 있지 않은 문자열 배열을 받는다. study_mode_description이 있으면 비어 있지 않은 문자열이어야 하며, 변환 goal 끝에 `학습 방식 설명: …`로 그대로 붙여 검토자에게도 전달한다. 원형·변환본·두 해시가 변환 근거다. 알 수 없는 키와 잘못된 자료형은 거부한다. 기존 네 키 입력은 변경하지 않는다.
