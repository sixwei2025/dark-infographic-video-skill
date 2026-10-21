# -*- coding: utf-8 -*-
"""
example_scenes.py —— 完整可运行的参考答案（选题：睡眠剥夺，3 章 / 34 秒）

这是"照着改"的起点。它示范了本 Skill 当前推荐的全部做法：

  1. **紧凑节奏**：开场 12.85 秒（钩子→反差→速览→标题，不留纯转场页），
     **正文每章时长 = 该章动画走完的时间 + 0.8 秒落点**，一秒都不多留；
  2. **封面**：横屏首帧的中心 810×1080 正好是一张完整 3:4 竖版封面，
     平台按 `crop=810:1080:555:0` 裁切即可拿到干净封面；
  3. **配乐**：用 `music_gen_v2.py`（中频版），别用低频的 v1。

运行方式见文件底部注释。改选题时：换 TOTAL_SECONDS、CHAP/CSPAN、
各 s_chN 里的文案与数据即可，时间轴结构可以整套复用。
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import *  # noqa: F401,F403

# 各章时长 = 该章动画走完的时间 + 0.8 秒：入睡 5.0s、修复 5.3s、代价 5.9s
TOTAL_SECONDS = 34.45

CHAP = [('入睡', '被推迟的信号'), ('修复', '被跳过的夜班'), ('代价', '还不完的债')]
CSPAN = [(12.85, 17.85), (17.85, 23.15), (23.15, 29.05)]


# ============================== 开场段 ==============================

def s_hook(u):
    """钩子：计时器从 23:50 跳到 00:40。3 秒的场景，动画必须 2.5 秒内走完。"""
    seq = [(0.0, '23:50'), (1.0, '00:10'), (1.7, '00:40')]
    cur = seq[0]
    for sp in seq:
        if u >= sp[0]:
            cur = sp
    flick = 0.45 if (cur[0] > 0 and u - cur[0] < 0.12) else 1.0
    a0, dy = ap(u, 0.0, 0.6)
    T([S(cur[1], WHT, 'numul', 320)], 960, 540 + dy, 'c', a=a0 * flick)
    T([S('又是这个点。', WHT, 'semi', 58)], 960, 740, 'c', p=ramp(u, 0.9, 0.9))


def s_think(u):
    """认知反差。3.2 秒。"""
    a, dy = ap(u, 0.2)
    T([S('你以为，', GRY, 'reg', 46)], 960, 400 + dy, 'c', a=a)
    T([S('只是睡晚了一点。', WHT, 'semi', 96)], 960, 580, 'c', p=ramp(u, 0.6, 1.0))
    a, dy = ap(u, 1.7)
    T([S('身体记的，是另一本账。', GRY, 'reg', 40)], 960, 730 + dy, 'c', a=a)


def s_grid(u):
    """3 宫格速览，一次给全。4.6 秒。"""
    items = [('入睡', '· 信号被推迟'), ('修复', '· 夜班被跳过'), ('代价', '· 债还不完')]
    for i, (a_text, b_text) in enumerate(items):
        x = [400, 960, 1520][i]
        y = 620
        al, dy = ap(u, 0.35 + 0.42 * i, 0.5)
        if al <= 0:
            continue
        FR.d.line([(x - 34, y - 64 + dy), (x - 34, y + 14 + dy)], fill=C(ORG, al), width=6)
        T([S('%02d' % (i + 1), ORG, 'numd', 22)], x - 20, y - 72 + dy, a=al * 0.85)
        T([S(a_text, WHT, 'med', 58), S(b_text, ORG, 'semi', 30)], x, y + dy, a=al)


def s_title(u):
    """大标题揭示（配一次全屏闪色）。3.4 秒。"""
    FR.post.append(('fill', ORG, 0.85 * (1 - ramp(u, 0, 0.5))))
    T([S('睡眠', WHT, 'semi', 280), S('债', ORG, 'semi', 280)], 960, 600, 'c', glow=32, ga=0.55)
    L = 560 * eo(ramp(u, 0.6, 0.8))
    if L > 1:
        FR.d.line([(960 - L, 700), (960 + L, 700)], fill=C(ORG, 0.85), width=3)
    T([S('是怎样，一夜一夜，欠下来的？', WHT, 'med', 50)], 960, 820, 'c', p=ramp(u, 1.3, 1.2))


# ============================== 正文段 ==============================

def s_ch1(u):
    """01 入睡：褪黑素分泌被推迟（圆环仪表）。11 秒，动画在 5.5 秒内走完。"""
    cx, cy, R = 480, 545, 268
    for k in range(72):
        ang = math.radians(-90 + k * 5)
        major = (k % 12 == 0)
        r0 = R + (6 if major else 16)
        r1 = R + 34
        FR.d.line([(cx + r0 * math.cos(ang), cy + r0 * math.sin(ang)),
                   (cx + r1 * math.cos(ang), cy + r1 * math.sin(ang))],
                  fill=C(GRY if major else DIM, 0.85 if major else 0.65),
                  width=4 if major else 2)
    ring(cx, cy, R - 44, DIM, 0.4, 2)
    v = 1.5 * eio(ramp(u, 1.0, 2.0))
    deg = v / 2.0 * 270
    if deg > 0.5:
        bb = [cx - R + 10, cy - R + 10, cx + R - 10, cy + R - 10]
        FR.d.arc([bb[0] - 12, bb[1] - 12, bb[2] + 12, bb[3] + 12], -135, -135 + deg,
                 fill=C(ORG, 0.14), width=56)
        FR.d.arc(bb, -135, -135 + deg, fill=C(ORG, 0.95), width=28)
        ea = math.radians(-135 + deg)
        dot(cx + (R - 24) * math.cos(ea), cy + (R - 24) * math.sin(ea), 9, WHT, 0.95)
    T([S('%.1f' % v, WHT, 'numd', 130)], cx, cy + 50, 'c', a=ramp(u, 1.0, 0.3), glow=16, ga=0.4)
    T([S('小时 · 入睡推迟', GRY, 'reg', 24)], cx, cy + 112, 'c', a=ramp(u, 1.3, 0.4))

    X = 1010
    a, dy = ap(u, 0.5)
    T([S('睡前盯着屏幕，身体以为天还没黑。', GRY, 'reg', 38)], X, 300 + dy, a=a)
    a, dy = ap(u, 1.3)
    T([S('褪黑素分泌', WHT, 'semi', 58)], X, 430 + dy, a=a)
    a, dy = ap(u, 1.8)
    T([S('被推迟了。', ORG, 'semi', 58)], X, 515 + dy, a=a, glow=12, ga=0.3)
    a, dy = ap(u, 3.6)
    T([S('被推迟的，不只是困意。', GRY, 'reg', 40)], X, 680 + dy, a=a)
    source('示例数据 · 请替换为你检索到的真实来源（机构/论文 + 年份 + 样本量）')


def s_ch2(u):
    """02 修复：深睡被压缩（双曲线交叉）。11.5 秒。"""
    x0, x1, y0, y1 = 150, 800, 410, 800
    T([S('一夜之间，深睡被切走多少', GRY, 'reg', 28)], 470, 322, 'c', p=ramp(u, 0.3, 1.0))
    pp = eio(ramp(u, 1.1, 2.4))
    n = max(2, int(80 * pp))
    up, down = [], []
    for k in range(n):
        s_ = k / 79.0
        sg = 1 / (1 + math.exp(-(s_ - 0.5) * 9))
        xx = x0 + (x1 - x0) * s_
        up.append((xx, y1 - 30 - (y1 - y0 - 70) * sg))
        down.append((xx, y0 + 30 + (y1 - y0 - 70) * sg))
    if pp > 0:
        gline(up, ORG, 1.0, 6)
        FR.d.line(down, fill=C(WHT, 0.85), width=4)
    a = ramp(u, 2.2, 0.5)
    T([S('浅睡', ORG, 'semi', 34)], x1 + 16, 452, a=a)
    T([S('深睡', WHT, 'semi', 34)], x1 + 16, 772, a=a)

    X = 1010
    a, dy = ap(u, 0.5)
    T([S('越晚入睡，', GRY, 'reg', 42)], X, 300 + dy, a=a)
    a, dy = ap(u, 1.3)
    T([S('深睡越短。', WHT, 'semi', 66)], X, 420 + dy, a=a, glow=10, ga=0.3)
    a, dy = ap(u, 3.4)
    T([S('修复，发生在你以为', GRY, 'reg', 38)], X, 620 + dy, a=a)
    a, dy = ap(u, 3.9)
    T([S('「没在干嘛」的时候。', GRY, 'reg', 38)], X, 676 + dy, a=a)
    source('示例数据 · 请替换为你检索到的真实来源')


def s_ch3(u):
    """03 代价：一周累计欠睡（柱状图）。10.5 秒。"""
    a, dy = ap(u, 0.3)
    T([S('睡眠债', WHT, 'semi', 92)], 150, 330 + dy, a=a)
    a, dy = ap(u, 0.8)
    T([S('每晚少睡 ', GRY, 'reg', 36), S('1.5', ORG, 'numd', 44), S(' 小时', GRY, 'reg', 36)],
      150, 420 + dy, a=a)

    yb = 300
    days = ['一', '二', '三', '四', '五', '六', '日']
    for i in range(7):
        x = 800 + i * 145
        v = 1.5 * (i + 1)
        al = ramp(u, 1.0 + 0.28 * i, 0.3)
        g = eio(ramp(u, 1.0 + 0.28 * i, 0.7))
        T([S(days[i], GRY, 'semi', 26)], x + 50, yb - 20, 'c', a=al)
        hgt = v / 10.5 * 480 * g
        if hgt > 1:
            FR.d.rectangle([x, yb + 3, x + 100, yb + 3 + hgt], fill=C(ORG, (0.40 + 0.08 * i) * al))
        T([S('-%.1f' % v, WHT, 'numd', 26)], x + 50, yb + 3 + hgt + 38, 'c', a=al * g)

    a, dy = ap(u, 3.6)
    T([S('一周下来，欠下 ', GRY, 'reg', 40), S('10.5', ORG, 'numd', 50), S(' 小时。', GRY, 'reg', 40)],
      150, 660 + dy, a=a)
    a, dy = ap(u, 4.5)
    T([S('周末补觉，补不回来。', WHT, 'semi', 48)], 150, 780 + dy, a=a)
    source('示例数据 · 请替换为你检索到的真实来源')


def s_outro(u):
    """结尾：3 条建议 + 升华句。10.8 秒。"""
    tips = [('01', '固定熄灯时间'), ('02', '睡前1小时离屏'), ('03', '每晚 7-9 小时')]
    for i, (n, tx) in enumerate(tips):
        al, dy = ap(u, 0.4 + 0.42 * i)
        T([S(n + '  ', ORG, 'numd', 34), S(tx, WHT, 'reg', 34)], [380, 960, 1540][i],
          258 + dy, 'c', a=al)
    T([S('今晚，', WHT, 'light', 120), S('早点睡。', ORG, 'semi', 120)],
      960, 620, 'c', p=ramp(u, 1.8, 1.0), glow=16, ga=0.35)
    a, dy = ap(u, 4.0)
    T([S('把欠下的，还给今天的自己。', GRY, 'reg', 42)], 960, 745 + dy, 'c', a=a)


# ============== 组装时间轴 ==============
SCENES = [
    # 开场 12.85s：钩子 → 反差 → 速览 → 标题
    (0.0, 3.1, s_hook, [(960, 540, 640, 0.12, ORG)], 0.25, 0.25),
    (3.1, 6.2, s_think, [(960, 560, 640, 0.08, ORG)], 0.25, 0.25),
    (6.2, 9.35, s_grid, [(960, 610, 620, 0.07, ORG)], 0.25, 0.25),
    (9.35, 12.85, s_title, [(960, 540, 700, 0.22, ORG)], 0.0, 0.30),
    # 铁律：每章时长 = 该章动画走完 + 0.8 秒落点，一秒都不多留
    (12.85, 17.85, s_ch1, [(480, 545, 480, 0.11, ORG)], 0.25, 0.25),
    (17.85, 23.15, s_ch2, [(490, 600, 520, 0.10, ORG)], 0.25, 0.25),
    (23.15, 29.05, s_ch3, [(1280, 560, 560, 0.09, ORG)], 0.25, 0.25),
    (29.05, 34.45, s_outro, [(960, 560, 650, 0.11, ORG)], 0.35, 0.70),
]


def render_t(t):
    """按全局时间 t（秒）渲染一帧。engine.run_cli 会调用这个函数名。"""
    # 场景之间做真正的交叉淡化（前一个场景的淡出与后一个的淡入重叠），不会"闪黑"
    im = render_crossfade(SCENES, t)
    # HUD 是常驻元素，画在最上层，不参与场景的淡入淡出
    im.alpha_composite(overlay_layer(lambda: hud(t, CHAP, CSPAN, fade_in=(12.85, 0.6))))
    return im


def _cover_block(cx, w, h):
    """
    竖版封面内容块。设计基准 810×1080 —— 正好是 3:4。
    字号按 w/810 缩放、纵坐标按 h/1080 缩放，所以同一份代码既能画纯 3:4 封面（1080×1440），
    也能画横屏画布里居中的那个 3:4 安全区（810×1080）。
    """
    s = w / 810.0
    sy = h / 1080.0
    def Y(v): return v * sy
    def fx(v): return max(1, int(round(v * s)))

    tag = '3 个阶段 · 一夜之间'
    ty = Y(300)
    tw_ = TW([S(tag, ORG, 'semi', fx(32))])
    FR.d.rounded_rectangle([cx - tw_ / 2 - 30 * s, ty - 46 * s, cx + tw_ / 2 + 30 * s, ty + 18 * s],
                           32 * s, outline=C(ORG, 0.95), width=max(2, fx(3)))
    T([S(tag, ORG, 'semi', fx(32))], cx, ty, 'c')

    # 大标题按字数自适应，保证不超出内容区
    t_size = fx(min(150, 660 / 3))
    T([S('睡眠', WHT, 'semi', t_size), S('债', ORG, 'semi', t_size)],
      cx, Y(500), 'c', glow=fx(26), ga=0.5)

    L = 300 * s
    yy = Y(575)
    FR.d.line([(cx - L, yy), (cx + L, yy)], fill=C(ORG, 0.20), width=max(2, fx(8)))
    FR.d.line([(cx - L, yy), (cx + L, yy)], fill=C(ORG, 0.90), width=max(1, fx(3)))

    T([S('你以为只是睡晚了一点', WHT, 'semi', fx(38))], cx, Y(680), 'c', glow=fx(6), ga=0.3)
    T([S('入睡 · 深睡 · 修复 · 代价', GRY, 'reg', fx(28))], cx, Y(775), 'c')

    for j, (big, unit, lab) in enumerate([('1.5', '小时', '入睡延迟'), ('10.5', '小时', '一周欠睡')]):
        x = cx + (j * 2 - 1) * (172 * s)
        T([S(big, ORG if j == 0 else WHT, 'num', fx(72)), S(unit, GRY, 'semi', fx(25))], x, Y(930), 'c')
        T([S(lab, GRY, 'reg', fx(21))], x, Y(972), 'c')
    FR.d.line([(cx, Y(840)), (cx, Y(982))], fill=C(DIM, 0.8), width=1)


def cover(size=None):
    """
    - size 为 3:4（如 1080×1440）→ 输出纯竖版封面，供平台手动上传；
    - 横屏 / 不传 → 输出 1920×1080 首帧：中心 810×1080 正好是一整张 3:4 封面，
      左右两侧用背景光晕自然延展。平台裁切参数：crop=810:1080:555:0
    """
    vert = bool(size) and size[0] < size[1]
    if vert:
        Wc, Hc = 1080, 1440
        glows = [(540, 690, 660, 0.26, ORG), (540, 1440, 540, 0.07, WHT)]
    else:
        Wc, Hc = W, H
        glows = [(960, 540, 820, 0.24, ORG), (960, 1080, 560, 0.06, WHT)]
    cx = Wc // 2
    begin_frame(glows, (Wc, Hc))
    CTX[0] = 1.0
    rng = np.random.default_rng(21)
    for _ in range(110):
        dot(rng.uniform(0, Wc), rng.uniform(0, Hc), rng.uniform(1.2, 3.4), ORG,
            rng.uniform(0.15, 0.5))
    _cover_block(cx, 1080 if vert else 810, Hc)
    return flush()


if __name__ == '__main__':
    run_cli(render_t, cover, TOTAL_SECONDS)

"""
使用说明：

