# ⚠️ 퀴즈 데이터 1,000,000개 이상 시 예상 문제점 및 개선 방안

---

## 현재 구조의 문제점 분석

### 1. 메모리 과부화 🧠 (가장 치명적)

```python
def load_data(self):
    self.quizzes = [Quiz.from_dict(q) for q in data.get("quizzes", [])]
```

| 데이터 수   | 예상 JSON 파일 크기 | RAM 사용량      |
|-----------|-------------------|---------------|
| 10개      | ~3 kB            | ~2 MB         |
| 1,000개   | ~300 KB          | ~50 MB        |
| 100,000개 | ~30 MB           | ~5 GB         |
| 1,000,000개| ~300 MB          | **~50 GB** (Python 객체 오버헤드) |

문제: 모든 퀴즈를 **한 번에 메모리에 로드**하므로 RAM 부족으로 프로그램 충돌.


### 2. JSON 파일의 병목 🐢

```python
def save_data(self):
    json.dump(data, f, ensure_ascii=False, indent=2)
```

| 단계        | 문제                                 |
|-----------|--------------------------------------|
| **저장**   | 전체를 메모리 → 직렬화 → 파일 쓰기 (100만 개면 수 분 소요) |
| **로딩**   | 파일 읽기 → 파싱 → 객체 생성 (최소 30초 이상)        |
| **수정**   | 하나의 퀴즈 추가해도 전체 파일 재작성                  |

JSON 은 순차 액세스 형식이라 임의 접근(random access )이 불가능합니다.


### 3. `_next_id()` 가 O(N) 탐색 🔍

```python
def _next_id(self) -> int:
    return max(q.id for q in self.quizzes) + 1   # 모든 퀴즈 스캔!
```

| 데이터 수 | 예상 소요 시간    |
|-----------|----------------|
| 10개       | ~0.001 ms     |
| 10,000개   | ~0.5 ms        |
| 1,000,000개 | **~50 ms**      |

퀴즈 추가 시마다 모든 객체를 탐색해야 합니다.


### 4. `quiz_list()`, `quiz_play()` 가 한 번에 전체 출력 📜

```python
print(f"총 {self.quiz_total_num}문제")          # 1,000,000 문제?!
for i, quiz in enumerate(self.quizzes, 1):      # 전체 순회
    print(...)                                   # 터미널 버저 오버플로우
```

- 화면에 1,000개 표시해도 **수십만 줄**이 출력됨 → 읽을 수 없음
- 플레이 시에도 **전체 퀴즈를 풀게 됨** → 현실적이지 않음


### 5. 검색/필터 기능 부재 🔎

카테고리별 탐색, 키워드 검색, 난이도 필터 등 **모든 기능이 완전히 없음**.


---

## 개선 방안

### 1단계: JSON → SQLite로 마이그레이션 🗄️

**SQLITE (sqilte3 모듈 — 표준 라이브러리)** 사용 시 해결되는 문제:

```python
import sqlite3

def create_table(self):
    self.db.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,  -- 순차 ID 자동 발급 O(1)
            question   TEXT NOT NULL,
            choices    TEXT NOT NULL,           -- JSON 배열 저장 ["A","B","C","D"]
            answer_idx INTEGER NOT NULL,
            category   TEXT DEFAULT '',
            difficulty TEXT DEFAULT 'middle',   -- 난이도 (easy/middle/hard)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

def create_indexes(self):
    self.db.execute("CREATE INDEX IF NOT EXISTS idx_category ON quizzes(category)")
    self.db.execute("CREATE INDEX IF NOT EXISTS idx_difficulty ON quizzes(difficulty)")
```

#### 비교

| 항목           | JSON 전체 로딩          | SQLite                   |
|--------------|----------------------|-------------------------|
| 메모리 사용량     | 30~50 GB             | **1~2 MB** (연결만 유지)       |
| 단일 퀴즈 조회    | O(1)                 | O(log N) + 인덱스 활용      |
| 카테고리별 조회   | O(N) 전체 스캔          | 인덱스 조회 **O(1)**        |
| 추가/수정        | 전체 삭제 후 재작성      | **INSERT / UPDATE**       |
| 최대 지원 데이터량  | RAM 한계 (GB 단위)     | **TB 단위**              |

---

### 2단계: 페이지네이션 구현 📄

