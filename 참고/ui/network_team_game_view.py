import json
import socket
import time
import tkinter as tk
from tkinter import messagebox, simpledialog, Toplevel, Listbox

from constants import *
from network.client import GameClient
from network.server import GameServer
from network.discovery import ZeroconfService, ZeroconfBrowser
from ui.team_game_view import TeamGameView
from utils.problem_store import load_network_team_problems


class NetworkTeamGameView(tk.Frame):
    """네트워크 2라운드(4 vs 4) 대전을 진행하는 뷰."""

    def __init__(self, master, is_host: bool, cost_distribution: dict,
                 target_number: int = None, team_problems=None):
        super().__init__(master, bg=BG_COLOR)
        self.master = master
        self.is_host = is_host
        self.cost_distribution = cost_distribution
        self.team_problems = team_problems or load_network_team_problems()
        self.target_number = target_number or (self.team_problems[0] if self.team_problems else 25)

        # Network components
        self.server = None
        self.client = None
        self.zeroconf_service = None
        self.zeroconf_browser = None
        self.browser_window = None

        # Game state
        self.round_active = False
        self.round_over = False
        self._closed = False
        self.team_attempts = {"host": [], "guest": []}
        self.attempt_log = []
        self.my_team_role = "host" if self.is_host else "guest"

        self.create_widgets()
        self.team_view = TeamGameView(
            self,
            cost_distribution=self.cost_distribution,
            target_number=self.target_number,
            team_problems=self.team_problems,
            network_delegate=self,
            timer_override_minutes=3
        )
        self.team_view.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.team_view.lock_inputs()

        self.after(100, self.start_network_flow)

    # --- UI 구성 ---
    def create_widgets(self):
        header = tk.Frame(self, bg=COMPONENT_BG_COLOR)
        header.pack(fill=tk.X, padx=10, pady=(10, 0))

        mode_label = tk.Label(
            header,
            text="네트워크 팀전 (4 vs 4)",
            font=SUBTITLE_FONT,
            bg=COMPONENT_BG_COLOR,
            fg=TEXT_COLOR,
        )
        mode_label.pack(side=tk.LEFT, padx=10, pady=10)

        self.status_label = tk.Label(
            header,
            text="네트워크 초기화 중...",
            font=BODY_FONT,
            bg=COMPONENT_BG_COLOR,
            fg=TEXT_COLOR,
        )
        self.status_label.pack(side=tk.RIGHT, padx=10)

        board_frame = tk.Frame(self, bg=BG_COLOR)
        board_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        my_desc = "우리 팀 (호스트)" if self.is_host else "우리 팀 (게스트)"
        opp_desc = "상대 팀 (게스트)" if self.is_host else "상대 팀 (호스트)"

        self.my_summary_label = tk.Label(
            board_frame,
            text=f"{my_desc} 최고기록: -",
            font=BODY_FONT,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            anchor="w"
        )
        self.my_summary_label.pack(fill=tk.X, pady=2)

        self.opp_summary_label = tk.Label(
            board_frame,
            text=f"{opp_desc} 최고기록: -",
            font=BODY_FONT,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            anchor="w"
        )
        self.opp_summary_label.pack(fill=tk.X, pady=2)

        self.history_text = tk.Text(
            board_frame,
            height=6,
            bg=INPUT_BG_COLOR,
            fg=TEXT_COLOR,
            state=tk.DISABLED,
            wrap=tk.WORD
        )
        self.history_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

    def _reset_round_state(self):
        self.team_attempts = {"host": [], "guest": []}
        self.attempt_log = []
        self.round_over = False
        self._update_attempt_board()

    # --- 네트워크 흐름 ---
    def start_network_flow(self):
        if self.is_host:
            self.setup_host()
        else:
            self.setup_guest()

    # Host
    def setup_host(self):
        self.status_label.config(text="서버 여는 중...")
        try:
            self.server = GameServer()
            self.server.start()
            self.server.on_receive = self.handle_server_message
            self.server.on_client_connect = self.on_client_connect
            self.server.on_client_disconnect = self.on_client_disconnect

            service_name = f"{socket.gethostname()}의 2라운드 팀전"
            props = {'mode': 'team'}
            self.zeroconf_service = ZeroconfService(service_name, self.server.port, props)
            self.zeroconf_service.register_service()

            self.status_label.config(
                text=f"상대를 기다리는 중... 참가 코드: {self.server.access_code}"
            )
        except Exception as exc:
            messagebox.showerror("서버 오류", f"서버를 시작할 수 없습니다: {exc}")
            self.leave_game()

    def on_client_connect(self, _socket):
        self.after(0, self.begin_round_as_host)

    def on_client_disconnect(self, _socket):
        if not self.round_over:
            self.status_label.config(text="상대 연결 끊김. 게임 종료.")
            messagebox.showinfo("연결 종료", "상대가 게임을 종료했습니다.")
        self.leave_game()

    def begin_round_as_host(self):
        if self.round_active:
            return
        self.round_active = True
        self.round_over = False
        self._reset_round_state()
        self.status_label.config(text=f"대전 시작! 목표: {self.target_number}")
        self.team_view.prepare_for_network_round(self.target_number)
        payload = json.dumps({
            "type": "team_round_start",
            "target": self.target_number,
            "duration": self.team_view.timer_minutes * 60,
        })
        if self.server:
            self.server.broadcast(payload)

    # Guest
    def setup_guest(self):
        self.status_label.config(text="열린 팀전 방을 찾는 중...")
        self.zeroconf_browser = ZeroconfBrowser()
        self.zeroconf_browser.start_browsing(update_callback=self.update_game_list)
        self.show_game_browser()

    def show_game_browser(self):
        self.browser_window = Toplevel(self)
        self.browser_window.title("팀전 방 참가하기")
        self.browser_window.geometry("420x320")
        self.browser_window.configure(bg=BG_COLOR)
        self.browser_window.grab_set()

        tk.Label(
            self.browser_window,
            text="참가할 게임을 선택하세요:",
            font=BODY_FONT,
            bg=BG_COLOR,
            fg=TEXT_COLOR
        ).pack(pady=10)

        self.game_listbox = Listbox(
            self.browser_window,
            bg=INPUT_BG_COLOR,
            fg=TEXT_COLOR,
            selectbackground=ACCENT_COLOR,
            relief=tk.FLAT
        )
        self.game_listbox.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)
        self.game_listbox.bind("<Double-Button-1>", self.on_game_select)

        tk.Button(
            self.browser_window,
            text="수동으로 IP 입력",
            command=self.manual_connect,
            bg=BORDER_COLOR,
            fg=TEXT_COLOR,
            relief=tk.FLAT,
            font=BODY_FONT
        ).pack(pady=10)

        self.update_game_list()
        self.browser_window.protocol("WM_DELETE_WINDOW", self.on_browser_close)

    def update_game_list(self):
        if not hasattr(self, 'game_listbox') or not self.game_listbox.winfo_exists():
            return
        self.game_listbox.delete(0, tk.END)
        self.listbox_map = {}
        for name, info in self.zeroconf_browser.found_services.items():
            display = f"[팀전] {name}"
            self.game_listbox.insert(tk.END, display)
            self.listbox_map[display] = name

    def on_game_select(self, _event):
        selection = self.game_listbox.curselection()
        if not selection:
            return
        display_name = self.game_listbox.get(selection[0])
        service_name = self.listbox_map.get(display_name)
        if not service_name:
            return
        service_info = self.zeroconf_browser.found_services.get(service_name)
        if not service_info:
            messagebox.showerror("오류", "선택한 게임 정보를 찾을 수 없습니다.")
            return
        host_ip, port, _ = service_info
        self.prompt_for_code_and_connect(host_ip, port)

    def manual_connect(self):
        ip = simpledialog.askstring("수동 연결", "호스트 IP:", parent=self.browser_window)
        if not ip:
            return
        port = simpledialog.askinteger(
            "수동 연결",
            "포트 번호:",
            parent=self.browser_window,
            minvalue=1024,
            maxvalue=65535
        )
        if not port:
            return
        self.prompt_for_code_and_connect(ip, port)

    def prompt_for_code_and_connect(self, host, port):
        code = simpledialog.askstring("참가 코드", "4자리 코드를 입력하세요:", parent=self.browser_window)
        if not code or len(code) != 4 or not code.isdigit():
            messagebox.showwarning("입력 오류", "유효한 4자리 숫자를 입력하세요.", parent=self.browser_window)
            return

        self.client = GameClient()
        self.client.on_receive = self.handle_client_message
        self.client.on_disconnect = self.on_server_disconnect

        success, message_text = self.client.connect(host, port, code)
        if success:
            self.browser_window.destroy()
            self.zeroconf_browser.stop_browsing()
            self.status_label.config(text="연결 성공! 호스트를 기다리는 중...")
        else:
            messagebox.showerror("연결 실패", message_text, parent=self.browser_window)
            self.client = None

    def on_browser_close(self):
        self.browser_window.destroy()
        self.leave_game()

    # --- 메시지 처리 ---
    def handle_server_message(self, message, sender_socket):
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return
        msg_type = data.get("type")

        if msg_type == "team_attempt":
            self.master.after(0, self._handle_remote_team_attempt, data)
        elif msg_type == "team_leave":
            self.on_client_disconnect(sender_socket)

    def handle_client_message(self, message):
        data = json.loads(message)
        msg_type = data.get("type")

        if msg_type == "team_round_start":
            self.target_number = data.get("target", self.target_number)
            self.round_active = True
            self.round_over = False
            self._reset_round_state()
            self.status_label.config(text=f"대전 시작! 목표: {self.target_number}")
            self.team_view.prepare_for_network_round(self.target_number)
        elif msg_type == "team_game_over":
            self._process_team_result(data)
        elif msg_type == "team_attempt":
            self._handle_remote_team_attempt(data)

    def on_server_disconnect(self):
        if not self.round_over:
            messagebox.showinfo("연결 종료", "호스트와의 연결이 끊어졌습니다.")
        self.leave_game()

    # --- TeamGameView 콜백 ---
    def on_team_attempt_recorded(self, record: dict):
        team_role = "host" if self.is_host else "guest"
        self._record_team_attempt(team_role, record, propagate=True)

    def on_team_timer_expired(self):
        if self.round_over:
            return
        self.team_view.lock_inputs()
        if self.is_host:
            self.status_label.config(text="시간 종료! 결과 계산 중...")
            self._finalize_team_round()
        else:
            self.status_label.config(text="시간 종료! 결과 대기 중...")

    def _record_team_attempt(self, team_role: str, record: dict, propagate=False):
        enriched = record.copy()
        enriched["team"] = team_role
        enriched["recorded_at"] = time.time()
        self.team_attempts.setdefault(team_role, []).append(enriched)

        actor_label = "우리 팀" if team_role == self.my_team_role else "상대 팀"
        self.attempt_log.append(self._format_attempt_line(actor_label, enriched))
        if len(self.attempt_log) > 40:
            self.attempt_log = self.attempt_log[-40:]
        self._update_attempt_board()

        if propagate:
            payload = {
                "type": "team_attempt",
                "team": team_role,
                "record": record
            }
            if self.is_host and self.server:
                self.server.broadcast(json.dumps(payload))
            elif not self.is_host and self.client:
                self.client.send_message(payload)

    def _handle_remote_team_attempt(self, data):
        team_role = data.get("team")
        record = data.get("record", {})
        if team_role not in ("host", "guest"):
            return
        self._record_team_attempt(team_role, record, propagate=False)

    def _update_attempt_board(self):
        host_best = self._select_best_team_attempt("host")
        guest_best = self._select_best_team_attempt("guest")
        my_best = host_best if self.my_team_role == "host" else guest_best
        opp_best = guest_best if self.my_team_role == "host" else host_best

        self.my_summary_label.config(text=self._format_summary_text("우리 팀", my_best))
        self.opp_summary_label.config(text=self._format_summary_text("상대 팀", opp_best))

        self.history_text.config(state=tk.NORMAL)
        if self.attempt_log:
            self.history_text.delete("1.0", tk.END)
            self.history_text.insert("1.0", "\n".join(self.attempt_log))
        else:
            self.history_text.delete("1.0", tk.END)
            self.history_text.insert("1.0", "시도 기록이 없습니다.")
        self.history_text.config(state=tk.DISABLED)

    def _format_attempt_line(self, label: str, record: dict) -> str:
        cost = record.get("cost")
        time_taken = record.get("time")
        status = "최적해" if record.get("is_optimal") else "정답"
        if cost is None:
            cost_text = "-"
        else:
            cost_text = f"{cost} COIN"
        if time_taken is None:
            time_text = ""
        else:
            time_text = f"{time_taken:.2f}초"
        return f"[{label}] {record.get('expression', '')} | {cost_text} | {time_text} | {status}"

    def _format_summary_text(self, label: str, record: dict) -> str:
        if not record:
            return f"{label} 최고기록: -"
        cost = record.get("cost", "-")
        time_taken = record.get("time")
        time_text = f"{time_taken:.2f}초" if time_taken is not None else "-"
        status = "최적해" if record.get("is_optimal") else "정답"
        return f"{label} 최고기록: {record.get('expression', '')} | COIN {cost} | {time_text} | {status}"

    def _select_best_team_attempt(self, team_role: str):
        attempts = self.team_attempts.get(team_role, [])
        if not attempts:
            return None
        scored = [(self._score_team_attempt(rec), rec) for rec in attempts]
        scored.sort(reverse=True, key=lambda item: item[0])
        return scored[0][1]

    def _score_team_attempt(self, record: dict):
        base = 2 if record.get("is_optimal") else 1
        cost = record.get("cost")
        time_taken = record.get("time")
        cost_score = -cost if cost is not None else 0
        time_score = -time_taken if time_taken is not None else 0
        return (base, cost_score, time_score)

    def _finalize_team_round(self):
        host_best = self._select_best_team_attempt("host")
        guest_best = self._select_best_team_attempt("guest")
        host_score = self._score_team_attempt(host_best) if host_best else (-1, 0, 0)
        guest_score = self._score_team_attempt(guest_best) if guest_best else (-1, 0, 0)

        if host_best is None and guest_best is None:
            winner = "draw"
        elif host_score > guest_score:
            winner = "host"
        elif guest_score > host_score:
            winner = "guest"
        else:
            winner = "draw"

        payload = {
            "type": "team_game_over",
            "winner": winner,
            "host_best": host_best,
            "guest_best": guest_best
        }
        self._process_team_result(payload)
        if self.is_host and self.server:
            self.server.broadcast(json.dumps(payload))

    def _process_team_result(self, payload: dict):
        if self.round_over:
            return
        self.round_over = True
        self.round_active = False
        self.team_view.lock_inputs()
        self.team_view.stop_timer()

        winner = payload.get("winner", "draw")
        host_best = payload.get("host_best")
        guest_best = payload.get("guest_best")

        self.team_attempts["host_best_final"] = host_best
        self.team_attempts["guest_best_final"] = guest_best
        self._update_attempt_board()

        if winner == "draw":
            self.status_label.config(text="무승부! 메인 메뉴로 돌아갑니다.")
            messagebox.showinfo("무승부", "이번 팀전은 무승부입니다.")
        else:
            is_winner = (winner == ("host" if self.is_host else "guest"))
            if is_winner:
                self.status_label.config(text="🎉 승리! 메인 메뉴로 돌아갑니다.")
                messagebox.showinfo("승리", "축하합니다! 팀이 승리했습니다.")
            else:
                self.status_label.config(text="패배... 메인 메뉴로 돌아갑니다.")
                best_expr = (host_best if winner == "host" else guest_best) or {}
                messagebox.showinfo("패배", f"아쉽지만 패배했습니다.\n상대 기록: {best_expr.get('expression', '-')}")
        self.after(3000, self.leave_game)

    # --- 종료/정리 ---
    def cleanup_resources(self):
        if self._closed:
            return
        self._closed = True
        if self.server:
            try:
                self.server.stop()
            except Exception:
                pass
        if self.zeroconf_service:
            try:
                self.zeroconf_service.unregister_service()
            except Exception:
                pass
        if self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass
        if self.zeroconf_browser:
            try:
                self.zeroconf_browser.stop_browsing()
            except Exception:
                pass
        try:
            self.team_view.stop_timer()
        except Exception:
            pass

    def leave_game(self):
        self.cleanup_resources()
        from ui.main_menu_view import MainMenuView
        self.master.switch_frame(MainMenuView)

    # --- 프레임 위임자 ---
    def geometry(self, *args, **kwargs):
        return self.master.geometry(*args, **kwargs)

    def switch_frame(self, frame_class, *args, **kwargs):
        self.cleanup_resources()
        return self.master.switch_frame(frame_class, *args, **kwargs)

