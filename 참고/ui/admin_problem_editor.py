import tkinter as tk
from tkinter import messagebox
from utils.problem_store import (
    load_problems, save_problems, load_costs, save_costs, 
    load_team_mode_settings, save_team_mode_settings,
    load_team_problems, save_team_problems,
    load_team_costs, save_team_costs,
    load_timer_settings, save_timer_settings,
    load_team_cost_range, save_team_cost_range,
    load_strategy_time, save_strategy_time,
    load_reset_limit, save_reset_limit,
    load_mode1_problems, save_mode1_problems,
    load_mode2_problems, save_mode2_problems,
    load_mode1_costs, save_mode1_costs,
    load_mode2_costs, save_mode2_costs,
    load_network_mode1_problems, save_network_mode1_problems,
    load_network_mode2_problems, save_network_mode2_problems,
    load_network_team_problems, save_network_team_problems
)
from constants import *

class AdminProblemEditor(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("관리자 설정")
        self.configure(bg=BG_COLOR)
        self.geometry("600x800")  # 크기 더 증가
        self.create_widgets()

    def create_widgets(self):
        # 스크롤 가능한 프레임 생성
        canvas = tk.Canvas(self, bg=BG_COLOR)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # === 1라운드 팀별 개인전 모드 I 설정 ===
        title1 = tk.Label(scrollable_frame, text="1라운드 팀별 개인전 모드 I 설정", bg=BG_COLOR, fg=ACCENT_COLOR, font=SUBTITLE_FONT)
        title1.pack(pady=(10, 5))

        info = tk.Label(scrollable_frame, text="목표 숫자와 최적 연산기호 개수를 입력하세요", bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT)
        info.pack(pady=5)
        
        info2 = tk.Label(scrollable_frame, text="형식: 목표숫자:최적개수 (예: 16:3, 25:5, 30)", bg=BG_COLOR, fg=TEXT_COLOR, font=("Segoe UI", 10))
        info2.pack(pady=2)
        
        info3 = tk.Label(scrollable_frame, text="※ 최적 개수를 생략하면 최적해 체크를 하지 않습니다", bg=BG_COLOR, fg=TEXT_COLOR, font=("Segoe UI", 10))
        info3.pack(pady=2)

        self.mode1_text = tk.Text(scrollable_frame, bg=INPUT_BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT, height=3)
        self.mode1_text.pack(padx=10, pady=5, fill=tk.X)

        # Load existing mode1 problems
        mode1_problems = load_mode1_problems()
        if mode1_problems:
            # 문제를 목표 숫자와 최적 개수로 표시
            problem_strs = []
            for p in mode1_problems:
                if isinstance(p, dict):
                    target = p['target']
                    if 'optimal_cost' in p:
                        problem_strs.append(f"{target}:{p['optimal_cost']}")
                    else:
                        problem_strs.append(str(target))
                else:
                    problem_strs.append(str(p))
            self.mode1_text.insert("1.0", ", ".join(problem_strs))

        # === 1라운드 팀별 개인전 모드 II 설정 ===
        separator_mode2 = tk.Frame(scrollable_frame, bg=BORDER_COLOR, height=2)
        separator_mode2.pack(fill=tk.X, pady=10)
        
        title2 = tk.Label(scrollable_frame, text="1라운드 팀별 개인전 모드 II 설정", bg=BG_COLOR, fg=ACCENT_COLOR, font=SUBTITLE_FONT)
        title2.pack(pady=(10, 5))

        info_mode2 = tk.Label(scrollable_frame, text="목표 숫자와 최적 연산기호 개수를 입력하세요", bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT)
        info_mode2.pack(pady=5)
        
        info2_mode2 = tk.Label(scrollable_frame, text="형식: 목표숫자:최적개수:기준COIN (예: 16:3:5, 25:5:8, 30)", bg=BG_COLOR, fg=TEXT_COLOR, font=("Segoe UI", 10))
        info2_mode2.pack(pady=2)
        
        info3_mode2 = tk.Label(scrollable_frame, text="※ 최적 개수나 기준COIN을 생략하면 해당 기능을 사용하지 않습니다", bg=BG_COLOR, fg=TEXT_COLOR, font=("Segoe UI", 10))
        info3_mode2.pack(pady=2)
        
        info4_mode2 = tk.Label(scrollable_frame, text="※ 기준COIN: 히스토리에 남을 최대 COIN 값 (이보다 적은 값만 히스토리에 표시)", bg=BG_COLOR, fg=TEXT_COLOR, font=("Segoe UI", 10))
        info4_mode2.pack(pady=2)

        self.mode2_text = tk.Text(scrollable_frame, bg=INPUT_BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT, height=3)
        self.mode2_text.pack(padx=10, pady=5, fill=tk.X)

        # Load existing mode2 problems
        mode2_problems = load_mode2_problems()
        if mode2_problems:
            # 문제를 목표 숫자, 최적 개수, 기준 COIN으로 표시
            problem_strs = []
            for p in mode2_problems:
                if isinstance(p, dict):
                    target = p['target']
                    parts = [str(target)]
                    if 'optimal_cost' in p:
                        parts.append(str(p['optimal_cost']))
                        if 'threshold_coin' in p:
                            parts.append(str(p['threshold_coin']))
                    elif 'threshold_coin' in p:
                        parts.append("")  # 최적개수 없이 기준COIN만 있는 경우
                        parts.append(str(p['threshold_coin']))
                    problem_strs.append(":".join(parts))
                else:
                    problem_strs.append(str(p))
            self.mode2_text.insert("1.0", ", ".join(problem_strs))

        # === 네트워크 대전 문제 설정 ===
        separator_network = tk.Frame(scrollable_frame, bg=BORDER_COLOR, height=2)
        separator_network.pack(fill=tk.X, pady=10)

        network_title = tk.Label(
            scrollable_frame,
            text="네트워크 대전 문제 설정",
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
            font=SUBTITLE_FONT
        )
        network_title.pack(pady=(10, 5))

        network_info = tk.Label(
            scrollable_frame,
            text="비워두면 일반 모드 설정을 그대로 사용합니다.",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=BODY_FONT
        )
        network_info.pack(pady=(0, 5))

        # 네트워크 1라운드 모드 I
        net_mode1_label = tk.Label(
            scrollable_frame,
            text="네트워크 1라운드 모드 I (형식: 목표숫자:최적개수)",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=BODY_FONT
        )
        net_mode1_label.pack(pady=(5, 2))

        self.network_mode1_text = tk.Text(
            scrollable_frame,
            bg=INPUT_BG_COLOR,
            fg=TEXT_COLOR,
            font=BODY_FONT,
            height=2
        )
        self.network_mode1_text.pack(padx=10, pady=5, fill=tk.X)

        network_mode1 = load_network_mode1_problems()
        if network_mode1:
            mode1_strs = []
            for p in network_mode1:
                if isinstance(p, dict):
                    target = p.get('target')
                    optimal = p.get('optimal_cost')
                    if optimal is not None:
                        mode1_strs.append(f"{target}:{optimal}")
                    else:
                        mode1_strs.append(str(target))
                else:
                    mode1_strs.append(str(p))
            self.network_mode1_text.insert("1.0", ", ".join(mode1_strs))

        # 네트워크 1라운드 모드 II
        net_mode2_label = tk.Label(
            scrollable_frame,
            text="네트워크 1라운드 모드 II (형식: 목표숫자:최적개수:기준COIN)",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=BODY_FONT
        )
        net_mode2_label.pack(pady=(10, 2))

        self.network_mode2_text = tk.Text(
            scrollable_frame,
            bg=INPUT_BG_COLOR,
            fg=TEXT_COLOR,
            font=BODY_FONT,
            height=2
        )
        self.network_mode2_text.pack(padx=10, pady=5, fill=tk.X)

        network_mode2 = load_network_mode2_problems()
        if network_mode2:
            mode2_strs = []
            for p in network_mode2:
                if isinstance(p, dict):
                    parts = [str(p.get('target'))]
                    if p.get('optimal_cost') is not None:
                        parts.append(str(p['optimal_cost']))
                    if p.get('threshold_coin') is not None:
                        if len(parts) == 1:
                            parts.append("")
                        parts.append(str(p['threshold_coin']))
                    mode2_strs.append(":".join(parts))
                else:
                    mode2_strs.append(str(p))
            self.network_mode2_text.insert("1.0", ", ".join(mode2_strs))

        # 네트워크 2라운드 팀전
        net_team_label = tk.Label(
            scrollable_frame,
            text="네트워크 2라운드 팀전 문제 (콤마로 구분)",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=BODY_FONT
        )
        net_team_label.pack(pady=(10, 2))

        self.network_team_text = tk.Text(
            scrollable_frame,
            bg=INPUT_BG_COLOR,
            fg=TEXT_COLOR,
            font=BODY_FONT,
            height=2
        )
        self.network_team_text.pack(padx=10, pady=5, fill=tk.X)

        network_team = load_network_team_problems()
        if network_team:
            self.network_team_text.insert("1.0", ", ".join(map(str, network_team)))

        # === 1라운드 팀별 개인전 모드 I 기호별 코스트 설정 ===
        separator1 = tk.Frame(scrollable_frame, bg=BORDER_COLOR, height=2)
        separator1.pack(fill=tk.X, pady=10)

        cost_title1 = tk.Label(scrollable_frame, text="1라운드 팀별 개인전 모드 I 기호별 코스트", bg=BG_COLOR, fg=ACCENT_COLOR, font=SUBTITLE_FONT)
        cost_title1.pack(pady=5)

        cost_info1 = tk.Label(scrollable_frame, text="※ 1의 코스트는 연속된 개수로 계산됩니다", 
                    bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT)
        cost_info1.pack(pady=2)

        cost_frame1 = tk.Frame(scrollable_frame, bg=BG_COLOR)
        cost_frame1.pack(pady=5)

        self.mode1_cost_vars = {}
        mode1_costs = load_mode1_costs()
        symbols = ['1', '+', '*', '(', ')']
        for i, sym in enumerate(symbols):
            tk.Label(cost_frame1, text=sym, bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=i, column=0, padx=5, sticky='e')
            var = tk.StringVar(value=str(mode1_costs.get(sym, 1)))
            self.mode1_cost_vars[sym] = var
            tk.Entry(cost_frame1, textvariable=var, width=5, bg=INPUT_BG_COLOR, fg=TEXT_COLOR).grid(row=i, column=1, padx=5, sticky='w')

        # === 1라운드 팀별 개인전 모드 II 기호별 코스트 설정 ===
        separator_cost2 = tk.Frame(scrollable_frame, bg=BORDER_COLOR, height=2)
        separator_cost2.pack(fill=tk.X, pady=10)

        cost_title2 = tk.Label(scrollable_frame, text="1라운드 팀별 개인전 모드 II 기호별 코스트", bg=BG_COLOR, fg=ACCENT_COLOR, font=SUBTITLE_FONT)
        cost_title2.pack(pady=5)

        cost_info2 = tk.Label(scrollable_frame, text="※ 1의 코스트는 연속된 개수로 계산됩니다", 
                    bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT)
        cost_info2.pack(pady=2)

        cost_frame2 = tk.Frame(scrollable_frame, bg=BG_COLOR)
        cost_frame2.pack(pady=5)

        self.mode2_cost_vars = {}
        mode2_costs = load_mode2_costs()
        for i, sym in enumerate(symbols):
            tk.Label(cost_frame2, text=sym, bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=i, column=0, padx=5, sticky='e')
            var = tk.StringVar(value=str(mode2_costs.get(sym, 1)))
            self.mode2_cost_vars[sym] = var
            tk.Entry(cost_frame2, textvariable=var, width=5, bg=INPUT_BG_COLOR, fg=TEXT_COLOR).grid(row=i, column=1, padx=5, sticky='w')

        # === 타이머 설정 ===
        separator_timer = tk.Frame(scrollable_frame, bg=BORDER_COLOR, height=2)
        separator_timer.pack(fill=tk.X, pady=15)
        
        timer_title = tk.Label(scrollable_frame, text="타이머 설정", bg=BG_COLOR, fg=ACCENT_COLOR, font=SUBTITLE_FONT)
        timer_title.pack(pady=5)
        
        timer_info = tk.Label(scrollable_frame, text="각 라운드의 제한 시간을 분 단위로 설정하세요", 
                             bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT)
        timer_info.pack(pady=2)
        
        timer_frame = tk.Frame(scrollable_frame, bg=BG_COLOR)
        timer_frame.pack(pady=10)
        
        # 타이머 설정 로드
        timer_settings = load_timer_settings()
        
        # 1라운드 모드 I 타이머
        tk.Label(timer_frame, text="1라운드 모드 I 제한 시간:", bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.mode1_timer_var = tk.StringVar(value=str(timer_settings['mode1_minutes']))
        tk.Entry(timer_frame, textvariable=self.mode1_timer_var, width=5, bg=INPUT_BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=0, column=1, padx=5, pady=5)
        tk.Label(timer_frame, text="분", bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=0, column=2, padx=5, pady=5, sticky='w')
        
        # 1라운드 모드 II 타이머
        tk.Label(timer_frame, text="1라운드 모드 II 제한 시간:", bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.mode2_timer_var = tk.StringVar(value=str(timer_settings['mode2_minutes']))
        tk.Entry(timer_frame, textvariable=self.mode2_timer_var, width=5, bg=INPUT_BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=1, column=1, padx=5, pady=5)
        tk.Label(timer_frame, text="분", bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=1, column=2, padx=5, pady=5, sticky='w')
        
        # 2라운드 타이머
        tk.Label(timer_frame, text="2라운드 제한 시간:", bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=2, column=0, padx=5, pady=5, sticky='e')
        self.round2_timer_var = tk.StringVar(value=str(timer_settings['round2_minutes']))
        tk.Entry(timer_frame, textvariable=self.round2_timer_var, width=5, bg=INPUT_BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=2, column=1, padx=5, pady=5)
        tk.Label(timer_frame, text="분", bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=2, column=2, padx=5, pady=5, sticky='w')
        
        # COIN 분배창 타이머
        tk.Label(timer_frame, text="COIN 분배 제한 시간:", bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=3, column=0, padx=5, pady=5, sticky='e')
        self.coin_dist_timer_var = tk.StringVar(value=str(timer_settings.get('coin_distribution_minutes', 10)))
        tk.Entry(timer_frame, textvariable=self.coin_dist_timer_var, width=5, bg=INPUT_BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=3, column=1, padx=5, pady=5)
        tk.Label(timer_frame, text="분", bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=3, column=2, padx=5, pady=5, sticky='w')

        # === 2라운드 팀전 모드 설정 ===
        separator2 = tk.Frame(scrollable_frame, bg=BORDER_COLOR, height=2)
        separator2.pack(fill=tk.X, pady=15)

        team_title = tk.Label(scrollable_frame, text="2라운드 팀전 모드 설정", bg=BG_COLOR, fg=ACCENT_COLOR, font=TITLE_FONT)
        team_title.pack(pady=10)

        # 2라운드 팀전 모드 목표 숫자 목록
        team_problems_title = tk.Label(scrollable_frame, text="2라운드 팀전 모드 목표 숫자 목록", bg=BG_COLOR, fg=TEXT_COLOR, font=SUBTITLE_FONT)
        team_problems_title.pack(pady=5)

        team_problems_info = tk.Label(scrollable_frame, text="콤마로 구분해 팀전에서 사용할 목표 숫자들을 입력하세요", 
                                     bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT)
        team_problems_info.pack(pady=2)

        self.team_problems_text = tk.Text(scrollable_frame, bg=INPUT_BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT, height=3)
        self.team_problems_text.pack(padx=10, pady=5, fill=tk.X)

        # Load existing team problems
        team_problems = load_team_problems()
        if team_problems:
            self.team_problems_text.insert("1.0", ", ".join(map(str, team_problems)))

        # 2라운드 팀전 모드 총 코스트 설정
        team_cost_frame = tk.Frame(scrollable_frame, bg=BG_COLOR)
        team_cost_frame.pack(pady=10)

        team_settings = load_team_mode_settings()

        tk.Label(team_cost_frame, text="팀전 총 사용 가능한 코스트:", bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.total_cost_var = tk.StringVar(value=str(team_settings['total_cost']))
        tk.Entry(team_cost_frame, textvariable=self.total_cost_var, width=10, bg=INPUT_BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=0, column=1, padx=5, pady=5, sticky='w')

        # === 2라운드 팀전 모드 학생당 코스트 범위 설정 ===
        cost_range_title = tk.Label(scrollable_frame, text="2라운드 팀전 모드 학생당 코스트 범위", bg=BG_COLOR, fg=TEXT_COLOR, font=SUBTITLE_FONT)
        cost_range_title.pack(pady=(15, 5))
        
        cost_range_info = tk.Label(scrollable_frame, text="각 학생이 사용할 수 있는 코스트의 최소/최대 범위를 설정하세요", 
                                  bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT)
        cost_range_info.pack(pady=2)
        
        cost_range_frame = tk.Frame(scrollable_frame, bg=BG_COLOR)
        cost_range_frame.pack(pady=10)
        
        # 코스트 범위 설정 로드
        cost_range = load_team_cost_range()
        
        # 최소 코스트
        tk.Label(cost_range_frame, text="최소 코스트:", bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.min_cost_var = tk.StringVar(value=str(cost_range['min_cost']))
        tk.Entry(cost_range_frame, textvariable=self.min_cost_var, width=10, bg=INPUT_BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=0, column=1, padx=5, pady=5)
        
        # 최대 코스트
        tk.Label(cost_range_frame, text="최대 코스트:", bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.max_cost_var = tk.StringVar(value=str(cost_range['max_cost']))
        tk.Entry(cost_range_frame, textvariable=self.max_cost_var, width=10, bg=INPUT_BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=1, column=1, padx=5, pady=5)
        
        # 설명 텍스트
        range_note = tk.Label(scrollable_frame, text="※ 총 코스트를 4명에게 분배할 때 각 학생은 이 범위 내의 코스트를 받게 됩니다", 
                             bg=BG_COLOR, fg=TEXT_COLOR, font=("Segoe UI", 10))
        range_note.pack(pady=2)
        
        # === 작전회의 시간 설정 ===
        strategy_title = tk.Label(scrollable_frame, text="2라운드 작전회의 시간", bg=BG_COLOR, fg=TEXT_COLOR, font=SUBTITLE_FONT)
        strategy_title.pack(pady=(15, 5))
        
        strategy_info = tk.Label(scrollable_frame, text="전체 초기화 시 주어지는 작전회의 시간을 설정하세요", 
                                bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT)
        strategy_info.pack(pady=2)
        
        strategy_frame = tk.Frame(scrollable_frame, bg=BG_COLOR)
        strategy_frame.pack(pady=10)
        
        # 작전회의 시간 입력
        tk.Label(strategy_frame, text="작전회의 시간:", bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=0, column=0, padx=5, pady=5, sticky='e')
        strategy_minutes = load_strategy_time()
        self.strategy_time_var = tk.StringVar(value=str(strategy_minutes))
        tk.Entry(strategy_frame, textvariable=self.strategy_time_var, width=5, bg=INPUT_BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=0, column=1, padx=5, pady=5)
        tk.Label(strategy_frame, text="분", bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=0, column=2, padx=5, pady=5, sticky='w')
        
        # 설명 텍스트
        strategy_note = tk.Label(scrollable_frame, text="※ 작전회의 동안 모든 입력이 비활성화되며, 시간이 끝나면 자동으로 게임이 재개됩니다", 
                                bg=BG_COLOR, fg=TEXT_COLOR, font=("Segoe UI", 10))
        strategy_note.pack(pady=2)
        


        # === 2라운드 팀전 모드 기호별 코스트 설정 ===
        team_costs_title = tk.Label(scrollable_frame, text="2라운드 팀전 모드 기호별 코스트", bg=BG_COLOR, fg=TEXT_COLOR, font=SUBTITLE_FONT)
        team_costs_title.pack(pady=(15, 5))

        team_cost_frame2 = tk.Frame(scrollable_frame, bg=BG_COLOR)
        team_cost_frame2.pack(pady=5)

        self.team_cost_vars = {}
        team_costs = load_team_costs()
        for i, sym in enumerate(symbols):
            tk.Label(team_cost_frame2, text=sym, bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT).grid(row=i, column=0, padx=5, sticky='e')
            var = tk.StringVar(value=str(team_costs.get(sym, 1)))
            self.team_cost_vars[sym] = var
            tk.Entry(team_cost_frame2, textvariable=var, width=5, bg=INPUT_BG_COLOR, fg=TEXT_COLOR).grid(row=i, column=1, padx=5, sticky='w')

        # 2라운드 팀전 모드 설명
        team_info = tk.Label(scrollable_frame, 
                            text="2라운드 팀전 모드에서는 4명의 학생이 순서대로\n주어진 코스트를 분배하여 목표 숫자를 만듭니다.", 
                            bg=BG_COLOR, fg=TEXT_COLOR, font=BODY_FONT, justify=tk.CENTER)
        team_info.pack(pady=10)

        # 저장 버튼
        save_btn = tk.Button(scrollable_frame, text="모든 설정 저장", command=self.save, 
                            bg=ACCENT_COLOR, fg=TEXT_COLOR, font=SUBTITLE_FONT, pady=10)
        save_btn.pack(pady=20)

        # 마우스 휠 스크롤 바인딩
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def save(self):
        # === 모드 I 문제 저장 ===
        mode1_raw = self.mode1_text.get("1.0", tk.END).strip()
        mode1_problems = self._parse_mode1_input(mode1_raw, "모드 I")
        if mode1_problems is None:
            return
        save_mode1_problems(mode1_problems)
        
        # === 모드 II 문제 저장 ===
        mode2_raw = self.mode2_text.get("1.0", tk.END).strip()
        mode2_problems = self._parse_mode2_input(mode2_raw, "모드 II")
        if mode2_problems is None:
            return
        save_mode2_problems(mode2_problems)

        # === 네트워크 모드 I 문제 저장 ===
        network_mode1_raw = self.network_mode1_text.get("1.0", tk.END).strip()
        network_mode1 = self._parse_mode1_input(network_mode1_raw, "네트워크 모드 I")
        if network_mode1 is None:
            return
        save_network_mode1_problems(network_mode1)

        # === 네트워크 모드 II 문제 저장 ===
        network_mode2_raw = self.network_mode2_text.get("1.0", tk.END).strip()
        network_mode2 = self._parse_mode2_input(network_mode2_raw, "네트워크 모드 II")
        if network_mode2 is None:
            return
        save_network_mode2_problems(network_mode2)

        # === 네트워크 팀전 문제 저장 ===
        network_team_raw = self.network_team_text.get("1.0", tk.END)
        network_team = self._parse_team_problem_text(network_team_raw, "네트워크 팀전")
        if network_team is None:
            return
        save_network_team_problems(network_team)

        # === 모드 I 코스트 설정 저장 ===
        mode1_costs = {}
        for sym, var in self.mode1_cost_vars.items():
            val = var.get().strip()
            if not val.isdigit():
                messagebox.showerror("오류", f"모드 I에서 {sym}의 코스트가 유효한 숫자가 아닙니다.")
                return
            mode1_costs[sym] = int(val)
        save_mode1_costs(mode1_costs)

        # === 모드 II 코스트 설정 저장 ===
        mode2_costs = {}
        for sym, var in self.mode2_cost_vars.items():
            val = var.get().strip()
            if not val.isdigit():
                messagebox.showerror("오류", f"모드 II에서 {sym}의 코스트가 유효한 숫자가 아닙니다.")
                return
            mode2_costs[sym] = int(val)
        save_mode2_costs(mode2_costs)

        # === 팀전모드 목표 숫자 저장 ===
        team_raw = self.team_problems_text.get("1.0", tk.END)
        team_nums = self._parse_team_problem_text(team_raw, "팀전모드")
        if team_nums is None:
            return
        save_team_problems(team_nums)

        # === 팀전모드 총 코스트 저장 ===
        try:
            total_cost = int(self.total_cost_var.get().strip())
            if total_cost <= 0:
                messagebox.showerror("오류", "팀전 총 코스트는 1 이상이어야 합니다.")
                return
        except ValueError:
            messagebox.showerror("오류", "팀전 총 코스트가 유효한 숫자가 아닙니다.")
            return

        # === 팀전모드 기호별 코스트 저장 ===
        team_costs = {}
        for sym, var in self.team_cost_vars.items():
            val = var.get().strip()
            if not val.isdigit():
                messagebox.showerror("오류", f"팀전모드에서 {sym}의 코스트가 유효한 숫자가 아닙니다.")
                return
            team_costs[sym] = int(val)
        save_team_costs(team_costs)

        # 팀전모드 설정 저장 (target_number는 첫 번째 목표로 설정)
        target_number = team_nums[0] if team_nums else 25
        save_team_mode_settings(total_cost, target_number)
        
        # === 타이머 설정 저장 ===
        try:
            mode1_minutes = int(self.mode1_timer_var.get().strip())
            mode2_minutes = int(self.mode2_timer_var.get().strip())
            round2_minutes = int(self.round2_timer_var.get().strip())
            coin_dist_minutes = int(self.coin_dist_timer_var.get().strip())
            
            if mode1_minutes <= 0 or mode2_minutes <= 0 or round2_minutes <= 0 or coin_dist_minutes <= 0:
                messagebox.showerror("오류", "제한 시간은 1분 이상이어야 합니다.")
                return
                
            save_timer_settings(round2_minutes=round2_minutes, coin_distribution_minutes=coin_dist_minutes, 
                              mode1_minutes=mode1_minutes, mode2_minutes=mode2_minutes)
        except ValueError:
            messagebox.showerror("오류", "제한 시간이 유효한 숫자가 아닙니다.")
            return
            
        # === 팀전 코스트 범위 설정 저장 ===
        try:
            min_cost = int(self.min_cost_var.get().strip())
            max_cost = int(self.max_cost_var.get().strip())
            
            if min_cost <= 0 or max_cost <= 0:
                messagebox.showerror("오류", "코스트 범위는 1 이상이어야 합니다.")
                return
                
            if min_cost > max_cost:
                messagebox.showerror("오류", "최소 코스트가 최대 코스트보다 클 수 없습니다.")
                return
                
            # 총 코스트가 범위에 맞는지 확인
            if total_cost < min_cost * 4:
                messagebox.showerror("오류", f"총 코스트({total_cost})가 최소 범위({min_cost} × 4 = {min_cost * 4})보다 작습니다.")
                return
                
            if total_cost > max_cost * 4:
                messagebox.showerror("오류", f"총 코스트({total_cost})가 최대 범위({max_cost} × 4 = {max_cost * 4})보다 큽니다.")
                return
                
            save_team_cost_range(min_cost, max_cost)
        except ValueError:
            messagebox.showerror("오류", "코스트 범위가 유효한 숫자가 아닙니다.")
            return
            
        # === 작전회의 시간 설정 저장 ===
        try:
            strategy_minutes = int(self.strategy_time_var.get().strip())
            if strategy_minutes <= 0:
                messagebox.showerror("오류", "작전회의 시간은 1분 이상이어야 합니다.")
                return
            save_strategy_time(strategy_minutes)
        except ValueError:
            messagebox.showerror("오류", "작전회의 시간이 유효한 숫자가 아닙니다.")
            return
            


        messagebox.showinfo("완료", "모든 설정이 저장되었습니다.")
        self.destroy() 

    # === Helper methods ===
    def _parse_mode1_input(self, raw_text: str, context_label: str):
        problems = []
        parts = [p.strip() for p in raw_text.replace("\n", " ").split(',') if p.strip()]
        for part in parts:
            if ':' in part:
                try:
                    target_str, optimal_str = part.split(':', 1)
                    target = int(target_str.strip())
                    optimal = int(optimal_str.strip())
                    problems.append({'target': target, 'optimal_cost': optimal})
                except ValueError:
                    messagebox.showerror("오류", f"{context_label}에서 유효하지 않은 형식: {part}")
                    return None
            else:
                try:
                    target = int(part)
                    problems.append({'target': target})
                except ValueError:
                    messagebox.showerror("오류", f"{context_label}에서 유효하지 않은 숫자: {part}")
                    return None
        return problems

    def _parse_mode2_input(self, raw_text: str, context_label: str):
        problems = []
        parts = [p.strip() for p in raw_text.replace("\n", " ").split(',') if p.strip()]
        for part in parts:
            try:
                split_parts = part.split(':')
                target = int(split_parts[0].strip())
                problem_dict = {'target': target}
                if len(split_parts) >= 2 and split_parts[1].strip():
                    problem_dict['optimal_cost'] = int(split_parts[1].strip())
                if len(split_parts) >= 3 and split_parts[2].strip():
                    problem_dict['threshold_coin'] = int(split_parts[2].strip())
                problems.append(problem_dict)
            except ValueError:
                messagebox.showerror("오류", f"{context_label}에서 유효하지 않은 형식: {part}")
                return None
        return problems

    def _parse_team_problem_text(self, raw_text: str, context_label: str):
        numbers = []
        for part in raw_text.replace("\n", ",").split(','):
            value = part.strip()
            if value:
                try:
                    numbers.append(int(value))
                except ValueError:
                    messagebox.showerror("오류", f"{context_label}에서 유효하지 않은 숫자: {part}")
                    return None
        return numbers