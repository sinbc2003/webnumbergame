import pygame
import numpy as np
import time


 
def generate_ttidi_sound():
    """오답 효과음: '띠디' 소리를 생성합니다."""
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    duration = 0.8
    sample_rate = 22050
    
    # '띠' 소리 - 높은 주파수에서 시작
    tti_duration = 0.3
    tti_samples = int(tti_duration * sample_rate)
    t1 = np.linspace(0, tti_duration, tti_samples)
    
    # 높은 주파수 (띠)
    tti_freq = 800
    tti_wave = np.sin(2 * np.pi * tti_freq * t1) * 0.4
    # 빠르게 감쇠
    tti_decay = np.exp(-t1 * 8)
    tti_wave *= tti_decay
    
    # '디' 소리 - 낮은 주파수
    di_duration = 0.5
    di_samples = int(di_duration * sample_rate)
    t2 = np.linspace(0, di_duration, di_samples)
    
    # 낮은 주파수 (디)
    di_freq = 400
    di_wave = np.sin(2 * np.pi * di_freq * t2) * 0.3
    # 더 천천히 감쇠
    di_decay = np.exp(-t2 * 3)
    di_wave *= di_decay
    
    # 전체 사운드 조합
    total_samples = int(duration * sample_rate)
    samples = np.zeros(total_samples)
    
    # '띠' 소리 배치
    samples[:tti_samples] = tti_wave
    
    # '디' 소리 배치 (약간 겹치게)
    di_start = int(0.2 * sample_rate)
    di_end = min(di_start + di_samples, total_samples)
    di_actual_samples = di_end - di_start
    samples[di_start:di_end] += di_wave[:di_actual_samples]
    
    # 스테레오로 변환
    stereo_samples = np.zeros((len(samples), 2))
    stereo_samples[:, 0] = samples
    stereo_samples[:, 1] = samples
    
    sound_array = (stereo_samples * 32767).astype(np.int16)
    sound = pygame.sndarray.make_sound(sound_array)
    
    return sound

def generate_dingdongdaeng_sound():
    """정답 효과음: '딩동댕' 소리를 생성합니다."""
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    duration = 1.5
    sample_rate = 22050
    
    # 각 음의 지속시간
    note_duration = 0.4
    note_samples = int(note_duration * sample_rate)
    
    # '딩동댕' 주파수 (도-미-솔)
    frequencies = [523.25, 659.25, 783.99]  # C5, E5, G5
    
    total_samples = int(duration * sample_rate)
    samples = np.zeros(total_samples)
    
    for i, freq in enumerate(frequencies):
        start_time = i * 0.45  # 약간씩 겹치게
        start_sample = int(start_time * sample_rate)
        end_sample = min(start_sample + note_samples, total_samples)
        actual_samples = end_sample - start_sample
        
        if actual_samples > 0:
            t = np.linspace(0, actual_samples / sample_rate, actual_samples)
            
            # 벨 소리 효과 (기본 주파수 + 배음)
            wave = (np.sin(2 * np.pi * freq * t) * 0.4 +
                   np.sin(2 * np.pi * freq * 2 * t) * 0.2 +
                   np.sin(2 * np.pi * freq * 3 * t) * 0.1)
            
            # 각 음마다 다른 감쇠율
            decay_rate = 3 + i * 0.5  # 점점 더 길게 울림
            decay = np.exp(-t * decay_rate)
            wave *= decay
            
            # 볼륨 조절 (마지막 '댕'이 가장 크게)
            volume = 0.6 + i * 0.2
            wave *= volume
            
            samples[start_sample:end_sample] += wave
    
    # 전체적인 페이드 아웃
    fade_start = int(1.0 * sample_rate)
    if fade_start < len(samples):
        fade_samples = len(samples) - fade_start
        samples[fade_start:] *= np.linspace(1, 0, fade_samples)
    
    # 스테레오로 변환
    stereo_samples = np.zeros((len(samples), 2))
    stereo_samples[:, 0] = samples
    stereo_samples[:, 1] = samples
    
    sound_array = (stereo_samples * 32767).astype(np.int16)
    sound = pygame.sndarray.make_sound(sound_array)
    
    return sound

