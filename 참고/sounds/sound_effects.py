import pygame
import numpy as np
import threading
import time

class SoundEffects:
    """게임 효과음 관리 클래스"""
    
    def __init__(self):
        self.initialized = False
        self._init_pygame()
        self._generate_sounds()
    
    def _init_pygame(self):
        """pygame 초기화"""
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.initialized = True
        except Exception as e:
            print(f"사운드 초기화 실패: {e}")
            self.initialized = False
    
    def _generate_sounds(self):
        """효과음 생성"""
        if not self.initialized:
            return
            
        try:
            self.correct_sound = self._generate_correct_sound()
            self.wrong_sound = self._generate_wrong_sound()
            self.timer_end_sound = self._generate_timer_end_tick_tock_sound() # 기본 효과음 설정
        except Exception as e:
            print(f"효과음 생성 실패: {e}")
            self.initialized = False
    
    def set_timer_sound(self, sound_type='tick_tock'):
        """타이머 종료 효과음 변경"""
        if not self.initialized:
            return
            
        try:
            if sound_type == 'chime':
                self.timer_end_sound = self._generate_timer_end_chime_sound()
            elif sound_type == 'descending':
                self.timer_end_sound = self._generate_timer_end_descending_sound()
            else: # 기본값
                self.timer_end_sound = self._generate_timer_end_tick_tock_sound()
        except Exception as e:
            print(f"타이머 효과음 변경 실패: {e}")

    def _generate_timer_end_tick_tock_sound(self):
        """타이머 종료 효과음 1: 긴장감 있는 똑딱 소리"""
        duration = 1.0
        sample_rate = 22050
        
        # '똑' 소리
        t1 = np.linspace(0, 0.1, int(0.1 * sample_rate))
        wave1 = np.sin(2 * np.pi * 1000 * t1) * np.exp(-t1 * 30)
        
        # '딱' 소리
        t2 = np.linspace(0, 0.1, int(0.1 * sample_rate))
        wave2 = np.sin(2 * np.pi * 1200 * t2) * np.exp(-t2 * 40)
        
        samples = np.zeros(int(duration * sample_rate))
        samples[:len(wave1)] = wave1
        samples[int(0.5 * sample_rate) : int(0.5 * sample_rate) + len(wave2)] = wave2
        
        stereo_samples = np.zeros((len(samples), 2))
        stereo_samples[:, 0] = samples
        stereo_samples[:, 1] = samples
        
        sound_array = (stereo_samples * 32767).astype(np.int16)
        return pygame.sndarray.make_sound(sound_array)

    def _generate_timer_end_chime_sound(self):
        """타이머 종료 효과음 2: 차분한 종소리 (한 옥타브 높임, 길이 조정)"""
        duration = 0.67  # 길이를 다시 2/3로 줄임 (1.0 -> 0.67)
        sample_rate = 22050
        t = np.linspace(0, duration, int(duration * sample_rate))
        
        # C5 + C6 음으로 한 옥타브 높임
        freq1 = 523.25  # C5
        freq2 = 1046.50 # C6
        
        wave = (np.sin(2 * np.pi * freq1 * t) * 0.6 + 
                np.sin(2 * np.pi * freq2 * t) * 0.4)
        
        # 감쇠 효과
        wave *= np.exp(-t * 2.5)
        
        stereo_samples = np.zeros((len(wave), 2))
        stereo_samples[:, 0] = wave
        stereo_samples[:, 1] = wave
        
        sound_array = (stereo_samples * 32767).astype(np.int16)
        return pygame.sndarray.make_sound(sound_array)

    def _generate_timer_end_descending_sound(self):
        """타이머 종료 효과음 3: 하강 아르페지오"""
        duration = 1.0
        sample_rate = 22050
        samples = np.zeros(int(duration * sample_rate))
        
        notes = [(523.25, 0.0, 0.2), (440.00, 0.2, 0.2), (349.23, 0.4, 0.2), (261.63, 0.6, 0.4)] # C5-A4-F4-C4
        
        for freq, start_time, note_duration in notes:
            start_sample = int(start_time * sample_rate)
            note_samples = int(note_duration * sample_rate)
            end_sample = min(start_sample + note_samples, len(samples))
            
            t = np.linspace(0, (end_sample - start_sample) / sample_rate, end_sample - start_sample)
            wave = np.sin(2 * np.pi * freq * t) * np.exp(-t * 5)
            samples[start_sample:end_sample] += wave
            
        stereo_samples = np.zeros((len(samples), 2))
        stereo_samples[:, 0] = samples
        stereo_samples[:, 1] = samples
        
        sound_array = (stereo_samples * 32767).astype(np.int16)
        return pygame.sndarray.make_sound(sound_array)
        
    def _generate_correct_sound(self):
        """정답 효과음: 짧은 '쏠미~' 소리 (하강)"""
        duration = 0.5
        sample_rate = 22050
        total_samples = int(duration * sample_rate)
        samples = np.zeros(total_samples)
        
        # 쏠미 음계: 쏠(G) - 미(E) - 하강하는 소리
        notes = [
            (783.99, 0.0, 0.2),    # 쏠 (G5)
            (659.25, 0.15, 0.3)    # 미~ (E5)
        ]
        
        for freq, start_time, note_duration in notes:
            start_sample = int(start_time * sample_rate)
            note_samples = int(note_duration * sample_rate)
            end_sample = min(start_sample + note_samples, total_samples)
            actual_samples = end_sample - start_sample
            
            if actual_samples > 0:
                t = np.linspace(0, actual_samples / sample_rate, actual_samples)
                
                # 부드럽고 따뜻한 소리
                wave = (np.sin(2 * np.pi * freq * t) * 0.5 +
                       np.sin(2 * np.pi * freq * 2 * t) * 0.2 +
                       np.sin(2 * np.pi * freq * 3 * t) * 0.1)
                
                # 부드러운 어택과 더 빠른 감쇠
                attack_samples = int(0.015 * sample_rate)
                if len(t) > attack_samples:
                    wave[:attack_samples] *= np.linspace(0, 1, attack_samples)
                    decay_rate = 4 if freq > 700 else 3.5
                    decay = np.exp(-t * decay_rate)
                    wave *= decay
                
                samples[start_sample:end_sample] += wave
        
        # 스테레오로 변환
        stereo_samples = np.zeros((len(samples), 2))
        stereo_samples[:, 0] = samples
        stereo_samples[:, 1] = samples
        
        sound_array = (stereo_samples * 32767).astype(np.int16)
        sound = pygame.sndarray.make_sound(sound_array)
        
        return sound
    
    def _generate_wrong_sound(self):
        """오답 효과음: 개선된 초단축 부저음"""
        duration = 0.25
        sample_rate = 22050
        total_samples = int(duration * sample_rate)
        
        t = np.linspace(0, duration, total_samples)
        
        # 더 임팩트 있는 이중 부저음 (두 개의 불협화음 주파수)
        freq1 = 120  # 더 낮은 주파수
        freq2 = 160  # 약간 높은 주파수로 불협화음 생성
        
        # 두 개의 사각파로 더 거친 소리
        square_wave1 = np.sign(np.sin(2 * np.pi * freq1 * t)) * 0.35
        square_wave2 = np.sign(np.sin(2 * np.pi * freq2 * t)) * 0.25
        
        # 조합하여 비트 효과와 불협화음 생성
        base_sound = square_wave1 + square_wave2
        
        # 강한 변조로 더 거슬리는 소리
        modulation = 1 + 0.15 * np.sin(2 * np.pi * 12 * t)
        samples = base_sound * modulation
        
        # 약간의 노이즈 추가로 더 거친 느낌
        noise = np.random.normal(0, 0.03, total_samples)
        samples += noise
        
        # 펀치있는 엔벨로프 (빠른 어택, 적당한 지속, 빠른 릴리즈)
        attack_time = 0.01
        attack_samples = int(attack_time * sample_rate)
        
        # 어택 부분
        if attack_samples < len(samples):
            samples[:attack_samples] *= np.linspace(0, 1, attack_samples)
        
        # 릴리즈 부분 (더 늦게 시작해서 펀치감 유지)
        fade_start = int(0.18 * sample_rate)
        if fade_start < len(samples):
            samples[fade_start:] *= np.linspace(1, 0, len(samples) - fade_start)
        
        # 클리핑 방지
        samples = np.clip(samples, -0.7, 0.7)
        
        # 스테레오로 변환
        stereo_samples = np.zeros((len(samples), 2))
        stereo_samples[:, 0] = samples
        stereo_samples[:, 1] = samples
        
        sound_array = (stereo_samples * 32767).astype(np.int16)
        sound = pygame.sndarray.make_sound(sound_array)
        
        return sound
    
    def play_correct(self):
        """정답 효과음 재생 (비동기)"""
        if self.initialized and hasattr(self, 'correct_sound'):
            threading.Thread(target=self._play_sound, args=(self.correct_sound,), daemon=True).start()
    
    def play_wrong(self):
        """오답 효과음 재생 (비동기)"""
        if self.initialized and hasattr(self, 'wrong_sound'):
            threading.Thread(target=self._play_sound, args=(self.wrong_sound,), daemon=True).start()

    def play_timer_end(self):
        """타이머 종료 효과음 재생 (비동기)"""
        if self.initialized and hasattr(self, 'timer_end_sound'):
            threading.Thread(target=self._play_sound, args=(self.timer_end_sound,), daemon=True).start()
    
    def _play_sound(self, sound):
        """실제 사운드 재생"""
        try:
            sound.play()
            time.sleep(sound.get_length())
        except Exception as e:
            print(f"사운드 재생 실패: {e}")

# 전역 사운드 인스턴스
_sound_effects = None

def get_sound_effects():
    """사운드 이펙트 싱글톤 인스턴스 반환"""
    global _sound_effects
    if _sound_effects is None:
        _sound_effects = SoundEffects()
    return _sound_effects

def play_correct_sound():
    """정답 효과음 재생"""
    sound_effects = get_sound_effects()
    sound_effects.play_correct()

def play_wrong_sound():
    """오답 효과음 재생"""
    sound_effects = get_sound_effects()
    sound_effects.play_wrong()

def play_timer_end_sound(sound_type='tick_tock'):
    """타이머 종료 효과음 재생"""
    sound_effects = get_sound_effects()
    sound_effects.set_timer_sound(sound_type)
    sound_effects.play_timer_end()
