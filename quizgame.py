import json
import os
from datetime import datetime

DATA_FILE = "quiz_data.json"


class Quiz:
    """단일 퀴즈 항목"""

    def __init__(self, question: str, choices: list[str], answer_idx: int, category: str = ""):
        self.id = hash(f"{question}{datetime.now().isoformat()}") % 1000000
        self.question = question
        self.choices = choices  # 선택지 목록 (4개)
        self.answer_idx = answer_idx  # 정답 인덱스 (0~3)
        self.category = category

    def to_dict(self):
        return {
            "id": self.id,
            "question": self.question,
            "choices": self.choices,
            "answer_idx": self.answer_idx,
            "category": self.category,
        }

    @staticmethod
    def from_dict(data: dict) -> "Quiz":
        q = Quiz(data["question"], data["choices"], data["answer_idx"], data.get("category", ""))
        q.id = data.get("id", 0)
        return q


class QuizGame:
    def __init__(self):
        self.quiz_total_num = 0
        self.quiz_hit_cnt = 0
        self.top_score = 0
        self.quizzes: list[Quiz] = []
        self.load_data()

    # ---------- 데이터 파일 저장/로딩 ----------

    def load_data(self):
        """저장된 퀴즈 데이터를 로드합니다."""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.quizzes = [Quiz.from_dict(q) for q in data.get("quizzes", [])]
                    self.top_score = data.get("top_score", 0)
                    self.quiz_total_num = len(self.quizzes)
            except (json.JSONDecodeError, KeyError):
                self.quizzes = []
                self.init_default_quizzes()
        else:
            self.init_default_quizzes()

    def save_data(self):
        """퀴즈 데이터를 JSON 파일에 저장합니다."""
        data = {
            "quizzes": [q.to_dict() for q in self.quizzes],
            "top_score": self.top_score,
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def init_default_quizzes(self):
        """기본 퀴즈 5개를 생성합니다."""
        defaults = [
            Quiz("Python의 창시자는 누구인가?", ["Guido van Rossum", "James Gosling", "Dennis Ritchie", "Linus Torvalds"], 0, "프로그래밍"),
            Quiz("이름은 어디서 유래되었나요?", ["모든 것", "코딩", "알고리즘", "데이터베이스"], 1, "프로그래밍"),
        ]
        self.quizzes = defaults
        self.quiz_total_num = len(self.quizzes)
        self.save_data()

    # ---------- 유틸리티 ----------

    def getInputNum(self, prompt: str = "선택: ") -> int:
        while True:
            try:
                return int(input(prompt))
            except ValueError:
                print("⚠️  올바른 숫자를 입력해주세요!")

    def pause(self):
        input("\n>>> ENTER를 눌러 계속하세요...")

    def clear_screen(self):
        os.system("cls" if os.name == "nt" else "clear")

    # ---------- 표시 ----------

    def quiz_title_show(self):
        print("=" * 26)
        print("\t퀴즈 게임\t")
        print("=" * 26)

    def menu_list_show(self):
        print("1. 퀴즈풀기")
        print("2. 퀴즈추가")
        print("3. 퀴즈목록")
        print("4. 점수확인")
        print("5. 종료")

    # ---------- 핵심 기능 ----------

    def quiz_play(self):
        """퀴즈를 풀게 합니다."""
        if not self.quizzes:
            print("\n⚠️  풀 수 있는 퀴즈가 없습니다!")
            self.pause()
            return

        self.clear_screen()
        self.quiz_total_num = len(self.quizzes)
        self.quiz_hit_cnt = 0
        print(f"🎮 퀴즈를 시작합니다! (총 {self.quiz_total_num}문제)")
        print("-" * 30)

        for i, quiz in enumerate(self.quizzes, 1):
            print(f"\n[{i}/{self.quiz_total_num}] Q: {quiz.question}")
            if quiz.category:
                print(f"    카테고리: [{quiz.category}]")

            for j, choice in enumerate(quiz.choices, 1):
                print(f"    {j}. {choice}")

            # 정답 입력
            try:
                answer = self.getInputNum()
            except (EOFError, KeyboardInterrupt):
                return

            if answer == quiz.answer_idx + 1:
                print("✅ 정답입니다! 🎉")
                self.quiz_hit_cnt += 1
            else:
                correct_name = quiz.choices[quiz.answer_idx]
                print(f"❌ 오답입니다. 정답: {correct_name}")

        # 결과 표시
        score = self.quiz_hit_cnt * (100 // self.quiz_total_num) if self.quiz_total_num > 0 else 0
        print("\n" + "=" * 30)
        print(f"📊 최종 결과:")
        print(f"   정답: {self.quiz_hit_cnt}/{self.quiz_total_num}")
        print(f"   점수: {score}점")

        if score > self.top_score:
            self.top_score = score
            print("🏆 신규 기록! 최고 점수를 갱신했습니다!")

        self.save_data()
        self.pause()

    def quiz_add(self):
        """새 퀴즈를 추가합니다."""
        self.clear_screen()
        print("➕ 새 퀴즈 추가")
        print("-" * 30)

        # 문제 입력
        question = input("📝 문제를 입력하세요: ").strip()
        if not question:
            print("⚠️ 问题是空입니다!")
            self.pause()
            return

        # 선택지 입력 (4개)
        choices = []
        for i in range(1, 5):
            choice = input(f"   {i}번 선택지를 입력하세요: ").strip()
            if not choice:
                print("⚠️  선택지는 비워둘 수 없습니다!")
                return self.quiz_add()
            choices.append(choice)

        # 정답 인덱스
        try:
            answer = self.getInputNum("정답 번호(1~4): ")
            while answer not in (1, 2, 3, 4):
                print("⚠️  1~4 사이의 숫자를 입력해주세요!")
                answer = self.getInputNum("정답 번호(1~4): ")
        except (EOFError, KeyboardInterrupt):
            return

        # 카테고리 (선택사항)
        category = input("카테고리를 입력하세요 (생략 가능): ").strip()

        quiz = Quiz(question, choices, answer - 1, category)
        self.quizzes.append(quiz)
        self.save_data()

        print(f"\n✅ '{question}' 퀴즈가 추가되었습니다!")
        print(f"   총 퀴즈 수: {len(self.quizzes)}개")
        self.pause()

    def quiz_list(self):
        """등록된 퀴즈 목록을 보여줍니다."""
        self.clear_screen()
        print("📋 등록된 퀴즈 목록")
        print("-" * 30)

        if not self.quizzes:
            print("\n⚠️  등록된 퀴즈가 없습니다!")
            self.pause()
            return

        for i, quiz in enumerate(self.quizzes, 1):
            category_str = f" | [{quiz.category}]" if quiz.category else ""
            print(f"\n{i}. {quiz.question}{category_str}")
            for j, choice in enumerate(quiz.choices, 1):
                marker = " ✅" if j - 1 == quiz.answer_idx else ""
                print(f"   {j}. {choice}{marker}")

        print(f"\n   (총 {len(self.quizzes)}개)")
        self.pause()

    def quiz_score(self):
        """최고 점수를 확인합니다."""
        self.clear_screen()
        print("🏆 점수 확인")
        print("-" * 30)

        if not self.quizzes:
            print("\n⚠️  풀이 기록이 없습니다!")
            self.pause()
            return

        self.quiz_total_num = len(self.quizzes)
        total_possible = (100 // self.quiz_total_num) * self.quiz_total_num if self.quiz_total_num > 0 else 100
        pct = (self.top_score / total_possible * 100) if total_possible > 0 else 0

        print(f"\n   최고 점수: {self.top_score}점 (최대 {total_possible}점)")
        print(f"   달성률: {pct:.1f}%")
        self.pause()

    # ---------- 메인 루프 ----------

    def run(self):
        while True:
            try:
                self.clear_screen()
                self.quiz_title_show()
                self.menu_list_show()
                sel_num = self.getInputNum()

                if sel_num not in (1, 2, 3, 4, 5):
                    print("\n⚠️  1~5 사이의 메뉴 번호를 선택해주세요!")
                    self.pause()
                    continue

                match sel_num:
                    case 1:
                        self.quiz_play()
                    case 2:
                        self.quiz_add()
                    case 3:
                        self.quiz_list()
                    case 4:
                        self.quiz_score()
                    case 5:
                        print("\n👋 프로그램을 종료합니다. 감사합니다!")
                        return "quit"
            except EOFError:
                print("\n\n(입력 스트림이 닫혔습니다.)")
                break
            except KeyboardInterrupt:
                print("\n\n👋 Ctrl+C로 종료합니다.")
                return "quit"


if __name__ == "__main__":
    QuizGame().run()
