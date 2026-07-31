# 🎮 퀴즈 게임 (Quiz Game)

터미널에서 즐길 수 있는 간단한 퀴즈 게임입니다.

---

## 🔧 설치 / 실행 방법

```bash
uv sync
uv run main.py
```

또는:

```bash
python main.py
```

---

## 📋 기능 목록

| 번호 | 기능       | 설명                                             |
|------|------------|--------------------------------------------------|
| 1    | 퀴즈 풀기   | 등록된 모든 퀴즈 순차 풀이 및 점수 계산             |
| 2    | 퀴즈 추가   | 새 문제 + 선택지(4개) + 정답 + 카테고리 직접 입력   |
| 3    | 퀴지 목록 보기 | 등록된 퀴즈 전체 목록 확인 (20개 표시, 정답 포함)    |
| 4    | 점수 확인   | 최고 기록 / 달성률 확인                            |
| 5    | 프로그램 종료 |Graceful 종료                                     |

---

## 📂 파일 구조

```
quiz-game/
├── main.py              # 진입점 (QuizGame().run() 호출)
├── quizgame.py          # 핵심 로직
│   ├── QuizDB           # 이진 파일 기반 저장소引擎
│   ├── Quiz             # 단일 퀴즈 데이터 클래스
│   └── QuizGame         # 게임 메인 컨트롤러
├── pyproject.toml       # uv 프로젝트 설정
├── .python-version      # Python 3.12
├── .gitignore
├── scalability_analysis.md  # 확장성 분석 문서 (JSON → SQLite 개선안)
└── quiz_db/             # 이진 데이터 저장 폴더
    ├── data.bin         # 실제 퀴즈 페이로드 (이진 파일)
    ├── index.dat        # ID → 오프셋 인덱스 (바이너리)
    ├── free.dat         # 자유 블록 목록 (수거된 슬롯)
    └── meta.json        # 최고 점수 등 메타 정보
```

---

## 🏗️ 아키텍처 개요

### 저장소 전환 배경

기존 `quiz_data.json` 방식은 **전체 데이터를 RAM에 로딩**하므로,
대규모 데이터(10만 개 이상)에서 메모리 과부화 및 I/O 병목이 발생했습니다.
이를 해결하기 위해 **binary file 기반 커스텀 저장소(QuizDB)**로 마이그레이션 중입니다.

### QuizDB — 이진 파일 저장소

- **data.bin**: 각 퀴즈 데이터를 `json.dumps()` → UTF-8 인코딩 후, 헤더 3바와 함께 순차 기록
- **index.dat**: `(quiz_id: I4바, offset: Q8바)` 튜플로 바이너리 인덱스 유지 (ID 오름차순 정렬)
- **free.dat**: 삭제된 블록의 오프셋 & 크기를 기록하여 재사용 (best-fit 할당)

## 헤더 포맷 (3 bytes)

```
┌───────────┬───────┬───────────────┐
│ active(B) │ plen(H)| payload(variable) \n└───────────┴───────┴───────────────┘
   1=활성      길이 (bytes)
```

- `active = 0` → soft delete 상태 (가비지 컬렉션 블록)

### 핵심 알고리즘

| 기능         | 구현 방식                             |
|--------------|---------------------------------------|
| ID 할당       | 최대 ID + 1 (`get_next_id`, O(N))    |
| 블록 재사용   | free_blocks에서 best-fit 선택         |
| 개별 조회     | index.dat binary search (`get_quiz`)  |
| soft delete  | `active` flag를 `0`으로 덮어쓰기      |
| 카테고리 필터 | `get_by_category()` — 전체 스캔       |

---

### 마이그레이션 로직

```
quiz_data.json (존재 시)
   ↓ _migrate_json()
 quiz_db/{data.bin, index.dat, meta.json}
   ↑ 자동 변환 후 원본 json 삭제
```

## 🐛 알려진 문제 및 TODO

아직 해결 중인 항목입니다:

### 버그
- [ ] `add_quiz()` 내 변수명 불일치: `nid = self.db.get_next_id()` 이후 `self.db.add_quiz(n, payload)` — `n`은 loop 변수로 잘못 사용됨 (`nid`로 수정 필요)
- [ ] `list_quizzes()` 내 개별 조회 시 `print(f"   {j}. {c}{m}")` — `m` 대신 `m2` 사용해야 함
- [ ] `get_quiz()` binary search의 버그: `mid = (lo + hi // 2)` → `mid = (lo + hi) // 2` 로 수정 필요 (괄호 누락)

### 리팩토링 / 개선
- [ ] JSON 파일에서 binary file 저장소(QuizDB) 마이그레이션 **테스트 필요**
- [ ] `get_next_id()` 가 O(N) — 최대 ID 캐싱 또는 monotonically increasing counter로 개선
- [ ] `get_by_category()` 전체 스캔 — 별도 category 인덱스 추가 고려
- [ ] 페이지네이션: 퀴즈 풀기 시 전체가 아닌 무작위 N개 선택 모드 추가
- [ ] 확장성 분석 문서(`scalability_analysis.md`)에 제시된 **SQLite 마이그레이션** 최종 검토 필요

---

## 📊 데이터 저장소 이력

| 버전           | 저장 방식         | 저장 파일          |
|----------------|------------------ |--------------------|
| v1 (최초)     | JSON 전량 로딩    | quiz_data.json      |
| v2 (현재 구현중) | binary file + 인덱스 | quiz_db/{data.bin, index.dat, free.dat, meta.json} |
| future?       | SQLite            | TBD                 |

---

## 🛠 기술 스택

- **언어**: Python 3.12+
- **패키지 관리**: uv
- **저장소**: binary file (`struct.pack/unpack`), 이전 버전은 JSON
