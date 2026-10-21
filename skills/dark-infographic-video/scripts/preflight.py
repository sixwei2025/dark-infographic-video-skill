#!/usr/bin/env python3
"""
preflight.py —— 成片交付前自检

把这类视频最容易翻车的几项一次查完：规格、码率、音量、手机外放可闻性、首帧封面。

用法：
    python3 preflight.py 成片.mp4
    python3 preflight.py 成片.mp4 --min 48 --max 62     # 顺便核对时长区间

退出码：全部通过 0，有 FAIL 项 1。
"""
import subprocess
import sys
import json
import re
import os
import tempfile

OK, WARN, FAIL = '✅', '⚠️', '❌'


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(path):
    r = sh(['ffprobe', '-v', 'error', '-show_entries',
            'stream=codec_type,codec_name,width,height,r_frame_rate,bit_rate',
            '-show_entries', 'format=duration,size', '-of', 'json', path])
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


def vol(path, af='volumedetect'):
    r = sh(['ffmpeg', '-hide_banner', '-i', path, '-af', af, '-f', 'null', '-'])
    m = re.search(r'mean_volume:\s*([-\d.]+) dB', r.stderr)
    x = re.search(r'max_volume:\s*([-\d.]+) dB', r.stderr)
    return (float(m.group(1)) if m else None,
            float(x.group(1)) if x else None)


def first_frame_brightness(path):
    """首帧平均亮度。用于确认封面确实压在了第 0 帧（而不是一片黑）。"""
    tmp = os.path.join(tempfile.gettempdir(), '_pf_first.png')
    sh(['ffmpeg', '-y', '-v', 'error', '-i', path, '-vf', 'select=eq(n\\,0)',
        '-frames:v', '1', tmp])
    try:
        from PIL import Image
        import numpy as np
        return float(np.array(Image.open(tmp).convert('L')).mean())
    except Exception:
        return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = sys.argv[1]
    lo, hi = None, None
    if '--min' in sys.argv:
        lo = float(sys.argv[sys.argv.index('--min') + 1])
    if '--max' in sys.argv:
        hi = float(sys.argv[sys.argv.index('--max') + 1])

    if not os.path.exists(path):
        print('%s 文件不存在：%s' % (FAIL, path))
        sys.exit(1)

    print('=' * 62)
    print('成片自检：%s' % os.path.basename(path))
    print('=' * 62)

    info = probe(path)
    if not info:
        print('%s 无法读取该文件的流信息' % FAIL)
        sys.exit(1)

    v = next((s for s in info['streams'] if s.get('codec_type') == 'video'), None)
    a = next((s for s in info['streams'] if s.get('codec_type') == 'audio'), None)
    dur = float(info['format']['duration'])
    fsize = int(info['format']['size'])
    fails = 0

    # ---- 视频规格 ----
    w, h = v['width'], v['height']
    fps = v['r_frame_rate']
    vbr = int(v.get('bit_rate') or 0)
    print('\n【画面】')
    if w >= 1080 and h >= 1080:
        print('  %s 分辨率 %dx%d' % (OK, w, h))
    else:
        print('  %s 分辨率 %dx%d —— 低于 1080p，手机上文字会发糊' % (WARN, w, h))
    print('  %s 帧率 %s' % (OK, fps))
    if vbr >= 4_000_000:
        print('  %s 码率 %.2f Mbps（深色背景+文字需要 ≥4 Mbps，否则出现色带和毛边）' % (OK, vbr / 1e6))
    else:
        print('  %s 码率只有 %.2f Mbps，建议用 -crf 12 -preset slow 重编码' % (WARN, vbr / 1e6))
        fails += 1

    # ---- 时长 ----
    print('\n【时长】')
    m, s = divmod(dur, 60)
    line = '  %s %.2f 秒（%d:%04.1f）· 文件 %.1f MB' % (OK, dur, int(m), s, fsize / 1e6)
    if lo is not None and dur < lo:
        print('  %s %.2f 秒 —— 短于预期下限 %.1f 秒' % (FAIL, dur, lo))
        fails += 1
    elif hi is not None and dur > hi:
        print('  %s %.2f 秒 —— 长于预期上限 %.1f 秒，检查是不是又给观众留了阅读时间' % (FAIL, dur, hi))
        fails += 1
    else:
        print(line)

    # ---- 音频 ----
    print('\n【声音】')
    if a is None:
        print('  %s 没有音轨 —— 无旁白的片子配乐是唯一声源，必须有' % FAIL)
        fails += 1
    else:
        mean, peak = vol(path)
        print('  %s 音轨 %s %s bps' % (OK, a.get('codec_name', '?'), a.get('bit_rate', '?')))
        if peak is not None:
            if peak > -0.5:
                print('  %s 峰值 %.1f dB 太贴近 0，编码后可能削波，配乐应留到 -1.5 dB 以下' % (WARN, peak))
                fails += 1
            else:
                print('  %s 峰值 %.1f dB（有余量）' % (OK, peak))
        # 手机外放可闻性：这是最容易翻车的一项
        mid, _ = vol(path, 'highpass=f=400,volumedetect')
        if mid is not None:
            if mid < -35:
                print('  %s 手机外放段（高通 400Hz 后）只有 %.1f dB —— 外放等于没声音！'
                      '配乐能量压在低频了，换成 music_gen_v2.py 生成的中频版' % (FAIL, mid))
                fails += 1
            else:
                print('  %s 手机外放段 %.1f dB（可闻）' % (OK, mid))

    # ---- 首帧封面 ----
    print('\n【首帧】')
    br = first_frame_brightness(path)
    if br is None:
        print('  %s 无法检测首帧亮度（缺 Pillow？）' % WARN)
    elif br < 3:
        print('  %s 首帧几乎是全黑 —— 封面没压在第 0 帧，平台会抓到一张黑图做封面' % FAIL)
        fails += 1
    else:
        print('  %s 首帧平均亮度 %.1f，封面正常' % (OK, br))

    print('\n' + '=' * 62)
    if fails == 0:
        print('%s 全部通过，可以交付。' % OK)
        sys.exit(0)
    print('%s 有 %d 项需要处理。' % (FAIL, fails))
    sys.exit(1)


if __name__ == '__main__':
    main()
