import pygame
import numpy as np
import time



def generate_short_solmi_sound():
    """정답 효과음: 짧은 '쏠미~' 소리 (하강)"""
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    
    duration = 0.5  # 0.8초에서 0.5초로 단축
    sample_rate = 22050
    total_samples = int(duration * sample_rate)
    samples = np.zeros(total_samples)
    
    # 쏠미 음계: 쏠(G) - 미(E) - 하강하는 소리, 더 빠르게
    notes = [
        (783.99, 0.0, 0.2),    # 쏠 (G5) - 0.3초에서 0.2초로
        (659.25, 0.15, 0.3)    # 미~ (E5) - 0.25초에서 0.15초로, 0.5초에서 0.3초로
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
                # 두 번째 음은 더 천천히 감쇠하지만 전체적으로 빠르게
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
    print("🎵 짧은 '쏠미~' 정답 효과음 테스트")
    print("=" * 35)
    
    try:
        # 효과음 생성
        print("\n🎼 효과음 생성 중...")
        
        short_solmi = generate_short_solmi_sound()
        print("✅ 정답 효과음: 짧은 '쏠미~' 생성 완료")
        
        # 효과음 재생 테스트
        print(f"\n🔊 효과음 재생 테스트")
        print("=" * 35)
        
        print("1. 🎶 정답: 짧은 '쏠미~' (G-E, 0.5초)")
        play_sound(short_solmi, "🎶 정답: 짧은 '쏠미~' (G-E, 0.5초)")
        
        print("\n🎵 짧은 '쏠미~' 효과음 테스트 완료!")
        print("=" * 35)
        print("0.8초에서 0.5초로 단축된 '쏠미~'가 어떠신가요?")
        print("\n💡 특징:")
        print("- 쏠미~: G-E 하강, 부드럽지만 더 빠른 감쇠")
        print("- 길이: 0.8초 → 0.5초로 단축")
        print("- 게임에 적합한 빠른 반응속도")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print("numpy와 pygame이 설치되어 있는지 확인해주세요")
    
    finally:
        pygame.mixer.quit()

if __name__ == "__main__":
    main()