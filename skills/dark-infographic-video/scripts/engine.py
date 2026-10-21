"""
engine.py —— 暗黑数据可视化短视频 · 通用渲染引擎

这个文件是「不用改」的工具箱：字体富文本渲染、发光效果、缓动函数、背景光晕、
章节进度条(HUD)、数据来源角标、封面模板、以及命令行渲染入口(run_cli)。

你的选题内容（场景函数、章节数据、具体文案）写在另一个文件里（参照 example_scenes.py），
在那个文件顶部 `from engine import *` 之后即可使用这里的所有工具函数。

字体会自动探测（DARK_FONT 环境变量 → font_finder.py → 常见路径），
macOS / Linux / Windows 都不用手动改；找不到时会报错并提示该装什么字体。
"""
import sys, os, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ============== 画布与节奏基础参数 ==============
W, H, FPS = 1920, 1080, 30     # 默认横屏 1080P 30fps；竖屏抖音可改成 1080, 1920
COVER_FRAMES = 3                # 封面占用的帧数，3帧@30fps ≈ 0.1秒，抖音默认取首帧做封面

# ============== 字体（自动探测，一般不用改） ==============
# 查找顺序：
#   1. 环境变量 DARK_FONT（中文字体路径，可写成 "路径" 或 "路径#ttc序号"）；
#      可选 DARK_NUM_FONT 指定大号数字用的西文字体
#   2. font_finder.py 的候选表 + fc-list 探测
#   3. 常见路径：macOS PingFang/Hiragino、Linux Noto Sans CJK/思源/文泉驿、Windows 微软雅黑
# 都找不到会直接报错，并提示该装什么字体。
_PINGFANG_IDX = {'reg': 3, 'med': 7, 'semi': 11, 'light': 15, 'thin': 19}
_ZH_COMMON = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/*/AssetData/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/google-noto-cjk/NotoSansCJKsc-Regular.otf",
    "/usr/share/fonts/opentype/source-han-sans/SourceHanSansSC-Regular.otf",
    "/usr/share/fonts/adobe-source-han-sans/SourceHanSansSC-Regular.otf",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "C:\\Windows\\Fonts\\msyh.ttc",
    "C:\\Windows\\Fonts\\msyh.ttf",
    "C:\\Windows\\Fonts\\simhei.ttf",
]
_NUM_COMMON = [
    "/System/Library/Fonts/Avenir Next.ttc",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf",
]


def _font_ok(path, index=0, text=None):
    try:
        f = ImageFont.truetype(path, 40, index=index)
        if text:  # 确认真能画中文，避免拿到只有西文字形的字体
            m = f.getmask(text)
            if m.getbbox() is None:
                return False
        return True
    except Exception:
        return False


def _expand(paths):
    import glob
    out = []
    for p in paths:
        out += sorted(glob.glob(p)) if '*' in p else ([p] if os.path.exists(p) else [])
    return out


def _split_idx(v):
    if '#' in v:
        p, i = v.rsplit('#', 1)
        if i.isdigit():
            return p, int(i)
    return v, 0


def _find_fonts():
    zh = None
    env = os.environ.get('DARK_FONT', '').strip()
    if env:
        p, i = _split_idx(os.path.expanduser(env))
        if not _font_ok(p, i, '中文'):
            raise RuntimeError(f'DARK_FONT={env} 打不开或不含中文字形，请检查路径（ttc 可写成 路径#序号）')
        zh = (p, i)
    if zh is None:
        cands = []
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import font_finder as _ff
            cands += _expand(_ff.CANDIDATES_ZH)
            for l in _ff.try_fc_list():
                fp = l.split(':')[0].strip()
                if fp and os.path.exists(fp):
                    cands.append(fp)
        except Exception:
            pass
        cands += _expand(_ZH_COMMON)
        seen = set()
        for p in cands:
            if p in seen:
                continue
            seen.add(p)
            if 'Serif' in p or 'Mono' in p:   # 优先无衬线黑体
                continue
            if _font_ok(p, 0, '中文'):
                zh = (p, 0)
                break
    if zh is None:
        raise RuntimeError(
            '找不到可用的中文字体。请安装任意一种后重试：\n'
            '  Ubuntu/Debian: sudo apt install fonts-noto-cjk   （或 fonts-wqy-microhei）\n'
            '  CentOS/Fedora: sudo dnf install google-noto-sans-cjk-fonts\n'
            '  macOS 自带 PingFang；Windows 自带微软雅黑\n'
            '或用环境变量指定：export DARK_FONT=/path/to/font.ttc')
    num = None
    envn = os.environ.get('DARK_NUM_FONT', '').strip()
    if envn:
        p, i = _split_idx(os.path.expanduser(envn))
        if _font_ok(p, i):
            num = (p, i)
    if num is None:
        for p in _expand(_NUM_COMMON):
            if _font_ok(p, 0):
                num = (p, 0)
                break
    return zh, num


(_ZHP, _ZHI), _NUM = _find_fonts()
PF = _ZHP
if 'PingFang' in PF and not os.environ.get('DARK_FONT'):
    _zh = {k: (PF, v) for k, v in _PINGFANG_IDX.items()}
else:
    _zh = {k: (PF, _ZHI) for k in _PINGFANG_IDX}
if _NUM and 'Avenir Next' in _NUM[0]:
    _HN = "/System/Library/Fonts/HelveticaNeue.ttc"
    _hn = os.path.exists(_HN)
    _num = {'num': (_NUM[0], 0), 'numd': (_NUM[0], 2), 'numm': (_NUM[0], 5),
            'numl': (_HN, 7) if _hn else (_NUM[0], 0), 'numul': (_HN, 5) if _hn else (_NUM[0], 0)}
else:
    _n = _NUM or (PF, _ZHI)
    _num = {k: _n for k in ('num', 'numd', 'numm', 'numl', 'numul')}
# 字重映射：key -> (字体文件路径, ttc内的index)
FONTS = {**_zh, **_num}

# ============== 配色（这是唯一需要改就能换品牌色的地方） ==============
WHT = (242, 238, 230)   # 主文字白
ORG = (255, 90, 40)     # 强调色/品牌色，默认暗黑橙红；改成品牌红/蓝只需改这一行
GRY = (128, 131, 138)   # 次要文字灰
DIM = (78, 81, 88)      # 分割线/弱化元素
DARK = (11, 12, 15)     # 背景底色

# ============== 缓动与排版工具 ==============
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ramp(u, t0, d): return clamp((u - t0) / d) if d > 0 else (1.0 if u >= t0 else 0.0)
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3       # ease-out，文字淡入常用
def eio(x): x = clamp(x); return 3 * x * x - 2 * x * x * x  # ease-in-out，数字滚动/线条生长常用
def ap(u, t0, d=0.6):
    """标准"淡入+向上浮入"动效：返回 (透明度, y方向偏移量)"""
    p = eo(ramp(u, t0, d)); return p, (1 - p) * 18
def S(t, c=WHT, fk='semi', s=30): return (t, c, fk, s)   # 一段富文本：(文字, 颜色, 字重key, 字号)

_fc = {}
def F(k, s):
    key = (k, s)
    if key not in _fc:
        p, i = FONTS[k]; _fc[key] = ImageFont.truetype(p, s, index=i)
    return _fc[key]

_sc = {}
def rich(segs, glow=0):
    """把多段不同颜色/字重的文字渲染成一张位图（支持发光），并缓存复用。"""
    key = (tuple(segs), glow)
    if key in _sc: return _sc[key]
    segs = [s for s in segs if s[0]]
    if not segs: _sc[key] = None; return None
    fonts = [F(s[2], s[3]) for s in segs]
    asc = max(f.getmetrics()[0] for f in fonts); desc = max(f.getmetrics()[1] for f in fonts)
    ws = [f.getlength(s[0]) for f, s in zip(fonts, segs)]
    pad = int(glow * 3) + 6
    w = int(math.ceil(sum(ws)))
    img = Image.new('RGBA', (w + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    x = pad
    for f, s, wi in zip(fonts, segs, ws):
        d.text((x, pad + asc), s[0], font=f, fill=tuple(s[1]) + (255,), anchor='ls'); x += wi
    arr = np.array(img); g = None
    if glow:
        gi = np.array(img.filter(ImageFilter.GaussianBlur(glow))).astype(np.float32)
        gi[..., 3] = np.clip(gi[..., 3] * 1.8, 0, 255); g = gi.astype(np.uint8)
    r = dict(arr=arr, g=g, pad=pad, asc=asc, w=w)
    _sc[key] = r; return r

def TW(segs): r = rich(segs); return r['w'] if r else 0  # 量测富文本整体宽度，用于居中对齐分隔线等

def trunc(segs, p):
    """按比例 p (0~1) 截断富文本——实现打字机逐字出现效果。"""
    N = sum(len(s[0]) for s in segs); n = int(math.floor(p * N + 1e-6)); out = []
    for s in segs:
        tk = s[0][:max(0, n)]; n -= len(tk)
        if tk: out.append((tk,) + tuple(s[1:]))
    return out

CTX = [1.0]   # 全局透明度乘子栈，场景整体淡入淡出时临时调低
class Frame:
    def __init__(self, bgimg=None):
        self.reset(bgimg if bgimg is not None else Image.new('RGBA', (W, H), DARK + (255,)))
    def reset(self, bgimg):
        self.im = bgimg.copy(); self.ov = Image.new('RGBA', self.im.size, (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.ov); self.q = []; self.post = []
FR = Frame()  # 全局唯一的帧对象，整个渲染过程中只有这一个实例，每帧用 begin_frame() 原地重置它的内容

def begin_frame(glows, size=None):
    """
    每帧渲染的第一步，必须调用这个函数来开始新的一帧，不要自己写 `FR = Frame(BG(glows))`。

    原因：你的场景文件用 `from engine import *` 导入了 engine 的所有名字（包括 FR）。
    Python 的 `import *` 只是把"当前值"复制一份引用到你的模块里，如果谁后续把 engine.FR
    重新指向一个新对象（`global FR; FR = Frame(...)`），你的场景文件里那份拷贝的 FR 名字
    还是指向旧对象，根本看不到新画布——这是 Python 模块间"重新绑定全局变量"的经典陷阱。
    所以 FR 从始至终都是同一个对象，每帧只是调用 FR.reset(...) 原地清空重画，不重新赋值。
    """
    FR.reset(BG(glows, size))
    return FR

def C(c, a): return tuple(c) + (int(255 * clamp(a * CTX[0])),)

def blit(im, arr, x, y, a):
    if a <= 0.003: return
    x = int(round(x)); y = int(round(y)); h, w = arr.shape[:2]; IW, IH = im.size
    x0 = max(0, x); y0 = max(0, y); x1 = min(IW, x + w); y1 = min(IH, y + h)
    if x1 <= x0 or y1 <= y0: return
    sub = arr[y0 - y:y1 - y, x0 - x:x1 - x]
    if a < 0.999:
        sub = sub.copy(); sub[..., 3] = (sub[..., 3].astype(np.float32) * a).astype(np.uint8)
    im.alpha_composite(Image.fromarray(sub), dest=(x0, y0))

def T(segs, x, y, anchor='l', a=1.0, glow=0, ga=0.75, p=1.0):
    """绘制一段富文本。anchor: 'l'左对齐/'c'居中/'r'右对齐。p<1 时做打字机截断。返回整体宽度（像素）。"""
    a *= CTX[0]
    full = rich(segs, glow)
    if full is None: return 0
    w = full['w']
    if a <= 0.004 or p <= 0: return w
    x0 = x if anchor == 'l' else (x - w / 2 if anchor == 'c' else x - w)
    r = full
    if p < 1:
        s2 = trunc(segs, p)
        if not s2: return w
        r = rich(s2, glow)
    FR.q.append((r, x0 - r['pad'], y - r['asc'] - r['pad'], a, ga if glow else 0))
    return w

def flush():
    FR.im.alpha_composite(FR.ov)
    for r, x, y, a, ga in FR.q:
        if ga and r['g'] is not None: blit(FR.im, r['g'], x, y, a * ga)
        blit(FR.im, r['arr'], x, y, a)
    for kind, c, a in FR.post:
        if a > 0.003:
            FR.im.alpha_composite(Image.new('RGBA', FR.im.size, tuple(c) + (int(255 * clamp(a)),)))
    return FR.im

_bgc = {}
def BG(glows, size=None):
    """生成带若干光晕圆斑的深色背景（带轻微暗角与噪点）。glows: [(cx,cy,半径,强度,颜色), ...]"""
    size = size or (W, H)
    key = (size,) + tuple((int(cx), int(cy), int(r), round(i, 2), c) for cx, cy, r, i, c in glows)
    if key in _bgc: return _bgc[key]
    Wd, Hd = size; w, h = Wd // 4, Hd // 4
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    img = np.zeros((h, w, 3), np.float32) + np.array(DARK, np.float32)
    for cx, cy, r, i, c in glows:
        dd = ((xx - cx / 4) ** 2 + (yy - cy / 4) ** 2) / ((r / 4) ** 2)
        img += np.exp(-dd)[..., None] * np.array(c, np.float32) * i
    rn = ((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2
    img *= (1 - 0.3 * clamp_arr(rn))[..., None]
    big = np.array(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((Wd, Hd), Image.BICUBIC)).astype(np.int16)
    rng = np.random.default_rng(1)
    big += rng.integers(-2, 3, size=big.shape, dtype=np.int16)
    im = Image.fromarray(np.clip(big, 0, 255).astype(np.uint8)).convert('RGBA')
    _bgc[key] = im; return im

def clamp_arr(a): return np.clip(a, 0, 1.4)

# ============== 基础绘图部件 ==============
def gline(pts, c, a, w=2):
    """带柔光的曲线/折线（实际画3层：宽光晕+中间层+实线），用于趋势线、漂移游走等。"""
    d = FR.d
    d.line(pts, fill=C(c, a * 0.12), width=w * 6, joint='curve')
    d.line(pts, fill=C(c, a * 0.3), width=w * 2 + 2, joint='curve')
    d.line(pts, fill=C(c, a), width=w, joint='curve')

def dline(x0, y, x1, c, a, dash=8, gap=7, w=1):
    """虚线，用于坐标轴/参考线。"""
    x = x0
    while x < x1:
        FR.d.line([(x, y), (min(x + dash, x1), y)], fill=C(c, a), width=w); x += dash + gap

def dot(x, y, r, c, a): FR.d.ellipse([x - r, y - r, x + r, y + r], fill=C(c, a))
def ring(x, y, r, c, a, w=1): FR.d.ellipse([x - r, y - r, x + r, y + r], outline=C(c, a), width=w)

# ============== 漂浮粒子背景 ==============
def make_particles(seed=7, n=80):
    """生成一套固定的粒子初始状态（位置/速度/相位），返回给 particles() 复用。"""
    rng = np.random.default_rng(seed)
    px = rng.uniform(0, W, n); py = rng.uniform(0, H, n)
    pvx = rng.uniform(-6, 6, n); pvy = rng.uniform(-18, -4, n)
    ps = rng.uniform(1.4, 3.6, n); pph = rng.uniform(0, 6.28, n)
    return dict(n=n, px=px, py=py, pvx=pvx, pvy=pvy, ps=ps, pph=pph)

_DEFAULT_PARTICLES = None
def particles(t, a=1.0, state=None):
    """绘制缓慢漂浮的橙色光点。state 省略则用全局默认一套（整条片子共用一套更省心）。"""
    global _DEFAULT_PARTICLES
    if state is None:
        if _DEFAULT_PARTICLES is None: _DEFAULT_PARTICLES = make_particles()
        state = _DEFAULT_PARTICLES
    for i in range(state['n']):
        x = (state['px'][i] + state['pvx'][i] * t) % W
        y = (state['py'][i] + state['pvy'][i] * t) % H
        al = a * (0.10 + 0.32 * (0.5 + 0.5 * math.sin(state['pph'][i] + 1.1 * t)))
        dot(x, y, state['ps'][i], ORG, al)

# ============== 章节进度条 HUD + 数据来源角标 ==============
def hud(t, chap, cspan, fade_in=(30, 0.6), fade_out=None):
    """
    顶部"编号+章节名"小标题 + 底部7等分章节进度条，贯穿整条片子的"正文阶段"。
    chap: [(章节名, 副标题), ...]
    cspan: [(开始秒, 结束秒), ...] 与 chap 一一对应
    fade_in: (出现时间, 淡入时长)；fade_out: (消失时间, 淡出时长)，不传则跟最后一章结束同步淡出
    """
    idx = None
    for i, (s, e) in enumerate(cspan):
        if s <= t < e: idx = i
    if idx is None: return
    fo_t, fo_d = fade_out if fade_out else (cspan[-1][1] - 0.6, 0.6)
    a = ramp(t, fade_in[0], fade_in[1]) * (1 - ramp(t, fo_t, fo_d))
    old = CTX[0]; CTX[0] = a
    s, e = cspan[idx]; n = len(chap)
    lab_a = ramp(t, s, 0.5) * (1 - ramp(t, e - 0.4, 0.4)) if idx < n - 1 else ramp(t, s, 0.5)
    T([S('%02d' % (idx + 1), ORG, 'numd', 34)], 60, 92, a=lab_a)
    FR.d.line([(124, 80), (210, 80)], fill=C(GRY, 0.6 * lab_a), width=2)
    T([S(chap[idx][0], WHT, 'semi', 32), S('  ·  ' + chap[idx][1], GRY, 'reg', 28)], 228, 92, a=lab_a)
    y = 1022; x0, x1 = 60, 1860; seg = (x1 - x0) / n
    FR.d.line([(x0, y), (x1, y)], fill=C(DIM, 0.6), width=2)
    for i in range(n):
        xs = x0 + i * seg; on = (i == idx)
        T([S('%02d' % (i + 1), ORG if on else DIM, 'numd', 22), S('  ' + chap[i][0], WHT if on else DIM, 'semi' if on else 'reg', 22)], xs, y + 40)
        if i < idx: FR.d.line([(xs, y), (xs + seg - 10, y)], fill=C(ORG, 0.35), width=4)
        if on:
            pr = clamp((t - s) / (e - s))
            FR.d.line([(xs, y), (xs + (seg - 10) * pr, y)], fill=C(ORG, 0.95), width=4)
    CTX[0] = old

def source(txt, a=1.0, y=978, x=60):
    """左下角数据来源一行小字。每个数据章节都应该调用这个——这是这类视频可信度的关键。"""
    T([S(txt, (105, 108, 116), 'reg', 22)], x, y, a=a)

# ============== 封面模板 ==============
def cover_template(tag, title_segs, sub_segs, keywords, stats=None, size=None):
    """
    通用封面生成器。
    tag: 顶部胶囊标签文字，如 "7 个系统 · 深度拆解"
    title_segs: 大标题的 S(...) 列表，如 [S('短', WHT,'semi',ts), S('视频', ORG,'semi',ts)]
    sub_segs: 副标题 S(...) 列表
    keywords: 底部一行小字，如 "注意力 · 记忆 · 睡眠 · 情绪 · 自控"
    stats: 竖版封面底部可选显示 2 个数据项 [(数值, 单位, 说明), (数值, 单位, 说明)]；横版忽略
    size: (W,H)，默认等于全局 W,H；传 (1080,1440) 做抖音竖版封面
    """
    Wc, Hc = size or (W, H); cx = Wc // 2
    begin_frame([(cx, Hc * 0.52, 640, 0.26, ORG), (cx, Hc, 520, 0.07, WHT)], (Wc, Hc))
    CTX[0] = 1.0
    rng = np.random.default_rng(21)
    for i in range(90):
        dot(rng.uniform(0, Wc), rng.uniform(0, Hc), rng.uniform(1.2, 3.4), ORG, rng.uniform(0.15, 0.5))
    ty, ts_scale = (300, 1.0) if Wc > Hc else (420, 1.0)
    sy = 600 if Wc > Hc else 770
    ly = 660 if Wc > Hc else 830
    smy = 880 if Wc > Hc else 1010
    tw_ = TW([S(tag, ORG, 'semi', 36)])
    FR.d.rounded_rectangle([cx - tw_ / 2 - 30, ty - 50, cx + tw_ / 2 + 30, ty + 20], 34, outline=C(ORG, 0.95), width=3)
    T([S(tag, ORG, 'semi', 36)], cx, ty - 2, 'c')
    title_w = T(title_segs, cx, sy, 'c', glow=26, ga=0.6)
    FR.d.line([(cx - 340, ly), (cx + 340, ly)], fill=C(ORG, 0.2), width=8)
    FR.d.line([(cx - 340, ly), (cx + 340, ly)], fill=C(ORG, 0.9), width=3)
    sub_h = T(sub_segs, cx, ly + 120, 'c', glow=6, ga=0.3)
    T([S(keywords, GRY, 'reg', 36)], cx, smy, 'c')
    if Wc < Hc and stats:
        for j, (big, unit, lab) in enumerate(stats[:2]):
            x = cx + (j * 2 - 1) * 230
            T([S(big, ORG if j == 0 else WHT, 'num', 104), S(unit, GRY, 'semi', 28)], x, 1230, 'c')
            T([S(lab, GRY, 'reg', 24)], x, 1280, 'c')
        FR.d.line([(cx, 1150), (cx, 1290)], fill=C(DIM, 0.8), width=1)
    return flush()

# ============== 时间轴合成（含场景交叉淡化） ==============
def render_crossfade(scenes, t):
    """
    按 SCENES 时间轴合成一帧，**场景之间做真正的交叉淡化**，返回 PIL Image（不含 HUD）。

    实现要点（两个坑，都是实测踩出来的）：

    1. **淡出必须延后到切换点之后**（从 s1 才开始，而不是 s1-fo）。
       否则就是"上一个场景先淡到黑、下一个场景再从黑淡起"，中间闪一下全黑。
       延后之后，前一个的淡出与后一个的淡入在 [s1, s1+fo] 区间重叠 → 真正的 crossfade。
       （最后一个场景例外：它的淡出要在片尾之内完成，仍从 s1-fo 开始。）

    2. **不能用 alpha_composite 叠加两层**。alpha_composite 是 "over" 语义，
       两层各 50% 时实际结果是 0.5*cur + 0.25*prev，前一个场景会被压得过淡、
       看起来就像闪黑。正确做法是按权重对 RGB 做加权求和：result = prev*(1-w) + cur*w。

    要求：fi 与 fo 取相同值（这样两层权重之和恒为 1，亮度不会忽明忽暗）。
    """
    idx = 0
    for i, s in enumerate(scenes):
        if s[0] <= t < s[1]:
            idx = i
    acc = None
    for k in (idx - 1, idx):
        if k < 0 or k >= len(scenes):
            continue
        s0, s1, fn, glows, fi, fo = scenes[k]
        if t < s0:
            continue
        if k < idx:
            # 上一个场景：随当前场景的淡入而退场（重叠区间内两者权重和为 1）
            w = 1.0 - (ramp(t, s1, fo) if fo > 0 else 0.0)
        else:
            w = ramp(t, s0, fi) if fi > 0 else 1.0
            # 若它同时是全片最后一个场景，还要在片尾之内淡出
            if k == len(scenes) - 1 and fo > 0:
                w *= 1.0 - ramp(t, s1 - fo, fo)
        if w <= 0.004:
            continue
        begin_frame(glows)
        CTX[0] = 1.0            # 场景内部的元素透明度由各自的 ap()/ramp() 控制
        particles(t)
        fn(t - s0)              # t - s0 可能超过场景时长，但动画都已到终态，无副作用
        arr = np.array(flush())[:, :, :3].astype(np.float32)
        acc = arr * w if acc is None else acc + arr * w
    if acc is None:
        return Image.new('RGBA', (W, H), DARK + (255,))
    return Image.fromarray(np.clip(acc, 0, 255).astype(np.uint8)).convert('RGBA')


def overlay_layer(draw_fn):
    """在透明画布上画常驻元素（HUD 等），返回可直接叠加到成帧上的图层。"""
    FR.reset(Image.new('RGBA', (W, H), (0, 0, 0, 0)))
    CTX[0] = 1.0
    draw_fn()
    return flush()


# ============== 命令行渲染入口 ==============
def run_cli(render_t, cover_fn, total_seconds):
    """
    在你的场景文件（example_scenes.py）底部这样调用：
        if __name__ == '__main__':
            run_cli(render_t, cover, TOTAL_SECONDS)
    支持三种子命令：
        python3 your_scenes.py still <输出目录> <时间点1> <时间点2> ...   # 渲染静帧自查版式
        python3 your_scenes.py cover <输出目录>                          # 生成横版+竖版封面PNG
        python3 your_scenes.py seg <起始帧> <结束帧> <输出mp4>            # 渲染一段(配合并行渲染)
    """
    if len(sys.argv) < 2:
        print(__doc__ or run_cli.__doc__); sys.exit(1)
    mode = sys.argv[1]
    total_frames = COVER_FRAMES + int(round(total_seconds * FPS))
    if mode == 'still':
        outdir = sys.argv[2]
        os.makedirs(outdir, exist_ok=True)
        for ts in sys.argv[3:]:
            render_t(float(ts)).convert('RGB').save(os.path.join(outdir, 'still_%s.jpg' % ts), quality=90)
            print('saved still_%s.jpg' % ts)
    elif mode == 'cover':
        outdir = sys.argv[2]
        os.makedirs(outdir, exist_ok=True)
        cover_fn().convert('RGB').save(os.path.join(outdir, 'cover_16x9.png'))
        cover_fn((1080, 1440)).convert('RGB').save(os.path.join(outdir, 'cover_3x4.png'))
        print('saved cover_16x9.png, cover_3x4.png')
    elif mode == 'seg':
        f0, f1, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        cov = None
        p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                               '-s', '%dx%d' % (W, H), '-r', str(FPS), '-i', '-',
                               '-c:v', 'libx264', '-preset', 'slow', '-tune', 'animation', '-crf', '12',
                               '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-g', '60', out], stdin=subprocess.PIPE)
        for f in range(f0, f1):
            if f < COVER_FRAMES:
                if cov is None: cov = cover_fn().convert('RGB')
                img = cov
            else:
                img = render_t((f - COVER_FRAMES) / FPS).convert('RGB')
            p.stdin.write(img.tobytes())
        p.stdin.close(); p.wait()
    elif mode == 'frames':
        # 打印总帧数，方便写并行渲染脚本时计算切片
        print(total_frames)
    else:
        print('未知模式:', mode, '——可用: still / cover / seg / frames')
        sys.exit(1)
