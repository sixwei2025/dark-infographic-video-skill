# 场景部件食谱

每章拆解页基本是这些部件的排列组合：左边放一个"数据可视化部件"，右边放文字（或反过来），
部件负责视觉冲击，文字负责讲清楚逻辑。下面每个部件给出最小可用代码骨架，照抄改参数即可，
都假设已经 `from engine import *`。

数据类型 → 部件选择参考：
- **占比/进度类**（专注度、完成率）→ 圆环仪表
- **趋势/对比类**（A组 vs B组随时间变化）→ 双曲线交叉图
- **离散对比类**（7天数据、5类情绪强度）→ 柱状图
- **神经/概率/成瘾感类**（抽象的"大脑在发生什么"）→ 点阵脑区
- **决策/犹豫类**（想停却停不下来）→ 漂移游走线
- **时间流逝类**（深夜时钟跳动）→ 日历/计时器
- **多项并列预告类**（6个危害速览）→ 网格宫格
- **揭示/转场类** → 标题揭示 + 扫光分隔线

---

## 1. 圆环仪表（占比/进度）

```python
def gauge(u, cx, cy, R, target_val, max_val, t0, dur, label_top, label_bottom):
    """target_val 在 t0 开始、历时 dur 秒 滚动画到最终值；max_val 决定圆环最大对应 270度弧"""
    # 刻度环
    for k in range(72):
        ang = math.radians(-90 + k * 5); major = (k % 12 == 0)
        r0 = R + (6 if major else 16); r1 = R + 34
        FR.d.line([(cx + r0*math.cos(ang), cy + r0*math.sin(ang)),
                   (cx + r1*math.cos(ang), cy + r1*math.sin(ang))],
                  fill=C(GRY if major else DIM, 0.85 if major else 0.65), width=4 if major else 2)
    ring(cx, cy, R - 44, DIM, 0.4, 2)
    v = target_val * eio(ramp(u, t0, dur))
    deg = v / max_val * 270  # 270度留出一个缺口，不画满整圈
    if deg > 0.5:
        bb = [cx-R+10, cy-R+10, cx+R-10, cy+R-10]
        FR.d.arc([bb[0]-12, bb[1]-12, bb[2]+12, bb[3]+12], -135, -135+deg, fill=C(ORG, 0.14), width=56)
        FR.d.arc(bb, -135, -135+deg, fill=C(ORG, 0.95), width=28)
        ea = math.radians(-135 + deg)
        dot(cx + (R-24)*math.cos(ea), cy + (R-24)*math.sin(ea), 9, WHT, 0.95)
    FR.d.ellipse([cx-84, cy-84, cx+84, cy+84], fill=C((22,20,22),1), outline=C(ORG,0.85), width=4)
    T([S(label_top, WHT, 'numd', 30)], cx, cy+6, 'c')
    T([S(label_bottom, GRY, 'reg', 22)], cx, cy+40, 'c')
```

## 2. 点阵脑区（神经/概率意象）

```python
# 模块顶部预先生成一次脑形轮廓点阵（避免每帧重新计算）
_rng = np.random.default_rng(3); BRAIN_PTS = []
for gy in range(-11, 12):
    for gx in range(-16, 17):
        x, y = gx/16.0, gy/11.0
        if x*x + (y/0.95)**2 < 1:   # 椭圆轮廓，可加缺口模拟脑回
            BRAIN_PTS.append((cx0 + gx*23 + _rng.uniform(-3,3), cy0 + gy*23 + _rng.uniform(-3,3), _rng.uniform(0,1)))

def brain(u, t0, activate_ratio_fn):
    """activate_ratio_fn(u) 返回 0~1 的"激活比例"，比如从 0.06 随 u 增长到 0.3"""
    tick = int(u * 8)
    ratio = activate_ratio_fn(u)
    for i, (x, y, r) in enumerate(BRAIN_PTS):
        h = ((i * 2654435761 + tick * 40503) % 1000) / 1000.0
        if h < ratio:
            dot(x, y, 4.6, ORG, 0.95)  # 高亮点代表"被激活的神经元"
        else:
            dot(x, y, 2.8, GRY, 0.4)
```

