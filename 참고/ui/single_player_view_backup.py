# ui/single_player_view.py
import tkinter as tk
from tkinter import PanedWindow, Text, messagebox, Frame, Label
from constants import *
from game_logic.calculator import analyze_input
import random
from utils.problem_store import load_problems

class SinglePlayerView(tk.Frame):
    def __init__(self, master, mode='normal'):
        super().__init__(master, bg=BG_COLOR)
        self.master = master
        self.mode = mode
        # self.problems = [] # 예시: 문제 목록을 여기서 로드해야 합니다.
        # self.problem_index = 0
        self.create_widgets()

        self.problems = load_problems()
        self.problem_index = 0

        if self.problems:
            self.target_number = self.problems[0]
        else:
            self.target_number = random.randint(10, 50)

        # panels will be created after this call; postpone setting problem using after_idle
        def _init_labels():
            for p in self._panels:
                p.set_problem(self.target_number)

        self.after_idle(_init_labels)
        
        # 게임 시작 시 자동으로 타이머 시작
        self.after_idle(self.auto_start_timer)

    def auto_start_timer(self):
        """게임 시작 시 자동으로 타이머를 시작하는 메서드"""
        # 첫 번째 패널을 활성화하고 타이머 시작
        self.active_panel_index = 0
        if hasattr(self, '_panels') and len(self._panels) > 1:
            self._panels[0].set_editable(True)
            self._panels[1].set_editable(False)
        self.start_timer()

    def create_widgets(self):
        # Vertical paned window to hold two student panels
        # Configure grid
        self.rowconfigure(0, weight=4)  # 메인 패널 영역 (4/5)
        self.rowconfigure(1, weight=0)  # 타이머 영역 (고정)
        self.rowconfigure(2, weight=1)  # 히스토리 영역 (1/5)
        self.columnconfigure(0, weight=1)

        v_pane = PanedWindow(self, orient=tk.VERTICAL, sashrelief=tk.RAISED, bg=BORDER_COLOR)
        v_pane.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        from ui.student_panel import StudentPanel
        self.panel_a = StudentPanel(v_pane, mode=self.mode)
        self.panel_b = StudentPanel(v_pane, mode=self.mode)

        v_pane.add(self.panel_a, stretch="always")
        v_pane.add(self.panel_b, stretch="always")

        # Place sash to center initially
        def _center_vert():
            self.update_idletasks()
            total_h = v_pane.winfo_height()
            v_pane.sash_place(0, 0, total_h // 2)

        self.after(50, _center_vert)

        # Bottom control frame (Timer / Next / History)
        ctrl = tk.Frame(self, bg=BG_COLOR)
        ctrl.grid(row=1, column=0, sticky="ew", pady=5)
        ctrl.columnconfigure(0, weight=1)  # left spacer
        ctrl.columnconfigure(1, weight=0)  # timer (center)
        ctrl.columnconfigure(2, weight=1)  # right spacer/next btn

        # Timer label (완전 중앙 정렬)
        self.timer_label = tk.Label(ctrl, text="03:00", font=TIMER_FONT, bg=BG_COLOR, fg=TEXT_COLOR, anchor=tk.CENTER)
        self.timer_label.grid(row=0, column=1, sticky="")

        self.next_btn = tk.Button(ctrl, text="다음 ▶", command=self.confirm_next,
                                   font=BODY_FONT, bg=ACCENT_COLOR, fg=TEXT_COLOR, relief=tk.FLAT, width=10)
        self.next_btn.grid(row=0, column=2, sticky="e", padx=10)

        # 히스토리 프레임 (작은 크기로 추가)
        history_frame = tk.Frame(self, bg=BG_COLOR)
        history_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        history_frame.rowconfigure(1, weight=1)
        history_frame.columnconfigure(0, weight=1)

        # 히스토리 제목
        history_title = tk.Label(history_frame, text="🏆 정답 히스토리", font=BODY_FONT, bg=BG_COLOR, fg=ACCENT_COLOR)
        history_title.grid(row=0, column=0, pady=2)

        # 히스토리 텍스트 (작은 크기)
        self.history_text = tk.Text(history_frame, bg=INPUT_BG_COLOR, fg=TEXT_COLOR,
                                   font=("Segoe UI", 9), height=3, state=tk.DISABLED, wrap=tk.WORD)
        self.history_text.grid(row=1, column=0, sticky="nsew", pady=2)

        # Ensure control frame stays on top (for subsequent navigations)
        self.after_idle(ctrl.lift)

        # Shortcut Shift+L -> main menu
        self.master.bind_all('<Shift-L>', self._shortcut_menu)
        self.master.bind_all('<Shift-l>', self._shortcut_menu)

        # bind shortcut Ctrl+Z remains bound in __init__

        # store panels list for easy iteration
        self._panels = [self.panel_a, self.panel_b]

        # timer attributes
        self.timer_id = None
        self.remaining_sec = 0
        self.active_panel_index = 0  # 0 -> A, 1 -> B
        self.timer_blink_state = False  # 깜빡임 상태 추적
        self.blink_timer_id = None  # 깜빡임 타이머 ID
        
        # 히스토리 관련 속성
        self.panel_start_times = [None, None]  # 각 패널의 시작 시간
        self.success_history = []  # 정답 히스토리 [{'panel': str, 'time': int, 'cost': int, 'expression': str}, ...]

    def load_problem(self):
        self.clear_all()
        if not self.problems or self.problem_index >= len(self.problems):
            messagebox.showinfo("게임 종료", f"'{self.mode}' 모드의 모든 문제를 해결했습니다!")
            self.go_to_main_menu()
            return

        problem = self.problems[self.problem_index]
        if isinstance(problem, dict):
            self.target_number = problem.get("target", 0)
            min_cost = problem.get("min_cost") if self.mode == 'cost' else None
        else:
            # problem is assumed to be an int
            self.target_number = int(problem)
            min_cost = None

        # Update all panels with new target
        for p in self._panels:
            p.set_problem(self.target_number)

        # initial active panel A only
        self.active_panel_index = 0
        self._panels[0].set_editable(True)
        self._panels[1].set_editable(False)
        self.start_timer()

        # Enable/disable next button
        if self.problems and self.problem_index < len(self.problems)-1:
            self.next_btn.config(state=tk.NORMAL)
        else:
            self.next_btn.config(state=tk.DISABLED)

        # restart timer with A first for new problem
        self.active_panel_index = 0
        self._panels[0].set_editable(True)
        self._panels[1].set_editable(False)
        self.start_timer()
        
        # 새 문제 시작 시 히스토리 초기화
        self.clear_history()

    def load_next_problem(self):
        self.stop_timer()
        self.problem_index += 1
        self.load_problem()

    def confirm_next(self):
        import tkinter.messagebox as mb
        if mb.askyesno("다음 문제", "다음 문제로 이동할까요?"):
            self.load_next_problem()

    def confirm_prev(self, event=None):
        import tkinter.messagebox as mb
        if self.problem_index > 0 and mb.askyesno("이전 문제", "이전으로 돌아가시겠습니까?"):
            self.problem_index -= 1
            self.load_problem()
            return 'break'

    def clear_all(self):
        for p in self._panels:
            p.clear_all()

    # ---------------- Timer -----------------
    def start_timer(self):
        self.stop_timer()
        self.remaining_sec = 180  # 3 minutes per student
        self.update_timer_label()
        self.timer_id = self.after(1000, self._tick)
        
        # 현재 활성 패널의 시작 시간 기록
        import time
        self.panel_start_times[self.active_panel_index] = time.time()

    def _tick(self):
        self.remaining_sec -= 1
        self.update_timer_label()
        if self.remaining_sec <= 0:
            if self.active_panel_index == 0:
                # Switch to B panel
                self._panels[0].set_editable(False)
                self._panels[1].set_editable(True)
                self.active_panel_index = 1
                self.remaining_sec = 180
                self.update_timer_label()
                self.timer_id = self.after(1000, self._tick)
                
                # B 패널 시작 시간 기록
                import time
                self.panel_start_times[1] = time.time()
            else:
                # B finished, move to next problem
                for p in self._panels:
                    p.set_editable(False)
                self.after(1000, self.load_next_problem)
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
    def record_success(self, panel_index, expression, cost):
        """정답 달성 시 히스토리에 기록"""
        import time
        current_time = time.time()
        
        if self.panel_start_times[panel_index] is None:
            return  # 시작 시간이 없으면 기록하지 않음
            
        elapsed_time = current_time - self.panel_start_times[panel_index]
        elapsed_seconds = int(elapsed_time)
        
        # 3분(180초) 이내인 경우만 기록
        if elapsed_seconds <= 180:
            panel_name = "A" if panel_index == 0 else "B"
            
            success_record = {
                'panel': panel_name,
                'time': elapsed_seconds,
                'cost': cost,
                'expression': expression.strip(),
                'problem': self.target_number
            }
            
            self.success_history.append(success_record)
            self.update_history_display()
    
    def update_history_display(self):
        """히스토리 표시 업데이트"""
        if not hasattr(self, 'history_text'):
            return
            
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete("1.0", tk.END)
        
        if not self.success_history:
            self.history_text.insert("1.0", "3분 이내 정답 기록이 표시됩니다.")
        else:
            # 최고 3개만 표시 (간단하게)
            sorted_history = sorted(self.success_history, key=lambda x: (x['time'], x['cost']))[:3]
            
            for i, record in enumerate(sorted_history):
                medal = ["🥇", "🥈", "🥉"][i] if i < 3 else "  "
                line = f"{medal} {record['panel']}패널 {record['time']}초 ({record['cost']}개) - {record['expression'][:15]}..."
                if i > 0:
                    line = "\n" + line
                self.history_text.insert("end", line)
        
        self.history_text.config(state=tk.DISABLED)
        
    def clear_history(self):
        """히스토리 초기화 (새 문제 시작 시)"""
        self.success_history = []
        self.panel_start_times = [None, None]
        self.update_history_display()
