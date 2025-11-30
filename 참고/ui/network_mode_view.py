import tkinter as tk

from constants import *
from ui.mode_selection_view import ModeSelectionView
from ui.multiplayer_view import MultiplayerView
from ui.network_spectator_view import NetworkSpectatorView


class NetworkModeView(tk.Frame):
    """호스트/게스트 역할을 선택하는 네트워크 진입 화면."""

    def __init__(self, master):
        super().__init__(master, bg=BG_COLOR)
        self.master = master
        self._build_layout()

    def _build_layout(self):
        title = tk.Label(
            self,
            text="네트워크 대전",
            font=TITLE_FONT,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
        )
        title.pack(pady=(60, 10))

        desc = tk.Label(
            self,
            text="다른 컴퓨터와 같은 네트워크에서 방을 만들거나 참가하여 대전할 수 있어요.",
            wraplength=640,
            justify="center",
            font=BODY_FONT,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
        )
        desc.pack(pady=(0, 40))

        button_frame = tk.Frame(self, bg=BG_COLOR)
        button_frame.pack(pady=10)

        host_btn = tk.Button(
            button_frame,
            text="방 만들기 (호스트)",
            font=SUBTITLE_FONT,
            width=22,
            pady=14,
            bg=COMPONENT_BG_COLOR,
            fg=TEXT_COLOR,
            activebackground=BUTTON_HOVER_COLOR,
            relief=tk.FLAT,
            command=self._start_as_host,
        )
        host_btn.grid(row=0, column=0, padx=10, pady=10)

        guest_btn = tk.Button(
            button_frame,
            text="방 참가하기 (게스트)",
            font=SUBTITLE_FONT,
            width=22,
            pady=14,
            bg=ACCENT_COLOR,
            fg=TEXT_COLOR,
            activebackground=HIGHLIGHT_COLOR,
            relief=tk.FLAT,
            command=self._start_as_guest,
        )
        guest_btn.grid(row=0, column=1, padx=10, pady=10)

        spectate_btn = tk.Button(
            button_frame,
            text="관전 모드",
            font=SUBTITLE_FONT,
            width=22,
            pady=14,
            bg=BORDER_COLOR,
            fg=TEXT_COLOR,
            activebackground=BUTTON_HOVER_COLOR,
            relief=tk.FLAT,
            command=self._start_spectator,
        )
        spectate_btn.grid(row=1, column=0, columnspan=2, padx=10, pady=10)

        info = tk.Label(
            self,
            text="- 호스트: 참가 코드를 공유하면 다른 컴퓨터가 접속할 수 있어요.\n"
            "- 게스트: 같은 네트워크에서 열린 방을 찾아 참가하거나 IP/포트를 직접 입력할 수 있어요.\n"
            "- 관전: 플레이어 두 대 외의 PC는 히스토리와 스코어만 확인하는 관전 전용 뷰를 사용하세요.",
            font=BODY_FONT,
            bg=BG_COLOR,
            fg=INACTIVE_TEXT_COLOR,
            justify="center",
        )
        info.pack(pady=20)

        back_btn = tk.Button(
            self,
            text="뒤로가기",
            font=BODY_FONT,
            width=14,
            pady=8,
            bg=BORDER_COLOR,
            fg=TEXT_COLOR,
            relief=tk.FLAT,
            command=self._go_back,
        )
        back_btn.pack(pady=(40, 0))

    def _start_as_host(self):
        """1P가 직접 문제 모드를 고르고 서버를 연다."""
        self.master.switch_frame(ModeSelectionView, game_type="multi_host")

    def _start_as_guest(self):
        """이미 열린 방을 찾아 참가한다."""
        self.master.switch_frame(MultiplayerView, is_host=False, mode="cost")

    def _start_spectator(self):
        """관전 전용 뷰"""
        self.master.switch_frame(NetworkSpectatorView)

    def _go_back(self):
        from ui.main_menu_view import MainMenuView

        self.master.switch_frame(MainMenuView)

