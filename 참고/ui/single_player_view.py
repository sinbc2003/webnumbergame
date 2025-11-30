# ui/single_player_view.py
import tkinter as tk
from tkinter import Text, messagebox, Frame, Label
from constants import *
from game_logic.calculator import analyze_input
import random
import time
from sounds.sound_effects import play_correct_sound, play_wrong_sound, play_timer_end_sound
from utils.problem_store import load_problems, load_timer_settings, load_mode1_problems, load_mode2_problems, load_mode1_costs, load_mode2_costs

class SinglePlayerView(tk.Frame):
    def __init__(self, master, mode='normal'):
        super().__init__(master, bg=BG_COLOR)
        self.master = master
        self.mode = mode
        
        # 히스토리 관련 초기화
        self.success_history = []
        self.panel_start_times = [None, None]  # 각 패널의 시작 시간
        self.first_student_cost = None  # 첫 번째 학생의 코스트 저장
        self.optimal_cost = None  # 현재 문제의 최적 코스트
        self.team_deduction_points = 0  # 팀전체 감점 누적
        self.game_start_time = None  # 게임 시작 시간
        
        # 현재 모드 (I 또는 II)
        self.current_mode = 'I'
        
        # 타이머 설정 로드
        timer_settings = load_timer_settings()
        self.mode1_minutes = timer_settings['mode1_minutes']
        self.mode2_minutes = timer_settings['mode2_minutes']
        self.timer_minutes = self.mode1_minutes  # 초기값은 모드 I
        
        # 모드 I, II 문제와 코스트 로드 (create_widgets 전에)
        self.mode1_problems = load_mode1_problems()
        self.mode2_problems = load_mode2_problems()
        self.mode1_costs = load_mode1_costs()
        self.mode2_costs = load_mode2_costs()
        
        self.problems = self.mode1_problems  # 초기값은 모드 I 문제
        self.current_costs = self.mode1_costs  # 초기값은 모드 I 코스트
        self.problem_index = 0

        if self.problems:
            problem = self.problems[0]
            if isinstance(problem, dict):
                self.target_number = problem.get("target", 0)
                self.optimal_cost = problem.get("optimal_cost", None)
            else:
                self.target_number = int(problem)
                self.optimal_cost = None
        else:
            self.target_number = random.randint(10, 50)
            self.optimal_cost = None
        
        # UI 생성
        self.create_widgets()
        
        # 전체 UI 업데이트
        self.update()
        self.update_idletasks()

        # panels will be created after this call; postpone setting problem using after_idle
        def _init_labels():
            self.load_problem()

        self.after_idle(_init_labels)
        
        # 게임 시작 시 자동으로 타이머 시작
        self.after_idle(self.auto_start_timer)

    def auto_start_timer(self):
        """게임 시작 시 자동으로 타이머를 시작하는 메서드"""
        # 패널을 활성화하고 타이머 시작
        self.active_panel_index = 0
        if hasattr(self, '_panels') and len(self._panels) > 0:
            self._panels[0].set_editable(True)
        self.start_timer()

    def create_widgets(self):
        # Configure grid
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)  # 하단 컨트롤 프레임용
        self.columnconfigure(0, weight=1)

        # Main panel frame
        panel_frame = tk.Frame(self, bg=BG_COLOR)
        panel_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        panel_frame.rowconfigure(0, weight=1)
        panel_frame.columnconfigure(0, weight=1)

        from ui.student_panel import StudentPanel
        self.panel_a = StudentPanel(panel_frame, mode='cost', timer_minutes=self.timer_minutes, 
                                   header_text=f'[팀별개인전 {self.current_mode}]', costs=self.current_costs)
        self.panel_a.grid(row=0, column=0, sticky="nsew")
        
        # 콜백 설정 (불완전한 식은 히스토리에 기록하지 않으므로 콜백 제거)
        # self.panel_a.on_incomplete_expression = self.handle_incomplete_expression
        
        # 패널이 제대로 표시되도록 강제 업데이트
        self.panel_a.update_idletasks()
        
        # 초기 문제 설정
        if hasattr(self, 'target_number'):
            self.panel_a.set_problem(self.target_number)

        # No need to center sash for single panel

        # Bottom control frame (Timer / Next)
        ctrl = tk.Frame(self, bg=BG_COLOR)
        ctrl.grid(row=1, column=0, sticky="ew", pady=5)
        ctrl.columnconfigure(0, weight=1)  # spacer
        ctrl.columnconfigure(1, weight=0)  # timer
        ctrl.columnconfigure(2, weight=0)  # cost table
        ctrl.columnconfigure(3, weight=1)  # spacer
        ctrl.columnconfigure(4, weight=0)  # prev btn
        ctrl.columnconfigure(5, weight=0)  # next btn

        # Timer label (center)
        initial_timer_text = f"{self.timer_minutes:02d}:00"
        self.timer_label = tk.Label(ctrl, text=initial_timer_text, font=TIMER_FONT, bg=BG_COLOR, fg=TEXT_COLOR, anchor=tk.CENTER)
        self.timer_label.grid(row=0, column=1, sticky="ew", padx=20)

        # Cost table
        self.cost_table = self._create_cost_table(ctrl)
        self.cost_table.grid(row=0, column=2, sticky="w", padx=20)
        self.cost_table.grid_remove() # Initially hidden

        # Buttons
        self.prev_btn = tk.Button(ctrl, text="◀ 뒤로가기", command=self.load_prev_problem,
                                  font=BODY_FONT, bg=BORDER_COLOR, fg=TEXT_COLOR, relief=tk.FLAT, width=15)
        self.prev_btn.grid(row=0, column=4, sticky="e", padx=10)
        self.prev_btn.grid_remove() # 처음에는 숨김

        self.next_btn = tk.Button(ctrl, text="다음 ▶", command=self.confirm_next,
                                  font=BODY_FONT, bg=ACCENT_COLOR, fg=TEXT_COLOR, relief=tk.FLAT, width=15)
        self.next_btn.grid(row=0, column=5, sticky="e", padx=10)

        # Ensure control frame stays on top (for subsequent navigations)
        self.after_idle(ctrl.lift)

        # Shortcut Shift+L -> main menu
        self.master.bind_all('<Shift-L>', self._shortcut_menu)
        self.master.bind_all('<Shift-l>', self._shortcut_menu)

        # bind shortcut Ctrl+Z remains bound in __init__

        # store panel list for easy iteration
        self._panels = [self.panel_a]

        # timer attributes
        self.timer_id = None
        self.remaining_sec = 0
        self.active_panel_index = 0  # Always 0 for single panel
        self.timer_blink_state = False  # 깜빡임 상태 추적
        self.blink_timer_id = None  # 깜빡임 타이머 ID

    def _create_cost_table(self, parent):
        """Creates a frame displaying the cost for each symbol."""
        table_frame = Frame(parent, bg=COMPONENT_BG_COLOR, relief=tk.RAISED, bd=2)
        
        symbols = ['1', '(', ')', '+', '*']
        
        Label(table_frame, text="기호", font=("Segoe UI", 12, "bold"), bg=COMPONENT_BG_COLOR, fg=TEXT_COLOR).grid(row=0, column=0, padx=5, pady=2)
        Label(table_frame, text="COIN", font=("Segoe UI", 12, "bold"), bg=COMPONENT_BG_COLOR, fg=TEXT_COLOR).grid(row=1, column=0, padx=5, pady=2)

        for i, symbol in enumerate(symbols):
            Label(table_frame, text=symbol, font=("Segoe UI", 14, "bold"), bg=COMPONENT_BG_COLOR, fg=HIGHLIGHT_COLOR).grid(row=0, column=i+1, padx=5)
            cost = self.mode2_costs.get(symbol, 1)
            Label(table_frame, text=str(cost), font=("Segoe UI", 14), bg=COMPONENT_BG_COLOR, fg=TEXT_COLOR).grid(row=1, column=i+1, padx=5)
            
        return table_frame

    def load_problem(self):
        self.clear_all()
        
        # 히스토리 초기화
        self.success_history = []
        self.panel_start_times = [None]
        self.first_student_cost = None  # 첫 번째 학생의 코스트 초기화
        self.team_deduction_points = 0  # 팀전체 감점 초기화
        # 각 패널의 히스토리 표시 초기화
        for panel in self._panels:
            panel.update_history([])
        
        if not self.problems:
            # 문제가 없으면 기본 문제 사용
            self.problems = [{'target': 16, 'optimal_cost': 3}, {'target': 25, 'optimal_cost': 5}, {'target': 30}]
            self.problem_index = 0
        elif self.problem_index >= len(self.problems):
            messagebox.showinfo("게임 종료", "1라운드가 모두 종료되었습니다.")
            self.go_to_main_menu()
            return

        problem = self.problems[self.problem_index]
        threshold_coin = None
        if isinstance(problem, dict):
            self.target_number = problem.get("target", 0)
            self.optimal_cost = problem.get("optimal_cost", None)
            threshold_coin = problem.get("threshold_coin", None)
        else:
            # problem is assumed to be an int
            self.target_number = int(problem)
            self.optimal_cost = None

        # Update all panels with new target and threshold_coin
        for p in self._panels:
            p.set_problem(self.target_number, threshold_coin=threshold_coin)

        # '뒤로가기' 버튼 상태 업데이트 (모드 II의 첫 문제에서도 보이도록)
        if self.problem_index > 0 or (self.current_mode == 'II' and self.mode1_problems):
            self.prev_btn.grid()
        else:
            self.prev_btn.grid_remove()

        # 항상 '다음' 버튼으로 표시
        self.next_btn.config(text="다음 ▶", state=tk.NORMAL, command=self.confirm_next)

        # restart timer for new problem
        self.active_panel_index = 0
        self._panels[0].set_editable(True)
        
        # 패널 상태 초기화 - 텍스트가 완전히 지워졌는지 확인
        for panel in self._panels:
            panel.clear_all()
        
        self.start_timer()

    def load_next_problem(self):
        self.stop_timer()
        self.problem_index += 1
        # 명시적으로 입력창 초기화
        self.clear_all()
        self.load_problem()

    def load_prev_problem(self):
        import tkinter.messagebox as mb

        # Case 1: Going back from Mode II to Mode I
        if self.current_mode == 'II' and self.problem_index == 0 and self.mode1_problems:
            if mb.askyesno("모드 전환", "팀별 개인전 모드 I의 마지막 문제로 돌아가시겠습니까?"):
                self.switch_to_mode1()
        # Case 2: Going back within the same mode
        elif self.problem_index > 0:
            if mb.askyesno("이전 문제", "이전 문제로 이동할까요?"):
                self.stop_timer()
                self.problem_index -= 1
                self.clear_all()
                self.load_problem()

    def confirm_next(self):
        import tkinter.messagebox as mb
        
        # 모드 I의 마지막 문제이고 모드 II 문제가 있는 경우
        if (self.current_mode == 'I' and 
            self.problem_index >= len(self.problems) - 1 and 
            self.mode2_problems):
            if mb.askyesno("모드 전환", "팀별 개인전 모드 II로 넘어가시겠습니까?"):
                self.switch_to_mode2()
        # 모드 II의 마지막 문제인 경우
        elif (self.current_mode == 'II' and 
              self.problem_index >= len(self.problems) - 1):
            if mb.askyesno("게임 종료", "1라운드가 모두 종료되었습니다. 메인 메뉴로 돌아가시겠습니까?"):
                self.go_to_main_menu()
        else:
            if mb.askyesno("다음 문제", "다음 문제로 이동할까요?"):
                self.load_next_problem()

    def confirm_prev(self, event=None):
        import tkinter.messagebox as mb
        if self.problem_index > 0 and mb.askyesno("이전 문제", "이전으로 돌아가시겠습니까?"):
            self.problem_index -= 1
            # 명시적으로 입력창 초기화
            self.clear_all()
            self.load_problem()
            return 'break'

    def clear_all(self):
        for p in self._panels:
            p.clear_all()
    
    def switch_to_mode1(self):
        """모드 I로 전환"""
        self.stop_timer()
        self.current_mode = 'I'
        self.problems = self.mode1_problems
        self.current_costs = self.mode1_costs
        self.problem_index = len(self.mode1_problems) - 1 # 마지막 문제로 설정
        self.timer_minutes = self.mode1_minutes
        
        # 헤더 텍스트 업데이트
        self.panel_a.header_text = '[팀별개인전 I]'
        self.panel_a.header_label.config(text='[팀별개인전 I]')
        
        # 패널의 코스트 설정 업데이트
        self.panel_a.costs = self.current_costs
        
        # 패널의 타이머 설정 업데이트
        self.panel_a.timer_minutes = self.timer_minutes
        
                # 히스토리 초기화
        self.success_history = []
        self.panel_start_times = [None]
        self.first_student_cost = None
        self.team_deduction_points = 0  # 팀전체 감점 초기화

        # COIN 표 숨기기
        self.cost_table.grid_remove()

        # 문제 로드
        self.load_problem()

    def switch_to_mode2(self):
        """모드 II로 전환"""
        self.stop_timer()
        self.current_mode = 'II'
        self.problems = self.mode2_problems
        self.current_costs = self.mode2_costs
        self.problem_index = 0
        self.timer_minutes = self.mode2_minutes
        
        # 헤더 텍스트 업데이트
        self.panel_a.header_text = '[팀별개인전 II]'
        self.panel_a.header_label.config(text='[팀별개인전 II]')
        
        # 패널의 코스트 설정 업데이트
        self.panel_a.costs = self.current_costs
        
        # 패널의 타이머 설정 업데이트
        self.panel_a.timer_minutes = self.timer_minutes
        
        # 히스토리 초기화
        self.success_history = []
        self.panel_start_times = [None]
        self.first_student_cost = None
        self.team_deduction_points = 0  # 팀전체 감점 초기화

        # COIN 표 보이기
        self.cost_table.grid()
        
        # 문제 로드
        self.load_problem()

    # ---------------- Timer -----------------
    def start_timer(self):
        self.stop_timer()
        self.remaining_sec = self.timer_minutes * 60  # 설정된 시간(분)을 초로 변환
        self.update_timer_label()
        self.timer_id = self.after(1000, self._tick)
        
        # 현재 패널의 시작 시간 기록
        import time
        self.panel_start_times[self.active_panel_index] = time.time()

    def _tick(self):
        self.remaining_sec -= 1
        self.update_timer_label()
        if self.remaining_sec <= 0:
            # 시간 초과
            self.stop_timer()
            play_timer_end_sound(sound_type='chime')
            self._panels[0].set_editable(False)
            
            # 시간 초과 시 입력창과 결과 완전 초기화
            self._panels[0].clear_all()
            
            # 종료 메시지 표시
            messagebox.showinfo("시간 종료", "시간이 초과되었습니다.")
            
            # 마지막 문제인 경우 버튼 활성화
            if self.problem_index >= len(self.problems) - 1:
                self.next_btn.config(state=tk.NORMAL)
            # 자동으로 다음 문제로 넘어가지 않음 - 사용자가 '다음' 버튼을 눌러야 함
        else:
            self.timer_id = self.after(1000, self._tick)

    def update_timer_label(self):
        m = self.remaining_sec // 60
        s = self.remaining_sec % 60
        
        # 10초 이하일 때 깜빡임 효과 시작
        if self.remaining_sec <= 10 and self.remaining_sec > 0:
            if self.blink_timer_id is None:
                self.start_timer_blink()
            # 깜빡임 상태에 따라 색상 변경 (깜빡임 로직은 별도 메서드에서 처리)
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
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
        self.stop_timer_blink()  # 깜빡임도 중지

    def go_to_main_menu(self):
        from ui.main_menu_view import MainMenuView
        self.master.switch_frame(MainMenuView)

    def _shortcut_menu(self, event=None):
        self.go_to_main_menu()
    

        
    # 히스토리 관련 메서드들
    def record_attempt(self, panel_index, expression, cost, is_correct, error_message=None):
        """모든 시도를 히스토리에 기록 (정답, 오답, 불완전한 식 모두 포함)"""
        from game_logic.expression_parser import normalize_expression
        import time

        # 기록 시간 측정 (밀리초 단위까지 정확하게)
        current_time = time.time()
        if self.panel_start_times[panel_index] is None:
            return  # 시작 시간이 없으면 기록하지 않음
        elapsed_time = current_time - self.panel_start_times[panel_index]
        elapsed_seconds = int(elapsed_time)
        if elapsed_seconds > self.timer_minutes * 60:
            return # 시간 초과

        panel_name = "A" if panel_index == 0 else "B"

        # 기본 기록 정보
        new_record = {
            'panel': panel_name,
            'time': elapsed_time,  # 실제 소요 시간 (초.밀리초)
            'cost': cost,
            'expression': expression.strip(),
            'problem': self.target_number,
            'is_correct': is_correct,
            'error_message': error_message
        }

        # 정답인 경우에만 최적해 여부 확인
        if is_correct:
            is_optimal = self.optimal_cost is not None and cost == self.optimal_cost
            new_record['is_optimal'] = is_optimal
            
            # 모드 II에서 정답인 경우 추가 분류
            if self.current_mode == 'II':
                threshold_coin = None
                if self.problems and self.problem_index < len(self.problems):
                    problem_data = self.problems[self.problem_index]
                    if isinstance(problem_data, dict):
                        threshold_coin = problem_data.get("threshold_coin")
                
                if threshold_coin is not None:
                    if cost <= threshold_coin:
                        # 기준 COIN 이하 정답 - 최적해가 아닌 경우만 중복 체크
                        if not is_optimal:
                            same_cost_exists = any(r.get('is_correct') and not r.get('is_optimal', False) and r['cost'] == cost for r in self.success_history)
                            new_record['attempt_type'] = 'first_valid' if not same_cost_exists else 'repeat_valid'
                        else:
                            # 최적해는 나중에 교환법칙 체크에서 처리
                            new_record['attempt_type'] = 'first_valid'
                    else:
                        # 기준 COIN 초과 정답
                        new_record['attempt_type'] = 'exceed_threshold'
                else:
                    new_record['attempt_type'] = 'first_valid'
            else:
                new_record['attempt_type'] = 'first_valid'
        else:
            # 오답인 경우
            if error_message and ("불완전" in error_message or "누락" in error_message):
                new_record['attempt_type'] = 'incomplete'
            else:
                new_record['attempt_type'] = 'wrong_answer'

        # 모드 II에서는 모든 시도를 기록
        if self.current_mode == 'II':
            # 정답인 경우 중복 체크
            if is_correct:
                is_optimal = new_record.get('is_optimal', False)
                
                if is_optimal:
                    # 최적해인 경우: 기준 COIN 초과가 아닌 경우에만 교환법칙 체크
                    if new_record['attempt_type'] != 'exceed_threshold':
                        from game_logic.expression_parser import normalize_expression
                        normalized_new_expr = normalize_expression(expression.strip())
                        
                        # 기존 최적해와 교환법칙 비교 (COIN 개수와 무관하게)
                        for existing_record in self.success_history:
                            if (existing_record.get('is_correct') and existing_record.get('is_optimal')):
                                existing_normalized = normalize_expression(existing_record['expression'])
                                if existing_normalized == normalized_new_expr:
                                    new_record['attempt_type'] = 'repeat_valid'  # 교환법칙 중복으로 분류
                                    break
                else:
                    # 일반 정답인 경우: 기준 COIN 초과가 아닌 경우에만 중복 체크
                    if new_record['attempt_type'] != 'exceed_threshold':
                        same_cost_exists = any(r.get('is_correct') and not r.get('is_optimal', False) and r['cost'] == cost for r in self.success_history)
                        if same_cost_exists:
                            new_record['attempt_type'] = 'repeat_valid'  # 중복 COIN으로 분류
            
            self.success_history.append(new_record)
        else:
            # 모드 I에서는 기존 로직 유지 (정답만 기록)
            if is_correct:
                self.record_success_mode1(panel_index, expression, cost, new_record)
                return

        # UI 업데이트
        panel_history = [r for r in self.success_history if r['panel'] == panel_name]
        self._panels[panel_index].update_history(panel_history)

    def record_success_mode1(self, panel_index, expression, cost, new_record):
        """모드 I 전용 정답 기록 로직 (기존 로직 유지)"""
        from game_logic.expression_parser import normalize_expression
        
        is_optimal = new_record.get('is_optimal', False)
        normalized_expression = normalize_expression(expression.strip())
        panel_name = new_record['panel']
        elapsed_time = new_record['time']
        elapsed_seconds = int(elapsed_time)

        # 모드 I 기존 로직
        optimal_solutions_in_history = [r for r in self.success_history if r.get('is_optimal')]
        
        if is_optimal:
            # Case 1: 새로운 답이 최적해
            # 구조적 중복 체크
            for r in optimal_solutions_in_history:
                if normalize_expression(r['expression']) == normalized_expression:
                    return  # 중복된 최적해는 추가하지 않음

            # 첫 최적해라면, 기존의 비최적해 기록을 모두 삭제
            if not optimal_solutions_in_history:
                self.success_history.clear()
            
            self.success_history.append(new_record)

        else:
            # Case 2: 새로운 답이 최적해가 아님
            if optimal_solutions_in_history:
                return  # 이미 최적해가 있다면 비최적해는 기록하지 않음

            # 비최적해만 있는 경우, 최고 기록인지 확인
            if not self.success_history:
                # 첫 번째 성공 기록
                self.success_history.append(new_record)
            else:
                # 기존 최고 기록과 비교
                current_best = self.success_history[0]
                # 새 기록이 더 좋은 경우 (cost가 더 작거나, 같으면 시간이 더 짧아야 함)
                if cost < current_best['cost'] or (cost == current_best['cost'] and elapsed_seconds < current_best['time']):
                    self.success_history = [new_record] # 기존 기록을 대체

        # UI 업데이트
        panel_history = [r for r in self.success_history if r['panel'] == panel_name]
        self._panels[panel_index].update_history(panel_history)

    def record_success(self, panel_index, expression, cost):
        """정답 달성 시 히스토리에 기록 - 새로운 record_attempt로 리다이렉트"""
        self.record_attempt(panel_index, expression, cost, is_correct=True)

        # 모드 II인 경우 기존 메시지만 표시 (기록은 이미 record_attempt에서 처리됨)
        if self.current_mode == 'II':
            # 현재 문제의 기준 COIN 값 확인
            threshold_coin = None
            if self.problems and self.problem_index < len(self.problems):
                problem_data = self.problems[self.problem_index]
                if isinstance(problem_data, dict):
                    threshold_coin = problem_data.get("threshold_coin")

            # 기준 COIN 초과인 경우 메시지만 표시 (기록은 이미 됨)
            if threshold_coin is not None and cost > threshold_coin:
                import tkinter.messagebox as messagebox
                messagebox.showinfo("기준 COIN 초과", 
                                  f"정답이지만 기준 COIN값({threshold_coin})보다 큽니다.\n"
                                  f"사용한 COIN: {cost}개")
                return

            # 교환법칙 중복 체크는 제거 - record_attempt에서 같은 COIN 개수 체크로 처리됨
    

    
    # def handle_incomplete_expression(self, expression, cost, error_message):
    #     """불완전한 식 입력 시 히스토리에 기록 (팀별개인전 II에서만) - 더 이상 사용하지 않음"""
    #     # 불완전한 식은 히스토리에 기록하지 않도록 변경됨
    #     pass
    
    def go_to_main_menu(self):
        """메인 메뉴로 돌아가기"""
        from ui.main_menu_view import MainMenuView
        self.master.switch_frame(MainMenuView)
