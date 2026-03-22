import os
from dotenv import load_dotenv
from openai import OpenAI

# 1. 打开“保险箱”，加载 .env 文件里的配置
load_dotenv()

# 2. 从环境变量中拿出 DeepSeek 的钥匙和地址
api_key = os.getenv("DEEPSEEK_API_KEY")
base_url = os.getenv("DEEPSEEK_BASE_URL")

print("正在尝试连接 AI 大脑...")

# 3. 初始化客户端
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

# 4. 发送你的第一句话
try:
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一位围棋九段高手，同时也是一位极其幽默的AI助手。"},
            {"role": "user", "content": "你好！我已经成功连接到你了，准备好和我一起分析围棋棋谱了吗？请用一句话简短回应我。"}
        ],
        temperature=0.7 
    )
    
    # 5. 打印 AI 的回答
    print("\n✅ 连接成功！AI的回复是：")
    print("---------------------------------")
    print(response.choices[0].message.content)
    print("---------------------------------")

except Exception as e:
    print(f"\n❌ 连接出错了，错误信息：{e}")