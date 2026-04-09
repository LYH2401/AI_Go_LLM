# 该文件用于解析 SGF 棋谱文件，提取前 10 手棋的落子信息，并打印出来。请根据需要修改 test_file 变量，指向你想要分析的 SGF 文件路径。
import os  # 导入操作系统模块，用于文件路径操作
from sgfmill import sgf  # 导入 sgfmill 库，用于解析 SGF 棋谱文件
from sgfmill import boards  # 导入 boards 模块，用于表示棋盘状态

def analyze_sgf_moves(file_path):  # 注意：函数定义缺少 target_move_num 参数，但函数体内使用了该变量
    """
    提取棋谱在 target_move_num 手后的完整棋盘状态
    返回: (board_state, next_player)
    board_state: sgfmill.boards.Board 对象
    next_player: 'b' 或 'w'，表示下一手该谁走
    注意：函数中使用了未定义的参数 target_move_num，可能需要修复
    """
    try:
        # 以二进制模式打开 SGF 文件
        with open(file_path, "rb") as f:
            # 读取文件内容并解析为 SGF 游戏对象
            game = sgf.Sgf_game.from_bytes(f.read())
        
        # 获取棋盘的尺寸（默认为19路）
        board_size = game.get_size()
        # 检查棋盘尺寸，如果不是19路则发出警告
        if board_size != 19:
            print(f"警告：非19路棋盘，尺寸为{board_size}")
        
        # 创建一个空的棋盘对象
        board = boards.Board(board_size)
        # 获取主对局序列（棋谱的主要走法）
        main_sequence = game.get_main_sequence()
        
        move_count = 0  # 已处理的落子计数
        # 遍历主序列中的每个节点
        for node in main_sequence:
            # 获取节点的颜色和落子坐标
            color, move = node.get_move()
            if color is not None and move is not None:
                move_count += 1  # 增加落子计数
                row, col = move  # 解包行和列坐标
                
                # 根据颜色在棋盘上放置棋子
                if color == 'b':
                    board.play(row, col, 'b')  # 放置黑棋
                else:
                    board.play(row, col, 'w')  # 放置白棋
                
                # 如果已经达到目标落子数，返回棋盘状态和下一手玩家
                if move_count >= target_move_num:
                    next_player = 'w' if color == 'b' else 'b'  # 计算下一手玩家
                    return board, next_player
        
        # 如果棋谱没有达到目标落子数，返回当前棋盘状态和下一手玩家
        next_player = 'w' if main_sequence[-1].get_move()[0] == 'b' else 'b'
        return board, next_player
        
    except Exception as e:
        # 异常处理：打印错误信息并返回 None
        print(f"解析失败 {os.path.basename(file_path)}: {e}")
        return None, None

def board_to_text(board, representation_type="matrix"):
    """
    将棋盘状态转换为文本表示
    representation_type: 
      "matrix" - 19x19矩阵
      "coordinates" - 坐标列表
      "simple" - 简化描述
    """
    size = board.side  # 获取棋盘尺寸（边长）
    
    if representation_type == "matrix":
        # 矩阵表示法：用字符网格显示整个棋盘
        text = "棋盘状态（19×19，.为空，X为黑，O为白）：\n"
        letters = "ABCDEFGHJKLMNOPQRST"  # 围棋坐标字母（跳过I）
        text += "   " + " ".join(letters) + "\n"  # 打印列标签
        
        # 从顶部（第19行）到底部（第1行）遍历行
        for row in range(size-1, -1, -1):  # 从上到下显示（行19到行1）
            line = f"{row+1:2} "  # 行号（右对齐）
            for col in range(size):
                stone = board.get(row, col)  # 获取(row, col)位置的棋子
                if stone is None:
                    line += ". "  # 空点
                elif stone == 'b':
                    line += "X "  # 黑棋
                else:
                    line += "O "  # 白棋
            text += line + f" {row+1}\n"  # 在行尾再次显示行号
        
        text += "   " + " ".join(letters)  # 底部列标签
        return text
    
    elif representation_type == "coordinates":
        # 坐标表示法：列出所有棋子的坐标
        black_stones = []  # 黑棋坐标列表
        white_stones = []  # 白棋坐标列表
        letters = "ABCDEFGHJKLMNOPQRST"  # 列字母映射
        
        # 遍历棋盘上的每个交叉点
        for row in range(size):
            for col in range(size):
                stone = board.get(row, col)  # 获取棋子
                if stone == 'b':
                    # 将坐标转换为围棋标准表示（如"A1"、"T19"）
                    black_stones.append(f"{letters[col]}{row+1}")
                elif stone == 'w':
                    white_stones.append(f"{letters[col]}{row+1}")
        
        # 构建黑棋坐标文本，最多显示20个坐标
        text = f"黑子 ({len(black_stones)}个): {', '.join(black_stones[:20])}"
        if len(black_stones) > 20:
            text += f" ...等{len(black_stones)}个"
        # 构建白棋坐标文本，最多显示20个坐标
        text += f"\n白子 ({len(white_stones)}个): {', '.join(white_stones[:20])}"
        if len(white_stones) > 20:
            text += f" ...等{len(white_stones)}个"
        return text
    
    else:  # simple 模式
        # 简单表示法：只统计棋子数量
        # 使用生成器表达式计算黑棋数量
        black_count = sum(1 for row in range(size) for col in range(size) 
                         if board.get(row, col) == 'b')
        # 使用生成器表达式计算白棋数量
        white_count = sum(1 for row in range(size) for col in range(size) 
                         if board.get(row, col) == 'w')
        # 返回简单统计信息
        return f"棋盘状态：黑子{black_count}个，白子{white_count}个，空点{size*size-black_count-white_count}个"
if __name__ == "__main__":
    # 主程序入口：当直接运行此脚本时执行
    test_file = r"E:\Github Projects\AI_Go_LLM\AI_Go_LLM\Go SGF\CSP01.SGF"  # 测试用的 SGF 文件路径
    
    if os.path.exists(test_file):
        # 注意：extract_board_at_move 函数未定义，可能需要使用 analyze_sgf_moves 函数
        board, next_player = extract_board_at_move(test_file, target_move_num=10)
        
        if board is not None:
            # 打印第10手后的棋盘状态标题
            print(f"第10手后的棋盘状态（下一手：{'黑棋' if next_player == 'b' else '白棋'}）:")
            print("=" * 50)  # 分隔线
            
            # 使用三种不同的表示法显示棋盘状态
            print("\n1. 矩阵表示法:")
            print(board_to_text(board, "matrix"))
            
            print("\n2. 坐标表示法:")
            print(board_to_text(board, "coordinates"))
            
            print("\n3. 简单表示法:")
            print(board_to_text(board, "simple"))
            
    else:
        # 文件不存在时的错误处理
        print("文件不存在，请检查路径！")
