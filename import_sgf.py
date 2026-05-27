"""
该文件为批量处理 SGF 文件
"""

import json
import time
from pathlib import Path
from datetime import datetime
import sgfmill.sgf
from config import SGF_DIR, OUTPUT_DIR

# ===== 配置 =====
# 从环境变量获取配置，如果没有设置则使用默认值

MAX_FILES = 0 # 最大处理文件数量，0 表示无限制
OUTPUT_FILE = OUTPUT_DIR / f"sgf_metadata_{datetime.now():%Y%m%d_%H%M%S}.json" # 输出文件
SKIP_ON_ERROR = True # 出错时跳过该文件

# ===== 函数定义 =====
def extract_metadata(sgf_path: Path) -> dict | None:
    """
    单个 SGF 文件提取关键数据，返回 dict 或者错误时返回 None
    """

    try:
        with open (sgf_path了, "rb") as f:
            game = sgfmill.sgf.Sgf_game.from_bytes(f.read())
        root = game.get_root()  # 获取根节点属性
        winner = root.get ("RE", "Unknown")  # 对局结果 B + 1.5 / W + R 等
        player_b = root.get ("PB", "Unknown")  # 黑棋选手
        player_w = root.get ("PW", "Unknown")  # 白棋选手
        komi = root.get ("KM", "6.5")  # 贴目
        board_size = game.get_size()  # 棋盘大小
        date = root.get ("DT", "")  # 比赛日期
        event = root.get ("EV", "")  # 比赛名称
        result = root.get ("RE", "")  # 

        moves = []
        node = root
        for _ in range(10):
            node = node[0] if len(node) > 0 else None
            if node is None:
                break
            move = node.get_move()
            if move is not None:
                color, (row, col) = move
                moves.append({"color": "B" if color == "b" else "W", "row": row, "col": col})
            else:
                break
        return {
            "file_name": sgf_path.name,
            "file_size_kb": round(sgf_path.stat().st_size / 1024, 1),
            "board_size": board_size,
            "komi": komi,
            "winner": winner,
            "black_player": player_b,
            "white_player": player_w,
            "date": date,
            "event": event,
            "result": result,
            "first_10_moves": moves,
        }
    except Exception as e:
        print(f"  ⚠ 解析失败: {sgf_path.name} → {e}")
        return None
# ===== 主流程 =====
def main():
    print("=" * 60)
    print("SGF 批量导入工具")
    print(f"SGF 目录: {SGF_DIR}")
    print(f"输出文件: {OUTPUT_FILE}")
    print("=" * 60)
    # 1. 扫描文件
    sgf_files = sorted(SGF_DIR.glob("*.sgf"))
    total = len(sgf_files)
    print(f"\n找到 {total} 个 SGF 文件")
    if MAX_FILES > 0:
        sgf_files = sgf_files[:MAX_FILES]
        print(f"  → 仅处理前 {len(sgf_files)} 个（调试模式）")
    # 2. 批量解析
    results = []
    success = 0
    failed = 0
    start_time = time.time()
    for i, sgf_path in enumerate(sgf_files):
        if (i + 1) % 100 == 0 or i == 0:
            elapsed = time.time() - start_time
            speed = (i + 1) / elapsed if elapsed > 0 else 0
            print(f"  进度: {i+1}/{len(sgf_files)} "
                  f"({100*(i+1)/len(sgf_files):.0f}%) "
                  f"速度: {speed:.0f}个/秒")
        metadata = extract_metadata(sgf_path)
        if metadata:
            results.append(metadata)
            success += 1
        else:
            failed += 1
    # 3. 统计
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"处理完成!")
    print(f"  总数: {total}")
    print(f"  成功: {success}")
    print(f"  失败: {failed}")
    print(f"  耗时: {elapsed:.1f} 秒")
    print(f"  速度: {total/elapsed:.1f} 个/秒")
    # 4. 保存结果
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 元数据已保存至: {OUTPUT_FILE}")
    print(f"   文件大小: {OUTPUT_FILE.stat().st_size / 1024 / 1024:.1f} MB")
    # 5. 快速统计
    if results:
        black_wins = sum(1 for r in results if r.get("winner", "").startswith("B"))
        white_wins = sum(1 for r in results if r.get("winner", "").startswith("W"))
        print(f"\n📊 对局统计（成功解析部分）:")
        print(f"   黑胜: {black_wins}")
        print(f"   白胜: {white_wins}")
        print(f"   平局/未知: {len(results) - black_wins - white_wins}")
if __name__ == "__main__":
    main()