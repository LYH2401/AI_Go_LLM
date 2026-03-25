# 测试连接 AI 的功能，确保能够成功调用 DeepSeek 的 API 并得到合理的回复。
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
                                                                                           
api_key = os.getenv("DEEPSEEK_API_KEY")
base_url = os.getenv("DEEPSEEK_BASE_URL")

print("正在进行连接 AI ...")

client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

try:
    response = client.chat.completions.create(
        model="deepseek-reasnoer",
        messages=[
            {"role": "system", "content": "你是一位围棋九段高手，同时也是一位极其幽默的AI助手。"},
            {"role": "user", "content": "你好！我已经成功连接到你了，准备好和我一起分析围棋棋谱了吗？请用一句话简短回应我。"}
        ],
        temperature=0.7 
    )
    
    # 5. 打印 AI 的回答
    print("\n 连接成功！AI的回复是：")
    print("=================================")
    print(response.choices[0].message.content)
    print("=================================")

except Exception as e:
    print(f"\n 连接出错了，错误信息：{e}")