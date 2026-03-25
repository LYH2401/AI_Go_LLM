# 该文件用于解析 SGF 棋谱文件，提取前 10 手棋的落子信息，并打印出来。请根据需要修改 test_file 变量，指向你想要分析的 SGF 文件路径。
import os
from sgfmill import sgf

def analyze_sgf_moves(file_path):
    """
    使用 sgfmill 库解析棋谱，提取前 10 手棋
    """
    print(f" 正在解析: {os.path.basename(file_path)}")
    
    try:
        with open(file_path, "rb") as f:
            # 读取 SGF 文件
            game = sgf.Sgf_game.from_bytes(f.read())
            
        # 获取主线对局记录
        main_sequence = game.get_main_sequence()
        
        print(" 解析成功！前 10 手棋如下：")
        print("-" * 30)
        
        # 遍历前 10 个节点（第0个节点通常是棋局信息，比如规则、贴目等，包含实际落子的是之后的节点）
        moves_count = 0
        for node in main_sequence:
            color, move = node.get_move()
            if color is not None and move is not None:
                moves_count += 1
                row, col = move
                
                # sgfmill的坐标是 0-18，且从左下角开始计算。我们稍微做个简单打印
                color_name = "黑棋" if color == "b" else "白棋"
                print(f"第 {moves_count} 手: {color_name} 落子在坐标 ({row}, {col})")
                
                if moves_count >= 10:
                    break # 这里只看前10手
                    
        print("-" * 30)
        
    except Exception as e:
        print(f" 解析失败: {e}")

if __name__ == "__main__":
    #测试文件路径
    test_file = r"E:\Github Projects\AI_Go_LLM\AI_Go_LLM\Go SGF\CSP01.SGF"  
    
    if os.path.exists(test_file):
        analyze_sgf_moves(test_file)
    else:
        print("文件不存在，请检查路径！")