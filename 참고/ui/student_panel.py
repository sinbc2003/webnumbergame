import tkinter as tk
from tkinter import Frame, Text, Label, messagebox
from constants import *
from game_logic.calculator import analyze_input
from sounds.sound_effects import play_correct_sound, play_wrong_sound
import re

class StudentPanel(Frame):
    """A reusable panel containing problem label, input box, result display and buttons."""
    def __init__(self, master, mode='normal', panel_name='', timer_minutes=3, header_text='', costs=None):
        super().__init__(master, bg=COMPONENT_BG_COLOR)
        self.mode = mode
        self.panel_name = panel_name  # A 또는 B
        self.target_number = None  # 목표 숫자 저장
        self.history_records = []  # 이 패널의 히스토리
        self.timer_minutes = timer_minutes  # 제한 시간 (분)
        self.header_text = header_text  # 헤더 텍스트
        self.costs = costs  # 기호별 코스트 설정
        
        # 콜백 함수들
        self.on_incomplete_expression = None  # 불완전한 식 입력 시 호출
        
        self._build_widgets()
        
        # 초기화 후 UI 강제 업데이트
        self.update()
        self.update_idletasks()

    # --------------------- UI ---------------------
    def _build_widgets(self):
        # Horizontal paned window dividing input/result
        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, bg=BORDER_COLOR)
        self.paned.pack(fill=tk.BOTH, expand=True)

        # Left side (problem + input + buttons)
        left = Frame(self.paned, bg=COMPONENT_BG_COLOR)
        self.paned.add(left, stretch="always")
        self.left_frame = left  # 나중에 색상 변경을 위해 참조 저장

        # Header and Problem in same line
        # Header label (if provided) - 좌측정렬, 흰색
        if self.header_text:
            self.header_frame = Frame(left, bg=COMPONENT_BG_COLOR)
            self.header_frame.pack(pady=(10, 0), fill=tk.X)
            self.header_label = Label(self.header_frame, text=self.header_text, font=TITLE_FONT, 
                                    bg=COMPONENT_BG_COLOR, fg=TEXT_COLOR, anchor="w")  # 흰색, 좌측정렬
            self.header_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Problem label - Text 위젯으로 변경하여 다중 색상 지원 (약간 좌측으로 이동)
        self.problem_frame = Frame(left, bg=COMPONENT_BG_COLOR)
        self.problem_frame.pack(pady=(5, 0), fill=tk.X)
        
        self.problem_text = Text(self.problem_frame, height=2, width=20, 
                               font=PROBLEM_FONT, bg=COMPONENT_BG_COLOR, 
                               state=tk.DISABLED, wrap=tk.NONE, cursor="arrow",
                               relief=tk.FLAT, highlightthickness=0)
        self.problem_text.pack(padx=(80, 0))  # 좌측에서 약간 들여쓰기
        
        # 색상 태그 설정
        self.problem_text.tag_configure("label", foreground=TEXT_COLOR)
        self.problem_text.tag_configure("number", foreground=HIGHLIGHT_COLOR)
        
        # 초기 텍스트 설정
        self._update_problem_text()

        # Input - wrap=tk.CHAR로 문자 단위 줄바꿈
        self.input_text = Text(left, bg=INPUT_BG_COLOR, fg=TEXT_COLOR, insertbackground=TEXT_COLOR,
                                relief=tk.FLAT, bd=2, font=INPUT_FONT, wrap=tk.CHAR)
        self.input_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        # Enter 키 바인딩
        self.input_text.bind("<Return>", self.run_analysis)
        self.input_text.bind("<KP_Enter>", self.run_analysis)  # 숫자 패드 Enter
        
        # 키보드 입력 제한 추가 (특수문자 !@#$%^& 등 차단)
        def on_key_press(event):
            # Enter 키는 run_analysis로 처리하고 기본 동작 차단
            if event.keysym in ['Return', 'KP_Enter']:
                return 'break'  # Enter 키의 기본 동작(줄바꿈) 차단
            # Shift+L 메인 메뉴 단축키는 허용
            if event.keysym in ['L', 'l'] and (event.state & 0x1):  # Shift가 눌린 경우
                return  # Shift+L은 허용
            # Ctrl 단축키만 허용 (Shift는 특수문자 입력에 사용되므로 제한)
            if event.state & 0x4:  # Ctrl이 눌린 경우만 허용
                return  # Ctrl 단축키는 허용
            if event.keysym == 'space':
                return 'break'  # 스페이스 입력 차단
            # Backspace, Delete 등 편집 키는 허용
            if event.keysym in ['BackSpace', 'Delete', 'Left', 'Right', 'Home', 'End']:
                return  # 편집 키는 허용
            # 허용된 문자가 아닌 경우 입력 차단 (Shift+숫자로 만드는 특수문자 !@#$%^& 등 포함)
            if event.char and event.char not in '1()+*':
                return 'break'
            
            # '*' 연속 입력 방지
            if event.char == '*':
                current_text = self.input_text.get("1.0", tk.END).strip()
                cursor_pos = self.input_text.index(tk.INSERT)
                cursor_line, cursor_col = map(int, cursor_pos.split('.'))
                
                # 커서 위치 앞의 문자가 '*'인지 확인
                if cursor_col > 0 and cursor_col <= len(current_text) and current_text[cursor_col - 1] == '*':
                    return 'break'  # '*' 연속 입력 차단
                
                # 커서 위치 뒤의 문자가 '*'인지 확인
                if cursor_col < len(current_text) and current_text[cursor_col] == '*':
                    return 'break'  # '*' 연속 입력 차단
        
        self.input_text.bind('<KeyPress>', on_key_press)
        
        # 붙여넣기 이벤트 처리 - 줄바꿈 제거 및 '*' 연속 입력 방지
        def on_paste(event):
            try:
                # 클립보드에서 텍스트 가져오기
                clipboard_text = self.input_text.clipboard_get()
                # 줄바꿈 제거
                cleaned_text = clipboard_text.replace('\n', '').replace('\r', '')
                
                # '*' 연속 입력 방지 - 연속된 '*' 제거
                import re
                cleaned_text = re.sub(r'\*{2,}', '*', cleaned_text)  # 2개 이상의 연속된 '*'를 하나로 변경
                
                # 현재 텍스트와 커서 위치 확인
                current_text = self.input_text.get("1.0", tk.END).strip()
                cursor_pos = self.input_text.index(tk.INSERT)
                cursor_line, cursor_col = map(int, cursor_pos.split('.'))
                
                # 붙여넣을 텍스트의 첫 번째 문자가 '*'이고 커서 앞 문자가 '*'인 경우
                if cleaned_text and cleaned_text[0] == '*' and cursor_col > 0 and cursor_col <= len(current_text) and current_text[cursor_col - 1] == '*':
                    cleaned_text = cleaned_text[1:]  # 첫 번째 '*' 제거
                
                # 붙여넣을 텍스트의 마지막 문자가 '*'이고 커서 뒤 문자가 '*'인 경우
                if cleaned_text and cleaned_text[-1] == '*' and cursor_col < len(current_text) and current_text[cursor_col] == '*':
                    cleaned_text = cleaned_text[:-1]  # 마지막 '*' 제거
                
                # 현재 커서 위치에 삽입
                if cleaned_text:  # 빈 문자열이 아닌 경우만 삽입
                    self.input_text.insert(tk.INSERT, cleaned_text)
                # 기본 붙여넣기 동작 방지
                return 'break'
            except:
                return
        
        self.input_text.bind('<<Paste>>', on_paste)
        self.input_text.bind('<Control-v>', on_paste)
        self.input_text.bind('<Control-V>', on_paste)
        
        # 텍스트 변경 시 자동 크기 조정
        def on_text_change(event=None):
            content = self.input_text.get("1.0", tk.END).strip()
            if content:
                # 텍스트 길이에 따라 폰트 크기 조정 (2배로 증가)
                text_length = len(content)
                if text_length <= 20:
                    font_size = 48
                elif text_length <= 40:
                    font_size = 40
                elif text_length <= 60:
                    font_size = 36
                elif text_length <= 80:
                    font_size = 32
                elif text_length <= 100:
                    font_size = 28
                else:
                    font_size = 24
                
                self.input_text.config(font=("Segoe UI", font_size))
            else:
                # 텍스트가 비어있을 때는 기본 크기 (64)로 설정
                self.input_text.config(font=INPUT_FONT)
        
        self.input_text.bind('<KeyRelease>', on_text_change)
        self.input_text.bind('<<Modified>>', on_text_change)

        # Button frame 제거 - 초기화, 검증 버튼 불필요

        # Right side (result)
        right = Frame(self.paned, bg=COMPONENT_BG_COLOR)
        self.paned.add(right, stretch="always")
        self.right_frame = right  # 나중에 색상 변경을 위해 참조 저장

        # 결과 헤더 삭제됨

        label_text = "COIN 갯수" if "II" in self.header_text else "연산기호개수"
        # 팀별개인전 II에서는 더 작은 폰트와 여백 사용
        if "II" in self.header_text:
            font_size = ("Segoe UI", 14)  # 더 작은 폰트
            padding = (5, 5)  # 더 작은 여백
        else:
            font_size = TITLE_FONT
            padding = (20, 10)
            
        self.result_label = Label(right, text=f"값 : -, {label_text} : -", font=font_size, bg=COMPONENT_BG_COLOR,
                                   fg=TEXT_COLOR, wraplength=800, justify=tk.LEFT)
        self.result_label.pack(pady=padding, expand=False if "II" in self.header_text else True)

        # 히스토리 텍스트 위젯 추가 (결과 영역 하단) - 다중 색상 지원, 스크롤바 포함
        # 팀별개인전 II에서는 더 큰 높이 사용 (더 많은 기록을 위해 높이 증가)
        history_height = 15 if "II" in self.header_text else 8
        history_font_size = 15 if "II" in self.header_text else 18
        
        # 히스토리 프레임 (텍스트 + 스크롤바)
        history_frame = tk.Frame(right, bg=COMPONENT_BG_COLOR)
        history_frame.pack(pady=(5, 5), fill=tk.BOTH, expand=True)
        
        # 스크롤바 생성
        history_scrollbar = tk.Scrollbar(history_frame, bg=COMPONENT_BG_COLOR)
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 히스토리 텍스트 위젯
        self.history_text = tk.Text(history_frame, height=history_height, font=("Segoe UI", history_font_size, "bold"), 
                                   bg=COMPONENT_BG_COLOR, fg=TEXT_COLOR, 
                                   state=tk.DISABLED, wrap=tk.NONE, cursor="arrow",
                                   yscrollcommand=history_scrollbar.set)
        self.history_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 스크롤바와 텍스트 위젯 연결
        history_scrollbar.config(command=self.history_text.yview)
        
        # 마우스 휠 스크롤 지원 (팀별개인전 II에서만)
        if "II" in self.header_text:
            def on_mousewheel(event):
                self.history_text.yview_scroll(int(-1*(event.delta/120)), "units")
            self.history_text.bind("<MouseWheel>", on_mousewheel)
        
        # 색상 태그 설정 (팀별개인전 II에 맞게 조정)
        base_font_size = history_font_size
        header_font = ("Segoe UI", base_font_size + 2, "bold")
        self.history_text.tag_configure("header", font=header_font, foreground=TEXT_COLOR, justify=tk.CENTER)
        self.history_text.tag_configure("title", foreground=TEXT_COLOR, justify=tk.CENTER)
        self.history_text.tag_configure("value", foreground=HIGHLIGHT_COLOR, justify=tk.CENTER)
        self.history_text.tag_configure("optimal", foreground=SUCCESS_COLOR, justify=tk.LEFT)
        
        # 팀별개인전 II용 색상 태그 (좌측 정렬)
        self.history_text.tag_configure("first_valid", foreground=SUCCESS_COLOR, justify=tk.LEFT)  # 기준 COIN 이하 첫 번째 정답 - 초록색
        self.history_text.tag_configure("repeat_valid", foreground="#FFA500", justify=tk.LEFT)     # 기준 COIN 이하 중복 정답 - 주황색
        self.history_text.tag_configure("exceed_threshold", foreground="#808080", justify=tk.LEFT) # 기준 COIN 초과 정답 - 어두운 회색
        self.history_text.tag_configure("wrong_answer", foreground=ERROR_COLOR, justify=tk.LEFT)   # 오답 - 빨간색
        self.history_text.tag_configure("incomplete", foreground="#8B0000", justify=tk.LEFT)       # 불완전한 식 - 진한 빨간색
        
        # 초기 텍스트 설정
        self._update_history_text("🏆 최고기록", is_empty=True)

    def _update_history_text(self, text, is_empty=False):
        """히스토리 텍스트를 다중 색상으로 업데이트"""
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete("1.0", tk.END)

        if is_empty:
            if "❌" in text:
                lines = text.split('\n')
                self.history_text.insert("1.0", lines[0], "header")
                if len(lines) > 1:
                    self.history_text.insert(tk.END, '\n')
                    self._parse_and_color_deduction_line(lines[1])
            else:
                self.history_text.insert("1.0", text, "header")
        else:
            record_blocks = text.split('\n\n')
            for i, block in enumerate(record_blocks):
                if i > 0:
                    self.history_text.insert(tk.END, '\n\n')

                if "❌" in block:
                    self._parse_and_color_deduction_line(block)
                    continue

                lines = block.split('\n')
                
                # 라인별로 파싱하여 색상 적용
                for j, line in enumerate(lines):
                    if j > 0:
                        self.history_text.insert(tk.END, '\n')

                    is_optimal = "⭐" in line
                    content = line.replace("⭐최적해", "").strip()

                    # 블록의 첫 줄 처리
                    if j == 0:
                        if content.startswith("🏆"):
                            self.history_text.insert(tk.END, content, "header")
                        else: # 식이 오는 경우
                            self.history_text.insert(tk.END, content, "value")
                    # 블록의 두 번째 줄 처리
                    elif j == 1:
                        if ":" in content: # 상세 정보
                            self._parse_and_color_detail_line(content)
                        else: # 식
                            self.history_text.insert(tk.END, content, "value")
                    # 블록의 세 번째 줄 처리 (최고기록의 경우)
                    elif j == 2:
                        self._parse_and_color_detail_line(content)

                    if is_optimal:
                        self.history_text.insert(tk.END, " ⭐최적해", "optimal")

        self.history_text.config(state=tk.DISABLED)
        
        # 히스토리가 업데이트된 후 맨 아래로 스크롤 (팀별개인전 II에서 항상)
        if "II" in self.header_text:
            self.history_text.see(tk.END)
        
        def _center_horiz():
            self.update_idletasks()
            w = self.winfo_width()
            self.paned.sash_place(0, w // 2, 0)
        self.after(50, _center_horiz)

    def _parse_and_color_detail_line(self, line):
        """상세 정보 라인을 파싱하여 색상을 적용하는 도우미 함수"""
        if '(' in line and ')' in line: # 간략한 포맷
            # 예: 1+1*1 (3개, 8초)
            match = re.match(r"(.+)\s\((.+)\)", line)
            if match:
                self.history_text.insert(tk.END, match.group(1), "value")
                self.history_text.insert(tk.END, f" ({match.group(2)})", "title")
            else:
                self.history_text.insert(tk.END, line, "title")
        elif ':' in line: # 자세한 포맷
            parts = line.split(',')
            for k, part in enumerate(parts):
                if k > 0:
                    self.history_text.insert(tk.END, ',', "title")
                
                sub_parts = part.strip().split(':', 1)
                self.history_text.insert(tk.END, sub_parts[0] + ':', "title")
                if len(sub_parts) > 1:
                    self.history_text.insert(tk.END, sub_parts[1], "value")

    def _parse_and_color_deduction_line(self, line):
        """감점 라인 파싱 및 색상 적용"""
        parts = line.strip().split(':')
        self.history_text.insert(tk.END, parts[0] + ':', "title")
        if len(parts) > 1:
            self.history_text.insert(tk.END, parts[1], "value")

    # --------------------- Logic ---------------------
    def set_problem(self, target_number: int, cost_text: str = "", threshold_coin: int = None):
        self.target_number = target_number  # 목표 숫자 저장
        self.threshold_coin = threshold_coin  # 기준 COIN 저장
        self._update_problem_text()
        # cost_text could be shown in future if needed
    
    def _update_problem_text(self):
        """문제 텍스트 업데이트 (다중 색상)"""
        self.problem_text.config(state=tk.NORMAL)
        self.problem_text.delete("1.0", tk.END)
        
        # '문제 : ' (흰색) + '숫자' (노란색)
        self.problem_text.insert("1.0", "문제 : ", "label")
        if self.target_number is not None:
            self.problem_text.insert(tk.END, str(self.target_number), "number")
        else:
            self.problem_text.insert(tk.END, "-", "label")
        
        # 팀별개인전 II 모드이고 기준 COIN이 설정된 경우 표시
        if "II" in self.header_text and hasattr(self, 'threshold_coin') and self.threshold_coin is not None:
            self.problem_text.insert(tk.END, "\n기준 COIN : ", "label")
            self.problem_text.insert(tk.END, str(self.threshold_coin), "number")
        
        self.problem_text.config(state=tk.DISABLED)

    def clear_all(self):
        # 입력창이 비활성화 상태여도 초기화할 수 있도록 임시로 활성화
        original_state = str(self.input_text['state'])
        if original_state == 'disabled':
            self.input_text.configure(state=tk.NORMAL)
        
        # 입력창 내용 완전 삭제
        self.input_text.delete("1.0", tk.END)
        
        # 원래 상태로 복원
        if original_state == 'disabled':
            self.input_text.configure(state=tk.DISABLED)
        
        # 결과 레이블 초기화
        label_text = "총 사용한 COIN 갯수" if "II" in self.header_text else "연산기호개수"
        self.result_label.config(text=f"값 : -, {label_text} : -", font=TITLE_FONT, fg=TEXT_COLOR)

    def run_analysis(self, event=None):
        if str(self.input_text['state']) == 'disabled':
            return 'break'
        content = self.input_text.get("1.0", tk.END).strip()
        # 줄바꿈 문자 제거 (자동 줄바꿈으로 인한 것)
        content = content.replace('\n', '').replace('\r', '')
        
        # 허용된 기호만 사용했는지 검증 (영문, 숫자 1 이외, 특수문자 !@#$%^& 등 차단)
        allowed_chars = set("1()+*")
        for char in content:
            if char not in allowed_chars:
                messagebox.showerror("허용되지 않은 기호", 
                                   f"'{char}'는 사용할 수 없는 기호입니다.\n사용 가능한 기호: 1, (, ), +, *\n영문, 다른 숫자, 특수문자(!@#$%^& 등)는 사용할 수 없습니다.")
                return 'break'
        
        # 모드에 따라 레이블 텍스트 변경 (미리 정의)
        label_text = "사용 COIN 갯수" if "II" in self.header_text else "연산기호개수"
        
        # '*' 연속 입력 검증 - '**'가 포함되면 무조건 불완전한 식으로 처리
        if '**' in content:
            if "II" in self.header_text:
                # 팀별개인전 II에서는 불완전한 식으로 처리
                # 임시 분석으로 코스트 계산
                temp_analysis = analyze_input(content, self.mode, costs=self.costs)
                if 'total_cost' in temp_analysis:
                    current_cost = temp_analysis['total_cost']
                else:
                    current_cost = temp_analysis['char_count']
                
                res_text = "거듭제곱 연산은 지원하지 않습니다"
                diff_text = f"값 : {res_text}\n{label_text} : {current_cost}\n❌ 오답 (팀 -3점)"
                font_size = ("Segoe UI", 14)
                self.result_label.config(text=diff_text, font=font_size, fg=ERROR_COLOR)
                self.result_label.pack_configure(expand=False)
                
                # 팀전체 감점 처리 (팀별개인전 II에서만)
                self._add_team_deduction_points(3)
                
                # 불완전한 식을 히스토리에 기록
                self._record_attempt_to_parent(content, current_cost, is_correct=False, error_message=res_text)
                
                # 팀별개인전 II에서는 불완전한 식도 입력창 초기화
                self.input_text.delete("1.0", tk.END)
                
                return 'break'  # 줄바꿈 방지
            else:
                # 팀별개인전 I에서는 기존 모달창 표시
                messagebox.showerror("연산자 오류", 
                                   "'*' 기호는 연속으로 사용할 수 없습니다.\n거듭제곱 연산은 지원하지 않습니다.")
                return 'break'
        
        analysis = analyze_input(content, self.mode, costs=self.costs)

        # update count
        if 'total_cost' in analysis:
            current_cost = analysis['total_cost']
        else:
            current_cost = analysis['char_count']
        
        current_input = content  # 현재 입력 내용 저장

        results = analysis['results']
        if not results:
            self.result_label.config(text=f"값 : -, {label_text} : -")
            

        elif len(results) == 1:
            res_text = results[0]['result']
            if isinstance(res_text, str) and ("불완전" in res_text or "누락" in res_text or "Invalid" in res_text):
                # 수식 오류인 경우: 오답 효과음 재생
                play_wrong_sound()
                # 콤마 제거 및 줄바꿈 추가
                res_text = res_text.replace(",", "")
                
                # 팀별개인전 II에서는 불완전한 식도 히스토리에 기록 (팀 -3점)
                if "II" in self.header_text:
                    diff_text = f"값 : {res_text}\n{label_text} : {current_cost}\n❌ 오답 (팀 -3점)"
                    font_size = ("Segoe UI", 14)
                    self.result_label.config(text=diff_text, font=font_size, fg=ERROR_COLOR)
                    self.result_label.pack_configure(expand=False)
                    
                    # 팀전체 감점 처리 (팀별개인전 II에서만)
                    self._add_team_deduction_points(3)
                    
                    # 불완전한 식을 히스토리에 기록
                    self._record_attempt_to_parent(current_input, current_cost, is_correct=False, error_message=res_text)
                    
                    # 팀별개인전 II에서는 불완전한 식도 입력창 초기화
                    self.input_text.delete("1.0", tk.END)
                    
                    return 'break'  # 줄바꿈 방지
                else:
                    self.result_label.config(text=f"값 : {res_text}\n{label_text} : {current_cost}", font=("Segoe UI", 29, "bold"), fg=ERROR_COLOR)
                    return 'break'  # 줄바꿈 방지
            else:
                # 목표 숫자와 비교하여 색상 결정
                if self.target_number is not None and str(res_text) == str(self.target_number):
                    # 먼저 최적해 확인
                    is_optimal = self._check_optimal_solution(current_cost)
                    
                    # 코스트 비교 확인
                    cost_check_passed = self._check_cost_comparison(current_cost)
                    
                    if cost_check_passed:
                        # 코스트 체크 통과: 정답 효과음 재생
                        play_correct_sound()
                        
                        # 목표 연산기호 개수와 정확히 일치하는지 확인
                        is_exact_match = self._check_exact_cost_match(current_cost)
                        
                        # 팀별개인전 II에서는 간소화된 폰트와 레이아웃 사용
                        font_size = ("Segoe UI", 14) if "II" in self.header_text else TITLE_FONT
                        expand_setting = False if "II" in self.header_text else True
                        
                        if is_optimal:
                            # 최적해인 경우
                            success_text = f"값 : {res_text} ✓\n{label_text} : {current_cost}"
                            if "II" in self.header_text:
                                success_text += "\n⭐ 최적해"
                            self.result_label.config(text=success_text, font=font_size, fg=SUCCESS_COLOR)
                            self.result_label.pack_configure(expand=expand_setting)
                            messagebox.showinfo("최적해", "최적해를 찾았습니다!")
                        elif is_exact_match:
                            # 목표 연산기호 개수와 정확히 일치하지만 최적해가 아닌 경우
                            if "II" in self.header_text:
                                success_text = f"값 : {res_text} ✓\n{label_text} : {current_cost}\n정답 (득점없음)"
                            else:
                                success_text = f"값 : {res_text} ✓\n{label_text} : {current_cost}\n정답을 입력했지만 득점이나 감점은 없습니다."
                            self.result_label.config(text=success_text, font=font_size, fg=SUCCESS_COLOR)
                            self.result_label.pack_configure(expand=expand_setting)
                        else:
                            # 정답이지만 최적해가 아닌 일반적인 경우
                            if "II" in self.header_text:
                                success_text = f"값 : {res_text} ✓\n{label_text} : {current_cost}\n정답"
                            else:
                                success_text = f"값 : {res_text} ✓\n{label_text} : {current_cost}\n최적해는 아닙니다. 더 찾아보세요."
                            self.result_label.config(text=success_text, font=font_size, fg=SUCCESS_COLOR)
                            self.result_label.pack_configure(expand=expand_setting)
                        
                        # 부모가 SinglePlayerView인 경우 히스토리에 기록
                        self._record_success_if_single_player(content, analysis)
                        # 정답인 경우에만 입력 필드 초기화
                        self.input_text.delete("1.0", tk.END)
                        return 'break'  # 줄바꿈 방지
                    else:
                        # 코스트가 목표보다 큰 경우: 오답 효과음만 재생
                        play_wrong_sound()
                        
                        # 부모 뷰에서 현재 모드 가져오기
                        current_mode = 'I'
                        if hasattr(self.master.master.master, 'current_mode'):
                            current_mode = self.master.master.master.current_mode
                            
                        # 팀별개인전 II에서는 간소화된 폰트와 레이아웃 사용
                        font_size = ("Segoe UI", 14) if "II" in self.header_text else TITLE_FONT
                        expand_setting = False if "II" in self.header_text else True
                            
                        if is_optimal:
                            # 최적해이지만 목표보다 큰 경우
                            if "II" in self.header_text:
                                diff_text = f"값 : {res_text}\n{label_text} : {current_cost}\n⚠️ 승리값 초과 (최적해: {current_cost}개)"
                            else:
                                diff_text = f"값 : {res_text}\n{label_text} : {current_cost}\n팀별개인전 {current_mode}에서 승리한 값보다 값이 큽니다.\n(최적해: {current_cost}개)"
                            self.result_label.config(text=diff_text, font=font_size, fg=WARNING_COLOR)
                            self.result_label.pack_configure(expand=expand_setting)
                            messagebox.showinfo("최적해", "최적해를 찾았습니다!")
                        else:
                            if "II" in self.header_text:
                                diff_text = f"값 : {res_text}\n{label_text} : {current_cost}\n⚠️ 승리값 초과"
                            else:
                                diff_text = f"값 : {res_text}\n{label_text} : {current_cost}\n팀별개인전 {current_mode}에서 승리한 값보다 값이 큽니다."
                            self.result_label.config(text=diff_text, font=font_size, fg=ERROR_COLOR)
                            self.result_label.pack_configure(expand=expand_setting)
                            
                        # 팀별개인전 II에서는 승리값 초과인 경우에도 입력창 초기화
                        if "II" in self.header_text:
                            self.input_text.delete("1.0", tk.END)
                            return 'break'  # 줄바꿈 방지
                        return 'break'  # 줄바꿈 방지
                else:
                    # 정답이 아닌 경우: 오답 효과음 재생
                    play_wrong_sound()
                    
                    # 팀전체 감점 처리 (팀별개인전 II에서만)
                    if "II" in self.header_text:
                        self._add_team_deduction_points(3)
                    
                    # 메시지 간소화 및 동적 레이아웃 적용
                    if self.target_number is not None:
                        if "II" in self.header_text:
                            diff_text = f"값 : {res_text}\n{label_text} : {current_cost}\n❌ 오답 (팀 -3점)"
                            # 팀별개인전 II에서는 작은 폰트와 최소 여백 유지
                            font_size = ("Segoe UI", 14)
                            self.result_label.pack_configure(expand=False)
                        else:
                            diff_text = f"값 : {res_text}\n{label_text} : {current_cost}\n❌ 오답"
                            font_size = TITLE_FONT
                            self.result_label.pack_configure(expand=True)
                    else:
                        diff_text = f"값 : {res_text}\n{label_text} : {current_cost}"
                        font_size = ("Segoe UI", 14) if "II" in self.header_text else TITLE_FONT
                        
                    self.result_label.config(text=diff_text, font=font_size, fg=ERROR_COLOR)
                    # 팀별개인전 II에서는 최소 공간 사용
                    expand_setting = False if "II" in self.header_text else True
                    self.result_label.pack_configure(expand=expand_setting)
                    
                    # 팀별개인전 II에서는 오답인 경우에도 히스토리에 기록하고 입력창 초기화
                    if "II" in self.header_text:
                        # 오답을 히스토리에 기록 (감점 처리는 이미 다른 곳에서 되고 있음)
                        self._record_attempt_to_parent(current_input, current_cost, is_correct=False, error_message=f"목표값 {self.target_number}, 실제값 {res_text}")
                        self.input_text.delete("1.0", tk.END)
                        return 'break'  # 줄바꿈 방지
                    return 'break'  # 줄바꿈 방지
        else:
            display = "".join([f"{item['expr']} = {item['result']}\n" for item in results]).strip()
            # 팀별개인전 II에서는 간소화된 폰트와 레이아웃 사용
            font_size = ("Segoe UI", 12) if "II" in self.header_text else BODY_FONT
            expand_setting = False if "II" in self.header_text else True
            self.result_label.config(text=display, font=font_size, fg=TEXT_COLOR, justify=tk.LEFT)
            self.result_label.pack_configure(expand=expand_setting)
            


        return 'break'

    # Enable or disable editing (when timer ends)
    def set_editable(self, editable: bool):
        state = tk.NORMAL if editable else tk.DISABLED
        self.input_text.configure(state=state)

        # 활성화/비활성화 상태에 따라 패널 색상과 스타일 변경
        if editable:
            # 활성화 상태: 기본 컴포넌트 색상 유지
            panel_color = COMPONENT_BG_COLOR
            text_color = TEXT_COLOR
            # 패널에 활성화 테두리 효과 추가
            self.configure(bg=panel_color, relief=tk.RAISED, bd=2, highlightbackground=SUCCESS_COLOR, highlightthickness=2)
        else:
            # 비활성화 상태: 기본 컴포넌트 색상 유지
            panel_color = COMPONENT_BG_COLOR
            text_color = TEXT_COLOR  # 비활성화 상태에서도 텍스트는 보이도록
            # 평면 스타일로 음영 처리
            self.configure(bg=panel_color, relief=tk.FLAT, bd=0, highlightthickness=0)

        # 패널과 프레임들의 배경색 변경
        self.left_frame.configure(bg=panel_color)
        self.right_frame.configure(bg=panel_color)
        self.problem_frame.configure(bg=panel_color)
        if hasattr(self, 'header_frame'):
            self.header_frame.configure(bg=panel_color)

        # 레이블들의 배경색과 텍스트 색상 변경
        self.problem_text.configure(bg=panel_color)
        if hasattr(self, 'header_label'):
            self.header_label.configure(bg=panel_color)
        self.result_label.configure(bg=panel_color, fg=text_color)

        # 입력창에 포커스 설정
        if editable:
            self.input_text.focus_set()
            
        # 히스토리 텍스트 위젯 색상도 변경 (배경색만 변경, 텍스트 색상은 유지)
        self.history_text.configure(bg=panel_color)
            
    def _record_success_if_single_player(self, expression, analysis):
        """SinglePlayerView인 경우 정답을 히스토리에 기록"""
        # 부모 위젯들을 탐색하여 SinglePlayerView 찾기
        widget = self.master
        while widget is not None:
            if hasattr(widget, 'record_success') and hasattr(widget, '_panels'):
                # SinglePlayerView 찾음
                try:
                    # 현재 패널이 A인지 B인지 확인
                    panel_index = widget._panels.index(self)
                    
                    # 연산기호 개수 추출
                    if 'total_cost' in analysis:
                        cost = analysis['total_cost']
                    else:
                        cost = analysis['char_count']
                    
                    # 히스토리에 기록
                    widget.record_success(panel_index, expression, cost)
                    
                    # 첫 번째 학생(A 패널)인 경우 코스트 저장
                    if panel_index == 0:
                        widget.first_student_cost = cost
                except (ValueError, AttributeError) as e:
                    pass  # 오류 발생 시 무시
                break
            widget = widget.master
    
    def _check_cost_comparison(self, current_cost):
        """두 번째 학생의 코스트가 첫 번째 학생보다 작거나 같은지 확인"""
        # 팀원기회대결에서 목표 코스트가 설정된 경우 우선 확인
        if hasattr(self, 'team_target_cost') and self.team_target_cost is not None:
            return current_cost <= self.team_target_cost
        
        # 부모 위젯들을 탐색하여 SinglePlayerView 찾기
        widget = self.master
        while widget is not None:
            if hasattr(widget, 'first_student_cost') and hasattr(widget, '_panels'):
                # SinglePlayerView 찾음
                try:
                    # 현재 패널이 B(두 번째 학생)인지 확인
                    panel_index = widget._panels.index(self)
                    
                    if panel_index == 1 and widget.first_student_cost is not None:
                        # 두 번째 학생이고 첫 번째 학생의 코스트가 있는 경우
                        return current_cost <= widget.first_student_cost
                    else:
                        # 첫 번째 학생이거나 비교할 코스트가 없는 경우
                        return True
                except (ValueError, AttributeError):
                    return True
            widget = widget.master
        return True
    
    def _check_exact_cost_match(self, current_cost):
        """현재 코스트가 목표 연산기호 개수와 정확히 일치하는지 확인"""
        # 팀원기회대결에서 목표 코스트가 설정된 경우 우선 확인
        if hasattr(self, 'team_target_cost') and self.team_target_cost is not None:
            return current_cost == self.team_target_cost
        
        # 부모 위젯들을 탐색하여 SinglePlayerView 찾기
        widget = self.master
        while widget is not None:
            if hasattr(widget, 'first_student_cost') and hasattr(widget, '_panels'):
                # SinglePlayerView 찾음
                try:
                    # 현재 패널이 B(두 번째 학생)인지 확인
                    panel_index = widget._panels.index(self)
                    
                    if panel_index == 1 and widget.first_student_cost is not None:
                        # 두 번째 학생이고 첫 번째 학생의 코스트가 있는 경우
                        return current_cost == widget.first_student_cost
                    else:
                        # 첫 번째 학생이거나 비교할 코스트가 없는 경우
                        return False
                except (ValueError, AttributeError):
                    return False
            widget = widget.master
        return False
    
    def _check_optimal_solution(self, current_cost):
        """현재 코스트가 최적해인지 확인"""
        # 부모 위젯들을 탐색하여 SinglePlayerView 찾기
        widget = self.master
        while widget is not None:
            if hasattr(widget, 'optimal_cost') and widget.optimal_cost is not None:
                # SinglePlayerView 찾음, 최적 코스트와 비교
                return current_cost == widget.optimal_cost
            widget = widget.master
        return False
            
    def update_history(self, history_records):
        """히스토리 표시를 업데이트합니다. 전달된 모든 기록을 표시합니다."""
        self.history_records = history_records
        
        # 팀전체 감점 정보 가져오기
        team_deduction = 0
        widget = self.master
        while widget is not None:
            if hasattr(widget, 'team_deduction_points'):
                team_deduction = widget.team_deduction_points
                break
            widget = widget.master
        
        if not history_records:
            # 팀별개인전 II에서는 헤더 없이 감점 정보만 표시
            if "II" in self.header_text:
                base_text = ""
                if team_deduction > 0:
                    base_text = f"❌ 현재 누적된 팀 전체 감점 : {team_deduction}점"
            else:
                base_text = "🏆 최고기록"
                if team_deduction > 0:
                    base_text += f"\n❌ 현재 누적된 팀 전체 감점 : {team_deduction}점"
            self._update_history_text(base_text, is_empty=True)
            return

        # 팀별개인전 II에서는 입력 순서 유지, 다른 모드에서는 기존 정렬 방식
        if "II" in self.header_text:
            display_records = history_records  # 입력 순서 유지
        else:
            display_records = sorted(history_records, key=lambda x: (x['cost'], x['time']))
        
        label_text_key = "사용 COIN 갯수" if "II" in self.header_text else "연산기호개수"
        
        history_entry_strings = []
        # 팀별개인전 II에서는 기준 COIN보다 작은 모든 해를 표시 (최대 20개), 다른 모드는 3개
        max_records = 20 if "II" in self.header_text else 3
        records_to_show = display_records[:max_records]

        # 팀별개인전 II에서는 번호를 매김 (헤더 없이)
        if "II" in self.header_text:
            for i, record in enumerate(records_to_show, 1):
                # 시간을 초.밀리초 형식으로 표시 (예: 1.23초)
                total_seconds = record['time']
                seconds = int(total_seconds)
                milliseconds = int((total_seconds - seconds) * 100)  # 밀리초를 2자리로 표시
                
                if seconds >= 60:
                    minutes = seconds // 60
                    remaining_seconds = seconds % 60
                    time_text = f"{minutes}분 {remaining_seconds}.{milliseconds:02d}초"
                else:
                    time_text = f"{seconds}.{milliseconds:02d}초"
                
                expr = record['expression']
                
                # 모든 기록에 번호만 표시 (최고기록 헤더 제거)
                line = f"#{i}\n{expr}\n{label_text_key}: {record['cost']}개, 걸린시간: {time_text}"
                
                # 시도 유형에 따른 상태 표시
                if record.get('is_correct', True):  # 정답인 경우
                    attempt_type = record.get('attempt_type', 'first_valid')
                    if attempt_type == 'exceed_threshold':
                        line += " 🔴 기준COIN초과"
                    elif attempt_type == 'repeat_valid':
                        line += " 🟡 중복COIN"
                    elif record.get('is_optimal', False):
                        line += " ⭐최적해"
                    # first_valid인 경우는 추가 표시 없음 (정상 정답)
                else:  # 오답인 경우
                    attempt_type = record.get('attempt_type', 'wrong_answer')
                    if attempt_type == 'incomplete':
                        line += " ❌ 불완전식 (팀 -3점)"
                    else:
                        line += " ❌ 오답 (팀 -3점)"
                
                history_entry_strings.append((line, record))
        else:
            # 기존 로직 (팀별개인전 I)
            # 첫 번째 기록은 '최고기록'으로 표시
            if records_to_show:
                best_record = records_to_show[0]
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
                
                best_line = f"🏆 최고기록\n{expr}\n{label_text_key}: {best_record['cost']}개, 걸린시간: {time_text}"
                if best_record.get('is_optimal', False):
                    best_line += " ⭐최적해"
                history_entry_strings.append(best_line)

            # 두 번째 기록부터는 제목 없이 자세한 정보 표시
            for record in records_to_show[1:]:
                # 시간을 초.밀리초 형식으로 표시 (예: 1.23초)
                total_seconds = record['time']
                seconds = int(total_seconds)
                milliseconds = int((total_seconds - seconds) * 100)  # 밀리초를 2자리로 표시
                
                if seconds >= 60:
                    minutes = seconds // 60
                    remaining_seconds = seconds % 60
                    time_text = f"{minutes}분 {remaining_seconds}.{milliseconds:02d}초"
                else:
                    time_text = f"{seconds}.{milliseconds:02d}초"
                
                expr = record['expression']
                
                line = f"{expr}\n{label_text_key}: {record['cost']}개, 걸린시간: {time_text}"
                if record.get('is_optimal', False):
                     line += " ⭐최적해"
                history_entry_strings.append(line)

        # 팀별개인전 II와 I 구분하여 처리
        if "II" in self.header_text:
            # 팀별개인전 II - 색상 적용
            self._update_history_text_with_colors(history_entry_strings, team_deduction)
        else:
            # 팀별개인전 I - 기존 방식
            final_text = "\n\n".join(history_entry_strings)
            
            # 팀전체 감점 정보 추가 (팀별개인전 II에서만)
            if team_deduction > 0:
                final_text += f"\n\n❌ 현재 누적된 팀 전체 감점 : {team_deduction}점"
            
            self._adjust_history_font_size(final_text)
            self._update_history_text(final_text, is_empty=False)
    
    def _adjust_history_font_size(self, text):
        """히스토리 레이블의 폰트 크기를 텍스트 길이에 따라 동적으로 조정"""
        # 팀별개인전 II에서는 더 작은 기본 폰트 사용
        base_font_size = 15 if "II" in self.header_text else 18
        min_font_size = 8
        
        # 텍스트를 줄별로 분리하여 각 줄의 최대 길이 확인
        lines = text.split('\n')
        max_line_length = 0
        expression_line = ""
        
        for i, line in enumerate(lines):
            # 두 번째 줄(인덱스 1)이 보통 식이므로 특별히 처리
            if i == 1 and ':' not in line:
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

        # 헤더 태그 폰트도 함께 업데이트 (팀별개인전 II에 맞게 조정)
        header_size_add = 2 if "II" in self.header_text else 3
        header_font = (font_family, font_size + header_size_add, "bold")
        self.history_text.tag_configure("header", font=header_font)
    
    def set_target_cost(self, target_cost):
        """팀원기회대결에서 목표 코스트 설정"""
        self.team_target_cost = target_cost
    
    def _add_team_deduction_points(self, points):
        """팀전체 감점을 SinglePlayerView에 추가"""
        # 부모 위젯들을 탐색하여 SinglePlayerView 찾기
        widget = self.master
        while widget is not None:
            if hasattr(widget, 'team_deduction_points'):
                # SinglePlayerView 찾음
                widget.team_deduction_points += points
                # 히스토리 업데이트
                if hasattr(widget, '_panels'):
                    for panel in widget._panels:
                        panel.update_history(panel.history_records)
                break
            widget = widget.master

    def _update_history_text_with_colors(self, history_entry_strings, team_deduction):
        """팀별개인전 II용 색상이 적용된 히스토리 텍스트 업데이트"""
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete("1.0", tk.END)
        
        for i, entry_data in enumerate(history_entry_strings):
            if isinstance(entry_data, tuple):
                line, record = entry_data
                attempt_type = record.get('attempt_type', 'first_valid')
                is_correct = record.get('is_correct', True)
                
                # 색상 태그 결정 - attempt_type 우선 적용
                if is_correct:
                    if attempt_type == 'exceed_threshold':
                        color_tag = "exceed_threshold"
                    elif attempt_type == 'repeat_valid':
                        color_tag = "repeat_valid"
                    elif record.get('is_optimal', False):
                        color_tag = "optimal"
                    else:  # first_valid
                        color_tag = "first_valid"
                else:
                    if attempt_type == 'incomplete':
                        color_tag = "incomplete"
                    else:
                        color_tag = "wrong_answer"
            else:
                # 기존 방식 (팀별개인전 I)
                line = entry_data
                color_tag = "title"
            
            # 텍스트 삽입
            if i > 0:
                self.history_text.insert(tk.END, "\n\n")
            
            self.history_text.insert(tk.END, line, color_tag)
        
        # 팀전체 감점 정보 추가
        if team_deduction > 0:
            if history_entry_strings:
                self.history_text.insert(tk.END, "\n\n")
            self.history_text.insert(tk.END, f"❌ 현재 누적된 팀 전체 감점 : {team_deduction}점", "wrong_answer")
        
        self.history_text.config(state=tk.DISABLED)
        
        # 스크롤을 맨 아래로 이동하여 최신 입력에 포커싱
        self.history_text.see(tk.END)

    def _record_attempt_to_parent(self, expression, cost, is_correct, error_message=None):
        """부모 클래스의 record_attempt 메서드를 호출하여 시도를 기록"""
        # 부모 위젯을 찾아서 record_attempt 호출
        widget = self.master
        while widget is not None:
            if hasattr(widget, 'record_attempt'):
                # 패널 인덱스 찾기 (A 패널인지 B 패널인지)
                panel_index = 0  # 기본값은 A 패널 (첫 번째)
                if hasattr(widget, '_panels'):
                    for i, panel in enumerate(widget._panels):
                        if panel == self:
                            panel_index = i
                            break
                widget.record_attempt(panel_index, expression, cost, is_correct, error_message)
                break
            widget = widget.master 