## 3. 双曲线交叉图（对比/负相关）

```python
def cross_curves(u, x0, x1, y0, y1, t0, dur, label_a, label_b):
    """两条S形曲线一升一降在中点交叉，表达"A升B降"的负相关关系"""
    pp = eio(ramp(u, t0, dur)); n = max(2, int(80 * pp))
    curve_up, curve_down = [], []
    for k in range(n):
        s = k / 79.0; sg = 1 / (1 + math.exp(-(s - 0.5) * 9))
        xx = x0 + (x1 - x0) * s
        curve_up.append((xx, y1 - 30 - (y1-y0-70) * sg))
        curve_down.append((xx, y0 + 30 + (y1-y0-70) * sg))
    if pp > 0:
        gline(curve_up, ORG, 1.0, 6)
        FR.d.line(curve_down, fill=C(WHT, 0.85), width=4)
    T([S(label_a, ORG, 'semi', 36)], x1+20, y0+50)
    T([S(label_b, WHT, 'semi', 36)], x1+20, y1-20)
```

## 4. 柱状图（离散对比，如一周累计）

```python
def bar_chart(u, x0, y_base, bar_w, gap, items, t0, stagger=0.45):
    """items: [(标签, 数值, 是否高亮), ...]；每根柱子依次延迟出现，用 eio 做生长动画"""
    for i, (label, val, hot) in enumerate(items):
        x = x0 + i * (bar_w + gap)
        al = ramp(u, t0 + stagger*i, 0.3); g = eio(ramp(u, t0 + stagger*i, 0.8))
        hgt = val * g   # val 已按最大值归一化到像素高度
        if hgt > 1:
            col = ORG if hot else (0.45 + 0.1*i,)  # 高亮柱用强调色描边，普通柱用半透明填充
            if hot:
                FR.d.rectangle([x, y_base, x+bar_w, y_base+hgt], outline=C(ORG, 0.95*al), width=4, fill=C(ORG, 0.14*al))
            else:
                FR.d.rectangle([x, y_base, x+bar_w, y_base+hgt], fill=C(ORG, 0.5*al))
        T([S(label, GRY, 'semi', 30)], x+bar_w/2, y_base-22, 'c', a=al)
```

## 5. 漂移游走线（决策犹豫意象）

```python
def _walk(seed, y0, drift, sig, lo, hi, n=360, x0=110, step=2.1):
    """随机游走轨迹，drift 控制整体趋势方向，sig 控制抖动幅度，触边或到达终点就停止"""
    rng = np.random.default_rng(seed); pts = []; nz = 0
    for i in range(n):
        x = x0 + i * step; nz = nz*0.85 + rng.normal()*sig
        y = y0 + drift*i + nz*9; pts.append((x, y))
        if y <= lo or y >= hi: break
    return pts
# 预生成两条轨迹：对照组(更难越界=更谨慎)，实验组(更快越界=冲动决策)
WALK_CONTROL = _walk(5, 540, -0.62, 1.4, 340, 740)
WALK_IMPULSE = _walk(9, 540, 1.15, 1.6, 440, 640)

def drift_diagram(u, t0):
    pg = eio(ramp(u, t0, 5.0)); po = eio(ramp(u, t0, 1.8))
    ng, no = max(2,int(len(WALK_CONTROL)*pg)), max(2,int(len(WALK_IMPULSE)*po))
    if pg > 0: FR.d.line(WALK_CONTROL[:ng], fill=C(GRY, 0.9), width=4)
    if po > 0: gline(WALK_IMPULSE[:no], ORG, 1.0, 4)
```

## 6. 日历/计时器闪烁（时间流逝意象，常用于开场钩子）