```python
# ❌ 전: 한 번에 전체 출력
for quiz in self.quizzes:
    print(quiz.question)

# ✅ 후: 페이지별 조회
def quiz_list(self, page=1, per_page=20):
    offset = (page - 1) * per_page
    rows = self.db.execute(
        "SELECT id, question, category FROM quizzes LIMIT ? OFFSET ?",
        (per_page, offset),
    ).fetchall()

def quiz_play(self, count=5):
    """유연한 문제 수 선택"""
    rows = self.db.execute(
        "SELECT * FROM quizzes ORDER BY RANDOM() LIMIT ?",
        (count,)   # 5문제 무작위 추출만
    ).fetchmany(count)
```

---

### 3단계: 검색 및 필터 기능 추가 🔍

```python
# 카테고리별 조회
def find_by_category(self, category):
    return self.db.execute(
        "SELECT * FROM quizzes WHERE category = ?", (category,)
    ).fetchall()

# 키워드 검색
def search_keyword(self, keyword):
    return self.db.execute(
        "SELECT * FROM quizzes WHERE question LIKE ?", (f"%{keyword}%",)
    ).fetchall()

# 난이도별 조회
def filter_by_difficulty(self, level):
    return self.db.execute(
        "SELECT * FROM quizzes WHERE difficulty = ?", (level,)
    ).fetchall()
```

---

### 4단계: 퀴즈 플레이 모드 다양화 🎮

| 모드         | 설명                        | DB 쿼리                           |
|-------------|-----------------------------|----------------------------------|
| 전체 풀기(기존)        | 순차 전체                     | `SELECT * FROM quizzes`           |
| **무작위 N개**     | 랜덤으로 N문제만 뽑음            | `SELECT * ORDER BY RANDOM() LIMIT N` |
| **카테고리별**      | 특정 카테고리만 풀음             | `SELECT * WHERE category=? ...`    |
| **난이도별**       | 난이도 필터링                   | `SELECT * WHERE difficulty=? ...`  |
| **미해결 문제 위주**   | 잘못 푼 문제를 다시 연습           | JOIN + 오답 테이블               |

---

### 5단계: 점수 계산 논리 수정 🔢

```python
# ❌ 전: 정수가 아닌 비율 계산 → 큰 수에서 정밀도 손실
score = self.quiz_hit_cnt * (100 // self.quiz_total_num)

# ✅ 후: 각 문제당 가중치로 균일 분배
def calculate_score(self, hit_count, total_count):
    return (hit_count / total_count) * 100.0   # float 사용
```

---

## 개선 방향 요약도

````
현재 시스템 (JSON + 메모리 전량 로딩)
│
├── 문제점 ①: RAM 과다 소모      → SQLite로 lazy loading
├── 문제점 ②: I/O 병목         → 파일 저장소 대신 RDBMS,
                                 INSERT/UPDATE 개별 처리(전체 rewrite x),
                                 WAL Mode 활성화
├── 문제점 ③: ID O(N) 탐색     → AUTOIncrements 자동 할당 (O(1))
├── 문제점 ④: 전체 조회        → 페이지네이션 (LIMIT + OFFSET)
└── 문제점 ⑤: 필터/검색 x       → INDEx 기반 카테고리/키워드 검색

개선 시스템 (SQLite + 인덱스 + 페이지네이션)
````


### 개선 로드맵

```python
import sqlite3   # 표준 라이브러리 ⇒추가 설치 불필요



"""
┌─────────────┬───────────┬─────────┐
│     단계      │  작업 내용  │  소요 시간 │
├─────────────┼───────────┼─────────┤
│ Phase 1    │ SQLite 마이그레이션   │ ~30분    │
│ Phase 2  │ 페이지네이션, 무작위 추출 │ ~20 분   │
│ Phase   │ 검색 및 필터 기능 구현  │ ~25 분   │
│ 4       │ 난이도 시스템 추가 ┃ 15분      │



```

---

## 결론

| 항목         | 현재(JSON)           | 개선(SQLite + 페이지네이션 + 인덱스)|
|-------------|--------------------|-------------------------------------|
| 메모리 사용    | O(N) 전량 로드       | O(1) 연결만 유지                      |
| 추가/수정     | 전체 재작성          | INSERT / UPDATE                      |
| 조회 속도     | O(N),               | 인덱스 활용,                          |
| 지원 가능 데이터| RAM 한계            | TB 단위                              |

→ `sqlite3` 는 Python **표준 라이브러리** 이므로 의존성 추가 없이 바로 마이그레이션 가능합니다.
