import os
import requests
import zipfile
import io
import urllib3

# 消除关闭证书验证后产生的烦人警告信息
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 你的目标文件夹 (注意 r 前缀)
SAVE_DIR = r"E:\Github Projects\AI_Go_LLM\AI_Go_LLM\Go SGF"

def download_and_extract_sgf_zip():
    print("🚀 开始执行批量 SGF 下载与解压任务...")
    
    # Github 数据集链接
    DATASET_URL = "https://github.com/SabakiHQ/sgf-test-files/archive/refs/heads/master.zip"

    
    print(f"📦 正在从 {DATASET_URL} 下载数据，这可能需要一些时间...")
    
    try:
        # 【关键修改】：加入了 verify=False，强行忽略证书验证！
        response = requests.get(DATASET_URL, verify=False, timeout=60)
        
        if response.status_code == 200:
            print("✅ 下载完成！正在内存中解压...")
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                for file_info in zip_ref.infolist():
                    if file_info.filename.endswith('.sgf'):
                        file_info.filename = os.path.basename(file_info.filename)
                        if file_info.filename:
                            zip_ref.extract(file_info, SAVE_DIR)
                            print(f"📄 提取成功: {file_info.filename}")
            print(f"🎉 任务完成！请检查文件夹：{SAVE_DIR}")
        else:
            print(f"❌ 下载失败，服务器返回状态码: {response.status_code}")
            
    except Exception as e:
        print(f"💥 网络请求彻底失败了，错误信息：{e}")
        print("💡 导师提示：如果一直卡在这里失败，说明你的网络被墙拦截了，无法访问 Github。请开启魔法上网工具后再试！")

if __name__ == "__main__":
    download_and_extract_sgf_zip()