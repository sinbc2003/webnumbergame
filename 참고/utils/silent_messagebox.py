import tkinter as tk
from tkinter import messagebox
import ctypes
from ctypes import wintypes
import re

def silent_showinfo(title, message, parent=None):
    """소리가 나지 않는 정보 메시지박스"""
    # 윈도우 시스템 소리를 일시적으로 비활성화
    try:
        # 현재 시스템 볼륨 설정 저장
        user32 = ctypes.windll.user32
        
        # MessageBeep을 비활성화하기 위해 NULL 사운드 재생
        kernel32 = ctypes.windll.kernel32
        kernel32.Beep(0, 0)  # 무음 비프
        
        # 일반적인 messagebox 대신 커스텀 다이얼로그 생성
        return _create_silent_dialog(title, message, parent)
        
    except Exception:
        # 실패 시 기본 messagebox 사용 (소리 날 수 있음)
        return messagebox.showinfo(title, message, parent=parent)

def _create_silent_dialog(title, message, parent=None):
    """커스텀 무음 다이얼로그 생성"""
    # 새 다이얼로그 창 생성
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.resizable(False, False)
    dialog.grab_set()  # 모달 창으로 설정
    
    # 메시지 길이에 따른 동적 크기 계산
    message_lines = message.count('\n') + 1
    message_length = max(len(line) for line in message.split('\n'))
    
    # 기본 크기를 더 크게 설정 (1000x600)
    base_width = 1000
    base_height = 600
    
    # 메시지가 길면 추가로 크기 조정
    if message_length > 50:
        base_width = min(1400, base_width + (message_length - 50) * 12)
    if message_lines > 8:
        base_height = min(800, base_height + (message_lines - 8) * 40)
    
    # 창 크기와 위치 설정
    dialog.geometry(f"{base_width}x{base_height}")
    if parent:
        # 부모 창 중앙에 위치
        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (base_width // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (base_height // 2)
        dialog.geometry(f"{base_width}x{base_height}+{x}+{y}")
    else:
        # 화면 중앙에 위치
        dialog.geometry(f"{base_width}x{base_height}+{dialog.winfo_screenwidth() // 2 - base_width // 2}+{dialog.winfo_screenheight() // 2 - base_height // 2}")
    
    # 배경색 설정
    dialog.configure(bg='#2b2b2b')
    
    # 메시지 텍스트 위젯 (Rich Text 지원)
    message_text = tk.Text(
        dialog,
        font=('Segoe UI', 24, 'bold'),
        bg='#2b2b2b',
        fg='white',
        wrap=tk.WORD,
        width=int((base_width - 80) / 12),  # 대략적인 문자 수 계산
        height=max(10, message_lines + 4),  # 높이를 더 크게 조정
        relief=tk.FLAT,
        bd=0,
        cursor='arrow',
        state=tk.DISABLED,
        selectbackground='#2b2b2b'  # 선택 배경색도 동일하게
    )
    message_text.pack(pady=40, padx=40, expand=True)
    
    # 텍스트 태그 설정
    message_text.tag_configure("white", foreground="white")
    message_text.tag_configure("red", foreground="#ff4444")
    message_text.tag_configure("yellow", foreground="#ffdd44")
    
    # 메시지 내용 파싱 및 삽입
    message_text.config(state=tk.NORMAL)
    _insert_colored_text(message_text, message)
    message_text.config(state=tk.DISABLED)
    
    # 확인 버튼 (크기도 키움)
    ok_button = tk.Button(
        dialog,
        text="확인",
        font=('Segoe UI', 18, 'bold'),
        bg='#4a9eff',
        fg='white',
        relief='flat',
        width=12,
        pady=10,
        command=dialog.destroy
    )
    ok_button.pack(pady=(0, 30))
    
    # 키보드 이벤트 바인딩 (다이얼로그 전체에 적용)
    def close_dialog(event=None):
        dialog.destroy()
    
    dialog.bind('<Return>', close_dialog)
    dialog.bind('<Escape>', close_dialog)
    dialog.bind('<space>', close_dialog)  # 스페이스바도 추가
    
    # 확인 버튼에도 키 이벤트 바인딩
    ok_button.bind('<Return>', close_dialog)
    ok_button.bind('<Escape>', close_dialog)
    ok_button.bind('<space>', close_dialog)
    
    # 메시지 텍스트에도 키 이벤트 바인딩 (클릭 가능하게)
    message_text.bind('<Button-1>', close_dialog)
    message_text.bind('<Return>', close_dialog)
    message_text.bind('<Escape>', close_dialog)
    
    # 포커스 설정 및 키보드 포커스 강제 설정
    dialog.transient(parent)  # 부모 창 위에 항상 표시
    dialog.focus_set()
    dialog.focus_force()
    
    # 약간의 지연 후 포커스 설정 (더 확실하게)
    def set_focus():
        dialog.lift()  # 창을 맨 앞으로
        dialog.focus_force()
        ok_button.focus_set()
    
    dialog.after(10, set_focus)
    
    # 다이얼로그가 닫힐 때까지 대기
    dialog.wait_window()
    
    return None

# 편의 함수들
def silent_success(message, parent=None):
    """성공 메시지 (소리 없음)"""
    return silent_showinfo("성공!", message, parent)

def silent_error(message, parent=None):
    """오류 메시지 (소리 없음)"""
    return silent_showinfo("오류", message, parent)

def _insert_colored_text(text_widget, message):
    """메시지에서 색상 태그를 파싱하여 텍스트에 삽입"""
    # 색상 마커: <red>텍스트</red>, <yellow>텍스트</yellow>
    pattern = r'<(red|yellow)>(.*?)</\1>'
    
    last_end = 0
    for match in re.finditer(pattern, message):
        # 마커 이전의 일반 텍스트 (흰색)
        if match.start() > last_end:
            text_widget.insert(tk.END, message[last_end:match.start()], "white")
        
        # 색상이 적용된 텍스트
        color = match.group(1)
        text = match.group(2)
        text_widget.insert(tk.END, text, color)
        
        last_end = match.end()
    
    # 마지막 마커 이후의 일반 텍스트
    if last_end < len(message):
        text_widget.insert(tk.END, message[last_end:], "white")
    
    # 텍스트를 중앙 정렬
    text_widget.tag_add("center", "1.0", tk.END)
    text_widget.tag_configure("center", justify='center')

def silent_info(message, parent=None):
    """정보 메시지 (소리 없음)"""
    return silent_showinfo("알림", message, parent)

def silent_showinfo_no_button(title, message, parent=None):
    """확인 버튼이 없는 무음 정보 메시지박스 (자동으로 사라짐)"""
    try:
        # 현재 시스템 볼륨 설정 저장
        SND_SYNC = 0x0000
        SND_ASYNC = 0x0001
        SND_NODEFAULT = 0x0002
        SND_MEMORY = 0x0004
        SND_LOOP = 0x0008
        SND_NOSTOP = 0x0010
        SND_PURGE = 0x0040
        
        # 시스템 소리 비활성화
        ctypes.windll.winmm.PlaySoundW(None, None, SND_PURGE)
        
        # 커스텀 다이얼로그 생성 (확인 버튼 없음)
        return _create_silent_dialog_no_button(title, message, parent)
        
    except Exception:
        # 실패 시 기본 messagebox 사용 (소리 날 수 있음)
        return messagebox.showinfo(title, message, parent=parent)

def _create_silent_dialog_no_button(title, message, parent=None):
    """확인 버튼이 없는 커스텀 무음 다이얼로그 생성"""
    # 새 다이얼로그 창 생성
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.resizable(False, False)
    dialog.grab_set()  # 모달 창으로 설정
    
    # 메시지 길이에 따른 동적 크기 계산
    message_lines = message.count('\n') + 1
    message_length = max(len(line) for line in message.split('\n'))
    
    # 기본 크기를 더 크게 설정 (1000x500)
    base_width = 1000
    base_height = 500  # 확인 버튼이 없으므로 조금 작게
    
    # 메시지가 길면 추가로 크기 조정
    if message_length > 50:
        base_width = min(1400, base_width + (message_length - 50) * 12)
    if message_lines > 8:
        base_height = min(700, base_height + (message_lines - 8) * 40)
    
    # 창 크기와 위치 설정
    dialog.geometry(f"{base_width}x{base_height}")
    if parent:
        # 부모 창 중앙에 위치
        parent.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (base_width // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (base_height // 2)
        dialog.geometry(f"{base_width}x{base_height}+{x}+{y}")
    else:
        # 화면 중앙에 위치
        dialog.geometry(f"{base_width}x{base_height}+{dialog.winfo_screenwidth() // 2 - base_width // 2}+{dialog.winfo_screenheight() // 2 - base_height // 2}")
    
    # 배경색 설정
    dialog.configure(bg='#2b2b2b')
    
    # 메시지 텍스트 위젯 (Rich Text 지원)
    message_text = tk.Text(
        dialog,
        font=('Segoe UI', 24, 'bold'),
        bg='#2b2b2b',
        fg='white',
        wrap=tk.WORD,
        width=int((base_width - 80) / 12),  # 대략적인 문자 수 계산
        height=max(8, message_lines + 2),  # 높이를 더 크게 조정
        relief=tk.FLAT,
        bd=0,
        cursor='arrow',
        state=tk.DISABLED,
        selectbackground='#2b2b2b'  # 선택 배경색도 동일하게
    )
    message_text.pack(pady=40, padx=40, expand=True, fill=tk.BOTH)
    
    # 텍스트 태그 설정
    message_text.tag_configure("white", foreground="white")
    message_text.tag_configure("red", foreground="#ff4444")
    message_text.tag_configure("yellow", foreground="#ffdd44")
    
    # 메시지 내용 파싱 및 삽입
    message_text.config(state=tk.NORMAL)
    _insert_colored_text(message_text, message)
    message_text.config(state=tk.DISABLED)
    
    # 키보드 이벤트 바인딩 (다이얼로그 전체에 적용)
    def close_dialog(event=None):
        dialog.destroy()
    
    dialog.bind('<Return>', close_dialog)
    dialog.bind('<Escape>', close_dialog)
    dialog.bind('<space>', close_dialog)  # 스페이스바도 추가
    
    # 메시지 텍스트에도 키 이벤트 바인딩 (클릭 가능하게)
    message_text.bind('<Button-1>', close_dialog)
    message_text.bind('<Return>', close_dialog)
    message_text.bind('<Escape>', close_dialog)
    
    # 포커스 설정 및 키보드 포커스 강제 설정
    dialog.transient(parent)  # 부모 창 위에 항상 표시
    dialog.focus_set()
    dialog.focus_force()
    
    # 약간의 지연 후 포커스 설정 (더 확실하게)
    def set_focus():
        dialog.lift()  # 창을 맨 앞으로
        dialog.focus_force()
        message_text.focus_set()
    
    dialog.after(10, set_focus)
    
    # 다이얼로그가 닫힐 때까지 대기
    dialog.wait_window()
    
    return None