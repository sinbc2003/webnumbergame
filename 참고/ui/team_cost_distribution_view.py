# ui/team_cost_distribution_view.py
import tkinter as tk
from constants import *
import tkinter.messagebox as messagebox
import time
from sounds.sound_effects import play_timer_end_sound
from utils.problem_store import load_timer_settings
from ui.team_game_view import TeamGameView

class TeamCostDistributionView(tk.Frame):
    def __init__(self, master, next_view_class=None, next_view_kwargs=None,
                 forward_team_data=False, use_network_team_problems=False):
        super().__init__(master, bg=BG_COLOR)
        self.master = master
        self.next_view_class = next_view_class or TeamGameView
        self.next_view_kwargs = next_view_kwargs or {}
        self.forward_team_data = forward_team_data
        
        # 관리자가 설정한 팀전 설정 로드
        from utils.problem_store import (
            load_team_problems,
            load_team_mode_settings,
            load_team_cost_range,
            load_network_team_problems
        )
        if use_network_team_problems:
            self.team_problems = load_network_team_problems()
        else:
            self.team_problems = load_team_problems()
        team_settings = load_team_mode_settings()
        self.total_cost = team_settings['total_cost']
        
        # 코스트 범위 설정 로드
        cost_range = load_team_cost_range()
        self.min_cost = cost_range['min_cost']
        self.max_cost = cost_range['max_cost']
        
        # 첫 번째 목표 숫자 사용 (다음 버튼으로 변경 가능)
        self.target_number = self.team_problems[0] if self.team_problems else 25
        
        # 타이머 설정 로드
        timer_settings = load_timer_settings()
        self.timer_minutes = timer_settings['coin_distribution_minutes']
        
        # 타이머 관련 속성
        self.timer_id = None
        self.remaining_sec = self.timer_minutes * 60
        self.timer_running = False
        
        # 각 학생별 코스트 입력 변수
        self.cost_vars = {
            'A': tk.StringVar(),
            'B': tk.StringVar(),
            'C': tk.StringVar(),
            'D': tk.StringVar()
        }
        
        self.create_widgets()
        self.bind_cost_validation()
        
        # 단축키 바인딩 추가
        self.master.bind_all('<Control-l>', self._shortcut_menu)
        self.master.bind_all('<Control-L>', self._shortcut_menu)
        self.master.bind_all('<Shift-L>', self._shortcut_menu)
        self.master.bind_all('<Shift-l>', self._shortcut_menu)
        
        # 타이머 자동 시작
        self.after_idle(self.start_timer)
    
    def get_student_display_name(self, student):
        """학생 코드를 표시 이름으로 변환"""
        student_names = {
            'A': '첫 번째 수험생',
            'B': '두 번째 수험생', 
            'C': '세 번째 수험생',
            'D': '네 번째 수험생'
        }
        return student_names.get(student, f"학생 {student}")

    def create_widgets(self):
        # 메인 컨테이너를 grid로 변경하여 더 나은 레이아웃 제어
        self.grid_rowconfigure(0, weight=0)  # 타이틀
        self.grid_rowconfigure(1, weight=0)  # 정보
        self.grid_rowconfigure(2, weight=1)  # 입력 그리드 (확장 가능)
        self.grid_rowconfigure(3, weight=0)  # 타이머
        self.grid_rowconfigure(4, weight=0)  # 상태
        self.grid_rowconfigure(5, weight=0)  # 버튼 (항상 보이도록)
        self.grid_columnconfigure(0, weight=1)
        
        # Title frame
        title_frame = tk.Frame(self, bg=BG_COLOR)
        title_frame.grid(row=0, column=0, pady=(20, 15), sticky="ew")
        title_frame.grid_columnconfigure(0, weight=1)
        
        # Title (중앙)
        title_label = tk.Label(title_frame, text="팀전모드 - COIN 분배", font=TITLE_FONT, bg=BG_COLOR, fg=TEXT_COLOR)
        title_label.pack()

        # Info display
        info_frame = tk.Frame(self, bg=BG_COLOR)
        info_frame.grid(row=1, column=0, pady=10, sticky="ew")
        
        # 더 크고 굵은 폰트 설정
        info_title_font = ('Arial', 20, 'bold')  # 5포인트 크게
        info_value_font = ('Arial', 20, 'bold')  # 5포인트 크게
        
        # 분배할 총 COIN - 흰색 텍스트 + 노란색 값
        total_frame = tk.Frame(info_frame, bg=BG_COLOR)
        total_frame.pack()
        
        total_label = tk.Label(total_frame, text="분배할 총 ", 
                                  font=info_title_font, bg=BG_COLOR, fg=TEXT_COLOR)
        total_label.pack(side=tk.LEFT)
        
        total_value = tk.Label(total_frame, text=f"COIN: {self.total_cost}", 
                                  font=info_value_font, bg=BG_COLOR, fg="#FFD700")  # 노란색
        total_value.pack(side=tk.LEFT)
        
        # 안내 문구
        game_info = tk.Label(info_frame, text="4명의 수험생에게 COIN을 분배해주세요.", 
                                font=info_title_font, bg=BG_COLOR, fg=TEXT_COLOR)
        game_info.pack(pady=5)
        
        # 코스트 범위 표시 - 흰색 텍스트 + 노란색 값
        range_frame = tk.Frame(info_frame, bg=BG_COLOR)
        range_frame.pack()
        
        range_label = tk.Label(range_frame, text="각 수험생에게 부여할 수 있는 ", 
                                  font=info_title_font, bg=BG_COLOR, fg=TEXT_COLOR)
        range_label.pack(side=tk.LEFT)
        
        range_value = tk.Label(range_frame, text=f"COIN 범위: {self.min_cost} ~ {self.max_cost} ", 
                                  font=info_value_font, bg=BG_COLOR, fg="#FFD700")  # 노란색
        range_value.pack(side=tk.LEFT)

        # Cost distribution grid - 세로 중앙 정렬을 위한 컨테이너
        grid_container = tk.Frame(self, bg=BG_COLOR)
        grid_container.grid(row=2, column=0, pady=15, padx=20, sticky="nsew")
        grid_container.grid_rowconfigure(0, weight=1)  # 상단 여백
        grid_container.grid_rowconfigure(1, weight=0)  # 실제 그리드
        grid_container.grid_rowconfigure(2, weight=1)  # 하단 여백
        grid_container.grid_columnconfigure(0, weight=1)

        grid_frame = tk.Frame(grid_container, bg=BG_COLOR)
        grid_frame.grid(row=1, column=0, sticky="ew")

        # Configure columns
        for i in range(4):
            grid_frame.columnconfigure(i, weight=1)

        students = ['A', 'B', 'C', 'D']
        
        # Headers
        for i, student in enumerate(students):
            header_label = tk.Label(grid_frame, text=self.get_student_display_name(student), 
                                   font=TITLE_FONT, bg=BG_COLOR, fg=TEXT_COLOR)
            header_label.grid(row=0, column=i, pady=(0, 20))

        # Input fields
        self.cost_entries = {}
        for i, student in enumerate(students):
            entry_frame = tk.Frame(grid_frame, bg=COMPONENT_BG_COLOR, relief=tk.RAISED, bd=2)
            entry_frame.grid(row=1, column=i, padx=10, pady=10, sticky="ew")
            
            cost_label = tk.Label(entry_frame, text="COIN:", 
                                 font=BODY_FONT, bg=COMPONENT_BG_COLOR, fg=TEXT_COLOR)
            cost_label.pack(pady=5)
            
            cost_entry = tk.Entry(entry_frame, textvariable=self.cost_vars[student],
                                 font=SUBTITLE_FONT, bg=INPUT_BG_COLOR, fg=TEXT_COLOR,
                                 justify=tk.CENTER, width=10)
            cost_entry.pack(pady=5)
            self.cost_entries[student] = cost_entry

        # Timer display - '현재 총합' 위에 배치
        timer_frame = tk.Frame(self, bg=BG_COLOR)
        timer_frame.grid(row=3, column=0, pady=(10, 5), sticky="ew")
        
        initial_timer_text = f"{self.timer_minutes:02d}:00"
        self.timer_label = tk.Label(timer_frame, text=initial_timer_text, font=TIMER_FONT, bg=BG_COLOR, fg=TEXT_COLOR)
        self.timer_label.pack()
        
        # Status display
        status_frame = tk.Frame(self, bg=BG_COLOR)
        status_frame.grid(row=4, column=0, pady=(5, 15), sticky="ew")
        
        self.total_display_label = tk.Label(status_frame, text="현재 총합: 0", 
                                           font=SUBTITLE_FONT, bg=BG_COLOR, fg=TEXT_COLOR)
        self.total_display_label.pack()
        
        self.status_label = tk.Label(status_frame, text="", 
                                    font=BODY_FONT, bg=BG_COLOR)
        self.status_label.pack()

        # Buttons - 항상 화면 하단에 고정되도록 수정
        button_frame = tk.Frame(self, bg=BG_COLOR)
        button_frame.grid(row=5, column=0, pady=(10, 20), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        
        # 버튼들을 중앙에 배치하는 내부 프레임
        inner_button_frame = tk.Frame(button_frame, bg=BG_COLOR)
        inner_button_frame.grid(row=0, column=0)
        
        self.start_btn = tk.Button(inner_button_frame, text="시작", command=self.start_team_game,
                                   font=SUBTITLE_FONT, bg=ACCENT_COLOR, fg=TEXT_COLOR, 
                                   relief=tk.FLAT, width=15, pady=8, state=tk.DISABLED)
        self.start_btn.pack(side=tk.LEFT, padx=10)

        back_btn = tk.Button(inner_button_frame, text="뒤로가기", command=self.go_back,
                            font=BODY_FONT, bg=BORDER_COLOR, fg=TEXT_COLOR, relief=tk.FLAT, pady=8)
        back_btn.pack(side=tk.LEFT, padx=10)
        
        # 키 네비게이션 설정
        self.setup_key_navigation()
        
        # 첫 번째 입력 필드에 포커스 설정 (약간의 지연 후)
        self.after(100, lambda: self.cost_entries['A'].focus_set())

    def setup_key_navigation(self):
        """키 네비게이션 설정"""
        students = ['A', 'B', 'C', 'D']
        
        for i, student in enumerate(students):
            entry = self.cost_entries[student]
            
            # Tab 키와 Enter 키 바인딩
            if i < len(students) - 1:  # 마지막 학생이 아닌 경우
                next_student = students[i + 1]
                entry.bind('<Tab>', lambda e, next_s=next_student: self.focus_next_entry(next_s))
                entry.bind('<Return>', lambda e, next_s=next_student: self.focus_next_entry(next_s))
            else:  # 마지막 학생(D)인 경우
                # Tab 키는 첫 번째로 돌아가기
                entry.bind('<Tab>', lambda e: self.focus_next_entry('A'))
                # Enter 키는 아무것도 하지 않음 (시작 버튼 누르지 않음)
                entry.bind('<Return>', lambda e: 'break')
            
            # Shift+Tab으로 이전 필드로 이동
            if i > 0:  # 첫 번째 학생이 아닌 경우
                prev_student = students[i - 1]
                entry.bind('<Shift-Tab>', lambda e, prev_s=prev_student: self.focus_prev_entry(prev_s))
            else:  # 첫 번째 학생(A)인 경우
                # Shift+Tab으로 마지막 필드로 이동
                entry.bind('<Shift-Tab>', lambda e: self.focus_prev_entry('D'))
    
    def focus_next_entry(self, student):
        """다음 입력 필드로 포커스 이동"""
        self.cost_entries[student].focus_set()
        return 'break'  # 기본 Tab 동작 방지
    
    def focus_prev_entry(self, student):
        """이전 입력 필드로 포커스 이동"""
        self.cost_entries[student].focus_set()
        return 'break'  # 기본 Shift+Tab 동작 방지

    def bind_cost_validation(self):
        """코스트 입력 필드에 실시간 검증 바인딩"""
        for var in self.cost_vars.values():
            var.trace('w', self.validate_costs)

    def validate_costs(self, *args):
        """코스트 분배 검증"""
        try:
            costs = []
            for student in ['A', 'B', 'C', 'D']:
                value = self.cost_vars[student].get().strip()
                if value:
                    costs.append(int(value))
                else:
                    costs.append(0)
            
            current_total = sum(costs)
            self.total_display_label.config(text=f"현재 총합: {current_total}")
            
            # 범위 검증
            out_of_range = []
            for i, (student, cost) in enumerate(zip(['A', 'B', 'C', 'D'], costs)):
                if cost > 0 and (cost < self.min_cost or cost > self.max_cost):
                    out_of_range.append(f"{student}({cost})")
            
            if current_total == self.total_cost and all(cost > 0 for cost in costs):
                if out_of_range:
                    self.status_label.config(text=f"⚠ 범위 벗어남: {', '.join(out_of_range)}", fg=ERROR_COLOR)
                    self.start_btn.config(state=tk.DISABLED)
                else:
                    self.status_label.config(text="✓ 올바른 분배입니다!", fg=SUCCESS_COLOR)
                    self.start_btn.config(state=tk.NORMAL)
            elif current_total > self.total_cost:
                self.status_label.config(text="⚠ 총합이 너무 큽니다!", fg=ERROR_COLOR)
                self.start_btn.config(state=tk.DISABLED)
            elif current_total < self.total_cost:
                remaining = self.total_cost - current_total
                self.status_label.config(text=f"남은 COIN: {remaining}", fg=TEXT_COLOR)
                self.start_btn.config(state=tk.DISABLED)
            else:  # current_total == total but some are 0
                self.status_label.config(text="⚠ 모든 수험생에게 COIN을 할당해주세요!", fg=WARNING_COLOR)
                self.start_btn.config(state=tk.DISABLED)
                
        except ValueError:
            self.total_display_label.config(text="현재 총합: -")
            self.status_label.config(text="⚠ 숫자만 입력해주세요!", fg=ERROR_COLOR)
            self.start_btn.config(state=tk.DISABLED)

    def start_team_game(self):
        """팀 게임 시작"""
        if messagebox.askyesno("팀전 시작", "정말 시작하시겠습니까?"):
            # 타이머 정지
            self.stop_timer()
            
            # 코스트 분배 정보 수집
            cost_distribution = {}
            for student in ['A', 'B', 'C', 'D']:
                cost_distribution[student] = int(self.cost_vars[student].get())
            
            next_kwargs = dict(self.next_view_kwargs)
            next_kwargs.update({
                'cost_distribution': cost_distribution,
                'target_number': self.target_number
            })
            if self.forward_team_data:
                next_kwargs.setdefault('team_problems', self.team_problems)
            self.master.switch_frame(self.next_view_class, **next_kwargs)


    
    def go_back(self):
        # 타이머 정지
        self.stop_timer()
        from ui.main_menu_view import MainMenuView
        self.master.switch_frame(MainMenuView)
    
    def _shortcut_menu(self, event=None):
        """단축키로 메인 메뉴로 돌아가기"""
        self.go_back()
    
    def start_timer(self):
        """타이머 시작"""
        self.timer_running = True
        self.remaining_sec = self.timer_minutes * 60
        self.update_timer_label()
        self.timer_id = self.after(1000, self._tick)
    
    def stop_timer(self):
        """타이머 정지"""
        self.timer_running = False
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
    
    def _tick(self):
        """타이머 틱"""
        if not self.timer_running:
            return
            
        self.remaining_sec -= 1
        self.update_timer_label()
        
        if self.remaining_sec <= 0:
            # 시간 종료
            self.stop_timer()
            play_timer_end_sound(sound_type='chime')
            messagebox.showinfo("시간 종료", f"{self.timer_minutes}분이 모두 경과했습니다!")
            # 메인 메뉴로 돌아가기
            # self.go_back()
        else:
            self.timer_id = self.after(1000, self._tick)
    
    def update_timer_label(self):
        """타이머 표시 업데이트"""
        minutes = self.remaining_sec // 60
        seconds = self.remaining_sec % 60
        timer_text = f"{minutes:02d}:{seconds:02d}"
        self.timer_label.config(text=timer_text)
        
        # 남은 시간이 1분 미만이면 빨간색으로 표시
        if self.remaining_sec < 60:
            self.timer_label.config(fg=ERROR_COLOR)
        else:
            self.timer_label.config(fg=TEXT_COLOR) 