1. 自查版式（先看关键帧，不要直接渲染全片）：
   python3 example_scenes.py still ./chk 2 8 18 30 42 50

2. 生成封面（横版首帧 + 1080×1440 竖版）：
   python3 example_scenes.py cover ./chk
   # 从横屏首帧裁出 3:4 封面自查：crop=810:1080:555:0

3. 生成配乐（时长与 TOTAL_SECONDS 一致，章节切换点传进去让转场音效对齐）：
   python3 music_gen_v2.py 34.45 music.wav "3.1,6.2,12.85,17.85,23.15,29.05"
   # 注意用 v2（中频版）。v1 的能量压在 40-165Hz，手机外放听不见。
   # 自检：ffmpeg -i music.wav -af "highpass=f=400,volumedetect" -f null -
   #       mean 低于 -35dB 就等于没声音。

4. 并行渲染全片（按 CPU 核数切片）：
   python3 example_scenes.py frames          # 先看总帧数 N
   for i in 0 1 2 3 4 5 6 7; do
     f0=$((i*N/8)); f1=$(((i+1)*N/8)); [ $f1 -gt $N ] && f1=$N
     python3 example_scenes.py seg $f0 $f1 seg/s$i.mp4 &
   done
   wait

5. 拼接分段 + 混入配乐：
   printf "file 'seg/s%d.mp4'\n" 0 1 2 3 4 5 6 7 > list.txt
   ffmpeg -y -f concat -safe 0 -i list.txt -i music.wav \
     -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart 成片.mp4

6. 质检：
   ffprobe -v error -show_entries stream=width,height,r_frame_rate,bit_rate \
     -show_entries format=duration -of compact 成片.mp4
   # 另需抽查"每章结束前 1.5 秒"的帧，确认最后一句话确实显示完整了。
   # 注意别抽章节切换点那一帧——那正好是淡入起点，画面是空的，会误判成"内容没渲染出来"。
"""
