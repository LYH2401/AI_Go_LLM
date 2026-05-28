# 该文件用于从 SGF 棋谱文件中提取开局信息，生成适合大模型微调训练的 JSONL 数据集。请根据需要修改 source_folder 和 output_jsonl 变量。
import os
import json
from sgfmill import sgf

from config import SGF_DIR, OUTPUT_DIR

def format_coordinate(row, col):
    """
    将 sgfmill 的 (row, col) 转换为国际通用的 GTP 坐标 (如 Q16)
    围棋横坐标: A-T (跳过容易混淆的 I)
    围棋纵坐标: 1-19
    """
    letters = "ABCDEFGHJKLMNOPQRST"
    # sgfmill 的坐标是从 0 开始的，所以纵坐标要 +1
    return f"{letters[col]}{row + 1}"

def create_dataset_from_sgf(folder_path, output_file):
    print(f" 开始扫描文件夹: {folder_path}")
    dataset = []
    success_count = 0

    # 遍历文件夹下所有的 sgf 文件
    for filename in os.listdir(folder_path):
        if not filename.lower().endswith('.sgf'):
            continue
            
        file_path = os.path.join(folder_path, filename)
        
        try:
            with open(file_path, "rb") as f:
                game = sgf.Sgf_game.from_bytes(f.read())
            
            main_sequence = game.get_main_sequence()
            moves = []
            
            # 提取前 6 手棋 (用前 5 手作为问题，第 6 手作为答案)
            for node in main_sequence:
                color, move = node.get_move()
                if color is not None and move is not None:
                    row, col = move
                    gtp_coord = format_coordinate(row, col)
                    color_zh = "黑" if color == "b" else "白"
                    moves.append(f"{color_zh} {gtp_coord}")
                    
                if len(moves) >= 6:
                    break
            
            # 只有当棋谱包含至少 6 手棋时才处理
            if len(moves) == 6:
                # 把前 5 手拼成输入文本
                input_context = " | ".join([f"{i+1}. {m}" for i, m in enumerate(moves[:5])])
                # 第 6 手作为输出答案
                output_answer = moves[5]
                
                # 按照大模型微调的标准 Alpaca 格式组装数据
                data_item = {
                    "instruction": "你是一个围棋开局分析师。请阅读当前的开局前5手，并预测下一手（第6手）最可能的落子位置。",
                    "input": input_context,
                    "output": output_answer
                }
                dataset.append(data_item)
                success_count += 1
                
        except Exception as e:
            # 静默忽略解析失败的损坏文件
            pass

    # 将数据写入 jsonl 文件
    with open(output_file, "w", encoding="utf-8") as f:
        for item in dataset:
            # ensure_ascii=False 保证中文正常显示
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print(f" 数据集生成完毕！成功处理 {success_count} 个棋谱。")
    print(f" 大模型训练数据保存在: {output_file}")

if __name__ == "__main__":
    
    source_folder = SGF_DIR
    
    
    output_jsonl = str(OUTPUT_DIR / "go_training_dataset.jsonl")
    
    create_dataset_from_sgf(source_folder, output_jsonl)