class QuizGame():
    def __init__(self):
        self.quiz_total_num=5
        self.quiz_hit_cnt=0
        self.top_score=0

    def getInputNum(self):
        return int(input("선택: "))

    def quiz_title_show(self):
        print("="*26)
        print("\t퀴즈 게임\t")
        print("="*26)

    def menu_list_show(self):
        print("1.퀴즈풀기")
        print("2.퀴즈추가")
        print("3.퀴즈목록")
        print("4.점수확인")
        print("5.종료")

    def quiz_play(self):
        print(f"퀴즈를 시작합니다!(총 {self.quiz_total_num}문제)")
        pass

    def quiz_add(self):
        print(f"새로운 퀴즈를 추가합니다")
        pass

    def quiz_list(self):
        print(f"등록된 퀴즈 목록(총 {self.quiz_total_num}개)")
        pass

    def quiz_score(self):
        print(f"최고점수:{self.top_score}점({self.quiz_total_num}문제 중 {self.quiz_hit_cnt}문제 정답)")
        pass

    def run(self):
        while True:
            # 타이틀 표시
            self.quiz_title_show()
            # 프로그램 실행시 메뉴가 출력되어야 한다.
            self.menu_list_show()
            # 사용자가 기능을 선택할 수 있어야 한다.
            sel_num = self.getInputNum()
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
                    return "quit"
