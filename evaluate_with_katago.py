#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KataGo围棋AI引擎封装模块
功能：初始化KataGo引擎、发送GTP命令、分析围棋局面
"""

import subprocess
import time
import os
import json
import re
import threading
from typing import List, Dict, Optional, Tuple, Union


class KataGoEngine:
    """KataGo GTP引擎封装类（修复Windows兼容性问题）"""
    
    def __init__(self, 
                 katago_path: str, 
                 config_path: str, 
                 model_path: str,
                 boardsize: int = 19,
                 max_visits: int = 100,
                 timeout: float = 30.0):
        """
        初始化KataGo引擎
        
        Args:
            katago_path: katago可执行文件路径
            config_path: 配置文件路径（如gtp_example.cfg）
            model_path: 模型文件路径
            boardsize: 棋盘大小，默认19路
            max_visits: 最大搜索次数，默认100
            timeout: GTP命令超时时间（秒），默认30秒
        """
        self.katago_path = katago_path
        self.config_path = config_path
        self.model_path = model_path
        self.boardsize = boardsize
        self.max_visits = max_visits
        self.timeout = timeout
        self.process = None
        self.is_running = False
        self.command_lock = threading.Lock()
        
        # 验证文件是否存在
        self._validate_files()
    
    def _validate_files(self) -> None:
        """验证必要的文件是否存在"""
        missing_files = []
        
        if not os.path.exists(self.katago_path):
            missing_files.append(f"KataGo可执行文件: {self.katago_path}")
        
        if not os.path.exists(self.config_path):
            missing_files.append(f"配置文件: {self.config_path}")
        
        if not os.path.exists(self.model_path):
            missing_files.append(f"模型文件: {self.model_path}")
        
        if missing_files:
            error_msg = "以下文件不存在:\n" + "\n".join(f"  - {f}" for f in missing_files)
            raise FileNotFoundError(error_msg)
    
    def start(self) -> bool:
        """
        启动KataGo进程
        
        Returns:
            bool: 启动是否成功
        """
        try:
            print(f"正在启动KataGo引擎...")
            print(f"  可执行文件: {os.path.basename(self.katago_path)}")
            print(f"  配置文件: {os.path.basename(self.config_path)}")
            print(f"  模型文件: {os.path.basename(self.model_path)}")
            
            # 构建启动命令
            cmd = [
                self.katago_path,
                "gtp",
                "-config", self.config_path,
                "-model", self.model_path
            ]
            
            # 启动进程
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding='utf-8'
            )
            
            self.is_running = True
            
            # 等待引擎初始化
            time.sleep(1.0)
            
            # 发送初始化命令
            init_commands = [
                f"boardsize {self.boardsize}",
                "clear_board",
                f"komi 7.5"
            ]
            
            for cmd in init_commands:
                response = self._send_command_internal(cmd)
                if not response.startswith("="):
                    print(f"警告: 初始化命令失败 {cmd}: {response}")
            
            print(f"✅ KataGo引擎已启动 (PID: {self.process.pid})")
            return True
            
        except Exception as e:
            print(f"❌ 启动KataGo引擎失败: {e}")
            self.is_running = False
            return False
    
    def _send_command_internal(self, command: str) -> str:
        """
        内部方法：发送GTP命令并读取响应（线程安全版本）
        
        注意：此方法不检查引擎是否运行，由外部方法负责
        """
        try:
            # 发送命令
            self.process.stdin.write(command.strip() + "\n")
            self.process.stdin.flush()
            
            # 读取响应（跨平台兼容实现）
            response_lines = []
            start_time = time.time()
            
            while time.time() - start_time < self.timeout:
                # 尝试读取一行
                line = self.process.stdout.readline()
                if not line:
                    # 没有数据，短暂休眠
                    time.sleep(0.01)
                    continue
                
                line = line.rstrip('\n')
                
                if line:
                    response_lines.append(line)
                
                # GTP响应以"="（成功）或"?"（错误）开头的行为结束标志
                if line.startswith("=") or line.startswith("?"):
                    # 检查是否有多行响应（如kata-analyze的输出）
                    # 短暂等待是否有更多数据
                    time.sleep(0.05)
                    continue
                
                # 如果已经收到响应且当前行是空行，可能表示响应结束
                if response_lines and line == "":
                    # 再检查一次
                    time.sleep(0.02)
                    break
            
            response = "\n".join(response_lines)
            
            # 如果超时且没有响应，返回错误
            if time.time() - start_time >= self.timeout and not response:
                return "? timeout"
            
            return response
            
        except Exception as e:
            print(f"发送GTP命令失败: {command}, 错误: {e}")
            return f"? {e}"
    
    def send_command(self, command: str, wait_for_response: bool = True) -> str:
        """
        向KataGo发送GTP命令并获取响应
        
        Args:
            command: GTP命令字符串
            wait_for_response: 是否等待响应
            
        Returns:
            str: GTP响应
        """
        with self.command_lock:
            if not self.is_running or not self.process:
                raise RuntimeError("KataGo引擎未运行，请先调用start()方法")
            
            if not wait_for_response:
                self.process.stdin.write(command.strip() + "\n")
                self.process.stdin.flush()
                return ""
            
            return self._send_command_internal(command)
    
    def analyze_position_with_moves(self, 
                                  move_sequence: List[str], 
                                  analysis_visits: int = None,
                                  player_to_move: str = "B") -> Dict:
        """
        使用实际的着法序列分析局面
        
        Args:
            move_sequence: 从SGF提取的实际着法序列，如 ["B Q16", "W D4", ...]
            analysis_visits: 搜索次数（默认使用初始化时的max_visits）
            player_to_move: 轮到谁走棋（"B"或"W"）
            
        Returns:
            Dict: 分析结果，包含胜率、推荐着法、变化图等信息
        """
        if not self.is_running:
            raise RuntimeError("KataGo引擎未运行")
        
        try:
            # 清空棋盘
            self.send_command("clear_board")
            
            # 按实际顺序执行所有着法
            if move_sequence:
                print(f"正在设置棋盘状态（{len(move_sequence)}手）...")
                for i, move in enumerate(move_sequence):
                    if move.strip() and move.upper() != "PASS":
                        response = self.send_command(f"play {move}")
                        if response.startswith("?"):
                            print(f"警告: play命令失败 {move}: {response}")
            
            # 确定搜索次数
            visits = analysis_visits if analysis_visits is not None else self.max_visits
            
            # 尝试不同的分析命令格式（不同KataGo版本可能不同）
            analysis_commands = [
                f"kata-genmove_analyze {player_to_move} maxVisits {visits}",
                f"kata-analyze {visits}",
                f"lz-analyze {visits}"
            ]
            
            analysis_result = None
            
            for cmd in analysis_commands:
                print(f"尝试分析命令: {cmd}")
                response = self.send_command(cmd)
                
                if "info" in response or "winrate" in response or "visits" in response:
                    analysis_result = self._parse_analysis_response(response)
                    analysis_result["command_used"] = cmd
                    break
                elif "unknown command" in response:
                    print(f"命令不支持: {cmd}")
                    continue
            
            if analysis_result is None:
                return {
                    "success": False,
                    "error": "所有分析命令都失败",
                    "move_sequence": move_sequence
                }
            
            # 添加额外信息
            analysis_result["move_sequence"] = move_sequence
            analysis_result["player_to_move"] = player_to_move
            analysis_result["visits_used"] = visits
            
            # 获取当前棋盘状态
            try:
                analysis_result["board_state"] = self.get_board_state()
            except:
                analysis_result["board_state"] = "无法获取"
            
            return analysis_result
            
        except Exception as e:
            print(f"分析局面失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "move_sequence": move_sequence
            }
    
    def _parse_analysis_response(self, response: str) -> Dict:
        """
        解析KataGo的分析响应
        
        Args:
            response: kata-genmove_analyze或kata-analyze命令的响应
            
        Returns:
            Dict: 结构化分析结果
        """
        result = {
            "success": False,
            "best_move": None,
            "winrate": 0.5,
            "score_lead": 0.0,
            "visits": 0,
            "variations": [],
            "raw_response": response[:500]  # 保存部分原始响应用于调试
        }
        
        try:
            # 方法1：尝试解析JSON格式（新版KataGo）
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group(0)
                    data = json.loads(json_str)
                    
                    if "moveInfos" in data and len(data["moveInfos"]) > 0:
                        # 提取最佳着法信息
                        best_move_info = data["moveInfos"][0]
                        result["best_move"] = best_move_info.get("move", "")
                        result["winrate"] = best_move_info.get("winrate", 0.5)
                        result["score_lead"] = best_move_info.get("scoreLead", 0.0)
                        result["visits"] = best_move_info.get("visits", 0)
                        
                        # 提取变化图
                        variations = []
                        for i, move_info in enumerate(data["moveInfos"][:10]):  # 前10个变化
                            variation = {
                                "rank": i + 1,
                                "move": move_info.get("move", ""),
                                "winrate": move_info.get("winrate", 0.5),
                                "score_lead": move_info.get("scoreLead", 0.0),
                                "visits": move_info.get("visits", 0),
                                "pv": move_info.get("pv", []),
                                "order": move_info.get("order", i)
                            }
                            variations.append(variation)
                        
                        result["variations"] = variations
                        result["success"] = True
                        return result
                except json.JSONDecodeError:
                    pass  # 不是JSON格式，继续尝试其他解析方法
            
            # 方法2：解析传统文本格式
            lines = response.split('\n')
            current_variation = None
            
            for line in lines:
                line = line.strip()
                
                # 解析info行（包含着法信息）
                if line.startswith("info"):
                    # info move Q16 visits 387 winrate 54.32 scoreLead 2.13 pv Q16 C3 ...
                    parts = line.split()
                    
                    if len(parts) >= 10:
                        variation = {
                            "rank": len(result["variations"]) + 1,
                            "move": parts[2] if len(parts) > 2 else "",
                            "visits": int(parts[4]) if len(parts) > 4 else 0,
                            "winrate": float(parts[6]) if len(parts) > 6 else 0.5,
                            "score_lead": float(parts[8]) if len(parts) > 8 else 0.0,
                            "pv": parts[9:] if len(parts) > 9 else []
                        }
                        
                        result["variations"].append(variation)
                        
                        # 第一个变化就是最佳着法
                        if len(result["variations"]) == 1:
                            result["best_move"] = variation["move"]
                            result["winrate"] = variation["winrate"]
                            result["score_lead"] = variation["score_lead"]
                            result["visits"] = variation["visits"]
                            result["success"] = True
                
                # 解析胜率信息
                elif "winrate" in line.lower():
                    winrate_match = re.search(r'winrate[=:]?\s*([0-9.]+)', line, re.IGNORECASE)
                    if winrate_match and result["winrate"] == 0.5:
                        result["winrate"] = float(winrate_match.group(1))
                
                # 解析最佳着法
                elif line.startswith("=") and "pass" not in line.lower():
                    move_match = re.search(r'[=]\s*([A-Z][0-9]+)', line)
                    if move_match and not result["best_move"]:
                        result["best_move"] = move_match.group(1)
                        result["success"] = True
            
            # 如果没有解析到最佳着法，但有关键信息，也算成功
            if result["variations"]:
                result["success"] = True
        
        except Exception as e:
            print(f"解析分析响应失败: {e}")
            result["error"] = str(e)
        
        return result
    
    def get_board_state(self) -> Dict:
        """
        获取当前棋盘状态
        
        Returns:
            Dict: 棋盘状态字典，包含黑白棋子坐标列表
        """
        if not self.is_running:
            raise RuntimeError("KataGo引擎未运行")
        
        state = {"B": [], "W": []}
        
        # 获取黑棋
        response = self.send_command("list_stones B")
        if "=" in response:
            stones_part = response.split("=", 1)[1].strip()
            if stones_part:
                state["B"] = stones_part.split()
        
        # 获取白棋
        response = self.send_command("list_stones W")
        if "=" in response:
            stones_part = response.split("=", 1)[1].strip()
            if stones_part:
                state["W"] = stones_part.split()
        
        return state
    
    def stop(self) -> None:
        """停止KataGo进程"""
        if self.process and self.is_running:
            print("正在停止KataGo引擎...")
            try:
                # 发送退出命令
                self.send_command("quit", wait_for_response=False)
                time.sleep(0.5)
            except:
                pass
            
            try:
                # 终止进程
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                try:
                    self.process.kill()
                except:
                    pass
            
            self.is_running = False
            self.process = None
            print("✅ KataGo引擎已停止")
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()
    
    def __del__(self):
        """析构函数"""
        try:
            self.stop()
        except:
            pass


def test_katago_engine():
    """
    测试KataGo引擎功能
    
    注意：需要先设置环境变量或修改下面的路径配置
    """
    print("=" * 60)
    print("KataGo引擎测试")
    print("=" * 60)
    
    # 从环境变量读取路径配置
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # 配置路径（优先使用环境变量）
    KATAGO_PATH = os.getenv("KATAGO_PATH", r"C:\katago\katago.exe")
    CONFIG_PATH = os.getenv("KATAGO_CONFIG_PATH", r"C:\katago\gtp_example.cfg")
    MODEL_PATH = os.getenv("KATAGO_MODEL_PATH", r"C:\katago\model.bin.gz")
    
    print(f"KataGo路径: {KATAGO_PATH}")
    print(f"配置路径: {CONFIG_PATH}")
    print(f"模型路径: {MODEL_PATH}")
    
    # 检查文件是否存在
    missing_files = []
    for path, name in [(KATAGO_PATH, "可执行文件"), 
                       (CONFIG_PATH, "配置文件"), 
                       (MODEL_PATH, "模型文件")]:
        if not os.path.exists(path):
            missing_files.append(f"{name}: {path}")
    
    if missing_files:
        print("\n❌ 以下文件不存在:")
        for item in missing_files:
            print(f"  - {item}")
        
        print("\n请执行以下操作之一:")
        print("1. 在.env文件中设置正确的环境变量:")
        print("   KATAGO_PATH=你的katago.exe路径")
        print("   KATAGO_CONFIG_PATH=你的gtp_example.cfg路径")
        print("   KATAGO_MODEL_PATH=你的model.bin.gz路径")
        print("\n2. 或者直接修改test_katago_engine()函数中的路径变量")
        
        return False
    
    try:
        # 创建引擎实例
        print("\n正在初始化KataGo引擎...")
        engine = KataGoEngine(
            katago_path=KATAGO_PATH,
            config_path=CONFIG_PATH,
            model_path=MODEL_PATH,
            boardsize=19,
            max_visits=50,  # 测试时用较小的搜索次数
            timeout=20.0
        )
        
        # 使用上下文管理器确保引擎正确关闭
        with engine:
            print("\n✅ 引擎启动成功！")
            
            # 测试基本GTP命令
            print("\n测试基本GTP命令:")
            
            commands = [
                ("protocol_version", "协议版本"),
                ("name", "引擎名称"),
                ("version", "引擎版本"),
                ("list_commands", "支持的命令")
            ]
            
            for cmd, desc in commands:
                response = engine.send_command(cmd)
                print(f"  {desc}: {response[:50]}...")
            
            # 测试简单局面分析
            print("\n测试简单局面分析...")
            
            # 创建一个简单开局（四个角）
            test_moves = ["B Q16", "W D4", "B D16", "W Q4"]
            
            print(f"测试局面: {test_moves}")
            result = engine.analyze_position_with_moves(
                move_sequence=test_moves,
                analysis_visits=50,
                player_to_move="B"  # 轮到黑棋走
            )
            
            # 显示分析结果
            print(f"\n分析结果:")
            print(f"  成功: {result.get('success', False)}")
            
            if result.get('success'):
                print(f"  最佳着法: {result.get('best_move', 'N/A')}")
                print(f"  胜率: {result.get('winrate', 0.5):.1%}")
                print(f"  目数优势: {result.get('score_lead', 0.0):.1f}")
                print(f"  搜索次数: {result.get('visits', 0)}")
                
                # 显示前3个变化
                variations = result.get('variations', [])[:3]
                if variations:
                    print(f"\n  前{len(variations)}个变化:")
                    for i, var in enumerate(variations):
                        print(f"    {i+1}. {var.get('move', 'N/A')} "
                              f"(胜率: {var.get('winrate', 0.5):.1%}, "
                              f"优势: {var.get('score_lead', 0.0):.1f}目)")
            
            # 获取棋盘状态
            print("\n获取当前棋盘状态...")
            board_state = engine.get_board_state()
            print(f"  黑子: {len(board_state['B'])}个")
            print(f"  白子: {len(board_state['W'])}个")
            
            if board_state['B']:
                print(f"  黑子坐标: {', '.join(board_state['B'][:5])}")
            if board_state['W']:
                print(f"  白子坐标: {', '.join(board_state['W'][:5])}")
        
        print("\n✅ 测试完成！")
        return True
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    """
    主函数入口
    """
    print("=" * 60)
    print("KataGo引擎评估模块")
    print("=" * 60)
    
    print("\n功能说明:")
    print("1. 用于初始化KataGo围棋AI引擎")
    print("2. 支持发送GTP命令和局面分析")
    print("3. 提供棋盘状态提取和着法评估功能")
    
    print("\n使用前请确保:")
    print("1. 已安装KataGo并下载模型文件")
    print("2. 已设置环境变量或修改测试函数中的路径")
    print("3. 已创建正确的配置文件")
    
    print("\n" + "=" * 60)
    
    # 询问用户是否运行测试
    response = input("\n是否运行KataGo引擎测试？(y/n): ").strip().lower()
    
    if response == 'y' or response == 'yes':
        print()
        success = test_katago_engine()
        
        if success:
            print("\n🎉 测试成功！您可以在项目中使用KataGoEngine类")
        else:
            print("\n⚠️ 测试失败，请检查上述错误信息")
            
            # 显示创建配置文件的选项
            response2 = input("\n是否查看示例配置文件内容？(y/n): ").strip().lower()
            if response2 == 'y':
                print("\n示例gtp_example.cfg内容:")
                print("-" * 40)
                print("""# KataGo GTP配置文件
model = model.bin.gz

# 搜索设置
maxVisits = 100
numSearchThreads = 2
numNNServerThreadsPerModel = 1

# 日志设置
logFile = katago.log
logAllGTPCommunication = false
logSearchInfo = false

# 其他设置
komi = 7.5
rules = japanese""")
                print("-" * 40)
    else:
        print("\n跳过测试。")
        print("\n导入和使用示例:")
        print("  from evaluate_with_katago import KataGoEngine")
        print("  ")
        print("  engine = KataGoEngine(katago_path, config_path, model_path)")
        print("  engine.start()")
        print("  result = engine.analyze_position_with_moves(move_sequence)")
        print("  engine.stop()")
    
    print("\n程序结束。")