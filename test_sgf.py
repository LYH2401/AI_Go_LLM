from sgfmill import sgf

print("正在解析棋谱...")

# 1. 打开我们刚才准备的 sample.sgf 文件
with open("sample.sgf", "rb") as f:
    sgf_content = f.read()

# 2. 让 sgfmill 这个库来读取它
try:
    game = sgf.Sgf_game.from_bytes(sgf_content)
    
    # 3. 提取对局的基本信息
    root_node = game.get_root()
    black_player = root_node.get("PB") # PB = Player Black
    white_player = root_node.get("PW") # PW = Player White
    result = root_node.get("RE")       # RE = Result
    
    print("\n✅ 棋谱读取成功！")
    print("-" * 30)
    print(f"执黑：{black_player}")
    print(f"执白：{white_player}")
    print(f"对局结果：{result}")
    
    # 4. 看看有几手棋
    main_sequence = game.get_main_sequence()
    # 减去 1 是因为序列的第一个节点是根节点(存对局信息的)，后面的才是真正的落子
    print(f"当前棋谱共记录了 {len(main_sequence) - 1} 手棋。")
    print("-" * 30)

except Exception as e:
    print(f"❌ 读取出错了：{e}")