def generate_ttidi_sound_v2():
    """오답 효과음 버전2: 더 선명한 '띠디' 소리"""
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    duration = 0.6
    sample_rate = 22050
    total_samples = int(duration * sample_rate)
    samples = np.zeros(total_samples)
    
    # '띠' - 짧고 날카로운 소리
    tti_duration = 0.15
    tti_samples = int(tti_duration * sample_rate)
    t1 = np.linspace(0, tti_duration, tti_samples)
    
    tti_freq = 1000
    tti_wave = np.sin(2 * np.pi * tti_freq * t1) * 0.5
    # 매우 빠른 감쇠
    tti_decay = np.exp(-t1 * 15)
    tti_wave *= tti_decay
    
    # '디' - 낮고 길게 끌리는 소리
    di_start = int(0.2 * sample_rate)
    di_duration = 0.4
    di_samples = int(di_duration * sample_rate)
    di_end = min(di_start + di_samples, total_samples)
    di_actual_samples = di_end - di_start
    
    if di_actual_samples > 0:
        t2 = np.linspace(0, di_actual_samples / sample_rate, di_actual_samples)
        di_freq = 300
        di_wave = np.sin(2 * np.pi * di_freq * t2) * 0.4
        # 천천히 감쇠
        di_decay = np.exp(-t2 * 4)
        di_wave *= di_decay
        
        samples[di_start:di_end] = di_wave
    
    # '띠' 소리 배치
    samples[:tti_samples] = tti_wave
    
    # 스테레오로 변환
    stereo_samples = np.zeros((len(samples), 2))
    stereo_samples[:, 0] = samples
    stereo_samples[:, 1] = samples
    
    sound_array = (stereo_samples * 32767).astype(np.int16)
    sound = pygame.sndarray.make_sound(sound_array)
    
    return sound

def generate_dingdongdaeng_sound_v2():
    """정답 효과음 버전2: 더 명확한 '딩동댕' 소리"""
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    duration = 1.2
    sample_rate = 22050
    total_samples = int(duration * sample_rate)
    samples = np.zeros(total_samples)
    
    # 각 음의 정보 (주파수, 시작시간, 지속시간)
    notes = [
        (523.25, 0.0, 0.3),    # 딩 (C5)
        (659.25, 0.25, 0.35),  # 동 (E5)
        (783.99, 0.5, 0.7)     # 댕 (G5)
    ]
    
    for freq, start_time, note_duration in notes:
        start_sample = int(start_time * sample_rate)
        note_samples = int(note_duration * sample_rate)
        end_sample = min(start_sample + note_samples, total_samples)
        actual_samples = end_sample - start_sample
        
        if actual_samples > 0:
            t = np.linspace(0, actual_samples / sample_rate, actual_samples)
            
            # 맑은 벨 소리
            wave = np.sin(2 * np.pi * freq * t) * 0.5
            
            # 각 음마다 다른 특성
            if freq == 523.25:  # 딩 - 짧고 명확
                decay = np.exp(-t * 8)
            elif freq == 659.25:  # 동 - 중간
                decay = np.exp(-t * 6)
            else:  # 댕 - 길고 울림
                decay = np.exp(-t * 3)
            
            wave *= decay
            
            # 기존 샘플에 추가
            samples[start_sample:end_sample] += wave
    
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
    print("🎵 한국어 효과음 테스트: '띠디'(오답) vs '딩동댕'(정답)")
    print("=" * 50)
    
    try:
        # 효과음 생성
        print("\n🎼 효과음 생성 중...")
        
        ttidi1 = generate_ttidi_sound()
        print("✅ 오답 효과음 1 '띠디' 생성 완료")
        
        ttidi2 = generate_ttidi_sound_v2()
        print("✅ 오답 효과음 2 '띠디' (선명버전) 생성 완료")
        
        dingdongdaeng1 = generate_dingdongdaeng_sound()
        print("✅ 정답 효과음 1 '딩동댕' 생성 완료")
        
        dingdongdaeng2 = generate_dingdongdaeng_sound_v2()
        print("✅ 정답 효과음 2 '딩동댕' (명확버전) 생성 완료")
        
        # 효과음 재생 테스트
        print(f"\n🔊 한국어 효과음 재생 테스트")
        print("=" * 50)
        
        sounds = [
            (dingdongdaeng1, "🎉 정답: '딩동댕' (버전1 - 울림)"),
            (dingdongdaeng2, "🎊 정답: '딩동댕' (버전2 - 명확)"),
            (ttidi1, "❌ 오답: '띠디' (버전1 - 부드러움)"),
            (ttidi2, "🚫 오답: '띠디' (버전2 - 선명)")
        ]
        
        for i, (sound, description) in enumerate(sounds, 1):
            print(f"\n{i}. {description}")
            play_sound(sound, description)
            
            if i < len(sounds):
                print("   (다음 소리까지 2초 대기...)")
                time.sleep(2)
        
        print("\n🎵 모든 한국어 효과음 테스트 완료!")
        print("=" * 50)
        print("어떤 버전의 '딩동댕'과 '띠디'가 마음에 드시나요?")
        print("\n💡 추천:")
        print("- 1라운드: 딩동댕 버전2 + 띠디 버전1")
        print("- 2라운드: 딩동댕 버전1 + 띠디 버전2")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print("numpy와 pygame이 설치되어 있는지 확인해주세요")
    
    finally:
        pygame.mixer.quit()

if __name__ == "__main__":
    main()