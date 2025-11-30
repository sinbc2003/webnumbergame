# ui/mode_selection_view.py
import tkinter as tk
from constants import *
from ui.single_player_view import SinglePlayerView
from ui.multiplayer_view import MultiplayerView
from ui.team_cost_distribution_view import TeamCostDistributionView
from ui.network_team_game_view import NetworkTeamGameView

class ModeSelectionView(tk.Frame):
    def __init__(self, master, game_type: str):
        """
        모드를 고른 뒤 다음 화면으로 이동한다.
        :param master: 부모 위젯
        :param game_type: 'single', 'multi_host', 'multi_guest'
        """
        super().__init__(master, bg=BG_COLOR)
        self.master = master
        self.game_type = game_type
        self.create_widgets()

    def create_widgets(self):
        title_label = tk.Label(self, text="모드 선택", font=TITLE_FONT, bg=BG_COLOR, fg=TEXT_COLOR)
        title_label.pack(pady=(100, 50))

        # --- Mode Buttons ---
        normal_mode_btn = tk.Button(self, text="1라운드 팀별 개인전 모드", command=lambda: self.select_mode('cost'),
                                     font=SUBTITLE_FONT, bg=COMPONENT_BG_COLOR, fg=TEXT_COLOR,
                                     activebackground=BUTTON_HOVER_COLOR, width=20, pady=10, relief=tk.FLAT)
        normal_mode_btn.pack(pady=10)

        # 팀전모드 버튼 추가
        team_mode_btn = tk.Button(self, text="2라운드 팀전 모드", command=lambda: self.select_mode('team'),
                                   font=SUBTITLE_FONT, bg=COMPONENT_BG_COLOR, fg=TEXT_COLOR,
                                   activebackground=BUTTON_HOVER_COLOR, width=20, pady=10, relief=tk.FLAT)
        team_mode_btn.pack(pady=10)

        # --- Start Button (disabled until mode selected) ---
        self.start_btn = tk.Button(self, text="시작", command=self.start_game, state=tk.DISABLED,
                                   font=SUBTITLE_FONT, bg=ACCENT_COLOR, fg=TEXT_COLOR, width=20, pady=10, relief=tk.FLAT)
        self.start_btn.pack(pady=30)
        
        # --- Back Button ---
        back_btn = tk.Button(self, text="뒤로가기", command=self.go_back,
                             font=BODY_FONT, bg=BORDER_COLOR, fg=TEXT_COLOR, relief=tk.FLAT)
        back_btn.pack(pady=50)

    def select_mode(self, mode: str):
        self.selected_mode = mode
        self.start_btn.config(state=tk.NORMAL)

    def start_game(self):
        import tkinter.messagebox as mb
        if not getattr(self, 'selected_mode', None):
            return
        if not mb.askyesno("시작 확인", "정말 시작하시겠습니까?"):
            return

        mode = self.selected_mode
        
        # 팀전 모드 별도 분기
        if mode == 'team':
            if self.game_type == 'single':
                self.master.switch_frame(TeamCostDistributionView)
            elif self.game_type == 'multi_host':
                self.master.switch_frame(
                    TeamCostDistributionView,
                    next_view_class=NetworkTeamGameView,
                    next_view_kwargs={'is_host': True},
                    forward_team_data=True,
                    use_network_team_problems=True
                )
            elif self.game_type == 'multi_guest':
                self.master.switch_frame(
                    TeamCostDistributionView,
                    next_view_class=NetworkTeamGameView,
                    next_view_kwargs={'is_host': False},
                    forward_team_data=True,
                    use_network_team_problems=True
                )
            return
        elif self.game_type == 'single':
            self.master.switch_frame(SinglePlayerView, mode=mode)
        elif self.game_type == 'multi_host':
            self.master.switch_frame(MultiplayerView, is_host=True, mode=mode)
        elif self.game_type == 'multi_guest':
            self.master.switch_frame(MultiplayerView, is_host=False, mode=mode)

    def go_back(self):
        from ui.main_menu_view import MainMenuView
        self.master.switch_frame(MainMenuView) 