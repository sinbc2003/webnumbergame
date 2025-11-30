import tkinter as tk
from sounds.sound_effects import play_timer_end_sound

def main():
    root = tk.Tk()
    root.title("타이머 효과음 테스트")
    root.geometry("400x150")

    def play_sound(sound_type):
        print(f"'{sound_type}' 효과음 재생 중...")
        label.config(text=f"'{sound_type}' 효과음 재생 중...")
        root.update()
        play_timer_end_sound(sound_type)
        label.config(text="재생 준비 완료")
        root.update()
        print("재생 완료.")

    label = tk.Label(root, text="재생 준비 완료", font=("Segoe UI", 14))
    label.pack(pady=20)

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=10)
    
    btn1 = tk.Button(btn_frame, text="똑딱 소리 (tick_tock)", command=lambda: play_sound('tick_tock'))
    btn1.pack(side=tk.LEFT, padx=5)

    btn2 = tk.Button(btn_frame, text="차임벨 소리 (chime)", command=lambda: play_sound('chime'))
    btn2.pack(side=tk.LEFT, padx=5)

    btn3 = tk.Button(btn_frame, text="하강음 (descending)", command=lambda: play_sound('descending'))
    btn3.pack(side=tk.LEFT, padx=5)

    root.mainloop()

if __name__ == "__main__":
    main()
