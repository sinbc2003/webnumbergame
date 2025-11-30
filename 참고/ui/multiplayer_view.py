# ui/multiplayer_view.py
import tkinter as tk
from tkinter import simpledialog, messagebox, Toplevel, Listbox
from constants import *
from network.server import GameServer
from network.client import GameClient
from network.discovery import ZeroconfService, ZeroconfBrowser
from game_logic.calculator import calculate_expression, analyze_input
from utils.problem_store import (
    load_mode1_problems,
    load_mode2_problems,
    load_team_problems,
    load_timer_settings,
)
from sounds.sound_effects import play_timer_end_sound
import threading
import random
import json
import socket
import time

MODE_DISPLAY_MAP = {
    "normal": "일반",
    "cost": "1라운드 팀별 개인전 모드",
    "combo": "숫자 조합",
    "team": "팀전",
}

class MultiplayerView(tk.Frame):
    def __init__(self, master, is_host=False, mode='normal'):
        super().__init__(master, bg=BG_COLOR)
        self.master = master
        self.is_host = is_host
        self.mode = mode # Store the game mode
        self.mode_display = MODE_DISPLAY_MAP.get(self.mode, "")
        self.my_role = "host" if self.is_host else "guest"
        
        # Network components will be initialized later
        self.server = None
        self.client = None
        self.zeroconf_service = None
        self.zeroconf_browser = None
        self.target_number = None
        self.round_number = 0
        self.host_score = 0
        self.guest_score = 0
        self.round_history = []
        self.round_active = False
        self.problem_sequence = self._build_problem_sequence()
        self.problem_index = 0
        self.next_round_job = None
        self.current_problem_meta = None
        self.current_optimal_cost = None
        self.host_submissions = []
        self.guest_submissions = []
        self.submission_history = []
        self.timer_settings = load_timer_settings()
        self.round_duration_sec = self._get_round_duration_seconds()
        self.timer_remaining = 0
        self.timer_job = None

        self.create_widgets()
        
        # Start the appropriate network flow
        self.master.after(100, self.start_network_flow)

    def start_network_flow(self):
        if self.is_host:
            self.setup_host()
        else:
            self.setup_guest()
        
        # 단축키 바인딩 추가
        self.master.bind_all('<Control-l>', self._shortcut_menu)
        self.master.bind_all('<Control-L>', self._shortcut_menu)
        self.master.bind_all('<Shift-L>', self._shortcut_menu)
        self.master.bind_all('<Shift-l>', self._shortcut_menu)
            
    def create_widgets(self):
        # --- Top Status Frame ---
        status_frame = tk.Frame(self, bg=COMPONENT_BG_COLOR)
        status_frame.pack(pady=10, padx=10, fill=tk.X)

        # Display the mode in the status label
        self.status_label = tk.Label(status_frame, text=f"{self.mode_display} 모드 | 연결 준비 중...", font=SUBTITLE_FONT, bg=COMPONENT_BG_COLOR, fg=TEXT_COLOR)
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.target_number_label = tk.Label(status_frame, text="목표: -", font=TITLE_FONT, bg=COMPONENT_BG_COLOR, fg=ACCENT_COLOR)
        self.target_number_label.pack(side=tk.RIGHT, padx=10)

        # --- Scoreboard Frame ---
        score_frame = tk.Frame(self, bg=BG_COLOR)
        score_frame.pack(padx=10, pady=(0, 10), fill=tk.X)

        self.score_label = tk.Label(
            score_frame,
            text="스코어 | 호스트 0 : 0 게스트",
            font=SUBTITLE_FONT,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
        )
        self.score_label.pack(side=tk.LEFT, padx=10)

        self.round_label = tk.Label(
            score_frame,
            text="라운드 대기 중",
            font=BODY_FONT,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
        )
        self.round_label.pack(side=tk.RIGHT, padx=10)

        self.timer_label = tk.Label(
            score_frame,
            text="남은 시간 03:00",
            font=BODY_FONT,
            bg=BG_COLOR,
            fg=HIGHLIGHT_COLOR,
        )
        self.timer_label.pack(side=tk.RIGHT, padx=10)

        history_frame = tk.Frame(self, bg=BG_COLOR)
        history_frame.pack(padx=10, pady=(0, 10), fill=tk.X)

        history_title = tk.Label(
            history_frame,
            text="라운드 기록",
            font=BODY_FONT,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
        )
        history_title.pack(anchor="w")

        self.history_box = tk.Text(
            history_frame,
            height=6,
            bg=INPUT_BG_COLOR,
            fg=TEXT_COLOR,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.history_box.pack(fill=tk.X, pady=(4, 0))
        self._update_scoreboard_display()

        # --- Paned Window for Player Areas ---
        main_pane = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=BORDER_COLOR, sashrelief=tk.RAISED)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- My Area (Left) ---
        my_frame = tk.Frame(main_pane, bg=COMPONENT_BG_COLOR)
        my_label = tk.Label(my_frame, text="내 영역", font=SUBTITLE_FONT, bg=COMPONENT_BG_COLOR, fg=TEXT_COLOR)
        my_label.pack(pady=5)
        
        self.my_text = tk.Text(my_frame, bg=INPUT_BG_COLOR, fg=TEXT_COLOR, 
                               insertbackground=TEXT_COLOR, width=30,
                               font=INPUT_FONT) # Apply new font
        self.my_text.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        self.my_text.bind("<Return>", lambda event: self.submit_answer() or 'break') # Bind Enter key
        # self.my_text.bind("<KeyRelease>", self.on_my_text_change) # This is already disabled

        button_frame = tk.Frame(my_frame, bg=COMPONENT_BG_COLOR)
        button_frame.pack(pady=10)

        self.submit_btn = tk.Button(button_frame, text="검증", font=BODY_FONT, bg=SUCCESS_COLOR, fg=TEXT_COLOR, command=self.submit_answer, state=tk.DISABLED)
        self.submit_btn.pack(side=tk.LEFT, padx=5)
        
        reset_btn = tk.Button(button_frame, text="초기화", font=BODY_FONT, bg=BORDER_COLOR, fg=TEXT_COLOR, command=self.clear_my_text)
        reset_btn.pack(side=tk.LEFT, padx=5)

        main_pane.add(my_frame, stretch="always")

        # --- Opponent's Area (Right) ---
        opponent_frame = tk.Frame(main_pane, bg=COMPONENT_BG_COLOR)
        opponent_label = tk.Label(opponent_frame, text="상대방 영역", font=SUBTITLE_FONT, bg=COMPONENT_BG_COLOR, fg=TEXT_COLOR)
        opponent_label.pack(pady=5)

        self.opponent_text = tk.Text(opponent_frame, bg=INPUT_BG_COLOR, fg=TEXT_COLOR, state=tk.DISABLED, width=30)
        self.opponent_text.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        main_pane.add(opponent_frame, stretch="always")
        
        # --- Bottom Control Frame ---
        control_frame = tk.Frame(self, bg=BG_COLOR)
        control_frame.pack(pady=10)
        
        back_btn = tk.Button(control_frame, text="나가기", font=BODY_FONT, bg=ERROR_COLOR, fg=TEXT_COLOR, command=self.leave_game)
        back_btn.pack()

    # --- Round / Score helpers ---
    def _build_problem_sequence(self):
        """선택된 모드에 맞는 문제 목록을 불러온다."""
        if self.mode == "cost":
            records = load_mode1_problems()
            return self._normalize_problem_records(records)
        if self.mode == "combo":
            records = load_mode2_problems()
            return self._normalize_problem_records(records)
        if self.mode == "team":
            try:
                return self._normalize_problem_records(load_team_problems())
            except Exception:
                return []
        return []

    def _normalize_problem_records(self, records):
        seq = []
        for item in records or []:
            if isinstance(item, dict):
                data = item.copy()
                if "target" in data:
                    data["target"] = int(data["target"])
                seq.append(data)
            else:
                seq.append({"target": int(item)})
        return seq

    def _get_next_problem(self):
        if self.problem_index < len(self.problem_sequence):
            self.current_problem_meta = self.problem_sequence[self.problem_index]
            self.problem_index += 1
        else:
            self.current_problem_meta = {"target": random.randint(10, 50)}
        return self.current_problem_meta

    def _update_scoreboard_display(self):
        self.score_label.config(
            text=f"스코어 | 호스트 {self.host_score} : {self.guest_score} 게스트"
        )
        if self.round_number:
            self.round_label.config(text=f"라운드 {self.round_number}")
        else:
            self.round_label.config(text="라운드 대기 중")

    def _get_round_duration_seconds(self):
        return 3 * 60

    def _self_role(self):
        return "host" if self.is_host else "guest"

    def _append_history_entry(self, entry: str):
        if not entry:
            return
        self.round_history.append(entry)
        self.submission_history.append(entry)
        if len(self.submission_history) > 60:
            self.submission_history = self.submission_history[-60:]
        self._refresh_history_view()

    def _refresh_history_view(self):
        self.history_box.config(state=tk.NORMAL)
        display_text = "\n".join(self.submission_history) if self.submission_history else "히스토리가 없습니다."
        self.history_box.delete("1.0", tk.END)
        self.history_box.insert("1.0", display_text)
        self.history_box.config(state=tk.DISABLED)
        self.history_box.see(tk.END)

    def _reset_round_inputs(self):
        self.my_text.config(state=tk.NORMAL)
        self.my_text.delete("1.0", tk.END)
        self.opponent_text.config(state=tk.NORMAL)
        self.opponent_text.delete("1.0", tk.END)
        self.opponent_text.config(state=tk.DISABLED)
        self.submit_btn.config(state=tk.NORMAL)

    def _disable_round_inputs(self):
        self.submit_btn.config(state=tk.DISABLED)
        self.my_text.config(state=tk.DISABLED)

    def _schedule_next_round(self, delay_ms=2500):
        if not self.is_host:
            return
        if self.next_round_job:
            self.after_cancel(self.next_round_job)
        self.next_round_job = self.after(delay_ms, self.start_round)

    def _format_history_entry(self, winner_role: str) -> str:
        winner_text = "호스트" if winner_role == "host" else "게스트"
        return f"라운드 {self.round_number} | 목표 {self.target_number} | {winner_text} 승 ({self.host_score}:{self.guest_score})"

    def _evaluate_submission(self, expression: str) -> dict:
        details = {
            "expression": expression,
            "result": None,
            "result_text": "",
            "cost": None,
            "hit_target": False,
            "is_valid": False,
            "diff": None,
            "error": None,
        }
        try:
            analysis = analyze_input(expression, self.mode)
        except Exception as exc:
            details["error"] = str(exc)
            return details

        if 'total_cost' in analysis:
            details["cost"] = analysis['total_cost']
        else:
            details["cost"] = analysis.get('char_count', len(expression))

        results = analysis.get("results", [])
        if not results:
            details["error"] = "식이 불완전합니다."
            return details

        result_value = results[-1]['result']
        if isinstance(result_value, str):
            details["error"] = result_value
            details["result_text"] = result_value
            return details

        details["is_valid"] = True
        details["result"] = result_value
        details["result_text"] = str(result_value)
        if self.target_number is not None and isinstance(result_value, (int, float)):
            details["diff"] = abs(result_value - self.target_number)
            if str(result_value) == str(self.target_number):
                details["hit_target"] = True
        return details

    def _record_submission(self, player_role: str, submission: dict, propagate=False):
        submission = submission.copy()
        submission["player"] = player_role
        submission["timestamp"] = time.time()
        target_text = f"목표 {self.target_number}"
        actor = "나" if submission["player"] == self._self_role() else "상대"
        if submission.get("is_valid"):
            status = "정답" if submission.get("hit_target") else f"오차 {submission.get('diff', '-')}"
        else:
            status = submission.get("error", "오류")
        cost_text = submission.get("cost")
        line = f"[{actor}] {submission['expression']} = {submission.get('result_text') or submission.get('result')}\nCOIN {cost_text if cost_text is not None else '-'}, {status}\n{target_text}"
        self._append_history_entry(line)

        if player_role == "host":
            self.host_submissions.append(submission)
        else:
            self.guest_submissions.append(submission)

        if propagate:
            payload = submission.copy()
            payload["type"] = "submission"
            if self.is_host:
                if self.server:
                    self.server.broadcast(json.dumps(payload))
            else:
                if self.client:
                    self.client.send_message(payload)

    def _handle_register_role(self, data, sender_socket):
        role = data.get("role", "player")
        if role == "player":
            if self.player_connected:
                self._send_direct(sender_socket, {
                    "type": "register_ack",
                    "status": "denied",
                    "reason": "player_already_connected"
                })
                try:
                    sender_socket.close()
                except OSError:
                    pass
                return
            self.player_connected = True
            self.client_roles[sender_socket] = "player"
            self._send_direct(sender_socket, {
                "type": "register_ack",
                "status": "ok",
                "role": "player"
            })
            self._send_direct(sender_socket, self._build_round_snapshot())
            self.master.after(0, self.start_round)
        else:
            self.client_roles[sender_socket] = "spectator"
            self._send_direct(sender_socket, {
                "type": "register_ack",
                "status": "ok",
                "role": "spectator"
            })
            self._send_direct(sender_socket, self._build_round_snapshot())

    def _build_round_snapshot(self):
        return {
            "type": "round_snapshot",
            "mode": self.mode,
            "round": self.round_number,
            "target": self.target_number,
            "score": {"host": self.host_score, "guest": self.guest_score},
            "history": self.submission_history,
            "host_submissions": self.host_submissions,
            "guest_submissions": self.guest_submissions,
            "timer_remaining": self.timer_remaining,
            "round_active": self.round_active,
            "status_text": self.status_label.cget("text"),
        }

    def _send_direct(self, socket_obj, payload):
        try:
            socket_obj.send(json.dumps(payload).encode('utf-8'))
        except OSError:
            pass

    def _share_expression_preview(self, expression: str):
        message = {"type": "text_update", "content": expression}
        if self.is_host:
            if self.server:
                self.server.broadcast(json.dumps(message))
        else:
            if self.client:
                self.client.send_message(message)

    def _handle_remote_submission(self, data: dict):
        submission = {
            "expression": data.get("expression", ""),
            "result": data.get("result"),
            "result_text": data.get("result_text"),
            "cost": data.get("cost"),
            "hit_target": data.get("hit_target", False),
            "is_valid": data.get("is_valid", False),
            "diff": data.get("diff"),
            "error": data.get("error"),
        }
        player = data.get("player")
        if player not in ("host", "guest"):
            player = "guest" if self.is_host else "host"
        self._record_submission(player, submission, propagate=False)
        if player != self._self_role():
            self.update_opponent_text({"type": "text_update", "content": submission["expression"]})

    def _apply_round_start(self, payload):
        """라운드 시작 정보를 UI에 반영"""
        self.target_number = payload.get("target")
        self.round_number = payload.get("round", self.round_number)
        score = payload.get("score", {})
        self.host_score = score.get("host", self.host_score)
        self.guest_score = score.get("guest", self.guest_score)
        self.current_optimal_cost = payload.get("optimal_cost")
        self._update_scoreboard_display()
        self.target_number_label.config(text=f"목표: {self.target_number}")
        if self.round_number:
            self.status_label.config(text=f"{self.mode_display} 모드 | 라운드 {self.round_number} 진행 중")
        else:
            self.status_label.config(text=f"{self.mode_display} 모드 | 대전 준비 중")
        self._initialize_round_state(duration=payload.get("duration"))

    def _apply_round_snapshot(self, snapshot):
        score = snapshot.get("score", {})
        self.host_score = score.get("host", self.host_score)
        self.guest_score = score.get("guest", self.guest_score)
        self.round_number = snapshot.get("round", self.round_number)
        self.target_number = snapshot.get("target", self.target_number)
        self.current_optimal_cost = snapshot.get("optimal_cost", self.current_optimal_cost)
        self.host_submissions = snapshot.get("host_submissions", [])
        self.guest_submissions = snapshot.get("guest_submissions", [])
        self.submission_history = snapshot.get("history", [])
        self._refresh_history_view()
        self.round_active = snapshot.get("round_active", self.round_active)
        timer_value = snapshot.get("timer_remaining", self.round_duration_sec)
        self._stop_round_timer()
        self.timer_remaining = timer_value
        if self.round_active:
            self._start_round_timer(timer_value)
        else:
            self._update_timer_display()
        status_text = snapshot.get("status_text")
        if status_text:
            self.status_label.config(text=status_text)
        self._update_scoreboard_display()
        if self.target_number is not None:
            self.target_number_label.config(text=f"목표: {self.target_number}")

    def _initialize_round_state(self, duration=None):
        self.round_active = True
        self.host_submissions = []
        self.guest_submissions = []
        self.submission_history = []
        self.round_history = []
        self._refresh_history_view()
        self._stop_round_timer()
        self._start_round_timer(duration or self.round_duration_sec)
        self._reset_round_inputs()

    def _start_round_timer(self, duration):
        self.timer_remaining = int(duration)
        self._update_timer_display()
        if self.timer_job:
            self.after_cancel(self.timer_job)
        self.timer_job = self.after(1000, self._tick_round_timer)

    def _tick_round_timer(self):
        self.timer_remaining -= 1
        if self.timer_remaining <= 0:
            self.timer_remaining = 0
            self._update_timer_display()
            play_timer_end_sound(sound_type='chime')
            self._on_round_timer_finished()
            return
        self._update_timer_display()
        self.timer_job = self.after(1000, self._tick_round_timer)

    def _stop_round_timer(self):
        if self.timer_job:
            try:
                self.after_cancel(self.timer_job)
            except Exception:
                pass
            self.timer_job = None

    def _update_timer_display(self):
        minutes = self.timer_remaining // 60
        seconds = self.timer_remaining % 60
        text = f"남은 시간 {minutes:02d}:{seconds:02d}"
        if self.timer_remaining <= 10:
            color = ERROR_COLOR
        elif self.timer_remaining <= 30:
            color = WARNING_COLOR
        else:
            color = HIGHLIGHT_COLOR
        self.timer_label.config(text=text, fg=color)

    def _on_round_timer_finished(self):
        self._stop_round_timer()
        self.round_active = False
        self._disable_round_inputs()
        if self.is_host:
            self.status_label.config(text="시간 종료! 결과 계산 중...")
            self._finalize_round_by_timer()
        else:
            self.status_label.config(text="시간 종료! 결과 대기 중...")

    def _handle_round_result_ui(self, payload):
        """라운드 종료 정보를 UI에 반영"""
        self.round_active = False
        self.round_number = payload.get("round", self.round_number)
        self.target_number = payload.get("target", self.target_number)
        score = payload.get("score", {})
        self.host_score = score.get("host", self.host_score)
        self.guest_score = score.get("guest", self.guest_score)
        self._update_scoreboard_display()

        history_entry = payload.get("history_entry")
        if history_entry and (not self.round_history or self.round_history[-1] != history_entry):
            self._append_history_entry(history_entry)

        self._disable_round_inputs()

        best_host = payload.get("best_host")
        best_guest = payload.get("best_guest")
        summary_lines = []
        if best_host:
            summary_lines.append(self._format_submission_summary("호스트", best_host))
        if best_guest:
            summary_lines.append(self._format_submission_summary("게스트", best_guest))
        if summary_lines:
            self._append_history_entry("\n".join(summary_lines))

        winner_role = payload.get("winner")
        expression = payload.get("expression", "")
        did_win = (winner_role == "host" and self.is_host) or (winner_role == "guest" and not self.is_host)

        if expression and not did_win:
            self.opponent_text.config(state=tk.NORMAL)
            self.opponent_text.delete("1.0", tk.END)
            self.opponent_text.insert("1.0", expression)
            self.opponent_text.config(state=tk.DISABLED)

        if winner_role:
            if did_win:
                self.status_label.config(text=f"라운드 {self.round_number} 승리! 다음 라운드 준비 중...")
                if payload.get("winner") != "draw":
                    messagebox.showinfo("라운드 승리", "축하합니다! 다음 라운드가 곧 시작됩니다.")
            else:
                if payload.get("winner") == "draw":
                    self.status_label.config(text=f"라운드 {self.round_number} 무승부. 다음 라운드 준비 중")
                    messagebox.showinfo("무승부", "이번 라운드는 무승부입니다.")
                else:
                    self.status_label.config(text=f"라운드 {self.round_number} 패배... 다음 라운드 준비 중")
                    messagebox.showinfo("라운드 패배", "아쉽지만 패배했습니다. 다음 라운드를 준비하세요.")

    def _handle_register_ack(self, data):
        if data.get("status") != "ok":
            reason = data.get("reason", "연결할 수 없습니다.")
            messagebox.showerror("접속 불가", f"관전 또는 플레이어 자리에 접속할 수 없습니다.\n사유: {reason}")
            self.leave_game()


    def _finalize_round_as_host(self, winner_role: str, expression: str):
        if not self.is_host or not self.round_active:
            return
        if winner_role == "host":
            self.host_score += 1
        else:
            self.guest_score += 1

        history_entry = self._format_history_entry(winner_role)
        payload = {
            "type": "round_result",
            "winner": winner_role,
            "expression": expression,
            "score": {"host": self.host_score, "guest": self.guest_score},
            "round": self.round_number,
            "target": self.target_number,
            "history_entry": history_entry,
            "host_best": self._pick_best_submission(self.host_submissions),
            "guest_best": self._pick_best_submission(self.guest_submissions),
        }

        self._handle_round_result_ui(payload)
        if self.server:
            self.server.broadcast(json.dumps(payload))
        self._schedule_next_round()

    def _finalize_round_by_timer(self):
        winner, summary = self._determine_round_winner()
        if winner == "host":
            self.host_score += 1
        elif winner == "guest":
            self.guest_score += 1

        if summary.get("history_entry"):
            history_entry = summary["history_entry"]
        elif winner in ("host", "guest"):
            history_entry = self._format_history_entry(winner)
        else:
            history_entry = f"라운드 {self.round_number} | 목표 {self.target_number} | 무승부"

        payload = {
            "type": "round_result",
            "winner": winner if winner else "draw",
            "expression": summary.get("winning_expression"),
            "score": {"host": self.host_score, "guest": self.guest_score},
            "round": self.round_number,
            "target": self.target_number,
            "history_entry": history_entry,
            "best_host": summary.get("host"),
            "best_guest": summary.get("guest"),
        }

        self._handle_round_result_ui(payload)
        if self.server:
            self.server.broadcast(json.dumps(payload))
        self._schedule_next_round()

    def _determine_round_winner(self):
        host_best = self._pick_best_submission(self.host_submissions)
        guest_best = self._pick_best_submission(self.guest_submissions)
        host_score = self._score_submission(host_best)
        guest_score = self._score_submission(guest_best)

        if host_best is None and guest_best is None:
            winner = None
        elif host_score > guest_score:
            winner = "host"
        elif guest_score > host_score:
            winner = "guest"
        else:
            winner = None

        summary = {
            "host": host_best,
            "guest": guest_best,
            "winning_expression": (host_best if winner == "host" else guest_best or {}).get("expression"),
            "history_entry": None,
        }
        return winner, summary

    def _pick_best_submission(self, submissions):
        if not submissions:
            return None
        scored = [(self._score_submission(sub), sub) for sub in submissions if sub.get("is_valid")]
        if not scored:
            return None
        scored.sort(reverse=True, key=lambda item: item[0])
        return scored[0][1]

    def _score_submission(self, submission: dict):
        if not submission or not submission.get("is_valid"):
            return (-1, 0, 0)
        timestamp = submission.get("timestamp", 0)
        if submission.get("hit_target"):
            if self.current_optimal_cost is not None and submission.get("cost") is not None:
                cost_delta = abs(submission["cost"] - self.current_optimal_cost)
                cost_score = -cost_delta
            else:
                cost_score = - (submission.get("cost") or 0)
            return (3, cost_score, -timestamp)
        diff = submission.get("diff")
        if diff is None:
            diff_score = float("-inf")
        else:
            diff_score = -diff
        return (2, diff_score, -timestamp)

    def _format_submission_summary(self, label: str, submission: dict) -> str:
        cost = submission.get("cost")
        expression = submission.get("expression", "")
        if submission.get("hit_target"):
            status = "정답"
            if self.current_optimal_cost is not None and cost is not None:
                delta = abs(cost - self.current_optimal_cost)
                if delta == 0:
                    status += " (최적해)"
                else:
                    status += f" (최적해 차이 {delta})"
        else:
            diff = submission.get("diff")
            if diff is None:
                status = "오답"
            else:
                status = f"오차 {diff}"
        cost_text = cost if cost is not None else "-"
        return f"{label} 최고기록: {expression} | COIN {cost_text} | {status}"

    def setup_host(self):
        self.status_label.config(text="서버 여는 중...")
        try:
            self.server = GameServer()
            self.server.start()
            
            self.server.on_client_connect = self.on_client_connect
            self.server.on_client_disconnect = self.on_client_disconnect
            self.server.on_receive = self.handle_server_message

            # Add mode info to zeroconf service properties
            service_name = f"{socket.gethostname()}의 게임"
            properties = {'mode': self.mode}
            self.zeroconf_service = ZeroconfService(name=service_name, port=self.server.port, properties=properties)
            self.zeroconf_service.register_service()

            self.status_label.config(text=f"{self.mode_display} 모드 | 상대 기다리는 중... (참가 코드: {self.server.access_code})")
            self.client_roles = {}
            self.player_connected = False
        except Exception as e:
            messagebox.showerror("서버 오류", f"서버를 시작할 수 없습니다: {e}")
            self.leave_game()

    # --- Host Methods ---
    def on_client_connect(self, client_socket):
        # 역할 등록 메시지를 기다립니다.
        pass

    def start_round(self):
        """호스트가 새로운 라운드를 시작"""
        if not self.is_host or self.round_active:
            return
        if not self.player_connected:
            self.status_label.config(text=f"{self.mode_display} 모드 | 플레이어 접속 대기 중...")
            return
        self.round_number += 1
        problem_meta = self._get_next_problem()
        self.target_number = problem_meta.get("target")
        self.current_optimal_cost = problem_meta.get("optimal_cost")
        self.round_active = True

        payload = {
            "type": "round_start",
            "target": self.target_number,
            "mode": self.mode,
            "round": self.round_number,
            "score": {"host": self.host_score, "guest": self.guest_score},
            "optimal_cost": self.current_optimal_cost,
            "duration": self.round_duration_sec,
        }

        self._apply_round_start(payload)
        if self.server:
            self.server.broadcast(json.dumps(payload))

    def on_client_disconnect(self, client_socket):
        role = self.client_roles.pop(client_socket, None)
        if role == "player":
            self.player_connected = False
            self._stop_round_timer()
            self.round_active = False
            self.status_label.config(text="상대방 연결 끊김. 플레이어 대기 중...")
            self.submit_btn.config(state=tk.DISABLED)
        else:
            # 관전자 종료는 별도 안내 없이 무시
            if not self.player_connected:
                self.status_label.config(text=f"{self.mode_display} 모드 | 플레이어 접속 대기 중...")

    def handle_server_message(self, message, sender_socket):
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type")

        if msg_type == "register_role":
            self._handle_register_role(data, sender_socket)
        elif msg_type == "text_update":
            self.server.broadcast(message, sender_socket)
            self.master.after(0, self.update_opponent_text, data)
        elif msg_type == "submission":
            self.server.broadcast(message, sender_socket)
            self.master.after(0, self._handle_remote_submission, data)
        elif msg_type == "round_win_request":
            expression = data.get("expression", "")
            self.master.after(0, self._finalize_round_as_host, "guest", expression)
        elif msg_type == "legacy_game_over":
            # backward compatibility placeholder
            expression = data.get("expression", "")
            self.master.after(0, self._finalize_round_as_host, "guest", expression)

    # --- Guest Methods ---
    def setup_guest(self):
        self.status_label.config(text="열린 게임 찾는 중...")
        self.zeroconf_browser = ZeroconfBrowser()
        self.zeroconf_browser.start_browsing(update_callback=self.update_game_list)
        self.show_game_browser()

    def show_game_browser(self):
        self.browser_window = Toplevel(self)
        self.browser_window.title("게임 참가하기")
        self.browser_window.geometry("400x300")
        self.browser_window.configure(bg=BG_COLOR)
        
        # Make window modal
        self.browser_window.grab_set()

        label = tk.Label(self.browser_window, text="참가할 게임을 선택하세요:", font=BODY_FONT, bg=BG_COLOR, fg=TEXT_COLOR)
        label.pack(pady=10)

        self.game_listbox = Listbox(self.browser_window, bg=INPUT_BG_COLOR, fg=TEXT_COLOR, 
                                    selectbackground=ACCENT_COLOR, relief=tk.FLAT)
        self.game_listbox.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        self.game_listbox.bind("<Double-Button-1>", self.on_game_select)

        manual_ip_btn = tk.Button(self.browser_window, text="수동으로 IP 입력", command=self.manual_connect,
                                  bg=BORDER_COLOR, fg=TEXT_COLOR, font=BODY_FONT, relief=tk.FLAT)
        manual_ip_btn.pack(pady=10)
        
        # Populate with any already found services
        self.update_game_list()
        
        self.browser_window.protocol("WM_DELETE_WINDOW", self.on_browser_close)

    def on_browser_close(self):
        self.browser_window.destroy()
        self.leave_game() # Go back to main menu if browser is closed

    def update_game_list(self):
        if not hasattr(self, 'game_listbox') or not self.game_listbox.winfo_exists():
            return
            
        self.game_listbox.delete(0, tk.END)
        mode_map = {"normal": "일반", "cost": "코스트", "combo": "숫자 조합"}

        for name, info in self.zeroconf_browser.found_services.items():
            properties = info[2] # (ip, port, properties)
            mode = properties.get('mode', 'unknown')
            mode_display = mode_map.get(mode, '알 수 없음')
            
            display_name = f"[{mode_display}] {name}"
            self.game_listbox.insert(tk.END, display_name)
            # We need to store the original name to retrieve it later
            if not hasattr(self, 'listbox_map'):
                self.listbox_map = {}
            self.listbox_map[display_name] = name

    def on_game_select(self, event):
        selected_indices = self.game_listbox.curselection()
        if not selected_indices:
            return
        
        display_name = self.game_listbox.get(selected_indices[0])
        # Retrieve original service name from map
        service_name = self.listbox_map.get(display_name, "")
        if not service_name: return

        service_info = self.zeroconf_browser.found_services.get(service_name)
        if not service_info:
            messagebox.showerror("오류", "선택한 게임 정보를 찾을 수 없습니다.")
            return

        host_ip, port, _ = service_info # properties are already known
        self.prompt_for_code_and_connect(host_ip, port)

    def manual_connect(self):
        ip = simpledialog.askstring("수동 연결", "호스트의 IP 주소를 입력하세요:", parent=self.browser_window)
        if not ip: return
        port = simpledialog.askinteger("수동 연결", "포트 번호를 입력하세요:", parent=self.browser_window, minvalue=1024, maxvalue=65535)
        if not port: return
        
        self.prompt_for_code_and_connect(ip, port)

    def prompt_for_code_and_connect(self, host, port):
        code = simpledialog.askstring("참가 코드", "4자리 참가 코드를 입력하세요:", parent=self.browser_window)
        if not code or len(code) != 4 or not code.isdigit():
            messagebox.showwarning("입력 오류", "유효한 4자리 숫자를 입력하세요.", parent=self.browser_window)
            return

        self.client = GameClient()
        self.client.on_receive = self.handle_client_message
        self.client.on_disconnect = self.on_server_disconnect
        
        success, message = self.client.connect(host, port, code)

        if success:
            self.browser_window.destroy()
            self.zeroconf_browser.stop_browsing()
            self.status_label.config(text="연결 성공! 게임 시작 대기 중...")
            self._register_role("player")
        else:
            messagebox.showerror("연결 실패", message, parent=self.browser_window)
            self.client = None

    def handle_client_message(self, message):
        data = json.loads(message)
        msg_type = data.get("type")
        
        if msg_type in ("start_game", "round_start"):
            # 호스트가 라운드를 시작
            if msg_type == "start_game":
                # 이전 버전과 호환
                data = {
                    "type": "round_start",
                    "target": data.get("target"),
                    "mode": data.get("mode", "normal"),
                    "round": data.get("round", self.round_number + 1),
                    "score": {"host": self.host_score, "guest": self.guest_score},
                }
            self.target_number = data.get("target")
            self.mode = data.get("mode", self.mode)
            self.mode_display = MODE_DISPLAY_MAP.get(self.mode, self.mode_display)
            self.master.after(0, self._apply_round_start, data)
        elif msg_type == "round_snapshot":
            self.master.after(0, self._apply_round_snapshot, data)
        elif msg_type == "register_ack":
            self.master.after(0, self._handle_register_ack, data)
        elif msg_type == "round_result":
            self.master.after(0, self._handle_round_result_ui, data)
        elif msg_type == "submission":
            self.master.after(0, self._handle_remote_submission, data)
        else:
            self.master.after(0, self.update_opponent_text, data)
            
    def on_server_disconnect(self):
        self.master.after(0, self.show_disconnect_message)
        
    def show_disconnect_message(self):
        if self.submit_btn['state'] != tk.DISABLED:
            messagebox.showinfo("연결 종료", "호스트와의 연결이 끊어졌습니다.")
            self.leave_game()

    # --- Common Methods ---
    def on_my_text_change(self, event):
        # 실시간 전송 기능 제거
        pass

    def update_opponent_text(self, data):
        if data.get("type") != "text_update":
            return
        content = data.get("content", "")
        self.opponent_text.config(state=tk.NORMAL)
        self.opponent_text.delete("1.0", tk.END)
        self.opponent_text.insert("1.0", content)
        self.opponent_text.config(state=tk.DISABLED)


    def submit_answer(self, event=None): # Add event=None to handle bind
        my_expression = self.my_text.get("1.0", tk.END).strip()
        if not my_expression:
            return
        if not self.round_active:
            messagebox.showinfo("라운드 대기", "다음 라운드를 기다려주세요.")
            return

        submission = self._evaluate_submission(my_expression)
        if not submission.get("is_valid"):
            error_text = submission.get("error") or "잘못된 수식입니다."
            messagebox.showwarning("오류", error_text)
            self.my_text.delete("1.0", tk.END)
            return

        self._share_expression_preview(my_expression)
        self._record_submission(self._self_role(), submission, propagate=True)
        self.my_text.delete("1.0", tk.END)
    
    def leave_game(self):
        # Stop all network components cleanly
        self._stop_round_timer()
        if self.next_round_job:
            try:
                self.after_cancel(self.next_round_job)
            except Exception:
                pass
            self.next_round_job = None
        if self.server:
            self.server.stop()
        if self.zeroconf_service:
            self.zeroconf_service.unregister_service()
        if self.client:
            self.client.disconnect()
        if self.zeroconf_browser:
            self.zeroconf_browser.stop_browsing()
        
        from ui.main_menu_view import MainMenuView
        self.master.switch_frame(MainMenuView)

    def clear_my_text(self):
        """Clears the player's own text input area."""
        self.my_text.delete("1.0", tk.END)
    
    def _shortcut_menu(self, event=None):
        """단축키로 메인 메뉴로 돌아가기"""
        from ui.main_menu_view import MainMenuView
        self.master.switch_frame(MainMenuView)

    def _register_role(self, role: str):
        if self.client and self.client.is_connected:
            try:
                self.client.send_message({"type": "register_role", "role": role})
            except Exception:
                pass

if __name__ == '__main__':
    # For testing the view standalone
    root = tk.Tk()
    root.geometry("800x600")
    # Test as host
    # view = MultiplayerView(root, is_host=True)
    # Test as guest
    view = MultiplayerView(root, is_host=False)
    view.pack(fill="both", expand=True)
    root.mainloop()
