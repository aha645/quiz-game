import subprocess
import json
import os
import struct
from typing import Optional, List, Tuple

DATA_DIR = "quiz_db"
DATA_FILE = os.path.join(DATA_DIR, "data.bin")
IDX_FILE = os.path.join(DATA_DIR, "index.dat")
FREE_FILE = os.path.join(DATA_DIR, "free.dat")
HEADER_SIZE = 3


class QuizDB:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.index_list: List[Tuple[int, int]] = []
        self.free_blocks: List[Tuple[int, int]] = []
        self._load_index()
        self._load_free()

    def _load_index(self):
        if not os.path.exists(IDX_FILE):
            return
        with open(IDX_FILE, "rb") as f:
            while chunk := f.read(12):
                if len(chunk) < 12:
                    break
                qid, off = struct.unpack('<IQ', chunk)
                self.index_list.append((qid, off))

    def _save_index(self):
        with open(IDX_FILE, "wb") as f:
            for qid, off in self.index_list:
                f.write(struct.pack('<IQ', qid, off))

    def _load_free(self):
        if not os.path.exists(FREE_FILE):
            return
        with open(FREE_FILE, "rb") as f:
            while True:
                ob = f.read(8)
                if len(ob) < 8:
                    break
                sb = f.read(4)
                self.free_blocks.append((struct.unpack('<QI', ob + sb)[0], struct.unpack('<QI', ob + sb)[1]))

    def _save_free(self):
        with open(FREE_FILE, "wb") as f:
            for off, sz in self.free_blocks:
                f.write(struct.pack('<QI', off, sz))

    def _allocate_block(self, payload_len: int) -> int:
        need = HEADER_SIZE + payload_len
        best_i, best_s = -1, float('inf')
        for i, (off, sz) in enumerate(self.free_blocks):
            if sz >= need and sz < best_s:
                best_i, best_s = i, sz
        if best_i >= 0:
            off, _ = self.free_blocks.pop(best_i)
            self._save_free()
            return off
        with open(DATA_FILE, "ab") as f:
            return f.tell()

    def add_quiz(self, qid: int, payload: dict) -> bool:
        raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        off = self._allocate_block(len(raw))
        with open(DATA_FILE, "r+b" if os.path.getsize(DATA_FILE) > 0 else "wb+") as f:
            f.seek(off)
            f.write(struct.pack('<BH', 1, len(raw)))
            f.write(raw)
        self.index_list.append((qid, off))
        self.index_list.sort(key=lambda x: x[0])
        self._save_index()
        return True

    def _read_at(self, offset: int) -> Optional[dict]:
        with open(DATA_FILE, "rb") as f:
            f.seek(offset)
            hdr = f.read(HEADER_SIZE)
            if len(hdr) < HEADER_SIZE:
                return None
            active, plen = struct.unpack('<BH', hdr)
            if active == 0:
                return None
            data = f.read(plen)
        try:
            return json.loads(data.decode('utf-8'))
        except Exception:
            return None

    def get_quiz(self, qid: int) -> Optional[dict]:
        lo, hi = 0, len(self.index_list) - 1
        while lo <= hi:
            mid = (lo + hi // 2)
            if self.index_list[mid][0] == qid:
                return self._read_at(self.index_list[mid][1])


    def get_all_ids(self) -> List[int]:
        valid: List[int] = []
        for qid, off in self.index_list:
            if self._read_at(off) is not None:
                valid.append(qid)
        return valid

    def delete_quiz(self, qid: int) -> bool:
        lo, hi = 0, len(self.index_list) - 1
        found_i = -1
        while lo <= hi:
            mid = (lo + hi) // 2
            if self.index_list[mid][0] == qid:
                found_i = mid
                break
            elif self.index_list[mid][0] < qid:
                lo = mid + 1
            else:
                hi = mid - 1
        if found_i < 0:
            return False
        _, off = self.index_list.pop(found_i)
        # Soft delete: overwrite active flag with 0
        with open(DATA_FILE, "rb") as f:
            f.seek(off)
            hdr = f.read(HEADER_SIZE)
            if len(hdr) == HEADER_SIZE:
                _, plen = struct.unpack('<BH', hdr)
                full_sz = HEADER_SIZE + plen
            else:
                return False
        with open(DATA_FILE, "r+b") as f:
            f.seek(off)
            f.write(struct.pack('B', 0))   # active = 0 (inactive)
        self.free_blocks.append((off, full_sz))
        self._save_free()
        self._save_index()
        return True

    def get_by_category(self, cat: str) -> List[dict]:
        out: List[dict] = []
        for qid, off in self.index_list:
            d = self._read_at(off)
            if d and d.get('category') == cat:
                out.append(d)
        return out

    def get_next_id(self) -> int:
        if not self.index_list:
            return 1
        return max(q for q, _ in self.index_list) + 1


class Quiz:
    def __init__(self, question: str, choices: list[str], answer_idx: int, category: str = "", quiz_id: int = 0):
        self.id = quiz_id
        self.question = question
        self.choices = choices
        self.answer_idx = answer_idx
        self.category = category

    def to_dict(self) -> dict:
        return {
            "question": self.question,
            "choices": self.choices,
            "answer_idx": self.answer_idx,
            "category": self.category,
        }

    @staticmethod
    def from_dict(d: dict) -> 'Quiz':
        return Quiz(d["question"], d["choices"], d["answer_idx"], d.get("category", ""), d.get("id", 0))


class QuizGame:
    def __init__(self):
        self.db = QuizDB()
        self.top_score = self._load_top()

    def _load_top(self) -> int:
        mf = os.path.join(DATA_DIR, "meta.json")
        if os.path.exists(mf):
            with open(mf, "r", encoding="utf-8") as f:
                return json.load(f).get("top_score", 0)
        return 0

    def _save_top(self):
        mf = os.path.join(DATA_DIR, "meta.json")
        with open(mf, "w", encoding="utf-8") as f:
            json.dump({"top_score": self.top_score}, f, ensure_ascii=False, indent=2)

    def _migrate_json(self):
        jf = "quiz_data.json"
        if not os.path.exists(jf):
            return
        with open(jf, "r", encoding="utf-8") as f:
            d = json.load(f)
        for qd in d.get("quizzes", []):
            self.db.add_quiz(qd["id"], {
                "question": qd["question"],
                "choices": qd["choices"],
                "answer_idx": qd["answer_idx"],
                "category": qd.get("category", ""),
            })
        if d.get("top_score"):
            self.top_score = d["top_score"]
            self._save_top()
        os.remove(jf)

    def getInput(self, prompt: str = "입력: ") -> int:
        while True:
            try:
                return int(input(prompt))
            except ValueError:
                print("올바른 숫자를 입력해주세요!")

    def pause(self):
        input("\n>>> ENTER를 눌러 계속하세요...")

    def clear(self):
        subprocess.run("clear", shell=True)

    def show_title(self):
        print("=" * 30)
        print("\t\t퀴즈 게임\n" + "=" * 30)

    def show_menu(self):
        for item in ["1. 퀴즈 풀기", "2. 퀴즈 추가",
                     "3. 퀴지 목록 보기","4. 점수 확인", "5. 프로그램 종료"]:
            print(item)


    def play_quiz(self):
        ids = self.db.get_all_ids()
        if not ids:
            print("\n풀 수 있는 QUIZ가 등록되어 있지 않습니다!")
            self.pause()
            return
        self.clear()
        total, hits = len(ids), 0
        print(f"퀴즈를 시작합니다! (총 {total}문제)")
        print("-" * 35)
        for i, qid in enumerate(ids, 1):
            d = self.db.get_quiz(qid)
            if d is None:
                continue
            quiz = Quiz.from_dict(d)
            print(f"\n[{i}/{total}] {quiz.question}")
            if quiz.category:
                print(f"   카테고리: [{quiz.category}]")
            for j, c in enumerate(quiz.choices, 1):
                print(f"   {j}. {c}")
            try:
                ans = self.getInput()
            except (EOFError, KeyboardInterrupt):
                return
            if ans == quiz.answer_idx + 1:
                print("    ✅ 정답!")
                hits += 1
            else:
                print(f"    ❌ 오답..정답은 '{quiz.choices[quiz.answer_idx]}'")
        final_score = (hits // total) * 100 if total > 0 else 0
        print("\n" + "="*35)
        print(f"| 결과 | 정답: {hits}/{total} | 점수: {final_score}")
        if final_score > self.top_score:
            self.top_score = min(final_score, 100)
            self._save_top()
            print("🏆 신규 기록합니다!")
        print("="*35)
        self.pause()

    def add_quiz(self):
        self.clear()
        txt = input("문제: ").strip()
        if not txt:
            print("문제는 필수입니다.")
            self.pause()
            return
        choices2: list[str] = []
        for n in range(1, 5):
            v = input(f"   {n}번 선택지: ").strip()
            while not v:
                v = input(f"   {n}번 선택지 ( 필수): ").strip()
            choices2.append(v)
        a_num = -1
        try:
            a_in = self.getInput("정답 번호(1~4): ")
        except:
            return
        while a_in not in (1, 2, 3, 4):
            print("잘못된 답변입니다..1~4")
            try:
                a_num = int(input("정답 번호(1-4): "))
            except ValueError:
                pass
        aid_final = a_in - 1
        category2 = input("카테고리 입력: ").strip() or "기본"
        nid = self.db.get_next_id()
        payload = {
            "question": txt,
            "choices": choices2,
            "answer_idx": aid_final,
            "category": category2,
        }
        self.db.add_quiz(n, payload)
        print(f"\n✅ '{txt}' 퀴즈가 추가되었습니다!")
        cnt = len(self.db.get_all_ids())
        print(f'   전체 개수: {cnt}개')
        self.pause()

    def list_quizzes(self):
        self.clear()
        ids2 = self.db.get_all_ids()
        if not ids2:
            print("등록된 QUIZ가 없습니다!")
            self.pause()
        max_show = min(len(ids2), 20)
        for ii, qid in enumerate(ids2[:max_show], 1):
            d = self.db.get_quiz(qid)
            if d:
                zz = Quiz.from_dict(d)
                cat_s = f" | [{zz.category}]" if zz.category else ""
                print(f"\n{ii}. {zz.question}{cat_s}")
                for j, c in enumerate(zz.choices, 1):
                    mark = " ✅" if (j - 1) == zz.answer_idx else ""
                    print(f"   {j}. {c}{mark}")
        if len(ids2) > 20:
            print(f"\n..나머지 {len(ids2)-20}개는 개별 조회")
            try:
                sid = self.getInput("ID를 입력하세요~: ")
                dd = self.db.get_quiz(sid)
                if dd:
                    z = Quiz.from_dict(dd)
                    print(f"\nID {sid}:  {z.question}")
                    for j, c in enumerate(z.choices, 1):
                        m2 = " ✅" if (j - 1) == z.answer_idx else ""
                        print(f"   {j}. {c}{m}" )
            except:
                pass
        self.pause()

    def score_check(self):
        self.clear()
        print("점수 확인")
        print("-"*35)
        ids3 = self.db.get_all_ids()
        if not ids3:
            print("해당 기록이 없습니다!")
            self.pause()
            return
        tp = min(100, (100 // len(ids3)) * len(ids3) if len(ids3) > 0 else 100)
        pct = (self.top_score / tp) * 100 if tp > 0 else 0
        print(f"\n   최고 점수: {self.top_score}점 (최대 {tp}점)")
        print(f"   달성률: {pct:.1f}%")
        self.pause()

    def run(self):
        if os.path.exists("quiz_data.json"):
            self._migrate_json()
        while True:
            try:
                self.clear()
                self.show_title()
                self.show_menu()
                sel = self.getInput("메뉴 선택: ")
                if sel not in (1, 2, 3, 4, 5):
                    print("\n1~5 사이 숫자를 선택해주세요!")
                    self.pause()
                    continue
                match sel:
                    case 1:
                        self.play_quiz()
                    case 2:
                        self.add_quiz()
                    case 3:
                        self.list_quizzes()
                    case 4:
                        self.score_check()
                    case 5:
                        print("\n프로그램을 종료합니다. 감사합니다!")
                        return
            except EOFError:
                print("\n(입력 스트림 닫힘)")
                break
            except KeyboardInterrupt:
                print("\nCtrl+C")
                return
