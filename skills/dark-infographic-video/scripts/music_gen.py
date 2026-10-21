"""
music_gen.py —— 纯程序化生成原创氛围配乐（鼓点+低频铺底+转场音效）

为什么需要这个：参考视频的原声多半是商业音乐，直接盗用会有版权风险。
这个脚本用 numpy 合成一段完全原创的 WAV（和弦铺底 + 心跳鼓点 + 转场音效 + 结尾铃音），
不依赖任何采样库，可以放心商用。生成的和弦走向、鼓点时间点都是参数化的，
按你的分镜时间表改一下 CHORDS / KICK_RANGE / HITS 几个列表即可匹配新选题的节奏。

用法：
    python3 music_gen.py <总时长秒数> <输出wav路径>
    例如: python3 music_gen.py 158 music.wav
"""
import sys
import numpy as np
import wave


def generate(duration, out_path, chapter_times=None):
    """
    duration: 总秒数（应和视频正文时长一致，不含封面帧）
    out_path: 输出 wav 路径
    chapter_times: 章节切换时间点列表（秒），用于在每个转场处加一个轻微的 hit 音效；
                   不传则只用默认的几个比例时间点
    """
    SR = 44100
    D = duration + 0.1
    N = int(SR * D)
    t = np.arange(N) / SR
    rng = np.random.default_rng(0)

    def env(t0, t1, fi, fo):
        return np.clip((t - t0) / fi, 0, 1) * np.clip((t1 - t) / fo, 0, 1)

    out = np.zeros((N, 2))

    # 1) 和弦铺底：把全片按比例切成 5 段，频率逐段小幅上移/下移制造情绪起伏
    #    用小调三和弦/四和弦叠加 + 慢速 LFO 做出"氛围毯"的感觉
    seg_bounds = [0, 0.11, 0.19, 0.42, 0.61, 0.78, 1.0]
    base_chords = [
        [55, 82.4, 110], [43.65, 65.4, 87.3, 130.8], [55, 82.4, 110, 164.8],
        [49, 73.4, 98, 146.8], [43.65, 65.4, 87.3, 130.8], [55, 82.4, 110, 164.8],
    ]
    for i in range(len(seg_bounds) - 1):
        s, e = seg_bounds[i] * duration, seg_bounds[i + 1] * duration
        fr = base_chords[i % len(base_chords)]
        en = env(s - 1.5, e + 1.5, 2.5, 2.5)
        for k, f in enumerate(fr):
            for dt, pan in ((-0.6, 0.3), (0.6, 0.7)):
                ph = rng.uniform(0, 6.28)
                sig = np.sin(2 * np.pi * (f + dt) * t + ph) + 0.25 * np.sin(2 * np.pi * 2 * (f + dt) * t)
                lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.07 * t + k)
                v = sig * lfo * en * (0.05 / (1 + k * 0.3))
                out[:, 0] += v * (1 - pan)
                out[:, 1] += v * pan

    # 2) 心跳鼓点：从全片 18% 处开始到 86% 处结束，70 BPM，后半段稍轻一点避免疲劳
    def kick(at, amp):
        n = int(0.35 * SR); i0 = int(at * SR)
        if i0 + n > N or i0 < 0: return
        tt = np.arange(n) / SR
        f = 40 + 60 * np.exp(-tt * 30)
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9) * amp
        out[i0:i0 + n, 0] += s
        out[i0:i0 + n, 1] += s

    kb, ke = duration * 0.18, duration * 0.86
    b = kb
    while b < ke:
        amp = 0.28 if b < duration * 0.78 else 0.2
        kick(b, amp); kick(b + 0.26, amp * 0.6)
        b += 60 / 70

    # 3) 开场计时音效：钩子阶段模拟时钟滴答，制造"深夜/紧迫感"
    hook_end = duration * 0.04 * 1.6 if duration > 100 else duration * 0.1
    for k in np.arange(0.5, max(hook_end, 2.0), 1.0):
        i0 = int(k * SR); n = int(0.03 * SR)
        s = rng.normal(0, 1, n) * np.exp(-np.arange(n) / SR * 200) * 0.12
        out[i0:i0 + n] += s[:, None]

    # 4) 转场音效：在每个章节切换点加一个短 riser + hit
    def riser(t0, d, amp):
        i0 = int(t0 * SR); n = int(d * SR)
        if i0 < 0 or i0 + n > N: return
        nz = rng.normal(0, 1, n); nz = np.convolve(nz, np.ones(8) / 8, 'same')
        g = np.linspace(0, 1, n) ** 2.5 * amp
        out[i0:i0 + n, 0] += nz * g
        out[i0:i0 + n, 1] += nz * g * 0.9

    def hit(t0, amp):
        i0 = int(t0 * SR); n = int(2.5 * SR)
        if i0 < 0 or i0 + n > N: return
        tt = np.arange(n) / SR
        s = (np.sin(2 * np.pi * 55 * tt) * 0.8 + rng.normal(0, 1, n) * 0.25 * np.exp(-tt * 8)) * np.exp(-tt * 1.6) * amp
        out[i0:i0 + n] += s[:, None]

    times = chapter_times if chapter_times else [duration * p for p in (0.19, 0.42, 0.61, 0.78)]
    for s in times:
        riser(s - 1.0, 1.0, 0.06)
        hit(s, 0.22)
    # 标题揭示处给一个稍大的 hit
    title_t = duration * 0.11
    riser(title_t - 1.0, 2.0, 0.16)
    hit(title_t + 0.3, 0.55)

    # 5) 结尾铃音动机：最后 20% 时长内，4个音符下行，营造收束感
    outro_start = duration * 0.86
    bell_freqs = [659.3, 523.3, 587.3, 440]
    for k, f in enumerate(bell_freqs):
        at = outro_start + 2.0 + k * 2.0
        i0 = int(at * SR); n = int(4 * SR)
        if i0 + n > N: n = N - i0
        if n <= 0: continue
        tt = np.arange(n) / SR
        s = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.01 * tt)) * np.exp(-tt * 1.2) * 0.06
        out[i0:i0 + n, 0] += s * 0.6
        out[i0:i0 + n, 1] += s * 0.4

    # 6) 整体淡入淡出 + 归一化，避免削波
    out *= (np.clip(t / 0.3, 0, 1) * np.clip((D - t) / 3.0, 0, 1))[:, None]
    peak = np.max(np.abs(out))
    if peak > 0:
        out /= peak * 1.12
    pcm = (out * 32767).astype('<i2')
    with wave.open(out_path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print('已生成配乐:', out_path, '时长约 %.1fs' % duration)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('用法: python3 music_gen.py <总时长秒数> <输出wav路径> [章节切换时间点,逗号分隔]')
        sys.exit(1)
    dur = float(sys.argv[1])
    out = sys.argv[2]
    ch = None
    if len(sys.argv) > 3:
        ch = [float(x) for x in sys.argv[3].split(',') if x.strip()]
    generate(dur, out, ch)
