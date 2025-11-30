# ui/team_game_view.py
import tkinter as tk
from tkinter import Text, Frame, Label
from constants import *
from game_logic.calculator import analyze_input
from utils.problem_store import load_costs, load_timer_settings, load_strategy_time, load_reset_limit
import tkinter.messagebox as messagebox
import time
import re
# import winsound  # 경고음을 위해 추가 - 커스텀 효과음으로 대체
from sounds.sound_effects import play_correct_sound, play_wrong_sound, play_timer_end_sound
from utils.silent_messagebox import silent_showinfo, silent_showinfo_no_button

class TeamGameView(tk.Frame):
    def __init__(self, master, cost_distribution: dict, target_number: int = None,
                 team_problems: list = None, network_delegate=None, timer_override_minutes=None):
        super().__init__(master, bg=BG_COLOR)
        self.master = master
        self.cost_distribution = cost_distribution.copy()  # A, B, C, D 초기 코스트
        self.remaining_costs = cost_distribution.copy()    # A, B, C, D 남은 코스트
        self.network_delegate = network_delegate
        self.network_mode = network_delegate is not None
        self.inputs_locked = False
        self.timer_override_minutes = timer_override_minutes
        
        # 관리자가 설정한 팀전 문제 목록 로드
        from utils.problem_store import load_team_problems, load_team_costs
        if team_problems is not None:
            self.team_problems = team_problems
        else:
            self.team_problems = load_team_problems()
        self.problem_index = 0
        if self.team_problems:
            problem_data = self.team_problems[0]
            if isinstance(problem_data, dict):
                self.target_number = target_number or problem_data.get("target", 25)
            else: # int
                self.target_number = target_number or problem_data
        else:
            self.target_number = target_number or 25
        
        # 게임 상태
        self.current_student = 0  # 0=A, 1=B, 2=C, 3=D
        self.students = ['A', 'B', 'C', 'D']
        self.student_inputs = {'A': '', 'B': '', 'C': '', 'D': ''}  # 각 학생의 입력
        
        # 누적 입력 관련 속성
        self.accumulated_content = ""  # 전체 누적된 내용
        self.original_costs = {'A': 0, 'B': 0, 'C': 0, 'D': 0}  # 각 학생이 원래 사용한 연산기호 개수
        self.previous_content = ""  # 이전 내용을 추적하기 위한 변수
        
        self.student_ranges = {'A': [], 'B': [], 'C': [], 'D': []}  # 각 학생이 입력한 범위 [(start, end), ...]
        
        # 팀전용 코스트 계산 설정은 필요할 때마다 동적으로 로드
        
        # 타이머 설정 로드
        timer_settings = load_timer_settings()
        self.timer_minutes = timer_settings['round2_minutes']
        if self.timer_override_minutes is not None:
            self.timer_minutes = self.timer_override_minutes
        
        # 타이머 관련 속성
        self.timer_id = None
        self.remaining_sec = self.timer_minutes * 60  # 설정된 시간을 초로 변환
        self.timer_blink_state = False
        self.blink_timer_id = None
        self.game_start_time = None
        
        # 히스토리 관련
        self.success_history = []  # 성공 기록들
        self.deduction_count = 0  # 감점요인 (실패 + 초기화)
        
        # 백스페이스로 차감된 코인 추적
        self.backspace_costs = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        
        # 각 학생의 마지막 텍스트 상태 추적
        self.last_text_state = {'A': '', 'B': '', 'C': '', 'D': ''}
        
        # 각 학생이 입력한 문자의 위치 추적 (초록색으로 표시할 위치들)
        self.student_input_positions = {'A': set(), 'B': set(), 'C': set(), 'D': set()}
        # 전체 텍스트에서 각 위치별로 어떤 학생이 입력했는지 추적
        self.position_to_student = {}  # {position: student}
        
        # 자동 제출 중복 방지 플래그
        self.auto_submit_scheduled = False
        
        self.create_widgets()
        self.update_active_student()
        
        # 단축키 바인딩 추가 - 높은 우선순위로 설정
        self.bind_all('<Control-l>', self._shortcut_menu)
        self.bind_all('<Control-L>', self._shortcut_menu) 
        self.bind_all('<Shift-L>', self._shortcut_menu)
        self.bind_all('<Shift-l>', self._shortcut_menu)
        
        # 추가로 이 프레임에도 직접 바인딩
        self.focus_set()
        self.bind('<Control-l>', self._shortcut_menu)
        self.bind('<Control-L>', self._shortcut_menu)
        self.bind('<Shift-L>', self._shortcut_menu)
        self.bind('<Shift-l>', self._shortcut_menu)
        
        # 게임 시작 시 타이머 제어 (네트워크 모드에서는 외부에서 시작)
        if not self.network_mode:
            self.after_idle(self.start_timer)
        
        # 첫 번째 수험생 입력창에 포커스 설정 (약간의 지연을 두어 위젯이 완전히 생성된 후 실행)
        self.after(100, self.set_initial_focus)
        
        # 2라운드 게임 화면의 초기 너비를 '현재 턴: 첫 번째 수험생 입력을 기다리는중...' 텍스트가 한 줄로 보이도록 설정
        self.after(50, self._adjust_window_size)
    
    def get_student_display_name(self, student):
        """학생 코드를 표시 이름으로 변환"""
        student_names = {
            'A': '첫 번째 수험생',
            'B': '두 번째 수험생', 
            'C': '세 번째 수험생',
            'D': '네 번째 수험생'
        }
        return student_names.get(student, f"학생 {student}")
    
    def set_initial_focus(self):
        """게임 시작 시 첫 번째 수험생 입력창에 포커스 설정"""
        if self.students and len(self.students) > 0:
            first_student = self.students[0]
            if first_student in self.student_panels:
                panel = self.student_panels[first_student]
                if hasattr(panel, 'input_text'):
                    panel.input_text.focus_set()
    
    def _adjust_window_size(self):
        """2라운드 게임 화면의 초기 너비를 적절하게 조정"""
        # 왼쪽: '현재 턴: 첫 번째 수험생 입력을 기다리는중...' 
        # 오른쪽: '최고기록', '실패 횟수: 1회' 등의 텍스트가 모두 한 줄로 보이도록 설정
        
        # 최소 너비를 1400픽셀로 설정하여 '현재 턴: 첫 번째 수험생 입력을 기다리는중...' 텍스트가
        # 왼쪽 패널에서 한 줄로 완전히 표시되도록 충분한 공간 확보
        # 높이도 700픽셀로 설정하여 전체적으로 여유있게 표시
        min_width = 1400
        min_height = 700
        
        current_geometry = self.master.geometry()
        
        # 현재 크기 파싱
        if 'x' in current_geometry:
            # geometry 형태: "800x600" 또는 "800x600+100+100"
            size_part = current_geometry.split('+')[0]  # 위치 정보 제거
            parts = size_part.split('x')
            
            if len(parts) >= 2:
                current_width = int(parts[0])
                current_height = int(parts[1])
                
                # 위치 정보 추출 (있다면)
                pos_info = ""
                if '+' in current_geometry:
                    pos_parts = current_geometry.split('+')
                    if len(pos_parts) >= 3:
                        pos_info = f"+{pos_parts[1]}+{pos_parts[2]}"
                
                # 너비나 높이가 최소값보다 작으면 조정
                new_width = max(current_width, min_width)
                new_height = max(current_height, min_height)
                
                if new_width != current_width or new_height != current_height:
                    # 화면 중앙에 위치하도록 계산
                    screen_width = self.master.winfo_screenwidth()
                    screen_height = self.master.winfo_screenheight()
                    x = (screen_width - new_width) // 2
                    y = (screen_height - new_height) // 2
                    
                    new_geometry = f"{new_width}x{new_height}+{x}+{y}"
                    self.master.geometry(new_geometry)

    def create_widgets(self):
        # Configure main layout - 위쪽 영역을 더 크게, 아래쪽을 작게
        self.grid_rowconfigure(0, weight=3, minsize=400)    # 위쪽 (게임현황/계산결과) 더 크게
        self.grid_rowconfigure(1, weight=2, minsize=250)    # 아래쪽 (학생 입력) 더 작게
        self.grid_columnconfigure(0, weight=1)

        # ===== 위쪽 1/3: 계산 결과 표시 영역 (전체 너비 사용) =====
        result_frame = Frame(self, bg=COMPONENT_BG_COLOR, relief=tk.RAISED, bd=3)
        result_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        result_frame.grid_rowconfigure(0, weight=0)  # 제목 행
        result_frame.grid_rowconfigure(1, weight=1)  # 컨텐츠 행
        result_frame.grid_columnconfigure(0, weight=1)
        
        # 제목
        title_frame = Frame(result_frame, bg=COMPONENT_BG_COLOR)
        title_frame.grid(row=0, column=0, pady=15, sticky="ew")
        title_frame.grid_columnconfigure(0, weight=0)  # 문제 정보 (왼쪽)
        title_frame.grid_columnconfigure(1, weight=1)  # 빈 공간 (중앙)
        title_frame.grid_columnconfigure(2, weight=0)  # 타이머 + 버튼들 (오른쪽)
        
        # 문제 정보 (왼쪽) - Text 위젯으로 변경하여 다중 색상 지원
        problem_info_frame = Frame(title_frame, bg=COMPONENT_BG_COLOR)
        problem_info_frame.grid(row=0, column=0, sticky="w", padx=(10, 0))
        
        self.problem_info_text = Text(problem_info_frame, height=1, width=12, 
                                     font=("Segoe UI", 61, "bold"), bg=COMPONENT_BG_COLOR, 
                                     state=tk.DISABLED, wrap=tk.NONE, cursor="arrow",
                                     relief=tk.FLAT, highlightthickness=0)
        self.problem_info_text.pack()
        
        # 색상 태그 설정
        self.problem_info_text.tag_configure("label", foreground=TEXT_COLOR)
        self.problem_info_text.tag_configure("number", foreground=HIGHLIGHT_COLOR)
        
        # 초기 텍스트 설정
        self._update_problem_info_text()
        
        # 기호별 코스트 정보 (중앙) - 표 형태로 변경
        cost_info_frame = Frame(title_frame, bg=COMPONENT_BG_COLOR)
        cost_info_frame.grid(row=0, column=1, sticky="")
        
        # 팀전용 코스트 설정 로드
        from utils.problem_store import load_team_costs
        team_costs = load_team_costs()
        
        # 표 스타일의 프레임 생성
        table_frame = Frame(cost_info_frame, bg=COMPONENT_BG_COLOR, relief=tk.RAISED, bd=2)
        table_frame.pack()
        
        # 제목
        title_label = Label(table_frame, text="기호별 COIN", font=("Segoe UI", 16, "bold"),
                           bg=COMPONENT_BG_COLOR, fg=TEXT_COLOR, pady=5)
        title_label.grid(row=0, column=0, columnspan=7, sticky="ew")
        
        # 구분선
        separator = Frame(table_frame, height=2, bg=TEXT_COLOR)
        separator.grid(row=1, column=0, columnspan=7, sticky="ew", padx=5)
        
        # 행 제목 추가
        row_title1 = Label(table_frame, text="기호", font=("Segoe UI", 14, "bold"),
                          bg=COMPONENT_BG_COLOR, fg=TEXT_COLOR, width=6)
        row_title1.grid(row=2, column=0, padx=5, pady=2)
        
        row_title2 = Label(table_frame, text="COIN", font=("Segoe UI", 14, "bold"),
                          bg=COMPONENT_BG_COLOR, fg=TEXT_COLOR, width=6)
        row_title2.grid(row=3, column=0, padx=5, pady=2)
        
        # 기호와 코스트를 표 형태로 배치
        symbols = ['1', '(', ')', '+', '*', '삭제']
        self.cost_labels = {}
        
        for i, symbol in enumerate(symbols):
            # 기호 레이블
            symbol_label = Label(table_frame, text=symbol, font=("Segoe UI", 18, "bold"),
                               bg=COMPONENT_BG_COLOR, fg=HIGHLIGHT_COLOR, 
                               width=4, relief=tk.GROOVE, bd=1)
            symbol_label.grid(row=2, column=i+1, padx=2, pady=2)
            
            # 코스트 레이블
            if symbol == '삭제':
                cost = 1
            else:
                cost = team_costs.get(symbol, 1)
            cost_label = Label(table_frame, text=str(cost), font=("Segoe UI", 18),
                             bg=COMPONENT_BG_COLOR, fg=TEXT_COLOR,
                             width=4, relief=tk.GROOVE, bd=1)
            cost_label.grid(row=3, column=i+1, padx=2, pady=2)
            
            # 나중에 업데이트를 위해 저장
            if symbol != '삭제':
                self.cost_labels[symbol] = cost_label
        
        # 타이머 (오른쪽)
        right_frame = Frame(title_frame, bg=COMPONENT_BG_COLOR)
        right_frame.grid(row=0, column=2, sticky="e", padx=(0, 10))
        
        initial_timer_text = f"{self.timer_minutes:02d}:00"
        self.timer_label = Label(right_frame, text=initial_timer_text, font=("Segoe UI", 61, "bold"), 
                                bg=COMPONENT_BG_COLOR, fg=TEXT_COLOR)
        self.timer_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # PanedWindow로 계산결과와 히스토리를 분할
        paned_window = tk.PanedWindow(result_frame, orient=tk.HORIZONTAL, 
                                     bg=COMPONENT_BG_COLOR, 
                                     sashwidth=10, 
                                     sashrelief=tk.RAISED,
                                     sashpad=2,
                                     handlesize=10,
                                     showhandle=True,
                                     opaqueresize=True)
        paned_window.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 15))
        
        # 계산 결과 (왼쪽)
        calculation_frame = Frame(paned_window, bg=INPUT_BG_COLOR, relief=tk.SUNKEN, bd=2)
        
        self.calculation_text = Text(calculation_frame, bg=INPUT_BG_COLOR, fg=TEXT_COLOR,
                                    font=SUBTITLE_FONT,  # 폰트 크기 증가
                                    relief=tk.FLAT, state=tk.DISABLED,
                                    wrap=tk.WORD, height=10)  # height를 6에서 10으로 증가
        self.calculation_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 왼쪽 패널의 최소 크기를 충분히 설정하여 '현재 턴' 텍스트가 한 줄로 표시되도록
        paned_window.add(calculation_frame, minsize=450)

        # ===== 아래쪽 2/3: 4개 열 입력 영역 =====
        input_frame = Frame(self, bg=BG_COLOR, relief=tk.SUNKEN, bd=2)
        input_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # 4개 열 동일 크기 설정
        for i in range(4):
            input_frame.grid_columnconfigure(i, weight=1, minsize=180)
        input_frame.grid_rowconfigure(0, weight=1)

        # 각 학생별 입력 패널 생성
        self.student_panels = {}
        for i, student in enumerate(self.students):
            panel = self.create_student_panel(input_frame, student)
            panel.grid(row=0, column=i, sticky="nsew", padx=8, pady=8)
            self.student_panels[student] = panel
        
        # 히스토리 프레임 (오른쪽) - 프레임 테두리 제거
        history_frame = Frame(paned_window, bg=INPUT_BG_COLOR)
        
        # 히스토리 텍스트 위젯 (1라운드와 동일한 스타일) - 다중 색상 지원, 높이 증가
        self.history_text = tk.Text(history_frame, height=8, font=("Segoe UI", 18, "bold"),
                                   bg=INPUT_BG_COLOR, fg=TEXT_COLOR, 
                                   state=tk.DISABLED, wrap=tk.NONE, cursor="arrow")  # 높이 4→8, 폰트 22→18
        self.history_text.pack(pady=(5, 5), padx=10, fill=tk.BOTH, expand=True)  # 패딩 더 줄임
        
        # 색상 태그 설정
        self.history_text.tag_configure("title", foreground=TEXT_COLOR, justify=tk.CENTER)
        self.history_text.tag_configure("value", foreground=HIGHLIGHT_COLOR, justify=tk.CENTER)
        self.history_text.tag_configure("optimal", foreground=SUCCESS_COLOR, justify=tk.CENTER)
        self.history_text.tag_configure("fail", foreground="#ff4444", justify=tk.CENTER)
        
        base_font_size = 18
        header_font = ("Segoe UI", base_font_size + 3, "bold")  # 헤더 폰트도 줄임
        self.history_text.tag_configure("header", font=header_font, foreground=TEXT_COLOR, justify=tk.CENTER)
        
        # 초기 텍스트 설정
        self._update_team_history_text("🏆 최고기록", is_empty=True)
        
        # 오른쪽 패널의 최소 크기 설정
        paned_window.add(history_frame, minsize=350)
        
        # PanedWindow의 초기 비율 설정 - 왼쪽을 더 넓게 설정하여 '현재 턴' 텍스트가 한 줄로 표시되도록
        # 55:45 비율로 설정 (왼쪽 55%, 오른쪽 45%)
        self.after(100, lambda: paned_window.sash_place(0, 
                                                        int(paned_window.winfo_width() * 0.55), 0))
        
        # 초기 누적 결과 표시
        self.update_accumulated_result()
        
        # 초기 히스토리 표시 (실패 횟수 포함)
        self.update_history_display()

        # 우클릭 리셋 메뉴 설정
        self.reset_menu = tk.Menu(self, tearoff=0, bg=COMPONENT_BG_COLOR, fg=TEXT_COLOR)
        self.reset_menu.add_command(label="리셋", command=self.reset_all_inputs)

        # 메뉴 바인딩
        self.bind_class("TFrame", "<Button-3>", self.show_reset_menu)
        self.bind_class("TLabel", "<Button-3>", self.show_reset_menu)
        self.bind_class("TPanedwindow", "<Button-3>", self.show_reset_menu)
        
        # 특정 위젯에도 직접 바인딩 (클래스 바인딩이 적용 안되는 경우 대비)
        self.bind("<Button-3>", self.show_reset_menu)
        result_frame.bind("<Button-3>", self.show_reset_menu)
        title_frame.bind("<Button-3>", self.show_reset_menu)
        self.calculation_text.bind("<Button-3>", self.show_reset_menu)
        self.history_text.bind("<Button-3>", self.show_reset_menu)

    def show_reset_menu(self, event):
        """우클릭 시 리셋 메뉴 표시"""
        # 텍스트 입력 위젯에서는 기본 메뉴를 사용하도록 함
        if isinstance(event.widget, tk.Text):
             if event.widget.cget('state') == tk.NORMAL:
                 return

        try:
            self.reset_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.reset_menu.grab_release()

    def create_student_panel(self, parent, student):
        """개별 학생 패널 생성"""
        panel = Frame(parent, bg=INACTIVE_PANEL_COLOR, relief=tk.RAISED, bd=3)
        panel.grid_rowconfigure(2, weight=1)  # 입력 영역이 확장되도록
        panel.grid_columnconfigure(0, weight=1)
        
        # 헤더 - 더 눈에 띄게
        header = Label(panel, text=f"👨‍🎓 {self.get_student_display_name(student)}", font=SUBTITLE_FONT, 
                      bg=INACTIVE_PANEL_COLOR, fg=INACTIVE_TEXT_COLOR, relief=tk.FLAT, pady=5)
        header.grid(row=0, column=0, sticky="ew", padx=5, pady=(10, 5))
        
        # 코스트 정보 - 더 보기 좋게
        cost_info = Label(panel, 
                         text=f"💰 할당: {self.cost_distribution[student]}\n⏱️ 남은 COIN: {self.remaining_costs[student]}", 
                         font=BODY_FONT, bg=INACTIVE_PANEL_COLOR, fg=INACTIVE_TEXT_COLOR,
                         relief=tk.SUNKEN, bd=1, pady=3)
        cost_info.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        # 입력 영역 - 24포인트 텍스트에 맞는 박스 크기
        input_text = Text(panel, bg=INPUT_BG_COLOR, fg=INACTIVE_TEXT_COLOR,
                         font=("Segoe UI", 24), state=tk.DISABLED, height=8, width=15,  # 24포인트에 맞게 높이와 너비 조정
                         relief=tk.SUNKEN, bd=2, wrap=tk.WORD)
        input_text.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        
        # 스페이스 입력 차단 및 실시간 업데이트 이벤트 바인딩
            
        def on_key_release(event):
            # 현재 활성화된 학생인 경우에만 처리
            if self.current_student < len(self.students) and self.students[self.current_student] == student:
                # 텍스트 변경 확인
                current_text = input_text.get("1.0", tk.END).rstrip('\n')
                
                # 텍스트 변경 감지 및 처리
                prev_text = self.last_text_state.get(student, "")
                
                # 커서 위치 가져오기 (삽입 후의 위치)
                cursor_pos = input_text.index(tk.INSERT)
                cursor_line, cursor_col = map(int, cursor_pos.split('.'))
                
                # 문자가 추가된 경우
                if len(current_text) > len(prev_text):
                    # 추가된 문자 수
                    added_count = len(current_text) - len(prev_text)
                    
                    # 변경 위치 찾기 - 커서 위치를 활용
                    insert_pos = -1
                    
                    # 커서 위치가 추가된 문자 바로 뒤에 있으므로, 삽입 위치는 cursor_col - added_count
                    if cursor_col >= added_count:
                        # 중간에 삽입된 경우
                        insert_pos = cursor_col - added_count
                    else:
                        # 시작 부분에 삽입된 경우
                        insert_pos = 0
                    

                    
                    # 삽입 위치가 텍스트 범위 내인지 확인
                    if insert_pos >= 0 and insert_pos <= len(prev_text):
                            # 추가된 문자들 중 COIN 한도 내에서 입력 가능한 것만 처리
                            allowed_chars = []
                            total_cost_used = 0
                            
                            for j in range(added_count):
                                if insert_pos + j < len(current_text):
                                    char = current_text[insert_pos + j]
                                    if char in '1()+*':
                                        char_cost = self.calculate_team_cost(char)
                                        if total_cost_used + char_cost <= self.remaining_costs[student]:
                                            total_cost_used += char_cost
                                            allowed_chars.append((j, char, char_cost))
                                        else:
                                            # COIN이 부족하면 여기서 중단
                                            break
                            
                            # 허용된 문자 수가 추가된 문자 수보다 적으면 초과분 제거
                            if len(allowed_chars) < added_count:
                                # 허용된 부분까지만 포함한 텍스트 생성
                                new_text = prev_text[:insert_pos]
                                for j, char, _ in allowed_chars:
                                    new_text += char
                                new_text += prev_text[insert_pos:]
                                
                                # 텍스트 업데이트
                                input_text.delete("1.0", tk.END)
                                input_text.insert("1.0", new_text)
                                # 커서를 허용된 문자 다음으로 설정
                                input_text.mark_set(tk.INSERT, f"1.{insert_pos + len(allowed_chars)}")
                                current_text = new_text
                                added_count = len(allowed_chars)
                            
                            # 허용된 문자들에 대해 COIN 차감
                            for j, char, char_cost in allowed_chars:
                                self.remaining_costs[student] -= char_cost
                                self.update_cost_display(student)
                            # 코스트만 처리 (위치 기록은 아래에서 일괄 처리)
                            
                            # 기존 위치들 중 삽입 위치 이후의 것들을 이동
                            # 새로 추가한 위치들을 임시로 저장
                            new_positions = set()
                            for j in range(added_count):
                                new_positions.add(insert_pos + j)
                            
                            # 모든 학생의 위치 업데이트 (position_to_student 기반)
                            new_position_to_student = {}
                            # 먼저 기존 위치들을 업데이트 (삽입 위치 이전은 그대로, 이후는 이동)
                            for pos, stud in self.position_to_student.items():
                                if pos < insert_pos:
                                    new_position_to_student[pos] = stud
                                else:
                                    # insert_pos 위치 이후의 것들은 added_count만큼 뒤로 이동
                                    new_position_to_student[pos + added_count] = stud
                            
                            # 그 다음에 새로 추가한 위치들 추가
                            for j in range(added_count):
                                new_position_to_student[insert_pos + j] = student
                            
                            self.position_to_student = new_position_to_student
                            

                            
                            # 모든 학생의 student_input_positions 재구성
                            for stud in self.students:
                                self.student_input_positions[stud] = set()
                            for pos, stud in self.position_to_student.items():
                                self.student_input_positions[stud].add(pos)
                    else:
                        # 끝에 추가된 경우 (insert_pos가 prev_text 길이와 같은 경우)
                        added_chars = current_text[len(prev_text):]
                        
                        # 추가된 문자들 중 COIN 한도 내에서 입력 가능한 것만 처리
                        allowed_chars = []
                        total_cost_used = 0
                        
                        for j, char in enumerate(added_chars):
                            if char in '1()+*':
                                char_cost = self.calculate_team_cost(char)
                                if total_cost_used + char_cost <= self.remaining_costs[student]:
                                    total_cost_used += char_cost
                                    allowed_chars.append((j, char, char_cost))
                                else:
                                    # COIN이 부족하면 여기서 중단
                                    break
                        
                        # 허용된 문자 수가 추가된 문자 수보다 적으면 초과분 제거
                        if len(allowed_chars) < len(added_chars):
                            # 허용된 부분까지만 포함한 텍스트 생성
                            new_text = prev_text
                            for j, char, _ in allowed_chars:
                                new_text += char
                            
                            # 텍스트 업데이트
                            input_text.delete("1.0", tk.END)
                            input_text.insert("1.0", new_text)
                            # 커서를 텍스트 끝으로 설정
                            input_text.mark_set(tk.INSERT, f"1.{len(new_text)}")
                            current_text = new_text
                        
                        # 허용된 문자들에 대해 COIN 차감 및 위치 기록
                        for j, char, char_cost in allowed_chars:
                            self.remaining_costs[student] -= char_cost
                            self.update_cost_display(student)
                            # 입력한 위치 기록
                            self.student_input_positions[student].add(len(prev_text) + j)
                            self.position_to_student[len(prev_text) + j] = student
                
                # 현재 텍스트 상태 저장
                self.last_text_state[student] = current_text
                
                # 색상 업데이트
                self.on_text_change(student)
            
            # 실시간 코스트 업데이트는 항상
            self.after(10, lambda: self.update_realtime_feedback(student))
            
        def on_key_press(event):
            # Shift+L 메인 메뉴 단축키는 허용
            if event.keysym in ['L', 'l'] and (event.state & 0x1):  # Shift가 눌린 경우
                return  # Shift+L은 허용
            
            # Shift 조합 키 차단 (블록 선택 방지)
            if (event.state & 0x1):  # Shift가 눌린 경우
                # Shift+L은 허용 (위에서 처리됨)
                if event.keysym not in ['L', 'l']:
                    # Shift+방향키, Shift+Home/End, Shift+PageUp/PageDown 등 모든 선택 관련 키 차단
                    if event.keysym in ['Left', 'Right', 'Up', 'Down', 'Home', 'End', 'Prior', 'Next', 
                                       'Insert', 'Delete', 'BackSpace', 'Tab', 'ISO_Left_Tab']:
                        return 'break'
            
            # Ctrl 단축키 차단 (선택, 복사, 붙여넣기 등)
            if event.state & 0x4:  # Ctrl이 눌린 경우
                # Ctrl+L은 허용 (메인 메뉴)
                if event.keysym in ['l', 'L']:
                    return
                # 그 외 모든 Ctrl 단축키 차단
                # Ctrl+A (전체선택), Ctrl+C (복사), Ctrl+V (붙여넣기), Ctrl+X (잘라내기) 등
                return 'break'
            if event.keysym == 'space':
                return 'break'  # 스페이스 입력 차단
            
            # BackSpace 또는 Delete 키가 눌렸을 때 코인 감소
            if event.keysym in ['BackSpace', 'Delete']:
                # 현재 활성화된 학생인 경우에만 처리
                if self.current_student < len(self.students) and self.students[self.current_student] == student:
                    # 코인이 0이면 삭제 차단
                    if self.remaining_costs[student] <= 0:
                        return 'break'  # 삭제 동작 차단
                    
                    # 현재 텍스트 가져오기
                    current_text = input_text.get("1.0", tk.END).rstrip('\n')
                    
                    # 선택 영역이 있는지 확인
                    try:
                        sel_start = input_text.index(tk.SEL_FIRST)
                        sel_end = input_text.index(tk.SEL_LAST)
                        has_selection = True
                    except tk.TclError:
                        has_selection = False
                    
                    if has_selection:
                        # 선택 영역이 있는 경우 - 선택된 문자 수만큼 코인 필요
                        sel_start_line, sel_start_col = map(int, sel_start.split('.'))
                        sel_end_line, sel_end_col = map(int, sel_end.split('.'))
                        
                        # 선택된 텍스트 길이 계산
                        selected_text = input_text.get(sel_start, sel_end)
                        selected_length = len(selected_text)
                        
                        if selected_length > 0:
                            # 필요한 코인이 남은 코인보다 많으면 차단
                            if selected_length > self.remaining_costs[student]:
                                return 'break'  # 삭제 동작 차단
                            
                            # 코인 차감
                            self.remaining_costs[student] -= selected_length
                            self.backspace_costs[student] += selected_length
                            self.update_cost_display(student)
                            
                            # 선택 영역의 입력 기록 제거
                            start_pos = sel_start_col
                            end_pos = sel_end_col
                            
                            # position_to_student 업데이트
                            new_position_to_student = {}
                            for pos, stud in self.position_to_student.items():
                                if pos < start_pos:
                                    new_position_to_student[pos] = stud
                                elif pos >= end_pos:
                                    new_position_to_student[pos - selected_length] = stud
                            self.position_to_student = new_position_to_student
                            
                            # 모든 학생의 student_input_positions 재구성
                            for stud in self.students:
                                self.student_input_positions[stud] = set()
                            for pos, stud in self.position_to_student.items():
                                self.student_input_positions[stud].add(pos)
                    else:
                        # 선택 영역이 없는 경우 - 기존 로직
                        # BackSpace의 경우 커서 위치 확인
                        if event.keysym == 'BackSpace':
                            cursor_pos = input_text.index(tk.INSERT)
                            cursor_line, cursor_col = map(int, cursor_pos.split('.'))
                            # 커서가 문서 시작이 아닌 경우에만 처리
                            if not (cursor_line == 1 and cursor_col == 0):
                                # 코인 감소
                                self.remaining_costs[student] -= 1
                                self.backspace_costs[student] += 1  # 백스페이스로 차감된 코인 추적
                                self.update_cost_display(student)
                                
                                # 삭제할 위치의 입력 기록 제거 (cursor_col - 1 위치)
                                delete_pos = cursor_col - 1
                                
                                # position_to_student 업데이트
                                new_position_to_student = {}
                                for pos, stud in self.position_to_student.items():
                                    if pos < delete_pos:
                                        new_position_to_student[pos] = stud
                                    elif pos > delete_pos:
                                        new_position_to_student[pos - 1] = stud
                                self.position_to_student = new_position_to_student
                                
                                # 모든 학생의 student_input_positions 재구성
                                for stud in self.students:
                                    self.student_input_positions[stud] = set()
                                for pos, stud in self.position_to_student.items():
                                    self.student_input_positions[stud].add(pos)
                        
                        # Delete의 경우
                        elif event.keysym == 'Delete':
                            cursor_pos = input_text.index(tk.INSERT)
                            cursor_line, cursor_col = map(int, cursor_pos.split('.'))
                            text_content = input_text.get("1.0", tk.END).rstrip('\n')
                            
                            # 커서 위치가 텍스트 끝이 아닌 경우에만 처리
                            if cursor_col < len(text_content):
                                # 코인 감소
                                self.remaining_costs[student] -= 1
                                self.backspace_costs[student] += 1  # 백스페이스로 차감된 코인 추적
                                self.update_cost_display(student)
                                
                                # 삭제할 위치의 입력 기록 제거 (cursor_col 위치)
                                delete_pos = cursor_col
                                
                                # position_to_student 업데이트
                                new_position_to_student = {}
                                for pos, stud in self.position_to_student.items():
                                    if pos < delete_pos:
                                        new_position_to_student[pos] = stud
                                    elif pos > delete_pos:
                                        new_position_to_student[pos - 1] = stud
                                self.position_to_student = new_position_to_student
                                
                                # 모든 학생의 student_input_positions 재구성
                                for stud in self.students:
                                    self.student_input_positions[stud] = set()
                                for pos, stud in self.position_to_student.items():
                                    self.student_input_positions[stud].add(pos)
                
                return  # 편집 키는 허용
            
            # F8 키 차단 (일부 시스템에서 전체 선택)
            if event.keysym == 'F8':
                return 'break'
            
            # 다른 편집 키는 허용
            if event.keysym in ['Left', 'Right', 'Home', 'End']:
                return  # 편집 키는 허용
            
            # 허용된 문자가 아닌 경우 입력 차단 (Shift+숫자로 만드는 특수문자 !@#$%^& 등 포함)
            if event.char and event.char not in '1()+*':
                return 'break'
            
            # 코인 초과 체크 (문자 입력 시)
            if event.char in '1()+*':
                # 현재 활성화된 학생인 경우에만 처리
                if self.current_student < len(self.students) and self.students[self.current_student] == student:
                    # 입력하려는 문자의 코스트 계산
                    char_cost = self.calculate_team_cost(event.char)
                    
                    # 남은 코인 확인
                    if self.remaining_costs[student] < char_cost:
                        # 코인이 부족하면 입력 차단
                        return 'break'
            
        input_text.bind('<KeyPress>', on_key_press)
        input_text.bind('<KeyRelease>', on_key_release)
        input_text.bind('<Return>', lambda event: self.submit_student_input(student))
        
        # 마우스 드래그 차단 (선택 방지)
        def block_mouse_drag(event):
                return 'break'
        
        # 더블/트리플 클릭 차단 (단어/줄 선택 방지)
        def block_multi_click(event):
            # 커서 위치는 설정하되 선택은 차단
            input_text.mark_set(tk.INSERT, f"@{event.x},{event.y}")
            return 'break'
        
        # 드래그, 더블클릭, 트리플클릭만 차단
        # 단일 클릭은 허용하여 커서 위치 설정 가능
        input_text.bind('<B1-Motion>', block_mouse_drag)  # 드래그 차단
        input_text.bind('<Double-Button-1>', block_multi_click)  # 더블클릭 차단
        input_text.bind('<Triple-Button-1>', block_multi_click)  # 트리플클릭 차단
        input_text.bind('<Button-2>', block_mouse_drag)  # 중간 버튼 차단
        input_text.bind('<Button-3>', block_mouse_drag)  # 우클릭 차단
        
        # 텍스트 변경 시 자동 크기 조정
        def on_text_size_change(event=None):
            content = input_text.get("1.0", tk.END).strip()
            if content:
                # 텍스트 길이에 따라 폰트 크기 조정
                text_length = len(content)
                if text_length <= 20:
                    font_size = 24
                elif text_length <= 40:
                    font_size = 20
                elif text_length <= 60:
                    font_size = 18
                elif text_length <= 80:
                    font_size = 16
                elif text_length <= 100:
                    font_size = 14
                else:
                    font_size = 12
                
                input_text.config(font=("Segoe UI", font_size))
        
        input_text.bind('<KeyRelease>', lambda event: (on_key_release(event), on_text_size_change(event)))
        input_text.bind('<<Modified>>', on_text_size_change)
        
        # 버튼 프레임 - 제출 버튼만
        btn_frame = Frame(panel, bg=INACTIVE_PANEL_COLOR)
        btn_frame.grid(row=3, column=0, sticky="ew", padx=5, pady=(0, 10))
        btn_frame.grid_columnconfigure(0, weight=1)
        
        submit_btn = tk.Button(btn_frame, text="✅ 제출(Enter)", command=lambda: self.submit_student_input(student),
                              font=BODY_FONT, bg=SUCCESS_COLOR, fg=TEXT_COLOR, 
                              relief=tk.RAISED, state=tk.DISABLED, width=15)
        submit_btn.grid(row=0, column=0, padx=3, pady=3)
        
        # 참조 저장
        panel.header = header
        panel.cost_info = cost_info
        panel.input_text = input_text
        panel.submit_btn = submit_btn
        panel.btn_frame = btn_frame
        
        return panel

    def update_active_student(self):
        """현재 활성화된 학생 UI 업데이트"""
        if getattr(self, 'inputs_locked', False):
            for student in self.students:
                panel = self.student_panels[student]
                panel.configure(bg=INACTIVE_PANEL_COLOR, highlightthickness=1,
                                highlightbackground=BORDER_COLOR, relief=tk.FLAT)
                panel.header.configure(bg=INACTIVE_PANEL_COLOR, fg=INACTIVE_TEXT_COLOR,
                                       text=f"⛔ {self.get_student_display_name(student)} (대기 중)")
                panel.cost_info.configure(bg=INACTIVE_PANEL_COLOR, fg=INACTIVE_TEXT_COLOR)
                panel.btn_frame.configure(bg=INACTIVE_PANEL_COLOR)
                panel.input_text.configure(state=tk.DISABLED, fg=INACTIVE_TEXT_COLOR)
                panel.submit_btn.configure(state=tk.DISABLED, bg=BORDER_COLOR)
            return

        for i, student in enumerate(self.students):
            panel = self.student_panels[student]
            
            if i == self.current_student:
                # 활성화 상태 - 더 강조된 스타일
                panel.configure(bg=ACTIVE_PANEL_COLOR, highlightbackground=ACTIVE_BORDER_COLOR, 
                               highlightthickness=3, relief=tk.RAISED)
                panel.header.configure(bg=ACTIVE_PANEL_COLOR, fg=TEXT_COLOR, 
                                     text=f"🔥 {self.get_student_display_name(student)} (현재 턴)")
                panel.cost_info.configure(bg=ACTIVE_PANEL_COLOR, fg=TEXT_COLOR)
                panel.btn_frame.configure(bg=ACTIVE_PANEL_COLOR)
                panel.input_text.configure(state=tk.NORMAL, fg=TEXT_COLOR)
                panel.submit_btn.configure(state=tk.NORMAL, bg=SUCCESS_COLOR)
                
                # 누적된 내용을 표시
                panel.input_text.delete("1.0", tk.END)
                panel.input_text.insert("1.0", self.accumulated_content)
                
                # 이전 내용 저장 (변경 추적을 위해)
                self.previous_content = self.accumulated_content
                
                # 백스페이스 코인 초기화 (새로운 학생이 시작할 때)
                self.backspace_costs[student] = 0
                
                # 현재 텍스트 상태 저장
                self.last_text_state[student] = self.accumulated_content
                
                # 입력 위치 초기화 (새로운 학생이 시작할 때)
                self.student_input_positions[student].clear()
                
                # 색상 태그 설정
                panel.input_text.tag_configure("previous", foreground="#FFD700")  # 노란색
                panel.input_text.tag_configure("current", foreground=SUCCESS_COLOR)  # 초록색
                
                # 첫 번째 학생은 모든 내용을 초록색으로, 나머지는 노란색으로
                if student == 'A':
                    # 첫 번째 학생은 처음부터 시작하므로 모든 내용이 자신의 입력
                    if self.accumulated_content:
                        panel.input_text.tag_add("current", "1.0", tk.END)
                        # 첫 번째 학생이 이미 입력한 내용이 있다면 position_to_student 초기화
                        for pos in range(len(self.accumulated_content)):
                            self.position_to_student[pos] = 'A'
                            self.student_input_positions['A'].add(pos)
                else:
                    # 두 번째 이후 학생들은 이전 내용을 노란색으로
                    if self.accumulated_content:
                        panel.input_text.tag_add("previous", "1.0", tk.END)
                        # position_to_student이 비어있다면 이전 학생들의 입력을 재구성
                        if not self.position_to_student:
                            # 이전 학생들이 입력한 내용으로 position_to_student 재구성
                            current_pos = 0
                            for prev_student in self.students[:i]:
                                if prev_student in self.student_inputs and self.student_inputs[prev_student]:
                                    # 이전 학생의 입력 길이만큼 position 할당
                                    for j in range(len(self.student_inputs[prev_student])):
                                        if current_pos < len(self.accumulated_content):
                                            self.position_to_student[current_pos] = prev_student
                                            self.student_input_positions[prev_student].add(current_pos)
                                            current_pos += 1
                
                # 태그 우선순위 설정
                panel.input_text.tag_raise("current")
                
                # 현재 활성화된 학생에게만 포커스 설정
                panel.input_text.focus_set()
            else:
                # 비활성화 상태 - 음영 처리
                panel.configure(bg=INACTIVE_PANEL_COLOR, highlightthickness=1, 
                               highlightbackground=BORDER_COLOR, relief=tk.FLAT)
                panel.header.configure(bg=INACTIVE_PANEL_COLOR, fg=INACTIVE_TEXT_COLOR,
                                     text=f"⏸️ {self.get_student_display_name(student)}")
                panel.cost_info.configure(bg=INACTIVE_PANEL_COLOR, fg=INACTIVE_TEXT_COLOR)
                panel.btn_frame.configure(bg=INACTIVE_PANEL_COLOR)
                panel.input_text.configure(state=tk.DISABLED, fg=INACTIVE_TEXT_COLOR)
                panel.submit_btn.configure(state=tk.DISABLED, bg=BORDER_COLOR)
        
        # 누적 결과도 함께 업데이트
        self.update_accumulated_result()

    def lock_inputs(self):
        """모든 학생 입력 비활성화"""
        self.inputs_locked = True
        self.update_active_student()

    def unlock_inputs(self):
        """학생 입력 다시 활성화"""
        self.inputs_locked = False
        self.update_active_student()

    def set_target_number(self, target_number: int):
        """문제 번호를 갱신"""
        if target_number is not None:
            self.target_number = int(target_number)
            self.update_problem_info()

    def prepare_for_network_round(self, target_number: int):
        """네트워크 라운드 시작 시 문제와 상태를 초기화"""
        self.lock_inputs()
        self.set_target_number(target_number)
        self.reset_for_retry()
        self.inputs_locked = False
        self.update_active_student()
        self.game_start_time = time.time()
        self.stop_timer()
        self.start_timer()

    def on_text_change(self, student):
        """텍스트 변경 시 실시간으로 현재 학생의 입력 부분을 추적하고 색상 업데이트"""
        panel = self.student_panels[student]
        current_text = panel.input_text.get("1.0", tk.END).rstrip('\n')
        

        
        # 색상 태그 재설정 - 태그 우선순위 문제 해결
        panel.input_text.tag_configure("previous", foreground="#FFD700")  # 노란색
        panel.input_text.tag_configure("current", foreground=SUCCESS_COLOR)  # 초록색
        
        # 모든 태그 제거
        panel.input_text.tag_remove("previous", "1.0", tk.END)
        panel.input_text.tag_remove("current", "1.0", tk.END)
        
        # 첫 번째 학생인 경우 모든 내용을 초록색으로
        if student == 'A':
            if len(current_text) > 0:
                panel.input_text.tag_add("current", "1.0", tk.END)
        else:
            # 두 번째 이후 학생들은 위치 기반으로 색상 적용
            if len(current_text) > 0:
                # 기본적으로 모든 텍스트를 노란색으로
                panel.input_text.tag_add("previous", "1.0", tk.END)
        
                # 현재 학생이 입력한 위치들을 초록색으로
                for pos in sorted(self.student_input_positions[student]):
                    if pos < len(current_text):
                        start_idx = f"1.0+{pos}c"
                        end_idx = f"1.0+{pos+1}c"
                        panel.input_text.tag_add("current", start_idx, end_idx)
        
        # 태그 우선순위 설정 (current가 previous보다 우선)
        panel.input_text.tag_raise("current")
        
        # 실시간 피드백 업데이트
        self.update_realtime_feedback(student)

    def submit_student_input(self, student):
        """학생 입력 제출"""
        panel = self.student_panels[student]
        content = panel.input_text.get("1.0", tk.END).strip()
        
        # 허용된 기호만 사용했는지 검증 (영문, 숫자 1 이외, 특수문자 !@#$%^& 등 차단)
        allowed_chars = set("1()+*")
        for char in content:
            if char not in allowed_chars:
                messagebox.showerror("허용되지 않은 기호", 
                                   f"'{char}'는 사용할 수 없는 기호입니다.\n사용 가능한 기호: 1, (, ), +, *\n영문, 다른 숫자, 특수문자(!@#$%^& 등)는 사용할 수 없습니다.")
                return
        
        # 실시간으로 이미 차감된 코인을 고려하여 총 사용 코스트 계산
        # 총 사용 코스트 = 초기 할당 코인 - 현재 남은 코인
        cost_to_use = self.cost_distribution[student] - self.remaining_costs[student]
        
        # 최소 코스트 사용 확인
        if cost_to_use < 1:
            # 모달창 표시 후 입력창 정리
            messagebox.showerror("최소 코스트 필요", "제출하려면 최소 1COIN를 사용해야합니다!")
            # 모달창 후 입력창에 들어간 줄바꿈 문자 제거
            self.after(10, lambda: self.clean_input_after_modal(student))
            return
        
        # 누적 내용 업데이트
        self.accumulated_content = content
        
                        # 현재 학생의 연산기호 개수 저장
        self.original_costs[student] = cost_to_use
        
        # 학생별 입력 저장 (호환성을 위해)
        self.student_inputs[student] = content
        
        # position_to_student이 제대로 유지되도록 보장
        # 현재 학생이 입력한 위치들만 해당 학생으로 표시되어 있는지 확인
        
        # UI 업데이트
        self.update_cost_display(student)
        self.update_accumulated_result()
        
        # 다음 학생으로 전환 (입력 필드는 초기화하지 않고, 다음 학생에게 누적된 내용을 보여줌)
        self.next_student()

    def clean_input_after_modal(self, student):
        """모달창 후 입력창에 들어간 불필요한 문자들 정리"""
        panel = self.student_panels[student]
        current_content = panel.input_text.get("1.0", tk.END)
        
        # 줄바꿈 문자 제거 및 공백 정리
        cleaned_content = current_content.rstrip('\n\r ')
        
        # 내용이 변경되었다면 업데이트
        if cleaned_content != current_content.rstrip('\n'):
            panel.input_text.delete("1.0", tk.END)
            panel.input_text.insert("1.0", cleaned_content)
            
            # 텍스트 상태 업데이트
            self.last_text_state[student] = cleaned_content
            
            # 실시간 피드백 업데이트
            self.update_realtime_feedback(student)

    def update_cost_display(self, student):
        """코스트 표시 업데이트"""
        panel = self.student_panels[student]
        panel.cost_info.configure(text=f"💰 할당: {self.cost_distribution[student]}\n⏱️ 남은 COIN: {self.remaining_costs[student]}")

    def update_accumulated_result(self):
        """누적 결과 업데이트 - 계산 결과만 표시"""
        # 계산 결과 업데이트
        self.calculation_text.configure(state=tk.NORMAL)
        self.calculation_text.delete("1.0", tk.END)
        
        # 색상 태그 설정
        self.calculation_text.tag_configure("active_input", foreground=SUCCESS_COLOR)
        self.calculation_text.tag_configure("completed_input", foreground=TEXT_COLOR, font=("Segoe UI", 14, "bold"))
        self.calculation_text.tag_configure("header", font=("Segoe UI", 14, "bold"))
        self.calculation_text.tag_configure("result", font=("Segoe UI", 14, "bold"))
        
        # 실시간 연결식 표시
        accumulated_expression = self.accumulated_content
        
        # 현재 학생 표시
        current_student = self.students[self.current_student] if self.current_student < len(self.students) else "완료"
        if current_student != "완료":
            current_student_name = self.get_student_display_name(current_student)
            self.calculation_text.insert("end", f"🔢 현재 턴: {current_student_name} 입력을 기다리는중...\n\n", "header")
        else:
            current_student_name = "완료"
            self.calculation_text.insert("end", f"🔢 현재 턴: {current_student_name}\n\n", "header")
        
        if accumulated_expression:
            # 계산식을 표시
            self.calculation_text.insert("end", "🧮 계산식:\n", "header")
            self.calculation_text.insert("end", accumulated_expression, "completed_input")
            
            # 계산 시도
            try:
                safe_expr = accumulated_expression.replace(" ", "")
                
                import re
                # 허용된 문자만 확인 (1, +, *, (, ))
                if not re.match(r'^[1+*()]+$', safe_expr):
                    raise ValueError("허용되지 않는 문자가 포함되어 있습니다")
                
                # 잘못된 수식 패턴 검사
                # 연속된 연산자 확인 (++, **, +*, *+ 등)
                if re.search(r'[+*]{2,}', safe_expr):
                    raise ValueError("연산자가 연속으로 사용되었습니다")
                
                # 빈 괄호 확인
                if '()' in safe_expr:
                    raise ValueError("빈 괄호는 사용할 수 없습니다")
                
                # 연산자로 시작하거나 끝나는 경우
                if safe_expr and (safe_expr[0] in '+*' or safe_expr[-1] in '+*'):
                    raise ValueError("수식이 연산자로 시작하거나 끝날 수 없습니다")
                
                # 괄호 직전/직후 연산자 확인
                if re.search(r'\([+*]', safe_expr) or re.search(r'[+*]\)', safe_expr):
                    raise ValueError("괄호 안에 잘못된 연산자가 있습니다")
                
                if safe_expr.count('(') != safe_expr.count(')'):
                    result_text = "\n\n⏳ 수식 작성 중..."
                else:
                    result_value = eval(safe_expr, {"__builtins__": {}}, {})
                    
                    result_text = f"\n\n📊 결과: {result_value}\n"
                    
                    if str(result_value) == str(self.target_number):
                        result_text += f"🎉 정답 달성! "
                
            except ValueError as e:
                result_text = f"\n\n❌ 수식 오류: {str(e)}"
            except (SyntaxError, ZeroDivisionError, TypeError) as e:
                result_text = "\n\n⏳ 수식 작성 중..."
            except Exception as e:
                result_text = f"\n\n❌ 계산 오류: {str(e)}"
            
            self.calculation_text.insert("end", result_text, "result")
        else:
            # 아직 아무 입력이 없는 상태
            calc_display = ""
            
            self.calculation_text.insert("1.0", calc_display)

        self.calculation_text.configure(state=tk.DISABLED)
    
    def _handle_completion(self):
        """완료 처리 (중복 방지)"""
        self.check_game_completion()
        self._completion_scheduled = False

    def next_student(self):
        """다음 학생으로 전환"""
        # 현재 결과 확인
        accumulated_expression = self.accumulated_content
        success = False
        is_incomplete = False
        
        if accumulated_expression:
            # 불완전한 식 체크 (calculate_expression 사용)
            from game_logic.calculator import calculate_expression
            calc_result = calculate_expression(accumulated_expression)
            
            if isinstance(calc_result, str) and ("불완전" in calc_result or "Invalid" in calc_result):
                is_incomplete = True
            else:
                try:
                    safe_expr = accumulated_expression.replace(" ", "")
                    if safe_expr.count('(') == safe_expr.count(')'):
                        result_value = eval(safe_expr, {"__builtins__": {}}, {})
                        if str(result_value) == str(self.target_number):
                            success = True
                except:
                    pass
        
        # 마지막 학생(D)이고 불완전한 식인 경우 실패 처리 후 새 사이클 시작
        if self.current_student == 3 and is_incomplete:
            # 불완전한 식인 경우 별도 모달창 없이 바로 reset_for_new_cycle 호출
            # result_value를 "식이 불완전하여 계산할 수 없음."으로 설정하여 기존 실패 모달에서 처리
            self.reset_for_new_cycle_with_incomplete()
            return
        
        # 정답이면 게임 완료
        if success:
            self.check_game_completion()
            return
        
        # 정답이 아니면 다음 학생으로
        if self.current_student < 3:
            self.current_student += 1
            self.update_active_student()
        else:
            # D에서 끝 - 한 사이클 완료, 코스트만 초기화하고 A부터 다시 시작
            self.reset_for_new_cycle()

    def check_game_completion(self):
        """현재 게임 완료 체크 및 결과 표시"""
        # 최종 결과 계산
        accumulated_expression = self.accumulated_content
        
        success = False
        result_value = None
        if accumulated_expression:
            try:
                safe_expr = accumulated_expression.replace(" ", "")
                if safe_expr.count('(') == safe_expr.count(')'):
                    result_value = eval(safe_expr, {"__builtins__": {}}, {})
                    if str(result_value) == str(self.target_number):
                        success = True
                        # 성공 시 히스토리에 기록
                        self.record_success(accumulated_expression)
            except:
                pass
        
        total_cost_used = sum(self.cost_distribution[s] - self.remaining_costs[s] for s in self.students)
        
        if success:
            if self.network_mode:
                self.reset_for_retry()
            else:
                # 정답인 경우: 정답 효과음 재생
                play_correct_sound()
                message = f"🎉 성공!\n문제: {self.target_number}\n결과: {result_value}\n총 사용한 COIN 갯수: {total_cost_used}\n\n남은 시간 동안 팀별 회의가 가능하며 'enter'를 누르면 다시 입력이 초기화된 상태에서 도전할 수 있습니다.\n<yellow>'enter'누르면 반드시 첫번째 수험생은 대전석 바로 앉아야합니다.</yellow>"
                silent_showinfo("성공!", message)
                # 성공 후 자동으로 초기화하여 재도전 가능
                self.reset_for_retry()
        else:
            # 실패 시 오답 효과음 재생 및 감점요인 증가
            play_wrong_sound()
            self.deduction_count += 1
            self.update_history_display()  # 히스토리 업데이트
            
            message = f"😔 아쉽게 실패!\n문제: {self.target_number}\n결과: {result_value if result_value is not None else '계산 오류'}\n총 사용한 COIN 갯수: {total_cost_used}"
            silent_showinfo("게임 완료", message)

    def update_problem_info(self):
        """문제 정보 표시 업데이트"""
        self._update_problem_info_text()
        self._update_cost_info_display()
    
    def _update_problem_info_text(self):
        """문제 정보 텍스트 업데이트 (다중 색상)"""
        self.problem_info_text.config(state=tk.NORMAL)
        self.problem_info_text.delete("1.0", tk.END)
        
        # '문제: ' (흰색) + '숫자' (노란색)
        self.problem_info_text.insert("1.0", "문제: ", "label")
        self.problem_info_text.insert(tk.END, str(self.target_number), "number")
        
        self.problem_info_text.config(state=tk.DISABLED)
    
    def _update_cost_info_display(self):
        """기호별 코스트 정보 업데이트"""
        # 최신 팀전용 코스트 설정 로드
        from utils.problem_store import load_team_costs
        team_costs = load_team_costs()
        
        # 각 기호의 코스트 레이블 업데이트
        symbols = ['1', '(', ')', '+', '*']
        for symbol in symbols:
            cost = team_costs.get(symbol, 1)
            if symbol in self.cost_labels:
                self.cost_labels[symbol].config(text=str(cost))

    def calculate_team_cost(self, expression: str) -> int:
        """팀전용 코스트 계산 - 연속된 1도 지원"""
        # 최신 코스트 설정을 동적으로 로드 (설정 변경 시 즉시 반영)
        from utils.problem_store import load_team_costs
        cost_settings = load_team_costs()
        
        total_cost = 0
        i = 0
        while i < len(expression):
            if expression[i] == '1':
                # 연속된 1의 개수 세기
                ones_count = 0
                j = i
                while j < len(expression) and expression[j] == '1':
                    ones_count += 1
                    j += 1
                # 연속된 1의 개수에 설정된 코스트 곱하기
                total_cost += ones_count * cost_settings.get('1', 1)
                i = j
            elif expression[i] in cost_settings:
                total_cost += cost_settings[expression[i]]
                i += 1
            else:
                i += 1
        return total_cost

    def clear_student_input(self, student):
        """학생 입력 지우기"""
        panel = self.student_panels[student]
        panel.input_text.delete("1.0", tk.END)
        # 실시간 업데이트
        self.after(10, self.update_accumulated_result)

    def update_realtime_feedback(self, student):
        """실시간 피드백 업데이트: 남은 코스트 계산 및 누적 결과 반영"""
        panel = self.student_panels[student]
        
        # 현재 입력 내용 가져오기
        current_input = panel.input_text.get("1.0", tk.END).strip()
        
        # 변경 사항에 따른 코스트 계산
        import difflib
        
        old_chars = list(self.previous_content)
        new_chars = list(current_input)
        
        matcher = difflib.SequenceMatcher(None, old_chars, new_chars)
        
        # 백스페이스로 이미 차감된 코인
        already_used = self.backspace_costs[student]
        
        # 추가된 문자의 코스트만 계산 (삭제는 이미 백스페이스로 처리됨)
        additional_cost = 0
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'insert':
                # 추가된 문자들의 실제 코스트
                inserted_text = ''.join(new_chars[j1:j2])
                additional_cost += self.calculate_team_cost(inserted_text)
            elif tag == 'replace':
                # 교체의 경우 추가된 부분만 계산 (삭제는 이미 백스페이스로 처리됨)
                inserted_text = ''.join(new_chars[j1:j2])
                additional_cost += self.calculate_team_cost(inserted_text)
        
        # 총 사용 코스트 = 이미 사용한 백스페이스 코인 + 추가 코스트
        current_cost = already_used + additional_cost
        
        # 남은 코스트 계산 (이미 차감된 백스페이스 코인 고려)
        remaining = self.remaining_costs[student]
        
        # 코스트 정보 레이블 업데이트
        panel.cost_info.configure(text=f"💰 할당: {self.cost_distribution[student]}\n⏱️ 남은 COIN: {remaining}")
        
        # 코스트 초과 시 색상 변경
        if remaining < 0:
            panel.cost_info.configure(fg=ERROR_COLOR)
        else:
            panel.cost_info.configure(fg=TEXT_COLOR)
        
        # 누적 결과창도 실시간으로 업데이트
        self.update_accumulated_result()
        
        # 네 번째 학생(D)의 COIN이 모두 소모되면 자동 제출
        if student == 'D' and self.current_student == 3 and remaining <= 0 and current_input.strip() and not self.auto_submit_scheduled:
            # 자동 제출 스케줄링 (중복 방지)
            self.auto_submit_scheduled = True
            self.after(100, lambda: self.auto_submit_last_student())
        
        # 모든 학생의 코스트 표시 업데이트 (실시간 반영)
        for other_student in self.students:
            if other_student != student:
                other_panel = self.student_panels[other_student]
                # 비활성 학생들도 코스트 표시는 업데이트
                other_panel.cost_info.configure(
                    text=f"💰 할당: {self.cost_distribution[other_student]}\n⏱️ 남은 COIN: {self.remaining_costs[other_student]}"
                )

    def auto_submit_last_student(self):
        """네 번째 학생(D)의 COIN이 모두 소모되었을 때 자동 제출"""
        # 플래그 리셋
        self.auto_submit_scheduled = False
        
        if self.current_student == 3:  # D 학생
            student = 'D'
            panel = self.student_panels[student]
            content = panel.input_text.get("1.0", tk.END).strip()
            
            # 입력이 있고 COIN이 모두 소모된 경우에만 자동 제출
            if content and self.remaining_costs[student] <= 0:
                # 자동 제출 메시지 표시 (선택사항)
                # messagebox.showinfo("자동 제출", "D학생의 COIN이 모두 소모되어 자동 제출됩니다.")
                
                # 제출 처리
                self.submit_student_input(student)

    def reset_all_inputs(self):
        """모든 학생의 입력을 초기화 (코스트도 복원)"""
        import tkinter.messagebox as messagebox
        
        if messagebox.askyesno("전체 초기화", "모든 입력을 초기화하시겠습니까?"):
            # 모든 학생의 입력 초기화
            for student in self.students:
                self.student_inputs[student] = ""
                # 각 패널의 입력창도 초기화
                panel = self.student_panels[student]
                panel.input_text.configure(state=tk.NORMAL)
                panel.input_text.delete("1.0", tk.END)
            
            # 코스트 복원
            self.remaining_costs = self.cost_distribution.copy()
            
            # 누적 입력 관련 변수 초기화
            self.accumulated_content = ""
            self.student_ranges = {'A': [], 'B': [], 'C': [], 'D': []}
            self.original_costs = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
            self.previous_content = ""
            
            # 첫 번째 학생으로 돌아가기
            self.current_student = 0
            self.update_active_student()
            
            # 감점요인 증가 (초기화)
            self.deduction_count += 1
            
            # 히스토리 업데이트 (감점요인 반영)
            self.update_history_display()
            
            # 코스트 정보 업데이트 (관리자가 설정을 변경했을 수 있으므로)
            self._update_cost_info_display()
            
            # 커스텀 모달창으로 팀별회의 메시지 표시 (확인 버튼 없음)
            silent_showinfo_no_button("팀별회의", "남은 시간 동안 팀별 회의가 가능하며 'enter'를 누르면 다시 입력이 초기화된 상태에서 도전할 수 있습니다.\n<yellow>'enter'누르면 반드시 첫번째 수험생은 대전석에 바로 앉아야합니다.</yellow>")

    def reset_for_retry(self):
        """성공 후 재도전을 위한 초기화"""
        # 2라운드는 단일 문제이므로 문제를 변경하지 않음
        
        # 모든 학생의 입력 초기화
        for student in self.students:
            self.student_inputs[student] = ""
            panel = self.student_panels[student]
            panel.input_text.configure(state=tk.NORMAL)
            panel.input_text.delete("1.0", tk.END)
        
        # 코스트 복원
        self.remaining_costs = self.cost_distribution.copy()
        
        # 누적 입력 관련 변수 초기화
        self.accumulated_content = ""
        self.student_ranges = {'A': [], 'B': [], 'C': [], 'D': []}
        self.original_costs = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        self.previous_content = ""
        
        # 백스페이스로 차감된 코인 초기화
        self.backspace_costs = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        
        # 텍스트 상태 초기화
        self.last_text_state = {'A': '', 'B': '', 'C': '', 'D': ''}
        
        # 입력 위치 초기화
        self.student_input_positions = {'A': set(), 'B': set(), 'C': set(), 'D': set()}
        self.position_to_student = {}
        
        # 첫 번째 학생으로 돌아가기
        self.current_student = 0
        
        # 문제 정보 업데이트
        self.update_problem_info()
        
        # 코스트 표시 업데이트
        for student in self.students:
            self.update_cost_display(student)
        
        # UI 업데이트
        self.update_active_student()
        self.update_accumulated_result()

    def reset_for_new_cycle_with_incomplete(self):
        """불완전한 식으로 실패한 경우의 새 사이클 시작"""
        # 자동 제출 플래그 리셋
        self.auto_submit_scheduled = False
        
        # 불완전한 식인 경우 강제로 실패 처리
        accumulated_expression = self.accumulated_content
        success = False
        result_value = "식이 불완전하여 계산할 수 없음."
        
        # 사용한 총 코스트 계산
        total_cost_used = sum(self.cost_distribution[s] - self.remaining_costs[s] for s in self.students)
        
        # 틀린 경우 처리 (기존 로직과 동일)
        play_wrong_sound()
        self.deduction_count += 1
        self.update_history_display()  # 히스토리 업데이트
        
        message = f"😔 틀렸습니다!\n문제: {self.target_number}\n결과: {result_value}\n총 사용한 COIN 갯수: {total_cost_used}\n\n<red>오답입니다. 팀원 모두 개인별 점수 5점씩 감점됩니다.</red>\n남은 시간 동안 팀별 회의가 가능하며 'enter'를 누르면 다시 입력이 초기화된 상태에서 도전할 수 있습니다.\n<yellow>'enter'누르면 반드시 첫번째 수험생은 대전석에 바로 앉아야합니다.</yellow>"
        silent_showinfo("틀렸습니다", message)
        
        # 모든 학생의 입력은 유지하지만 UI는 초기화
        for student in self.students:
            panel = self.student_panels[student]
            panel.input_text.configure(state=tk.NORMAL)
            panel.input_text.delete("1.0", tk.END)
        
        # 코스트만 복원 (문제 번호는 그대로)
        self.remaining_costs = self.cost_distribution.copy()
        self.backspace_costs = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        self.student_input_positions = {'A': set(), 'B': set(), 'C': set(), 'D': set()}
        self.position_to_student = {}
        self.last_text_state = {'A': '', 'B': '', 'C': '', 'D': ''}
        self.accumulated_content = ""
        self.student_inputs = {'A': '', 'B': '', 'C': '', 'D': ''}
        self.original_costs = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        self.previous_content = ""
        
        # A 학생부터 다시 시작
        self.current_student = 0
        
        # UI 업데이트
        self.update_active_student()
        self.update_accumulated_result()

    def reset_for_new_cycle(self):
        """한 사이클 완료 후 정답 확인 및 코스트만 초기화하고 다시 A부터 시작"""
        # 자동 제출 플래그 리셋
        self.auto_submit_scheduled = False
        
        # 현재 누적된 결과 확인
        accumulated_expression = self.accumulated_content
        success = False
        result_value = None
        
        if accumulated_expression:
            try:
                safe_expr = accumulated_expression.replace(" ", "")
                if safe_expr.count('(') == safe_expr.count(')'):
                    result_value = eval(safe_expr, {"__builtins__": {}}, {})
                    if str(result_value) == str(self.target_number):
                        success = True
            except:
                pass
        
        # 사용한 총 코스트 계산
        total_cost_used = sum(self.cost_distribution[s] - self.remaining_costs[s] for s in self.students)
        
        if success:
            # 정답인 경우: 정답 효과음 재생
            play_correct_sound()
            message = f"🎉 정답!\n문제: {self.target_number}\n결과: {result_value}\n총 사용한 COIN 갯수: {total_cost_used}\n\n남은 시간 동안 팀별 회의가 가능하며 'enter'를 누르면 다시 입력이 초기화된 상태에서 도전할 수 있습니다.\n<yellow>'enter'누르면 반드시 첫번째 수험생은 대전석에 바로 앉아야합니다.</yellow>"
            silent_showinfo("정답!", message)
            # 성공 시 히스토리에 기록
            self.record_success(accumulated_expression)
        else:
            # 틀린 경우: 오답 효과음 재생 및 감점요인 증가
            play_wrong_sound()
            self.deduction_count += 1
            self.update_history_display()  # 히스토리 업데이트
            
            if result_value is not None:
                message = f"😔 틀렸습니다!\n문제: {self.target_number}\n결과: {result_value}\n총 사용한 COIN 갯수: {total_cost_used}\n\n<red>오답입니다. 팀원 모두 개인별 점수 5점씩 감점됩니다.</red>\n남은 시간 동안 팀별 회의가 가능하며 'enter'를 누르면 다시 입력이 초기화된 상태에서 도전할 수 있습니다.\n<yellow>'enter'누르면 반드시 첫번째 수험생은 대전석에 바로 앉아야합니다.</yellow>"
            else:
                message = f"😔 틀렸습니다!\n문제: {self.target_number}\n결과: 계산 오류\n총 사용한 COIN 갯수: {total_cost_used}\n\n<red>오답입니다. 팀원 모두 개인별 점수 5점씩 감점됩니다.</red>\n남은 시간 동안 팀별 회의가 가능하며 'enter'를 누르면 다시 입력이 초기화된 상태에서 도전할 수 있습니다.\n<yellow>'enter'누르면 반드시 첫번째 수험생은 대전석에 바로 앉아야합니다.</yellow>"
            silent_showinfo("틀렸습니다", message)
        
        # 모든 학생의 입력은 유지하지만 UI는 초기화
        for student in self.students:
            panel = self.student_panels[student]
            panel.input_text.configure(state=tk.NORMAL)
            panel.input_text.delete("1.0", tk.END)
        
        # 코스트만 복원 (문제 번호는 그대로)
        self.remaining_costs = self.cost_distribution.copy()
        
        # 누적 입력 관련 변수 초기화
        self.accumulated_content = ""
        self.student_ranges = {'A': [], 'B': [], 'C': [], 'D': []}
        self.original_costs = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        self.previous_content = ""
        
        # 백스페이스로 차감된 코인 초기화
        self.backspace_costs = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
        
        # 텍스트 상태 초기화
        self.last_text_state = {'A': '', 'B': '', 'C': '', 'D': ''}
        
        # 입력 위치 초기화
        self.student_input_positions = {'A': set(), 'B': set(), 'C': set(), 'D': set()}
        self.position_to_student = {}
        
        # 첫 번째 학생으로 돌아가기
        self.current_student = 0
        
        # 코스트 표시 업데이트
        for student in self.students:
            self.update_cost_display(student)
        
        # UI 업데이트
        self.update_active_student()
        self.update_accumulated_result()
    
    # ===== 타이머 관련 메서드들 =====
    def start_timer(self):
        """타이머 시작"""
        self.stop_timer()
        self.remaining_sec = self.timer_minutes * 60  # 설정된 시간을 초로 변환
        self.game_start_time = time.time()
        self.update_timer_label()
        self.timer_id = self.after(1000, self._tick)
    
    def _tick(self):
        """타이머 틱"""
        # 전체 게임 시간은 항상 감소
        self.remaining_sec -= 1
        
        # 타이머 표시 업데이트
        self.update_timer_label()
        
        if self.remaining_sec <= 0:
            # 시간 종료
            self.stop_timer()
            play_timer_end_sound(sound_type='chime')
            if self.network_mode and self.network_delegate:
                try:
                    self.network_delegate.on_team_timer_expired()
                except Exception:
                    pass
            
            # 시간 초과 시 모든 학생의 입력창 초기화
            for student in self.students:
                panel = self.student_panels[student]
                panel.input_text.configure(state=tk.NORMAL)
                panel.input_text.delete("1.0", tk.END)
                panel.input_text.configure(state=tk.DISABLED)
            
            messagebox.showinfo("시간 종료", f"{self.timer_minutes}분이 모두 경과했습니다!")
            # 메인 메뉴로 돌아가지 않고 현재 화면에 머물기
        else:
            self.timer_id = self.after(1000, self._tick)
    
    def update_timer_label(self):
        """타이머 표시 업데이트"""
        m = self.remaining_sec // 60
        s = self.remaining_sec % 60
        
        # 10초 이하일 때 깜빡임 효과 시작
        if self.remaining_sec <= 10 and self.remaining_sec > 0:
            if self.blink_timer_id is None:
                self.start_timer_blink()
        elif self.remaining_sec <= 30:
            # 30초 이하 10초 초과: 깜빡임 중지하고 고정 빨간색
            self.stop_timer_blink()
            self.timer_label.config(text=f"{m:02d}:{s:02d}", fg=WARNING_COLOR)
        else:
            # 30초 초과: 일반 색상
            self.stop_timer_blink()
            self.timer_label.config(text=f"{m:02d}:{s:02d}", fg=TEXT_COLOR)
    
    def start_timer_blink(self):
        """타이머 깜빡임 효과 시작"""
        if self.blink_timer_id is None:
            self.timer_blink_effect()
    
    def stop_timer_blink(self):
        """타이머 깜빡임 효과 중지"""
        if self.blink_timer_id:
            self.after_cancel(self.blink_timer_id)
            self.blink_timer_id = None
            self.timer_blink_state = False
    
    def timer_blink_effect(self):
        """타이머 깜빡임 효과 구현"""
        if self.remaining_sec <= 10 and self.remaining_sec > 0:
            m = self.remaining_sec // 60
            s = self.remaining_sec % 60
            
            # 깜빡임 상태 전환
            self.timer_blink_state = not self.timer_blink_state
            
            if self.timer_blink_state:
                # 깜빡임 ON: 빨간색
                self.timer_label.config(text=f"{m:02d}:{s:02d}", fg=WARNING_COLOR)
            else:
                # 깜빡임 OFF: 배경색과 비슷한 어두운 색
                self.timer_label.config(text=f"{m:02d}:{s:02d}", fg="#4a4a5e")
            
            # 500ms 간격으로 깜빡임 반복
            self.blink_timer_id = self.after(500, self.timer_blink_effect)
        else:
            # 10초 이하가 아니면 깜빡임 중지
            self.stop_timer_blink()
    
    def stop_timer(self):
        """타이머 중지"""
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
        self.stop_timer_blink()
    
    # ===== 히스토리 관련 메서드들 =====
    def record_success(self, expression):
        """성공 기록 추가. 2라운드 팀전 모드에서는 최고기록 1개만 유지."""
        from game_logic.expression_parser import normalize_expression
        
        # 기록 시간 측정 (밀리초 단위까지 정확하게)
        if self.game_start_time is None: self.game_start_time = time.time()
        elapsed_time = time.time() - self.game_start_time
        elapsed_seconds = int(elapsed_time)
        if elapsed_seconds > self.timer_minutes * 60: return
        
        # 현재 제출된 답안 정보
        total_cost = sum(self.cost_distribution[s] - self.remaining_costs[s] for s in self.students)
        normalized_expression = normalize_expression(expression.strip())
        
        # 문제 정보 가져오기
        threshold_coin = None
        is_optimal = False
        if self.team_problems and self.problem_index < len(self.team_problems):
            problem_data = self.team_problems[self.problem_index]
            if isinstance(problem_data, dict):
                threshold_coin = problem_data.get("threshold_coin")
                if problem_data.get("optimal_cost") is not None:
                    is_optimal = total_cost == problem_data.get("optimal_cost")

        # 기준 COIN 값이 설정되어 있고, 현재 코스트가 기준보다 크거나 같으면 히스토리에 추가하지 않음
        if threshold_coin is not None and total_cost >= threshold_coin:
            return

        # 새 기록 생성 (밀리초 단위까지 저장)
        new_record = {
            'time': elapsed_time,  # 실제 소요 시간 (초.밀리초)
                'cost': total_cost,
                'expression': expression.strip(),
                'problem': self.target_number,
            'is_optimal': is_optimal,
                'students': {s: self.student_inputs[s] for s in self.students}
            }
        if self.network_mode and self.network_delegate:
            try:
                self.network_delegate.on_team_attempt_recorded({
                    'expression': normalized_expression,
                    'cost': total_cost,
                    'time': elapsed_time,
                    'is_optimal': is_optimal
                })
            except Exception:
                pass
            
        # 2라운드 팀전 모드에서는 최고기록 1개만 유지
        # 기존 기록이 없거나, 새 기록이 더 좋은 경우에만 교체
        if not self.success_history:
            # 첫 번째 성공 기록
            self.success_history = [new_record]
        else:
            current_best = self.success_history[0]
            # 새 기록이 더 좋은 경우 교체 (cost가 더 작거나, 같으면 시간이 더 짧아야 함)
            if (total_cost < current_best['cost'] or 
                (total_cost == current_best['cost'] and elapsed_time < current_best['time'])):
                self.success_history = [new_record]
            # 새 기록이 더 나쁘거나 같으면 기존 기록 유지 (히스토리에 추가하지 않음)

            self.update_history_display()
    
    def update_history_display(self):
        """히스토리 표시를 업데이트합니다. 2라운드 팀전 모드에서는 최고기록 1개만 표시합니다."""
        if not self.success_history:
            history_text = "🏆 최고기록"
            if self.deduction_count > 0:
                 history_text += f"\n❌ 감점요인: {self.deduction_count}회"
            self._update_team_history_text(history_text, is_empty=True)
            return

        # 2라운드 팀전 모드에서는 최고기록 1개만 표시
        best_record = self.success_history[0]  # record_success에서 이미 최고기록만 유지하므로 첫 번째가 최고기록
        
        # 시간을 초.밀리초 형식으로 표시 (예: 1.23초)
        total_seconds = best_record['time']
        seconds = int(total_seconds)
        milliseconds = int((total_seconds - seconds) * 100)  # 밀리초를 2자리로 표시
        
        if seconds >= 60:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            time_text = f"{minutes}분 {remaining_seconds}.{milliseconds:02d}초"
        else:
            time_text = f"{seconds}.{milliseconds:02d}초"
        
        expr = best_record['expression']
        
        final_text = f"🏆 최고기록\n{expr}\n사용한 COIN 갯수: {best_record['cost']}개, 걸린시간: {time_text}\n승리시 획득 가능점수: {140-best_record['cost']-self.deduction_count*5}"
        if best_record.get('is_optimal', False):
            final_text += " ⭐최적해"
        
        if self.deduction_count > 0:
            final_text += f"\n❌ 감점요인: {self.deduction_count}회"
            
        self._adjust_history_font_size(final_text)
        self._update_team_history_text(final_text, is_empty=False)
    
    def _adjust_history_font_size(self, text):
        """히스토리 레이블의 폰트 크기를 텍스트 길이에 따라 동적으로 조정"""
        # 기본 폰트 크기 줄임
        base_font_size = 18
        min_font_size = 8
        
        # 텍스트를 줄별로 분리하여 각 줄의 최대 길이 확인
        lines = text.split('\n')
        max_line_length = 0
        expression_line = ""
        
        for i, line in enumerate(lines):
            # 두 번째 줄(인덱스 1)이 보통 식이므로 특별히 처리
            if i == 1 and ':' not in line and '❌' not in line:
                expression_line = line
                max_line_length = max(max_line_length, len(line))
            else:
                max_line_length = max(max_line_length, len(line))
        
        # 식의 길이에 따라 폰트 크기 조정
        if expression_line:
            expr_length = len(expression_line)
            if expr_length <= 30:
                font_size = base_font_size
            elif expr_length <= 40:
                font_size = 20
            elif expr_length <= 50:
                font_size = 18
            elif expr_length <= 60:
                font_size = 16
            elif expr_length <= 70:
                font_size = 14
            elif expr_length <= 80:
                font_size = 12
            elif expr_length <= 90:
                font_size = 10
            else:
                font_size = min_font_size
        else:
            # 식이 없는 경우 기본 크기
            font_size = base_font_size
        
        # 폰트 설정 업데이트
        current_font = self.history_text.cget("font")
        if isinstance(current_font, str):
            # 폰트가 문자열로 설정된 경우
            font_family = "Segoe UI"
        else:
            # 폰트가 튜플로 설정된 경우
            font_family = current_font[0] if len(current_font) > 0 else "Segoe UI"
        
        new_font = (font_family, font_size, "bold")
        self.history_text.config(font=new_font)
        
        # 헤더 태그 폰트도 함께 업데이트 (크기 줄임)
        header_font = (font_family, font_size + 3, "bold")
        self.history_text.tag_configure("header", font=header_font)
    
    def _update_team_history_text(self, text, is_empty=False):
        """히스토리 텍스트를 다중 색상으로 업데이트 (2라운드용)"""
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete("1.0", tk.END)
        
        if is_empty:
            if "❌" in text:
                lines = text.split('\n')
                self.history_text.insert("1.0", lines[0], "header")
                if len(lines) > 1:
                    self.history_text.insert(tk.END, '\n')
                    self._parse_and_color_fail_line(lines[1])
            else:
                self.history_text.insert("1.0", text, "header")
        else:
            record_blocks = text.split('\n\n')
            for i, block in enumerate(record_blocks):
                if i > 0:
                    self.history_text.insert(tk.END, '\n\n')
                
                lines = block.split('\n')
                
                for j, line in enumerate(lines):
                    if j > 0:
                        self.history_text.insert(tk.END, '\n')

                    # 감점요인 라인은 별도로 처리
                    if line.strip().startswith("❌"):
                        self._parse_and_color_fail_line(line)
                        continue

                    is_optimal = "⭐" in line
                    content = line.replace("⭐최적해", "").strip()

                    if j == 0:
                        if content.startswith("🏆"):
                            self.history_text.insert(tk.END, content, "header")
                        else:
                            self.history_text.insert(tk.END, content, "value")
                    elif j in [1, 2, 3]:
                        if ":" in content:
                            self._parse_and_color_detail_line(content)
                        else:
                            self.history_text.insert(tk.END, content, "value")
                    
                    if is_optimal:
                        self.history_text.insert(tk.END, " ⭐최적해", "optimal")
        
        self.history_text.config(state=tk.DISABLED)

    def _parse_and_color_detail_line(self, line):
        """팀전 히스토리의 상세 정보 라인 파싱 및 색상 적용"""
        if '(' in line and ')' in line: # 간략한 포맷
            match = re.match(r"(.+)\s\((.+)\)", line)
            if match:
                self.history_text.insert(tk.END, match.group(1), "value")
                self.history_text.insert(tk.END, f" ({match.group(2)})", "title")
            else:
                self.history_text.insert(tk.END, line, "title")
        elif ':' in line: # 자세한 포맷
            parts = line.split(',')
            for k, part in enumerate(parts):
                if k > 0: self.history_text.insert(tk.END, ',', "title")
                
                sub_parts = part.strip().split(':', 1)
                self.history_text.insert(tk.END, sub_parts[0] + ':', "title")
                if len(sub_parts) > 1:
                    self.history_text.insert(tk.END, sub_parts[1], "value")

    def _parse_and_color_fail_line(self, line):
        """감점요인 라인 파싱 및 색상 적용"""
        parts = line.strip().split(':')
        self.history_text.insert(tk.END, parts[0] + ':', "fail")
        if len(parts) > 1:
            self.history_text.insert(tk.END, parts[1], "fail")

    
    def go_to_main_menu(self):
        """메인 메뉴로 돌아가기"""
        # 단축키 바인딩 해제
        try:
            self.unbind_all('<Control-l>')
            self.unbind_all('<Control-L>')
            self.unbind_all('<Shift-L>')
            self.unbind_all('<Shift-l>')
            self.unbind('<Control-l>')
            self.unbind('<Control-L>')
            self.unbind('<Shift-L>')
            self.unbind('<Shift-l>')
        except:
            pass
        
        from ui.main_menu_view import MainMenuView
        self.master.switch_frame(MainMenuView)
    
    def _shortcut_menu(self, event=None):
        """단축키로 메인 메뉴로 돌아가기"""
        self.go_to_main_menu()
        return 'break'
    
    # ===== 작전회의 관련 메서드들 제거됨 =====
    # 작전회의 기능이 제거되어 관련 메서드들이 더 이상 사용되지 않습니다. 