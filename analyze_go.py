"""
围棋SGF棋谱解析模块
功能：解析SGF文件，提取棋盘状态和着法序列
"""

import os
from typing import Tuple, List, Optional
from sgfmill import sgf, boards
from config import SGF_DIR, OUTPUT_DIR

def extract_board_and_moves(file_path: str, target_move_num: int = 10) -> Tuple[Optional[boards.Board], Optional[str], List[str]]:
    """
    从SGF文件中提取棋盘状态和着法序列
    
    Args:
        file_path: SGF文件路径
        target_move_num: 目标手数（提取到此手数为止的状态）
        
    Returns:
        tuple: (board, next_player, move_sequence)
            - board: 棋盘对象（sgfmill.boards.Board）
            - next_player: 下一手玩家 ('b'或'w')
            - move_sequence: 实际着法序列列表，格式如 ["B Q16", "W D4", ...]
    
    注意：
        1. 返回的是实际着法序列，不是假设的交替落子
        2. 坐标转换为GTP标准格式（如Q16）
        3. 如果棋谱手数不足，返回所有可用着法
    """
    try:
        # 打开并解析SGF文件
        with open(file_path, "rb") as f:
            game = sgf.Sgf_game.from_bytes(f.read())
        
        # 检查棋盘尺寸
        board_size = game.get_size()
        if board_size != 19:
            print(f"警告：非19路棋盘，尺寸为{board_size}（部分功能可能受限）")
        
        # 创建空棋盘
        board = boards.Board(board_size)
        main_sequence = game.get_main_sequence()
        
        # 围棋坐标字母映射（跳过I）
        letters = "ABCDEFGHJKLMNOPQRST"
        
        # 初始化变量
        move_sequence = []
        move_count = 0
        
        # 遍历主序列中的所有着法
        for node in main_sequence:
            color, move = node.get_move()
            
            # 跳过非落子节点（如设置信息、注释等）
            if color is None or move is None:
                continue
            
            move_count += 1
            row, col = move
            
            # 在棋盘上落子
            if color == 'b':
                board.play(row, col, 'b')
            else:
                board.play(row, col, 'w')
            
            # 记录着法序列（转换为GTP标准坐标）
            # 注意：row是行（0-18），col是列（0-18）
            # GTP坐标：列字母 + (行+1)
            if 0 <= col < len(letters):
                coord = f"{letters[col]}{row+1}"
                move_sequence.append(f"{color.upper()} {coord}")
            else:
                print(f"警告：无效列坐标 {col}，跳过此着法")
                continue
            
            # 如果达到目标手数，返回结果
            if move_count >= target_move_num:
                next_player = 'w' if color == 'b' else 'b'
                return board, next_player, move_sequence
        
        # 如果棋谱没有达到目标手数，返回所有提取的着法
        if move_sequence:
            # 根据最后一个着法的颜色确定下一手
            last_color = move_sequence[-1][0]  # 获取第一个字符（B或W）
            next_player = 'w' if last_color == 'B' else 'b'
        else:
            # 空棋谱，默认黑棋先行
            next_player = 'b'
        
        return board, next_player, move_sequence
        
    except FileNotFoundError:
        print(f"错误：文件不存在 {file_path}")
        return None, None, []
    except Exception as e:
        print(f"解析SGF文件失败 {os.path.basename(file_path)}: {e}")
        return None, None, []


def board_to_text(board: boards.Board, representation_type: str = "matrix") -> str:
    """
    将棋盘状态转换为文本表示
    
    Args:
        board: 棋盘对象
        representation_type: 表示类型
            "matrix" - 19x19矩阵显示
            "coordinates" - 坐标列表
            "simple" - 简化统计信息
    
    Returns:
        str: 棋盘状态的文本表示
    """
    if board is None:
        return "棋盘为空"
    
    size = board.side  # 棋盘边长
    
    if representation_type == "matrix":
        # 矩阵表示法：用字符网格显示整个棋盘
        text = "棋盘状态（19×19，.为空，X为黑，O为白）：\n"
        letters = "ABCDEFGHJKLMNOPQRST"
        
        # 打印列标签（顶部）
        text += "   " + " ".join(letters) + "\n"
        
        # 从顶部（第19行）到底部（第1行）显示
        for row in range(size-1, -1, -1):
            line = f"{row+1:2} "  # 行号（右对齐）
            
            # 遍历该行的所有列
            for col in range(size):
                stone = board.get(row, col)
                if stone is None:
                    line += ". "  # 空点
                elif stone == 'b':
                    line += "X "  # 黑棋
                else:
                    line += "O "  # 白棋
            
            # 在行尾再次显示行号（便于阅读）
            text += line + f" {row+1}\n"
        
        # 打印列标签（底部）
        text += "   " + " ".join(letters)
        return text
    
    elif representation_type == "coordinates":
        # 坐标表示法：列出所有棋子的坐标
        black_stones = []
        white_stones = []
        letters = "ABCDEFGHJKLMNOPQRST"
        
        # 统计所有棋子
        for row in range(size):
            for col in range(size):
                stone = board.get(row, col)
                if stone == 'b':
                    black_stones.append(f"{letters[col]}{row+1}")
                elif stone == 'w':
                    white_stones.append(f"{letters[col]}{row+1}")
        
        # 构建输出文本
        result = []
        
        if black_stones:
            stones_text = ", ".join(black_stones[:20])
            if len(black_stones) > 20:
                stones_text += f" ...等{len(black_stones)}个"
            result.append(f"黑子 ({len(black_stones)}个): {stones_text}")
        else:
            result.append("黑子: 无")
        
        if white_stones:
            stones_text = ", ".join(white_stones[:20])
            if len(white_stones) > 20:
                stones_text += f" ...等{len(white_stones)}个"
            result.append(f"白子 ({len(white_stones)}个): {stones_text}")
        else:
            result.append("白子: 无")
        
        return "\n".join(result)
    
    else:  # simple模式
        # 简单表示法：只统计棋子数量
        black_count = 0
        white_count = 0
        
        for row in range(size):
            for col in range(size):
                stone = board.get(row, col)
                if stone == 'b':
                    black_count += 1
                elif stone == 'w':
                    white_count += 1
        
        empty_count = size * size - black_count - white_count
        
        return (f"棋盘状态：黑子{black_count}个，白子{white_count}个，"
                f"空点{empty_count}个（总数：{size}×{size}={size*size}）")


