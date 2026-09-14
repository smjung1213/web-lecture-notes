# web-lecture-notes

한국어 강의노트용 제작 지침·디자인·선택적 렌더링 도우미. 기존 `web-lecture-notes-0.1.0.zip`의 제작 파일을 내용 변경 없이 보관한다. 강의자료, 전사본, 실제 학습노트, 인증정보는 포함하지 않는다.

## Chat에서 파일 기반으로 사용

GitHub 연결로 이 저장소의 파일을 읽어 작업 지침으로 적용하도록 사용자가 명시적으로 요청한다. 이 방식은 네이티브 스킬 설치가 아니며, GitHub 연결이 모델이나 PDF 생성 도구를 추가하지 않는다. 읽은 리비전을 기록하고 작업 중 같은 리비전을 사용한다.

진입점은 `skills/lecture-notes-chat/SKILL.md`다. 그 문서가 연결하는 집필·디자인 기준과 자산을 실제로 읽는다. 검색 발췌나 파일 목록만으로 전문을 읽었다고 하지 않는다. 도구가 잘라 반환하면 지원되는 파일 읽기/행 범위 기능으로 끝까지 이어 읽고, 불가능하면 제한을 밝힌다.

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
