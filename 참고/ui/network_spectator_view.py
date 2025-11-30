import json
import tkinter as tk
from tkinter import Toplevel, Listbox, simpledialog, messagebox

from constants import *
from network.client import GameClient
from network.discovery import ZeroconfBrowser


class NetworkSpectatorView(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=BG_COLOR)
        self.master = master
        self.client = None
        self.zeroconf_browser = None
        self.game_listbox = None
        self.listbox_map = {}
        self.round_number = 0
        self.target_number = None
        self.host_score = 0
        self.guest_score = 0
        self.history = []
        self.timer_text = "남은 시간 --:--"
        self.create_widgets()
        self.after(100, self.setup_browser)

    def create_widgets(self):
        header = tk.Frame(self, bg=COMPONENT_BG_COLOR)
        header.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(
            header,
            text="관전 모드",
            font=TITLE_FONT,
            bg=COMPONENT_BG_COLOR,
            fg=TEXT_COLOR
        ).pack(side=tk.LEFT, padx=10)

        self.status_label = tk.Label(
            header,
            text="열린 방을 검색 중...",
            font=BODY_FONT,
            bg=COMPONENT_BG_COLOR,
            fg=TEXT_COLOR
        )
        self.status_label.pack(side=tk.RIGHT, padx=10)

        info_frame = tk.Frame(self, bg=BG_COLOR)
        info_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.score_label = tk.Label(
            info_frame,
            text="스코어 | 호스트 0 : 0 게스트",
            font=SUBTITLE_FONT,
            bg=BG_COLOR,
            fg=TEXT_COLOR
        )
        self.score_label.pack(anchor="w", pady=2)

        self.round_label = tk.Label(
            info_frame,
            text="라운드 -",
            font=BODY_FONT,
            bg=BG_COLOR,
            fg=TEXT_COLOR
        )
        self.round_label.pack(anchor="w", pady=2)

        self.timer_label = tk.Label(
            info_frame,
            text=self.timer_text,
            font=BODY_FONT,
            bg=BG_COLOR,
            fg=HIGHLIGHT_COLOR
        )
        self.timer_label.pack(anchor="w", pady=2)

        body = tk.Frame(self, bg=BG_COLOR)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.host_last_label = tk.Label(
            body,
            text="호스트 최근 제출: -",
            font=BODY_FONT,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            anchor="w",
            justify=tk.LEFT
        )
        self.host_last_label.pack(fill=tk.X, pady=2)

        self.guest_last_label = tk.Label(
            body,
            text="게스트 최근 제출: -",
            font=BODY_FONT,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            anchor="w",
            justify=tk.LEFT
        )
        self.guest_last_label.pack(fill=tk.X, pady=2)

        self.history_text = tk.Text(
            body,
            height=12,
            bg=INPUT_BG_COLOR,
            fg=TEXT_COLOR,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.history_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        control = tk.Frame(self, bg=BG_COLOR)
        control.pack(fill=tk.X, padx=10, pady=(0, 10))

        tk.Button(
            control,
            text="나가기",
            command=self.leave_game,
            bg=ERROR_COLOR,
            fg=TEXT_COLOR,
            relief=tk.FLAT,
            font=BODY_FONT,
            width=12
        ).pack(side=tk.RIGHT)

    def setup_browser(self):
        self.zeroconf_browser = ZeroconfBrowser()
        self.zeroconf_browser.start_browsing(update_callback=self.update_game_list)
        self.show_browser_window()

    def show_browser_window(self):
        self.browser_window = Toplevel(self)
        self.browser_window.title("관전할 방 선택")
        self.browser_window.geometry("420x320")
        self.browser_window.configure(bg=BG_COLOR)
        self.browser_window.grab_set()

        tk.Label(
            self.browser_window,
            text="관전할 게임을 선택하세요:",
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
        self.game_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
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
        if not self.game_listbox or not self.game_listbox.winfo_exists():
            return
        self.game_listbox.delete(0, tk.END)
        mode_map = {"normal": "일반", "cost": "코스트", "combo": "숫자 조합"}
        self.listbox_map = {}
        for name, info in self.zeroconf_browser.found_services.items():
            props = info[2]
            mode = props.get("mode", "unknown")
            display = f"[{mode_map.get(mode, '알 수 없음')}] {name}"
            self.listbox_map[display] = name
            self.game_listbox.insert(tk.END, display)

    def on_game_select(self, _event):
        sel = self.game_listbox.curselection()
        if not sel:
            return
        display = self.game_listbox.get(sel[0])
        service_name = self.listbox_map.get(display)
        if not service_name:
            return
        service_info = self.zeroconf_browser.found_services.get(service_name)
        if not service_info:
            messagebox.showerror("오류", "선택한 게임 정보를 찾을 수 없습니다.")
            return
        host_ip, port, _ = service_info
        self.connect_to_game(host_ip, port)

    def manual_connect(self):
        ip = simpledialog.askstring("수동 연결", "호스트 IP:", parent=self.browser_window)
        if not ip:
            return
        port = simpledialog.askinteger("수동 연결", "포트 번호:", parent=self.browser_window, minvalue=1024, maxvalue=65535)
        if not port:
            return
        self.connect_to_game(ip, port)

    def connect_to_game(self, host, port):
        code = simpledialog.askstring("관전 코드", "4자리 참가 코드를 입력하세요:", parent=self.browser_window)
        if not code or len(code) != 4 or not code.isdigit():
            messagebox.showwarning("입력 오류", "유효한 코드를 입력하세요.", parent=self.browser_window)
            return

        self.client = GameClient()
        self.client.on_receive = self.handle_client_message
        self.client.on_disconnect = self.on_server_disconnect

        success, message = self.client.connect(host, port, code)
        if success:
            self.browser_window.destroy()
            self.zeroconf_browser.stop_browsing()
            self.status_label.config(text="관전 연결 완료! 라운드 정보를 기다리는 중...")
            self._register_role()
        else:
            messagebox.showerror("연결 실패", message, parent=self.browser_window)
            self.client = None

    def handle_client_message(self, message):
        data = json.loads(message)
        msg_type = data.get("type")
        if msg_type == "round_snapshot":
            self.master.after(0, self._apply_snapshot, data)
        elif msg_type in ("start_game", "round_start"):
            self.master.after(0, self._apply_round_start, data)
        elif msg_type == "submission":
            self.master.after(0, self._apply_submission, data)
        elif msg_type == "round_result":
            self.master.after(0, self._apply_round_result, data)
        elif msg_type == "register_ack":
            if data.get("status") != "ok":
                reason = data.get("reason", "관전 자리가 없습니다.")
                messagebox.showerror("관전 불가", reason)
                self.leave_game()

    def _apply_snapshot(self, snapshot):
        score = snapshot.get("score", {})
        self.host_score = score.get("host", self.host_score)
        self.guest_score = score.get("guest", self.guest_score)
        self.round_number = snapshot.get("round", self.round_number)
        self.target_number = snapshot.get("target", self.target_number)
        self.history = snapshot.get("history", [])
        self.timer_text = self._format_timer(snapshot.get("timer_remaining"))
        status_text = snapshot.get("status_text", "관전 중")
        self.status_label.config(text=status_text)
        self._refresh_display()

    def _apply_round_start(self, payload):
        self.round_number = payload.get("round", self.round_number)
        self.target_number = payload.get("target", self.target_number)
        score = payload.get("score", {})
        self.host_score = score.get("host", self.host_score)
        self.guest_score = score.get("guest", self.guest_score)
        self.history = []
        self.status_label.config(text=f"라운드 {self.round_number} 진행 중")
        self.timer_text = self._format_timer(payload.get("duration", 0))
        self._refresh_display()

    def _apply_submission(self, data):
        player = data.get("player", "host")
        status = "정답" if data.get("hit_target") else f"오차 {data.get('diff', '-')}"
        entry = f"[{player.upper()}] {data.get('expression')} = {data.get('result_text') or data.get('result')} | COIN {data.get('cost', '-')}, {status}"
        self.history.append(entry)
        if player == "host":
            self.host_last_label.config(text=f"호스트 최근 제출: {data.get('expression')}")
        else:
            self.guest_last_label.config(text=f"게스트 최근 제출: {data.get('expression')}")
        self._refresh_history()

    def _apply_round_result(self, payload):
        winner = payload.get("winner")
        if winner == "draw":
            self.status_label.config(text=f"라운드 {self.round_number} 무승부")
        else:
            self.status_label.config(text=f"라운드 {self.round_number} 승자: {winner}")
        history_entry = payload.get("history_entry")
        if history_entry:
            self.history.append(history_entry)
        self._refresh_history()
        if payload.get("host_best"):
            self.host_last_label.config(text=f"호스트 최고기록: {payload['host_best'].get('expression')}")
        if payload.get("guest_best"):
            self.guest_last_label.config(text=f"게스트 최고기록: {payload['guest_best'].get('expression')}")

    def _refresh_display(self):
        self.score_label.config(text=f"스코어 | 호스트 {self.host_score} : {self.guest_score} 게스트")
        target_text = "-" if self.target_number is None else str(self.target_number)
        self.round_label.config(text=f"라운드 {self.round_number} | 목표 {target_text}")
        self.timer_label.config(text=self.timer_text)
        self._refresh_history()

    def _refresh_history(self):
        self.history_text.config(state=tk.NORMAL)
        if self.history:
            self.history_text.delete("1.0", tk.END)
            self.history_text.insert("1.0", "\n".join(self.history))
        else:
            self.history_text.delete("1.0", tk.END)
            self.history_text.insert("1.0", "아직 제출 기록이 없습니다.")
        self.history_text.config(state=tk.DISABLED)
        self.history_text.see(tk.END)

    def _format_timer(self, remaining):
        if remaining is None:
            return "남은 시간 --:--"
        remaining = max(0, int(remaining))
        return f"남은 시간 {remaining // 60:02d}:{remaining % 60:02d}"

    def _register_role(self):
        if self.client and self.client.is_connected:
            try:
                self.client.send_message({"type": "register_role", "role": "spectator"})
            except Exception:
                pass

    def on_server_disconnect(self):
        messagebox.showinfo("연결 종료", "호스트와의 연결이 끊어졌습니다.")
        self.leave_game()

    def on_browser_close(self):
        self.browser_window.destroy()
        self.leave_game()

    def leave_game(self):
        if self.client and self.client.is_connected:
            self.client.disconnect()
        if self.zeroconf_browser:
            self.zeroconf_browser.stop_browsing()
        from ui.main_menu_view import MainMenuView
        self.master.switch_frame(MainMenuView)