def get_board_statistics(board: boards.Board) -> dict:
    """
    获取棋盘的统计信息
    
    Args:
        board: 棋盘对象
        
    Returns:
        dict: 统计信息字典
    """
    if board is None:
        return {"error": "棋盘为空"}
    
    size = board.side
    statistics = {
        "board_size": size,
        "black_stones": [],
        "white_stones": [],
        "empty_points": [],
        "total_points": size * size
    }
    
    letters = "ABCDEFGHJKLMNOPQRST"
    
    for row in range(size):
        for col in range(size):
            stone = board.get(row, col)
            coord = f"{letters[col]}{row+1}"
            
            if stone == 'b':
                statistics["black_stones"].append(coord)
            elif stone == 'w':
                statistics["white_stones"].append(coord)
            else:
                statistics["empty_points"].append(coord)
    
    statistics["black_count"] = len(statistics["black_stones"])
    statistics["white_count"] = len(statistics["white_stones"])
    statistics["empty_count"] = len(statistics["empty_points"])
    
    return statistics


if __name__ == "__main__":
    """
    主函数：测试SGF解析功能
    """
    print("=" * 60)
    print("围棋SGF解析模块测试")
    print("=" * 60)
    
    # 测试文件路径
    test_file = SGF_DIR / "game.sgf"
    
    if not os.path.exists(test_file):
        # 尝试其他可能的路径
        alt_paths = [
            "Go SGF/CSP01.SGF",
            "./Go SGF/CSP01.SGF",
            "../Go SGF/CSP01.SGF"
        ]
        
        for path in alt_paths:
            if os.path.exists(path):
                test_file = path
                break
    
    if os.path.exists(test_file):
        print(f"正在解析文件: {os.path.basename(test_file)}")
        print("-" * 40)
        
        # 测试提取棋盘状态和着法序列
        board, next_player, move_sequence = extract_board_and_moves(
            test_file, 
            target_move_num=10
        )
        
        if board is not None:
            print(f"✅ 成功提取第10手后的棋盘状态")
            print(f"   下一手: {'黑棋' if next_player == 'b' else '白棋'}")
            print(f"   棋盘大小: {board.side}×{board.side}")
            
            if move_sequence:
                print(f"   前{len(move_sequence)}手着法序列:")
                for i, move in enumerate(move_sequence[:10], 1):
                    print(f"     {i:2}. {move}")
                if len(move_sequence) > 10:
                    print(f"     ... 还有{len(move_sequence)-10}手")
            
            print("\n" + "-" * 40)
            print("棋盘状态表示测试:")
            
            # 测试三种表示法
            print("\n1. 矩阵表示法:")
            print(board_to_text(board, "matrix"))
            
            print("\n2. 坐标表示法:")
            print(board_to_text(board, "coordinates"))
            
            print("\n3. 简单表示法:")
            print(board_to_text(board, "simple"))
            
            # 获取统计信息
            print("\n4. 统计信息:")
            stats = get_board_statistics(board)
            print(f"   黑子: {stats['black_count']}个")
            print(f"   白子: {stats['white_count']}个")
            print(f"   空点: {stats['empty_count']}个")
            print(f"   总计: {stats['total_points']}个交叉点")
            
        else:
            print("❌ 提取棋盘状态失败")
    else:
        print(f"❌ 文件不存在: {test_file}")
        print("\n请检查SGF文件路径，或修改test_file变量指向你的SGF文件")
    
    print("\n" + "=" * 60)
    print("测试完成！")