import pygame
import numpy as np
import time

def generate_correct_sound():
    """정답 효과음을 생성합니다 (상승하는 톤)."""
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    # 상승하는 톤 (C-E-G 코드)
    duration = 0.5
    sample_rate = 22050
    
    # 각 음의 주파수 (도-미-솔)
    frequencies = [523.25, 659.25, 783.99]  # C5, E5, G5
    
    samples = np.zeros(int(duration * sample_rate))
    
    for i, freq in enumerate(frequencies):
        start_time = i * 0.15
        end_time = (i + 1) * 0.15
        start_sample = int(start_time * sample_rate)
        end_sample = int(end_time * sample_rate)
        
        if end_sample <= len(samples):
            t = np.linspace(0, end_time - start_time, end_sample - start_sample)
            wave = np.sin(2 * np.pi * freq * t) * 0.3
            # 페이드 인/아웃
            fade_samples = int(0.02 * sample_rate)
            if len(wave) > fade_samples * 2:
                wave[:fade_samples] *= np.linspace(0, 1, fade_samples)
                wave[-fade_samples:] *= np.linspace(1, 0, fade_samples)
            samples[start_sample:end_sample] += wave
    
    # 스테레오로 변환
    stereo_samples = np.zeros((len(samples), 2))
    stereo_samples[:, 0] = samples
    stereo_samples[:, 1] = samples
    
    # pygame 사운드 객체 생성
    sound_array = (stereo_samples * 32767).astype(np.int16)
    sound = pygame.sndarray.make_sound(sound_array)
    
    return sound

def generate_wrong_sound():
    """오답 효과음을 생성합니다 (하강하는 부저음)."""
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    duration = 0.8
    sample_rate = 22050
    samples = np.zeros(int(duration * sample_rate))
    
    # 하강하는 부저음
    start_freq = 200
    end_freq = 100
    
    t = np.linspace(0, duration, len(samples))
    # 주파수가 시간에 따라 하강
    freq_sweep = start_freq * (end_freq / start_freq) ** (t / duration)
    
    # 부저 같은 사각파 생성
    phase = np.cumsum(2 * np.pi * freq_sweep / sample_rate)
    square_wave = np.sign(np.sin(phase)) * 0.3
    
    # 약간의 노이즈 추가로 더 거친 소리
    noise = np.random.normal(0, 0.05, len(samples))
    samples = square_wave + noise
    
    # 페이드 아웃
    fade_samples = int(0.1 * sample_rate)
    samples[-fade_samples:] *= np.linspace(1, 0, fade_samples)
    
    # 스테레오로 변환
    stereo_samples = np.zeros((len(samples), 2))
    stereo_samples[:, 0] = samples
    stereo_samples[:, 1] = samples
    
    sound_array = (stereo_samples * 32767).astype(np.int16)
    sound = pygame.sndarray.make_sound(sound_array)
    
    return sound

def generate_correct_sound_2():
    """정답 효과음 2 (밝은 벨소리)."""
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    duration = 0.6
    sample_rate = 22050
    t = np.linspace(0, duration, int(duration * sample_rate))
    
    # 벨 소리 (기본 주파수 + 배음들)
    base_freq = 800
    wave = (np.sin(2 * np.pi * base_freq * t) * 0.4 +
            np.sin(2 * np.pi * base_freq * 2 * t) * 0.2 +
            np.sin(2 * np.pi * base_freq * 3 * t) * 0.1)
    
    # 감쇠 효과 (벨이 울리다가 사라지는 효과)
    decay = np.exp(-t * 3)
    wave *= decay
    
    # 스테레오로 변환
    stereo_samples = np.zeros((len(wave), 2))
    stereo_samples[:, 0] = wave
    stereo_samples[:, 1] = wave
    
    sound_array = (stereo_samples * 32767).astype(np.int16)
    sound = pygame.sndarray.make_sound(sound_array)
    
    return sound

def generate_wrong_sound_2():
    """오답 효과음 2 (게임쇼 부저)."""
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    duration = 1.0
    sample_rate = 22050
    t = np.linspace(0, duration, int(duration * sample_rate))
    
    # 낮은 주파수의 부저음
    freq = 150
    wave = np.sin(2 * np.pi * freq * t) * 0.5
    
    # 약간의 변조 추가 (부저 특유의 거친 소리)
    modulation = 1 + 0.3 * np.sin(2 * np.pi * 8 * t)
    wave *= modulation
    
    # 페이드 아웃
    fade_start = int(0.7 * sample_rate)
    wave[fade_start:] *= np.linspace(1, 0, len(wave) - fade_start)
    
    # 스테레오로 변환
    stereo_samples = np.zeros((len(wave), 2))
    stereo_samples[:, 0] = wave
    stereo_samples[:, 1] = wave
    
    sound_array = (stereo_samples * 32767).astype(np.int16)
    sound = pygame.sndarray.make_sound(sound_array)
    
    return sound

def play_sound(sound, description):
    """효과음을 재생합니다."""
    try:
        print(f"🔊 {description} 재생 중...")
        sound.play()
        time.sleep(sound.get_length())
        print("   ✅ 재생 완료")
        return True
    except Exception as e:
        print(f"❌ 재생 실패: {e}")
        return False

def main():
    print("🎵 수학 게임 효과음 테스트")
    print("=" * 40)
    print("프로그램으로 생성한 효과음들을 테스트합니다.")
    
    try:
        # 효과음 생성
        print("\n🎼 효과음 생성 중...")
        
        correct1 = generate_correct_sound()
        print("✅ 정답 효과음 1 (상승 톤) 생성 완료")
        
        correct2 = generate_correct_sound_2()
        print("✅ 정답 효과음 2 (벨소리) 생성 완료")
        
        wrong1 = generate_wrong_sound()
        print("✅ 오답 효과음 1 (하강 부저) 생성 완료")
        
        wrong2 = generate_wrong_sound_2()
        print("✅ 오답 효과음 2 (게임쇼 부저) 생성 완료")
        
        # 효과음 재생 테스트
        print(f"\n🔊 효과음 재생 테스트")
        print("=" * 40)
        
        sounds = [
            (correct1, "🎉 정답 효과음 1 (상승하는 멜로디)"),
            (correct2, "🔔 정답 효과음 2 (밝은 벨소리)"),
            (wrong1, "❌ 오답 효과음 1 (하강하는 부저)"),
            (wrong2, "🚫 오답 효과음 2 (게임쇼 부저)")
        ]
        
        for i, (sound, description) in enumerate(sounds, 1):
            print(f"\n{i}. {description}")
            play_sound(sound, description)
            
            if i < len(sounds):
                print("   (다음 소리까지 2초 대기...)")
                time.sleep(2)
        
        print("\n🎵 모든 효과음 테스트 완료!")
        print("=" * 40)
        print("각 효과음을 들어보시고 마음에 드는 것을 선택해주세요.")
        print("\n💡 추천:")
        print("- 1라운드: 정답 효과음 1 또는 2, 오답 효과음 1")
        print("- 2라운드: 더 강렬한 정답 효과음 2, 오답 효과음 2")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print("numpy가 설치되어 있는지 확인해주세요: pip install numpy")
    
    finally:
        pygame.mixer.quit()

if __name__ == "__main__":
    main()