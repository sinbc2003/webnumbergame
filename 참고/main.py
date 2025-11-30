# main.py
import tkinter as tk
from constants import *
from ui.main_menu_view import MainMenuView

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("숫자 게임")
        self.geometry("800x600")
        self.configure(bg=BG_COLOR)
        
        # 윈도우 아이콘 설정
        try:
            self.iconbitmap("game_icon.ico")
        except:
            # 아이콘 파일이 없는 경우 무시
            pass
        
        # 전체 화면 상태 추적
        self.is_fullscreen = False
        self.normal_geometry = "800x600"  # 일반 모드 크기 저장
        
        # 전체 화면 토글 키바인딩 (F11)
        self.bind('<F11>', self.toggle_fullscreen)
        self.bind('<Escape>', self.exit_fullscreen)

        self._frame = None
        self.switch_frame(MainMenuView)

    def switch_frame(self, frame_class, *args, **kwargs):
        """Destroys current frame and replaces it with a new one."""
        if self._frame is not None:
            self._frame.destroy()
        self._frame = frame_class(self, *args, **kwargs)
        self._frame.pack(fill="both", expand=True)
    
    def toggle_fullscreen(self, event=None):
        """전체 화면 모드 토글"""
        if self.is_fullscreen:
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()
    
    def enter_fullscreen(self):
        """전체 화면 모드 진입"""
        if not self.is_fullscreen:
            # 현재 크기 저장
            self.normal_geometry = self.geometry()
            
            # 전체 화면 설정
            self.attributes('-fullscreen', True)
            self.is_fullscreen = True
            
            # 상태 표시줄 숨기기 (선택사항)
            self.overrideredirect(False)  # 타이틀바는 유지
    
    def exit_fullscreen(self, event=None):
        """전체 화면 모드 종료"""
        if self.is_fullscreen:
            # 전체 화면 해제
            self.attributes('-fullscreen', False)
            self.is_fullscreen = False
            
            # 이전 크기로 복원
            self.geometry(self.normal_geometry)
            
            # 창을 화면 중앙에 위치
            self.center_window()
    
    def center_window(self):
        """창을 화면 중앙에 위치시키기"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
    
    def get_fullscreen_status(self):
        """현재 전체 화면 상태 반환"""
        return self.is_fullscreen

if __name__ == "__main__":
    app = App()
    app.mainloop()
