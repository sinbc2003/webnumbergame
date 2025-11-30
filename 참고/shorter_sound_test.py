import pygame
import numpy as np
import time

def generate_short_xylophone_dingdongdaeng():
    """정답 효과음: 더 짧은 실로폰 '딩동댕'"""
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    duration = 0.8  # 1.2초에서 0.8초로 단축
    sample_rate = 22050
    total_samples = int(duration * sample_rate)
    samples = np.zeros(total_samples)
    
    # 실로폰 음계: 딩(C) - 동(E) - 댕(G) - 더 빠르게
    notes = [
        (523.25, 0.0, 0.25),   # 딩 (C5) - 0.35초에서 0.25초로
        (659.25, 0.2, 0.25),   # 동 (E5) - 0.3초에서 0.2초로
        (783.99, 0.4, 0.35)    # 댕 (G5) - 0.6초에서 0.4초로, 마지막만 약간 길게
    ]
    
    for freq, start_time, note_duration in notes:
        start_sample = int(start_time * sample_rate)
        note_samples = int(note_duration * sample_rate)
        end_sample = min(start_sample + note_samples, total_samples)
        actual_samples = end_sample - start_sample
        
        if actual_samples > 0:
            t = np.linspace(0, actual_samples / sample_rate, actual_samples)
            
            # 실로폰 특유의 맑고 밝은 소리 (기본음 + 배음들)
            wave = (np.sin(2 * np.pi * freq * t) * 0.6 +           # 기본음
                   np.sin(2 * np.pi * freq * 2 * t) * 0.3 +        # 2배음
                   np.sin(2 * np.pi * freq * 4 * t) * 0.15 +       # 4배음
                   np.sin(2 * np.pi * freq * 8 * t) * 0.05)        # 8배음
            
            # 실로폰 특유의 빠른 어택과 감쇠
            attack_time = 0.008  # 더 빠른 어택
            attack_samples = int(attack_time * sample_rate)
            
            if len(t) > attack_samples:
                # 어택 부분
                wave[:attack_samples] *= np.linspace(0, 1, attack_samples)
                # 더 빠른 감쇠
                decay = np.exp(-t * 5)  # 4에서 5로 증가
                wave *= decay
            
            samples[start_sample:end_sample] += wave
    
    # 스테레오로 변환
    stereo_samples = np.zeros((len(samples), 2))
    stereo_samples[:, 0] = samples
    stereo_samples[:, 1] = samples
    
    sound_array = (stereo_samples * 32767).astype(np.int16)
    sound = pygame.sndarray.make_sound(sound_array)
    
    return sound

def generate_very_short_buzzer_error():
    """오답 효과음: 매우 짧은 클래식 부저음"""
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    duration = 0.25  # 0.4초에서 0.25초로 단축
    sample_rate = 22050
    total_samples = int(duration * sample_rate)
    
    t = np.linspace(0, duration, total_samples)
    
    # 전형적인 부저음 (낮은 주파수)
    freq = 150
    
    # 사각파로 부저 소리 생성
    square_wave = np.sign(np.sin(2 * np.pi * freq * t)) * 0.45
    
    # 약간의 주파수 변조로 더 거슬리는 소리
    modulation = 1 + 0.1 * np.sin(2 * np.pi * 6 * t)
    samples = square_wave * modulation
    
    # 매우 빠른 페이드 아웃
    fade_start = int(0.15 * sample_rate)  # 0.25초에서 0.15초로
    samples[fade_start:] *= np.linspace(1, 0, len(samples) - fade_start)
    
    # 스테레오로 변환
    stereo_samples = np.zeros((len(samples), 2))
    stereo_samples[:, 0] = samples
    stereo_samples[:, 1] = samples
    
    sound_array = (stereo_samples * 32767).astype(np.int16)
    sound = pygame.sndarray.make_sound(sound_array)
    
    return sound

