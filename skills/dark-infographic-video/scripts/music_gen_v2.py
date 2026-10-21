"""
music_gen_v2.py —— 面向「手机外放」的暗黑氛围配乐（中频版）

与 music_gen.py 的区别（这是关键修复）：
  v1 的和声垫 / 鼓点全部压在 40–165 Hz，中频几乎是空的 —— 那是"给耳机听的"配乐，
  手机与笔记本扬声器根本推不出这个频段，外放时等于没声音。
  v2 做三件事：
    1. 和声垫整体上移到 175–440 Hz（A 小调），并叠 2 次 / 3 次泛音，把能量送进
       200–2000 Hz 这个"手机能出声"的区间；
    2. 新增稀疏的中频钟琴旋律线（A4–G5，440–784 Hz）与每拍的 hi-hat，
       让片子有明确的节奏与旋律存在感，而不是只有低频嗡嗡声；
    3. 输出端加软限幅（tanh）+ 目标响度归一化，把平均电平从 −23.5 dB 提到 −16 dB 附近。

用法：
    python3 music_gen_v2.py <总时长秒数> <输出wav路径> [章节切换时间点,逗号分隔]
"""
import sys
import numpy as np
import wave


def generate(duration, out_path, chapter_times=None):
    SR = 44100
    D = duration + 0.1
    N = int(SR * D)
    t = np.arange(N) / SR
    rng = np.random.default_rng(7)
    out = np.zeros((N, 2))

    def env(t0, t1, fi, fo):
        return np.clip((t - t0) / fi, 0, 1) * np.clip((t1 - t) / fo, 0, 1)

    # ---------- 1) 中频和声垫（A 小调，175–440 Hz） ----------
    prog = [
        [220.00, 261.63, 329.63],   # Am  A3 C4 E4
        [174.61, 220.00, 261.63],   # F   F3 A3 C4
        [196.00, 246.94, 293.66],   # G   G3 B3 D4
        [164.81, 196.00, 246.94],   # Em  E3 G3 B3
    ]
    bar = 3.4
    nbars = int(duration / bar) + 1
    for bi in range(nbars):
        s = bi * bar
        if s >= duration:
            break
        chord = prog[[0, 1, 2, 3, 0, 1][bi % 6]]
        mood = 0.72 if s > duration * 0.86 else 1.0      # 结尾段更暗、更收
        en = env(s - 0.6, min(s + bar, duration) + 0.6, 1.2, 1.2)
        for k, f in enumerate(chord):
            for det, pan in ((-0.5, 0.34), (0.5, 0.66)):
                ph = rng.uniform(0, 6.28)
                sig = (np.sin(2 * np.pi * (f + det) * t + ph)
                       + 0.42 * np.sin(2 * np.pi * 2 * (f + det) * t + ph * 1.7)
                       + 0.18 * np.sin(2 * np.pi * 3 * (f + det) * t + ph * 2.3))
                lfo = 0.80 + 0.20 * np.sin(2 * np.pi * 0.11 * t + k)
                v = sig * lfo * en * (0.046 / (1 + k * 0.25)) * mood
                out[:, 0] += v * (1 - pan)
                out[:, 1] += v * pan

    # ---------- 2) 中频钟琴旋律（稀疏，留白） ----------
    scale = [440.00, 523.25, 587.33, 659.25, 783.99]     # A4 C5 D5 E5 G5
    for mt in np.arange(2.2, duration * 0.86, 1.7):
        if rng.random() < 0.55:
            continue
        f = scale[int(rng.integers(0, len(scale)))]
        n = int(2.2 * SR)
        i0 = int(mt * SR)
        if i0 + n > N:
            n = N - i0
        if n <= 0:
            continue
        tt = np.arange(n) / SR
        amp = 0.066 if mt < duration * 0.80 else 0.048
        s = (np.sin(2 * np.pi * f * tt)
             + 0.35 * np.sin(2 * np.pi * f * 2 * tt)
             + 0.12 * np.sin(2 * np.pi * f * 3 * tt)) * np.exp(-tt * 2.6) * amp
        pan = rng.uniform(0.35, 0.65)
        out[i0:i0 + n, 0] += s * (1 - pan)
        out[i0:i0 + n, 1] += s * pan

    # ---------- 3) 节拍：心跳底鼓（带中频击打感）+ hi-hat ----------
    def kick(at, amp):
        n = int(0.40 * SR)
        i0 = int(at * SR)
        if i0 < 0 or i0 + n > N:
            return
        tt = np.arange(n) / SR
        f = 44 + 70 * np.exp(-tt * 26)
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 7.5) * amp
        click = rng.normal(0, 1, n) * np.exp(-tt * 150) * amp * 0.55   # 中频瞬态，外放才听得见
        s = body + click
        out[i0:i0 + n, 0] += s
        out[i0:i0 + n, 1] += s

    def hat(at, amp):
        n = int(0.09 * SR)
        i0 = int(at * SR)
        if i0 < 0 or i0 + n > N:
            return
        tt = np.arange(n) / SR
        nz = rng.normal(0, 1, n)
        nz = np.diff(np.concatenate([[0.0], nz]))          # 一阶差分 = 简易高通
        s = nz * np.exp(-tt * 55) * amp
        out[i0:i0 + n, 0] += s * 0.8
        out[i0:i0 + n, 1] += s * 1.0

    BPM = 78
    beat = 60.0 / BPM
    b = duration * 0.045
    k = 0
    while b < duration * 0.97:
        if k % 2 == 0:
            kick(b, 0.25)
        hat(b, 0.042)
        hat(b + beat / 2, 0.027)
        b += beat
        k += 1

    # ---------- 4) 开场滴答（钩子段紧迫感） ----------
    for kk in np.arange(0.5, max(duration * 0.05, 2.2), 1.0):
        i0 = int(kk * SR)
        n = int(0.03 * SR)
        if i0 + n > N:
            break
        s = rng.normal(0, 1, n) * np.exp(-np.arange(n) / SR * 200) * 0.10
        out[i0:i0 + n] += s[:, None]

    # ---------- 5) 章节转场 riser + hit ----------
    def riser(t0, d, amp):
        i0 = int(t0 * SR)
        n = int(d * SR)
        if i0 < 0 or i0 + n > N:
            return
        nz = rng.normal(0, 1, n)
        nz = np.convolve(nz, np.ones(8) / 8, 'same')
        g = np.linspace(0, 1, n) ** 2.5 * amp
        out[i0:i0 + n, 0] += nz * g
        out[i0:i0 + n, 1] += nz * g * 0.9

    def hit(t0, amp):
        i0 = int(t0 * SR)
        n = int(2.5 * SR)
        if i0 < 0 or i0 + n > N:
            return
        tt = np.arange(n) / SR
        s = (np.sin(2 * np.pi * 110 * tt) * 0.8
             + rng.normal(0, 1, n) * 0.25 * np.exp(-tt * 8)) * np.exp(-tt * 1.6) * amp
        out[i0:i0 + n] += s[:, None]

    times = chapter_times if chapter_times else [duration * p for p in (0.19, 0.42, 0.61, 0.78)]
    for s in times:
        riser(s - 1.0, 1.0, 0.055)
        hit(s, 0.20)
    riser(duration * 0.11 - 1.0, 2.0, 0.15)
    hit(duration * 0.11 + 0.3, 0.50)

    # ---------- 6) 结尾铃音动机（下行四音） ----------
    outro_start = duration * 0.86
    for j, f in enumerate([659.25, 523.25, 587.33, 440.00]):
        at = outro_start + 2.0 + j * 2.0
        i0 = int(at * SR)
        n = int(4 * SR)
        if i0 < 0:
            continue
        if i0 + n > N:
            n = N - i0
        if n <= 0:
            continue
        tt = np.arange(n) / SR
        s = (np.sin(2 * np.pi * f * tt) + 0.30 * np.sin(2 * np.pi * f * 2.01 * tt)) \
            * np.exp(-tt * 1.2) * 0.055
        out[i0:i0 + n, 0] += s * 0.6
        out[i0:i0 + n, 1] += s * 0.4

    # ---------- 7) 收尾：淡入淡出 + 软限幅 + 目标响度归一化 ----------
    out *= (np.clip(t / 0.45, 0, 1) * np.clip((D - t) / 3.0, 0, 1))[:, None]
    peak = np.max(np.abs(out))
    if peak > 0:
        out /= peak
    out = np.tanh(out * 2.3) / np.tanh(2.3)      # 软限幅：抬高平均电平又不削波
    peak = np.max(np.abs(out))
    if peak > 0:
        out /= peak * 1.42                        # 留约 -3 dB 余量（AAC 编码会有约 1.5dB 过冲）

    pcm = (out * 32767).astype('<i2')
    with wave.open(out_path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print('已生成配乐:', out_path, '时长约 %.1fs' % duration)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('用法: python3 music_gen_v2.py <总时长秒数> <输出wav路径> [章节切换时间点,逗号分隔]')
        sys.exit(1)
    dur = float(sys.argv[1])
    outp = sys.argv[2]
    ch = None
    if len(sys.argv) > 3:
        ch = [float(x) for x in sys.argv[3].split(',') if x.strip()]
    generate(dur, outp, ch)
