# 该文件用于从 Github 上下载 SGF 棋谱数据集，并解压到指定文件夹。请根据需要修改 SAVE_DIR 变量。
# 文件无法通过爬虫下载
import os
import requests
import zipfile
import io
import urllib3


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


SAVE_DIR = r"E:\Github Projects\AI_Go_LLM\AI_Go_LLM\Go SGF"

def download_and_extract_sgf_zip():
    print(" 开始执行批量 SGF 下载与解压任务...")
    
    # Github 数据集链接
    DATASET_URL = "https://github.com/SabakiHQ/sgf-test-files/archive/refs/heads/master.zip"

    
    print(f"📦 正在从 {DATASET_URL} 下载数据，这可能需要一些时间...")
    
    try:
        # 【关键修改】：加入了 verify=False，强行忽略证书验证！
        response = requests.get(DATASET_URL, verify=False, timeout=60)
        
        if response.status_code == 200:
            print(" 下载完成！正在内存中解压...")
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                for file_info in zip_ref.infolist():
                    if file_info.filename.endswith('.sgf'):
                        file_info.filename = os.path.basename(file_info.filename)
                        if file_info.filename:
                            zip_ref.extract(file_info, SAVE_DIR)
                            print(f"📄 提取成功: {file_info.filename}")
            print(f" 任务完成！请检查文件夹：{SAVE_DIR}")
        else:
            print(f" 下载失败，服务器返回状态码: {response.status_code}")
            
    except Exception as e:
        print(f" 网络请求彻底失败了，错误信息：{e}")
        print(" 网络被墙拦截了，无法访问 Github。请稍后后再试！")

if __name__ == "__main__":
    download_and_extract_sgf_zip()