# ui/main_menu_view.py
import tkinter as tk
import tkinter.simpledialog as sd
import tkinter.messagebox as messagebox

from constants import *
from ui.mode_selection_view import ModeSelectionView
from ui.network_mode_view import NetworkModeView

class MainMenuView(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=BG_COLOR)
        self.master = master
        self.create_widgets()

    def create_widgets(self):
        # Title
        title_label = tk.Label(self, text="숫자 게임", font=TITLE_FONT, bg=BG_COLOR, fg=TEXT_COLOR)
        title_label.pack(pady=(100, 50))

        # --- Buttons ---
        # 숫자 게임 시작 버튼 (로컬 플레이)
        start_game_btn = tk.Button(
            self,
            text="숫자 게임 시작",
            font=SUBTITLE_FONT,
            bg=COMPONENT_BG_COLOR,
            fg=TEXT_COLOR,
            activebackground=BUTTON_HOVER_COLOR,
            activeforeground=TEXT_COLOR,
            relief=tk.FLAT,
            borderwidth=2,
            highlightbackground=BORDER_COLOR,
            width=20,
            pady=10,
            command=self.start_game,
        )
        start_game_btn.pack(pady=10)
        self.bind_hover(start_game_btn, COMPONENT_BG_COLOR, BUTTON_HOVER_COLOR)

        # 네트워크 대전 진입 버튼
        network_btn = tk.Button(
            self,
            text="네트워크 대전",
            font=SUBTITLE_FONT,
            bg=ACCENT_COLOR,
            fg=TEXT_COLOR,
            activebackground=HIGHLIGHT_COLOR,
            activeforeground=TEXT_COLOR,
            relief=tk.FLAT,
            borderwidth=2,
            highlightbackground=BORDER_COLOR,
            width=20,
            pady=10,
            command=self.open_network_menu,
        )
        network_btn.pack(pady=10)
        self.bind_hover(network_btn, ACCENT_COLOR, HIGHLIGHT_COLOR)
        
        # 관리자 메뉴 버튼
        admin_menu_btn = tk.Button(self, text="관리자 메뉴", 
                                   font=SUBTITLE_FONT, 
                                   bg=ERROR_COLOR,
                                   fg=TEXT_COLOR,
                                   activebackground=WARNING_COLOR,
                                   activeforeground=TEXT_COLOR,
                                   relief=tk.FLAT,
                                   borderwidth=2,
                                   highlightbackground=BORDER_COLOR,
                                   width=20,
                                   pady=10,
                                   command=self.open_admin_menu)
        admin_menu_btn.pack(pady=10)
        self.bind_hover(admin_menu_btn, ERROR_COLOR, WARNING_COLOR)
        
        # 전체 화면 토글 버튼
        fullscreen_btn = tk.Button(self, text="전체 화면 (F11)", 
                                   font=BODY_FONT, 
                                   bg=ACCENT_COLOR,
                                   fg=TEXT_COLOR,
                                   activebackground=HIGHLIGHT_COLOR,
                                   activeforeground=TEXT_COLOR,
                                   relief=tk.FLAT,
                                   borderwidth=2,
                                   highlightbackground=BORDER_COLOR,
                                   width=20,
                                   pady=8,
                                   command=self.toggle_fullscreen)
        fullscreen_btn.pack(pady=10)
        self.bind_hover(fullscreen_btn, ACCENT_COLOR, HIGHLIGHT_COLOR)

    def bind_hover(self, widget, normal_color, hover_color):
        widget.bind("<Enter>", lambda e: widget.config(bg=hover_color))
        widget.bind("<Leave>", lambda e: widget.config(bg=normal_color))

    def start_game(self):
        print("숫자 게임 시작 선택")
        self.master.switch_frame(ModeSelectionView, game_type='single')
    
    def open_network_menu(self):
        """호스트/게스트 선택 화면으로 이동"""
        self.master.switch_frame(NetworkModeView)
        
    def open_admin_menu(self):
        """관리자 메뉴 열기 - 비밀번호 확인 후"""
        pwd = sd.askstring("관리자 인증", "관리자 비밀번호를 입력하세요", show='*')
        if pwd == '20250809!':
            from ui.admin_problem_editor import AdminProblemEditor
            AdminProblemEditor(self.master)
        elif pwd is not None:
            messagebox.showerror("인증 실패", "비밀번호가 일치하지 않습니다.")
    
    def toggle_fullscreen(self):
        """전체 화면 모드 토글"""
        self.master.toggle_fullscreen()

