import pygame
import numpy as np
import time

def generate_xylophone_dingdongdaeng():
    """정답 효과음: 실로폰 '딩동댕' (3음절)"""
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    duration = 1.2
    sample_rate = 22050
    total_samples = int(duration * sample_rate)
    samples = np.zeros(total_samples)
    
    # 실로폰 음계: 딩(C) - 동(E) - 댕(G) - 상승하는 3화음
    notes = [
        (523.25, 0.0, 0.35),   # 딩 (C5)
        (659.25, 0.3, 0.35),   # 동 (E5)
        (783.99, 0.6, 0.5)     # 댕 (G5) - 마지막이라 좀 더 길게
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
            attack_time = 0.01  # 매우 빠른 어택
            attack_samples = int(attack_time * sample_rate)
            
            if len(t) > attack_samples:
                # 어택 부분
                wave[:attack_samples] *= np.linspace(0, 1, attack_samples)
                # 감쇠 부분 (실로폰은 빠르게 감쇠)
                decay = np.exp(-t * 4)
                wave *= decay
            
            samples[start_sample:end_sample] += wave
    
    # 스테레오로 변환
    stereo_samples = np.zeros((len(samples), 2))
    stereo_samples[:, 0] = samples
    stereo_samples[:, 1] = samples
    
    sound_array = (stereo_samples * 32767).astype(np.int16)
    sound = pygame.sndarray.make_sound(sound_array)
    
    return sound

def generate_xylophone_bright():
    """정답 효과음 버전2: 더 밝은 실로폰 '딩동댕'"""
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    duration = 1.0
    sample_rate = 22050
    total_samples = int(duration * sample_rate)
    samples = np.zeros(total_samples)
    
    # 더 높은 옥타브로 밝게: 딩(C6) - 동(E6) - 댕(G6)
    notes = [
        (1046.5, 0.0, 0.3),    # 딩 (C6)
        (1318.5, 0.25, 0.3),   # 동 (E6)
        (1567.98, 0.5, 0.4)    # 댕 (G6)
    ]
    
    for freq, start_time, note_duration in notes:
        start_sample = int(start_time * sample_rate)
        note_samples = int(note_duration * sample_rate)
        end_sample = min(start_sample + note_samples, total_samples)
        actual_samples = end_sample - start_sample
        
        if actual_samples > 0:
            t = np.linspace(0, actual_samples / sample_rate, actual_samples)
            
            # 더 밝고 맑은 실로폰 소리
            wave = (np.sin(2 * np.pi * freq * t) * 0.7 +
                   np.sin(2 * np.pi * freq * 3 * t) * 0.2 +
                   np.sin(2 * np.pi * freq * 5 * t) * 0.1)
            
            # 빠른 어택과 자연스러운 감쇠
            attack_samples = int(0.005 * sample_rate)
            if len(wave) > attack_samples:
                wave[:attack_samples] *= np.linspace(0, 1, attack_samples)
                decay = np.exp(-t * 4.5)
                wave *= decay
            
            samples[start_sample:end_sample] += wave
    
    # 스테레오로 변환
    stereo_samples = np.zeros((len(samples), 2))
    stereo_samples[:, 0] = samples
    stereo_samples[:, 1] = samples
    
    sound_array = (stereo_samples * 32767).astype(np.int16)
    sound = pygame.sndarray.make_sound(sound_array)
    
    return sound

def generate_short_error_sound():
    """오답 효과음: 짧은 시스템 오류음"""
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    duration = 0.5  # 0.5초로 단축
    sample_rate = 22050
    total_samples = int(duration * sample_rate)
    samples = np.zeros(total_samples)
    
    # 오류음 특징: 불협화음과 노이즈
    t = np.linspace(0, duration, total_samples)
    
    # 여러 불협화음 주파수들 (더 적게)
    error_freqs = [220, 233, 185]  # 3개로 줄임
    
    for i, freq in enumerate(error_freqs):
        # 각 주파수마다 다른 시작 시간과 지속 시간
        start_time = i * 0.1
        start_sample = int(start_time * sample_rate)
        
        if start_sample < total_samples:
            end_sample = min(start_sample + int(0.3 * sample_rate), total_samples)
            wave_samples = end_sample - start_sample
            
            if wave_samples > 0:
                t_wave = np.linspace(0, wave_samples / sample_rate, wave_samples)
                
                # 사각파로 거친 소리 생성
                square_wave = np.sign(np.sin(2 * np.pi * freq * t_wave)) * 0.15
                
                # 주파수 변조로 더 불안정한 소리
                modulation = 1 + 0.2 * np.sin(2 * np.pi * 8 * t_wave)
                square_wave *= modulation
                
                # 빠른 감쇠
                decay = np.exp(-t_wave * 4)
                square_wave *= decay
                
                samples[start_sample:end_sample] += square_wave
    
    # 약간의 노이즈 추가
    noise = np.random.normal(0, 0.05, total_samples)
    noise_envelope = np.exp(-t * 6)  # 노이즈도 빠르게 감쇠
    samples += noise * noise_envelope
    
    # 클리핑 방지
    samples = np.clip(samples, -0.6, 0.6)
    
    # 스테레오로 변환
    stereo_samples = np.zeros((len(samples), 2))
    stereo_samples[:, 0] = samples
    stereo_samples[:, 1] = samples
    
    sound_array = (stereo_samples * 32767).astype(np.int16)
    sound = pygame.sndarray.make_sound(sound_array)
    
    return sound

def generate_short_buzzer_error():
    """오답 효과음 버전2: 짧은 클래식 부저음"""
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    duration = 0.4  # 0.4초로 단축
    sample_rate = 22050
    total_samples = int(duration * sample_rate)
    
    t = np.linspace(0, duration, total_samples)
    
    # 전형적인 부저음 (낮은 주파수)
    freq = 150
    
    # 사각파로 부저 소리 생성
    square_wave = np.sign(np.sin(2 * np.pi * freq * t)) * 0.4
    
    # 약간의 주파수 변조로 더 거슬리는 소리
    modulation = 1 + 0.15 * np.sin(2 * np.pi * 4 * t)
    samples = square_wave * modulation
    
    # 빠른 페이드 아웃
    fade_start = int(0.25 * sample_rate)
    samples[fade_start:] *= np.linspace(1, 0, len(samples) - fade_start)
    
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
    print("🎵 최종 효과음 테스트: 실로폰 '딩동댕' vs 짧은 오류음")
    print("=" * 55)
    
    try:
        # 효과음 생성
        print("\n🎼 효과음 생성 중...")
        
        xylophone1 = generate_xylophone_dingdongdaeng()
        print("✅ 정답 효과음 1: 실로폰 '딩동댕' (표준) 생성 완료")
        
        xylophone2 = generate_xylophone_bright()
        print("✅ 정답 효과음 2: 실로폰 '딩동댕' (밝은버전) 생성 완료")
        
        error1 = generate_short_error_sound()
        print("✅ 오답 효과음 1: 짧은 시스템 오류음 생성 완료")
        
        error2 = generate_short_buzzer_error()
        print("✅ 오답 효과음 2: 짧은 클래식 부저음 생성 완료")
        
        # 효과음 재생 테스트
        print(f"\n🔊 최종 효과음 재생 테스트")
        print("=" * 55)
        
        sounds = [
            (xylophone1, "🎼 정답: 실로폰 '딩동댕' (C-E-G, 1.2초)"),
            (xylophone2, "✨ 정답: 실로폰 '딩동댕' (밝은버전, 1.0초)"),
            (error1, "💥 오답: 짧은 시스템 오류음 (0.5초)"),
            (error2, "🚨 오답: 짧은 클래식 부저음 (0.4초)")
        ]
        
        for i, (sound, description) in enumerate(sounds, 1):
            print(f"\n{i}. {description}")
            play_sound(sound, description)
            
            if i < len(sounds):
                print("   (다음 소리까지 1.5초 대기...)")
                time.sleep(1.5)
        
        print("\n🎵 모든 최종 효과음 테스트 완료!")
        print("=" * 55)
        print("3음절 '딩동댕'과 짧아진 오류음이 어떠신가요?")
        print("\n💡 추천:")
        print("- 1라운드: 실로폰 표준버전 + 짧은 클래식 부저음")
        print("- 2라운드: 실로폰 밝은버전 + 짧은 시스템 오류음")
        print("\n🎼 실로폰 음계: C-E-G (도-미-솔) 3화음")
        print("⏱️  오류음 길이: 0.4~0.5초로 단축")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print("numpy와 pygame이 설치되어 있는지 확인해주세요")
    
    finally:
        pygame.mixer.quit()

if __name__ == "__main__":
    main()