def generate_ultra_short_xylophone():
    """정답 효과음: 초단축 실로폰 '딩동댕'"""
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    duration = 0.6  # 0.6초로 더욱 단축
    sample_rate = 22050
    total_samples = int(duration * sample_rate)
    samples = np.zeros(total_samples)
    
    # 실로폰 음계: 딩(C) - 동(E) - 댕(G) - 매우 빠르게
    notes = [
        (523.25, 0.0, 0.18),   # 딩 (C5)
        (659.25, 0.15, 0.18),  # 동 (E5)
        (783.99, 0.3, 0.25)    # 댕 (G5)
    ]
    
    for freq, start_time, note_duration in notes:
        start_sample = int(start_time * sample_rate)
        note_samples = int(note_duration * sample_rate)
        end_sample = min(start_sample + note_samples, total_samples)
        actual_samples = end_sample - start_sample
        
        if actual_samples > 0:
            t = np.linspace(0, actual_samples / sample_rate, actual_samples)
            
            # 실로폰 소리
            wave = (np.sin(2 * np.pi * freq * t) * 0.65 +
                   np.sin(2 * np.pi * freq * 2 * t) * 0.25 +
                   np.sin(2 * np.pi * freq * 4 * t) * 0.1)
            
            # 매우 빠른 어택과 감쇠
            attack_samples = int(0.005 * sample_rate)
            
            if len(t) > attack_samples:
                wave[:attack_samples] *= np.linspace(0, 1, attack_samples)
                decay = np.exp(-t * 6)  # 더욱 빠른 감쇠
                wave *= decay
            
            samples[start_sample:end_sample] += wave
    
    # 스테레오로 변환
    stereo_samples = np.zeros((len(samples), 2))
    stereo_samples[:, 0] = samples
    stereo_samples[:, 1] = samples
    
    sound_array = (stereo_samples * 32767).astype(np.int16)
    sound = pygame.sndarray.make_sound(sound_array)
    
    return sound

def generate_ultra_short_buzzer():
    """오답 효과음: 개선된 초단축 부저음"""
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    duration = 0.25  # 0.2초에서 0.25초로 약간 늘림 (너무 짧으면 인식하기 어려움)
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
    print("🎵 더 짧은 효과음 테스트: 1번 & 4번 단축버전")
    print("=" * 50)
    
    try:
        # 효과음 생성
        print("\n🎼 단축 효과음 생성 중...")
        
        short_xylophone = generate_short_xylophone_dingdongdaeng()
        print("✅ 정답 효과음: 짧은 실로폰 '딩동댕' (0.8초) 생성 완료")
        
        ultra_short_xylophone = generate_ultra_short_xylophone()
        print("✅ 정답 효과음: 초단축 실로폰 '딩동댕' (0.6초) 생성 완료")
        
        short_buzzer = generate_very_short_buzzer_error()
        print("✅ 오답 효과음: 매우 짧은 부저음 (0.25초) 생성 완료")
        
        ultra_short_buzzer = generate_ultra_short_buzzer()
        print("✅ 오답 효과음: 개선된 초단축 부저음 (0.25초) 생성 완료")
        
        # 효과음 재생 테스트
        print(f"\n🔊 단축 효과음 재생 테스트")
        print("=" * 50)
        
        sounds = [
            (short_xylophone, "🎼 정답: 짧은 실로폰 '딩동댕' (0.8초)"),
            (ultra_short_xylophone, "⚡ 정답: 초단축 실로폰 '딩동댕' (0.6초)"),
            (short_buzzer, "🚨 오답: 매우 짧은 부저음 (0.25초)"),
            (ultra_short_buzzer, "💥 오답: 개선된 초단축 부저음 (0.25초)")
        ]
        
        for i, (sound, description) in enumerate(sounds, 1):
            print(f"\n{i}. {description}")
            play_sound(sound, description)
            
            if i < len(sounds):
                print("   (다음 소리까지 1초 대기...)")
                time.sleep(1)
        
        print("\n🎵 모든 단축 효과음 테스트 완료!")
        print("=" * 50)
        print("더 짧아진 1번과 4번이 어떠신가요?")
        print("\n💡 길이 비교:")
        print("- 정답 효과음: 1.2초 → 0.8초 → 0.6초")
        print("- 오답 효과음: 0.4초 → 0.25초 → 0.2초")
        print("\n🎯 게임에 적합한 빠른 반응속도!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print("numpy와 pygame이 설치되어 있는지 확인해주세요")
    
    finally:
        pygame.mixer.quit()

if __name__ == "__main__":
    main()