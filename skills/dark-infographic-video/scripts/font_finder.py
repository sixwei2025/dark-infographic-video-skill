#!/usr/bin/env python3
"""
跨平台中文字体探测工具。
在 macOS / Linux / Windows 上找出可用的中文字体文件路径，
按「衬线感正文体」「圆体/数字体」两类角色各给一个推荐，
并直接打印出可以粘贴进 engine.py 顶部的 FONTS 常量代码。

用法：
    python3 font_finder.py
"""
import os
import platform
import subprocess
import sys

try:
    from PIL import ImageFont
except ImportError:
    print("❌ 未安装 Pillow，请先运行: pip3 install pillow")
    sys.exit(1)

# 候选路径表：(平台, [可能路径...], 说明)
# 每个条目是 (路径, ttc字重index猜测, 人类可读名称)
CANDIDATES_ZH = [
    # macOS
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/*/AssetData/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    # Linux - Noto Sans CJK（最常见，apt/yum 都能装）
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/google-noto-cjk/NotoSansCJKsc-Regular.otf",
    # Linux - 文泉驿
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",
    # Linux - 思源黑体
    "/usr/share/fonts/opentype/source-han-sans/SourceHanSansSC-Regular.otf",
    # Windows
    "C:\\Windows\\Fonts\\msyh.ttc",
    "C:\\Windows\\Fonts\\simhei.ttf",
    "C:\\Windows\\Fonts\\simsun.ttc",
]

NUMBER_FONT_CANDIDATES = [
    "/System/Library/Fonts/Avenir Next.ttc",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:\\Windows\\Fonts\\arialbd.ttf",
]


def expand_glob(path):
    if "*" not in path:
        return [path] if os.path.exists(path) else []
    import glob
    return glob.glob(path)


def try_fc_list():
    """优先用系统的 fc-list 工具，更准确。"""
    try:
        out = subprocess.run(["fc-list", ":lang=zh"], capture_output=True, text=True, timeout=5)
        lines = [l for l in out.stdout.splitlines() if l.strip()]
        return lines
    except Exception:
        return []


def probe_font(path, index=0):
    try:
        f = ImageFont.truetype(path, 40, index=index)
        name = f.getname()
        return True, name
    except Exception as e:
        return False, str(e)


def main():
    sysname = platform.system()
    print(f"系统: {sysname} {platform.machine()}")
    print("=" * 60)

    found_zh = []
    for cand in CANDIDATES_ZH:
        for p in expand_glob(cand):
            ok, info = probe_font(p)
            if ok:
                found_zh.append((p, info))

    fc_lines = try_fc_list()
    if fc_lines:
        print(f"fc-list 探测到 {len(fc_lines)} 条中文字体记录（节选前 8 条）：")
        for l in fc_lines[:8]:
            print("  " + l)
        # 从 fc-list 结果里再尝试解析出纯路径加入候选
        for l in fc_lines:
            p = l.split(":")[0].strip()
            if p and os.path.exists(p) and p not in [f[0] for f in found_zh]:
                ok, info = probe_font(p)
                if ok:
                    found_zh.append((p, info))
        print()

    found_num = []
    for p in NUMBER_FONT_CANDIDATES:
        if os.path.exists(p):
            ok, info = probe_font(p)
            if ok:
                found_num.append((p, info))

    print("可用中文字体：")
    if not found_zh:
        print("  ❌ 未找到任何中文字体文件！")
    for p, info in found_zh[:6]:
        print(f"  ✅ {p}  -> {info}")

    print("\n可用数字/西文字体（用于大号滚动数字，更有力度）：")
    if not found_num:
        print("  ⚠️ 未找到专用数字字体，将回退使用中文字体渲染数字（效果略逊但不影响使用）")
    for p, info in found_num[:4]:
        print(f"  ✅ {p}  -> {info}")

    print("\n" + "=" * 60)
    if found_zh:
        zh_path = found_zh[0][0]
        num_path = found_num[0][0] if found_num else zh_path
        print("✅ 字体就绪。可直接粘贴进 engine.py 顶部替换 FONTS 定义：\n")
        print(f'PF = "{zh_path}"')
        print(f'NUMF = "{num_path}"')
        print("""
# 如果中文字体文件是单一文件（非 ttc 合集，比如 NotoSansCJK-Regular.ttc 也常是 ttc）
# 需要用 fc-list 确认各字重在 ttc 内的 index，没把握就统一用 index=0（多数 Linux 发行版的
# Noto/WQY 字体文件内只有一个字重，用 index=0 即可，不像 macOS PingFang.ttc 有多个 index）。
FONTS = {
    'reg':  (PF, 0), 'med': (PF, 0), 'semi': (PF, 0), 'light': (PF, 0), 'thin': (PF, 0),
    'num':  (NUMF, 0), 'numd': (NUMF, 0), 'numm': (NUMF, 0), 'numl': (NUMF, 0), 'numul': (NUMF, 0),
}
""")
    else:
        print("❌ 未找到可用中文字体，渲染会出现方块/问号。请先安装字体，例如：")
        if sysname == "Linux":
            print("  Debian/Ubuntu:  apt-get update && apt-get install -y fonts-noto-cjk")
            print("  CentOS/RHEL:    yum install -y google-noto-sans-cjk-ttc-fonts")
            print("  或任选其一:      apt-get install -y fonts-wqy-microhei")
        elif sysname == "Darwin":
            print("  正常不应发生——请检查 /System/Library/Fonts 是否被权限限制")
        elif sysname == "Windows":
            print("  Windows 自带微软雅黑 msyh.ttc，请确认 C:\\Windows\\Fonts 路径可访问")
        print("\n安装完成后重新运行本脚本确认。")
        sys.exit(1)


if __name__ == "__main__":
    main()
