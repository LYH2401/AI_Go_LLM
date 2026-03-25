#该文件用于批量重命名文件夹中的SGF文件，添加前缀以防止文件名重复。请根据需要修改target_folder和prefix变量。
import os

def batch_rename_sgf():
    target_folder = r"E:\Github Projects\AI_Go_LLM\AI_Go_LLM\Go SGF\迷你中国流224局"
    
    # 添加的前缀防止文件名重复
    prefix = "minizgl_"

    # 检查文件夹是否存在
    if not os.path.exists(target_folder):
        print(f" 找不到文件夹: {target_folder}")
        return

    print(f"🚀 开始批量修改文件夹 [{target_folder}] 中的文件名...")
    
    count = 0
    # 遍历文件夹中的所有文件
    for filename in os.listdir(target_folder):
        # 确保只修改 .sgf 文件
        if filename.lower().endswith('.sgf'):
            # 拼接旧的完整路径
            old_path = os.path.join(target_folder, filename)
            
            # 生成新文件名并拼接新路径
            new_filename = prefix + filename
            new_path = os.path.join(target_folder, new_filename)
            
            # 执行重命名操作
            os.rename(old_path, new_path)
            count += 1
            # 打印几个看看效果
            if count <= 5:
                print(f" 重命名: {filename}  ->  {new_filename}")

    print(f"...\n 批量修改完成！共修改了 {count} 个文件。")

if __name__ == "__main__":
    batch_rename_sgf()