```python
def clock_hook(u, cx, cy, time_points):
    """time_points: [(触发时刻u, 显示文字, 附加计数), ...]，数字切换瞬间做一个"闪一下"效果"""
    cur = time_points[0]
    for tp in time_points:
        if u >= tp[0]: cur = tp
    flick = 0.45 if (cur[0] > 0 and u - cur[0] < 0.12) else 1.0
    T([S(cur[1], WHT, 'numul', 330)], cx, cy, 'c', a=flick)
```

## 7. 网格宫格（多项并列预告，开场常用）

```python
def grid_preview(u, items, t0, stagger=0.42, cols_x=(330,790,1250), rows_y=(520,690)):
    """items: [(前半句, 后半句强调词), ...] 最多 6 项，2行3列排布"""
    for i, (a_text, b_text) in enumerate(items):
        x = cols_x[i % 3]; y = rows_y[i // 3]
        al, dy = ap(u, t0 + stagger*i, 0.5)
        if al <= 0: continue
        FR.d.line([(x-30, y-62+dy), (x-30, y+12+dy)], fill=C(ORG, al), width=6)  # 左侧强调竖线
        T([S('%02d' % (i+1), ORG, 'numd', 22)], x-18, y-70+dy, a=al*0.85)
        T([S(a_text, WHT, 'med', 62), S(b_text, ORG, 'semi', 62)], x, y+dy, a=al)
```

## 8. 标题揭示 + 扫光分隔线（转场必备）

```python
def reveal_transition(u, dur=1.0):
    """一条线从中心向两侧展开，到顶点时触发一次全屏闪色，紧接着切到标题页"""
    p = eio(ramp(u, 0.0, dur*0.85)); L = 820*p
    gline([(960-L, 540), (960+L, 540)], ORG, 1.0, 6)
    if u > dur*0.8: FR.post.append(('fill', ORG, 0.85 * ramp(u, dur*0.8, dur*0.2)))

def title_reveal(u, big_word_segs, sub_segs):
    FR.post.append(('fill', ORG, 0.85 * (1 - ramp(u, 0, 0.5))))  # 闪色褪去
    T(big_word_segs, 960, 600, 'c', glow=30, ga=0.55)
    L = 560 * eo(ramp(u, 0.6, 0.9))
    if L > 1:
        FR.d.line([(960-L, 690), (960+L, 690)], fill=C(ORG, 0.8), width=3)
    T(sub_segs, 960, 810, 'c', p=ramp(u, 1.3, 1.3))
```

## 9. 结尾卡（升华句 + 行动建议）

```python
def outro_card(u, tips, closing_segs, sub_segs):
    """tips: [(编号, 建议文字), ...] 通常3条，先于升华句出现"""
    xs = [380, 960, 1540]
    for i, (n, tx) in enumerate(tips):
        al, dy = ap(u, 0.5 + 0.5*i)
        T([S(n+'  ', ORG, 'numd', 38), S(tx, WHT, 'reg', 38)], xs[i], 250+dy, 'c', a=al)
    T(closing_segs, 960, 820, 'c', p=ramp(u, 5.0, 1.1), glow=14, ga=0.35)
    a, dy = ap(u, 7.5); T(sub_segs, 960, 920+dy, 'c', a=a)
```

---

## 组装提醒

1. 所有坐标都基于 1920×1080；竖屏项目把横向坐标按 `1080/1920` 等比缩放，纵向坐标按 `1920/1080` 等比放大即可，不要整体重新设计布局。
2. 每个部件函数的 `u` 参数都是"该场景开始后经过的秒数"，不是视频全局时间——在 `SCENES` 列表里组装时，引擎会自动做 `t - s0` 的转换（参考 `example_scenes.py` 的 `render_t`）。
3. 不要在一个章节里塞超过 2 个部件，视觉会变乱。一个主部件 + 一组文字就足够讲清楚一个数据点。
