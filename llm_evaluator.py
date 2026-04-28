"""
LLM围棋评估模块
功能：调用大语言模型分析围棋局面，并用KataGo评估结果质量
"""

import json
import re
import os
import sys
from typing import Optional, Dict, Tuple, List, Any
from openai import OpenAI
from dotenv import load_dotenv

# 导入其他模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analyze_go import extract_board_and_moves, board_to_text
from evaluate_with_katago import KataGoEngine

# 加载环境变量
load_dotenv()


def init_llm_client() -> OpenAI:
    """
    初始化LLM客户端
    
    Returns:
        OpenAI: 初始化后的客户端对象
        
    Raises:
        ValueError: 如果API密钥未设置
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    
    if not api_key:
        raise ValueError(
            "❌ DEEPSEEK_API_KEY 环境变量未设置。\n"
            "请按以下步骤操作：\n"
            "1. 在项目根目录创建 .env 文件\n"
            "2. 添加以下内容：\n"
            "   DEEPSEEK_API_KEY=\"your_actual_api_key_here\"\n"
            "   DEEPSEEK_BASE_URL=\"https://api.deepseek.com\"\n"
            "3. 重新运行程序\n\n"
            "获取API密钥：https://platform.deepseek.com/api_keys"
        )
    
    print(f"✅ LLM客户端初始化成功 (Base URL: {base_url})")
    
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    return client


def parse_move_from_llm_response(response_text: str) -> Optional[str]:
    """
    从大模型的回复中解析出推荐的着法
    
    支持多种格式：
    1. JSON格式：{"move": "Q16", "reason": "..."}
    2. 自然语言："建议下在Q16"、"我认为D4是个好点"
    3. 英文格式："Next move: R10"、"play at K5"
    
    Args:
        response_text: LLM的回复文本
        
    Returns:
        Optional[str]: 解析出的坐标字符串（如"Q16"），如果解析失败则返回None
    """
    if not response_text:
        return None
    
    # 清理文本
    text = response_text.strip()
    
    # 方法1：优先尝试解析JSON格式（最可靠）
    try:
        # 查找JSON对象（可能包含在代码块或其他文本中）
        json_pattern = r'\{[^{}]*"move"[^{}]*:[^{}]*"[^"]*"[^{}]*\}'
        json_matches = re.findall(json_pattern, text, re.DOTALL | re.IGNORECASE)
        
        for json_str in json_matches:
            try:
                # 清理JSON字符串
                json_str = json_str.replace('\n', ' ').replace('\r', ' ')
                data = json.loads(json_str)
                
                if "move" in data:
                    move = data["move"]
                    if isinstance(move, str) and move.strip():
                        move = move.strip().upper()
                        # 验证坐标格式
                        if re.match(r'^[A-HJ-T](1[0-9]|[1-9])$', move):
                            return move
            except (json.JSONDecodeError, KeyError, AttributeError):
                continue
    except Exception:
        pass
    
    # 方法2：尝试提取标准坐标模式
    # 围棋坐标模式：大写字母A-T（跳过I）+ 数字1-19
    coord_pattern = r'\b([A-HJ-T])(1[0-9]|[1-9])\b'
    
    # 直接匹配坐标
    direct_matches = re.findall(coord_pattern, text, re.IGNORECASE)
    if direct_matches:
        # 取第一个匹配的坐标
        letter, number = direct_matches[0]
        return f"{letter.upper()}{number}"
    
    # 方法3：匹配带常见前缀的坐标
    prefixes = [
        r'下[在到于]\s*',
        r'推荐\s*',
        r'建议\s*(?:下在|落子)?\s*',
        r'落子\s*(?:于|在|到)?\s*',
        r'坐标[为是]\s*',
        r'位置[为是]\s*',
        r'着法[为是]\s*',
        r'选点\s*',
        r'next move[:\s]*',
        r'move[:\s]*',
        r'play[:\s]*',
        r'建议\s*'
    ]
    
    for prefix in prefixes:
        pattern = f'{prefix}\\s*{coord_pattern}'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            letter, number = match.group(1), match.group(2)
            return f"{letter.upper()}{number}"
    
    # 方法4：尝试提取"PASS"（停一手）
    if re.search(r'\b(pass|停一手|放弃|PASS)\b', text, re.IGNORECASE):
        return "PASS"
    
    # 所有方法都失败
    return None


def extract_reason_from_response(response_text: str) -> Optional[str]:
    """
    从LLM回复中提取分析理由
    
    Args:
        response_text: LLM的回复文本
        
    Returns:
        Optional[str]: 提取的理由文本
    """
    try:
        # 尝试从JSON中提取
        json_pattern = r'\{[^{}]*"reason"[^{}]*:[^{}]*"[^"]*"[^{}]*\}'
        json_matches = re.findall(json_pattern, response_text, re.DOTALL)
        
        for json_str in json_matches:
            try:
                data = json.loads(json_str)
                if "reason" in data:
                    reason = data["reason"]
                    if isinstance(reason, str) and reason.strip():
                        return reason.strip()
            except:
                continue
        
        # 如果没有JSON格式，尝试提取分析性文本
        # 查找常见的分析段落开头
        analysis_patterns = [
            r'理由[：:]\s*(.*?)(?=\n\n|\n[A-Z]|$)',
            r'原因[：:]\s*(.*?)(?=\n\n|\n[A-Z]|$)',
            r'分析[：:]\s*(.*?)(?=\n\n|\n[A-Z]|$)',
            r'这是因为\s*(.*?)(?=\n\n|\n[A-Z]|$)',
            r'reason[：:]\s*(.*?)(?=\n\n|\n[A-Z]|$)',
            r'analysis[：:]\s*(.*?)(?=\n\n|\n[A-Z]|$)'
        ]
        
        for pattern in analysis_patterns:
            match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
            if match:
                reason = match.group(1).strip()
                if reason and len(reason) > 5:  # 至少5个字符
                    return reason
        
        # 如果没有明确的分析段落，返回整个回复（去除坐标部分）
        move = parse_move_from_llm_response(response_text)
        if move:
            # 移除坐标和常见前缀，保留其他内容作为理由
            cleaned = re.sub(rf'\b{move}\b', '', response_text, flags=re.IGNORECASE)
            cleaned = re.sub(r'下在|推荐|建议|坐标|位置|着法|move|play', '', cleaned, flags=re.IGNORECASE)
            cleaned = cleaned.strip()
            if cleaned and len(cleaned) > 10:
                return cleaned[:200]  # 限制长度
        
    except Exception as e:
        print(f"提取理由失败: {e}")
    
    return None


def evaluate_single_position(
    sgf_path: str,
    move_num: int,
    llm_client: Optional[OpenAI] = None,
    katago_engine: Optional[KataGoEngine] = None,
    llm_model: str = "deepseek-reasoner",
    representation_type: str = "coordinates",
    temperature: float = 0.7
) -> Dict[str, Any]:
    """
    评估单个围棋局面
    
    Args:
        sgf_path: SGF文件路径
        move_num: 要评估的手数
        llm_client: LLM客户端（可选，会自动初始化）
        katago_engine: KataGo引擎（可选，不提供则跳过KataGo评估）
        llm_model: 使用的LLM模型名称
        representation_type: 棋盘表示类型（"matrix"、"coordinates"、"simple"）
        temperature: LLM生成温度（0.0-1.0）
        
    Returns:
        Dict: 完整的评估结果
    """
    result = {
        "success": False,
        "error": None,
        "position_info": {},
        "llm_analysis": {},
        "katago_evaluation": {},
        "quality_metrics": {}
    }
    
    try:
        # ===== 1. 提取棋盘状态和着法序列 =====
        print(f"\n{'='*60}")
        print(f"评估第{move_num}手后的局面")
        print(f"棋谱: {os.path.basename(sgf_path)}")
        print(f"{'='*60}")
        
        board, next_player, move_sequence = extract_board_and_moves(sgf_path, move_num)
        
        if board is None:
            result["error"] = "无法从SGF文件提取棋盘状态"
            return result
        
        result["position_info"] = {
            "sgf_file": os.path.basename(sgf_path),
            "move_number": move_num,
            "next_player": next_player,
            "next_player_zh": "黑棋" if next_player == 'b' else "白棋",
            "board_size": board.side,
            "total_moves_extracted": len(move_sequence),
            "move_sequence": move_sequence[:20]  # 只保存前20手
        }
        
        print(f"✅ 成功提取棋盘状态")
        print(f"   下一手: {'黑棋' if next_player == 'b' else '白棋'}")
        print(f"   着法序列: {len(move_sequence)}手")
        if move_sequence:
            print(f"   前5手: {' → '.join(move_sequence[:5])}")
        
        # ===== 2. 转换为文本描述并构建Prompt =====
        board_text = board_to_text(board, representation_type)
        
        prompt = f"""你是一位围棋职业九段高手，请分析当前围棋局面并推荐下一手。

棋盘信息：
- 棋盘大小：19×19
- 当前局面（{representation_type}表示）：
{board_text}

对局状态：
- 轮到{'黑棋' if next_player == 'b' else '白棋'}走棋
- 当前手数：第{move_num}手后

你的任务：
1. 分析当前局面的关键点（如大场、急所、厚薄等）
2. 推荐最合理的下一手落子位置
3. 简要说明推荐理由

请以JSON格式回复，包含以下字段：
{{
  "move": "推荐的坐标（如Q16）或PASS",
  "reason": "详细的推荐理由（100字以内）",
  "confidence": "你的置信度（0.0-1.0）",
  "alternative_moves": ["备选坐标1", "备选坐标2", ...]
}}

注意：
- 坐标使用标准围棋坐标（A-T，跳过I，1-19）
- 如果认为应该停一手，move字段设为"PASS"
- 分析要专业、简洁"""
        
        result["llm_analysis"]["prompt"] = prompt[:300] + "..." if len(prompt) > 300 else prompt
        
        # ===== 3. 调用LLM获取推荐着法 =====
        print(f"\n调用LLM分析局面...")
        
        if llm_client is None:
            llm_client = init_llm_client()
        
        try:
            response = llm_client.chat.completions.create(
                model=llm_model,
                messages=[
                    {
                        "role": "system", 
                        "content": "你是围棋职业九段高手，精通各种开局、中盘和官子技巧。请以专业、准确的方式分析围棋局面。"
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=500
            )
            
            llm_response_text = response.choices[0].message.content
            result["llm_analysis"]["raw_response"] = llm_response_text
            
            print(f"✅ LLM响应接收成功")
            print(f"   响应长度: {len(llm_response_text)}字符")
            
        except Exception as e:
            error_msg = f"LLM调用失败: {str(e)}"
            result["error"] = error_msg
            print(f"❌ {error_msg}")
            return result
        
        # ===== 4. 解析LLM回复 =====
        recommended_move = parse_move_from_llm_response(llm_response_text)
        reason = extract_reason_from_response(llm_response_text)
        
        if not recommended_move:
            result["error"] = "无法从LLM回复中解析出有效着法"
            result["llm_analysis"]["response_text"] = llm_response_text[:200]
            print(f"❌ {result['error']}")
            return result
        
        result["llm_analysis"]["parsed_move"] = recommended_move
        result["llm_analysis"]["reason"] = reason
        result["llm_analysis"]["model_used"] = llm_model
        
        print(f"✅ 解析LLM推荐着法: {recommended_move}")
        if reason:
            print(f"   推荐理由: {reason[:100]}...")
        
        # ===== 5. 用KataGo评估LLM着法质量 =====
        if katago_engine is not None:
            print(f"\n使用KataGo评估着法质量...")
            
            try:
                # 使用实际的着法序列进行分析
                analysis_result = katago_engine.analyze_position_with_moves(
                    move_sequence=move_sequence,
                    analysis_visits=100,  # 使用100次搜索
                    player_to_move=next_player.upper()
                )
                
                result["katago_evaluation"] = analysis_result
                
                if analysis_result.get("success"):
                    # 提取KataGo的推荐着法列表
                    kata_variations = analysis_result.get("variations", [])
                    kata_best_move = analysis_result.get("best_move", "")
                    
                    # 检查LLM推荐的着法在KataGo列表中的排名
                    llm_rank = None
                    llm_winrate = None
                    llm_score_lead = None
                    
                    for i, variation in enumerate(kata_variations):
                        if variation.get("move", "").upper() == recommended_move.upper():
                            llm_rank = i + 1
                            llm_winrate = variation.get("winrate", 0.5)
                            llm_score_lead = variation.get("score_lead", 0.0)
                            break
                    
                    # 计算质量指标
                    quality_metrics = {
                        "kata_best_move": kata_best_move,
                        "llm_move": recommended_move,
                        "llm_rank_in_kata": llm_rank,
                        "llm_winrate": llm_winrate,
                        "llm_score_lead": llm_score_lead,
                        "total_variations_analyzed": len(kata_variations),
                        "kata_visits_used": analysis_result.get("visits_used", 0)
                    }
                    
                    # 计算质量分数
                    if llm_rank is not None:
                        if llm_rank == 1:
                            quality_score = 1.0
                            quality_label = "完美匹配"
                        elif llm_rank <= 3:
                            quality_score = 0.8
                            quality_label = "优秀选择"
                        elif llm_rank <= 10:
                            quality_score = 0.6
                            quality_label = "合理选择"
                        else:
                            quality_score = 0.4
                            quality_label = "可接受"
                        
                        # 考虑胜率调整分数
                        if llm_winrate is not None:
                            winrate_adjustment = (llm_winrate - 0.5) * 0.5  # -0.25到+0.25
                            quality_score = min(1.0, max(0.0, quality_score + winrate_adjustment))
                        
                        print(f"✅ KataGo评估完成")
                        print(f"   KataGo最佳着法: {kata_best_move}")
                        print(f"   LLM着法排名: 第{llm_rank}名")
                        print(f"   LLM着法胜率: {llm_winrate:.1%}")
                        print(f"   质量评估: {quality_label} (分数: {quality_score:.2f})")
                        
                    else:
                        quality_score = 0.2
                        quality_label = "不在推荐列表中"
                        print(f"⚠️  LLM着法不在KataGo前{len(kata_variations)}推荐中")
                        print(f"   KataGo最佳着法: {kata_best_move}")
                        print(f"   质量评估: {quality_label}")
                    
                    quality_metrics["quality_score"] = quality_score
                    quality_metrics["quality_label"] = quality_label
                    result["quality_metrics"] = quality_metrics
                    
                else:
                    print(f"⚠️  KataGo分析失败: {analysis_result.get('error', '未知错误')}")
                    result["quality_metrics"] = {
                        "error": "KataGo分析失败",
                        "quality_score": 0.0,
                        "quality_label": "无法评估"
                    }
                    
            except Exception as e:
                error_msg = f"KataGo评估失败: {str(e)}"
                print(f"❌ {error_msg}")
                result["katago_evaluation"]["error"] = error_msg
                result["quality_metrics"] = {
                    "error": error_msg,
                    "quality_score": 0.0,
                    "quality_label": "评估失败"
                }
        else:
            print(f"⚠️  未提供KataGo引擎，跳过着法质量评估")
            result["quality_metrics"] = {
                "note": "未进行KataGo评估",
                "quality_score": None,
                "quality_label": "未评估"
            }
        
        # ===== 6. 最终处理 =====
        result["success"] = True
        print(f"\n✅ 局面评估完成")
        
        # 生成简要总结
        if "quality_metrics" in result and result["quality_metrics"].get("quality_score") is not None:
            score = result["quality_metrics"]["quality_score"]
            if score >= 0.8:
                summary = "🎉 优秀！LLM推荐着法与KataGo高度一致"
            elif score >= 0.6:
                summary = "👍 良好！LLM推荐着法合理"
            elif score >= 0.4:
                summary = "👌 可接受！LLM推荐着法在合理范围内"
            else:
                summary = "⚠️  需要改进！LLM推荐着法与AI推荐有较大差距"
            
            result["summary"] = summary
            print(f"   总结: {summary}")
        
        return result
        
    except Exception as e:
        error_msg = f"评估过程中发生未预期的错误: {str(e)}"
        result["error"] = error_msg
        print(f"❌ {error_msg}")
        import traceback
        traceback.print_exc()
        return result


def test_llm_evaluator():
    """
    测试LLM评估器功能
    """
    print("=" * 60)
    print("LLM围棋评估器测试")
    print("=" * 60)
    
    # 测试解析函数
    print("\n1. 测试着法解析函数:")
    
    test_cases = [
        ('{"move": "Q16", "reason": "抢占右上大场"}', "Q16", "JSON格式"),
        ('建议下在D4', "D4", "中文建议"),
        ("Next move: R10", "R10", "英文格式"),
        ("我认为K10是个好点", "K10", "中文描述"),
        ("落子于T19", "T19", "中文落子"),
        ("play at Q5", "Q5", "英文play"),
        ("没有坐标的文本", None, "无坐标文本"),
        ('{"move": "PASS", "reason": "形势领先"}', "PASS", "停一手")
    ]
    
    all_passed = True
    for text, expected, desc in test_cases:
        result = parse_move_from_llm_response(text)
        passed = result == expected
        status = "✅" if passed else "❌"
        
        if not passed:
            all_passed = False
        
        print(f"   {status} {desc}: '{text[:20]}...' -> {result} (期望: {expected})")
    
    if all_passed:
        print("   ✅ 所有解析测试通过")
    else:
        print("   ⚠️  部分解析测试失败")
    
    # 测试SGF文件处理
    print("\n2. 测试SGF文件处理:")
    
    sgf_path = r"E:\Github Projects\AI_Go_LLM\AI_Go_LLM\Go SGF\CSP01.SGF"
    
    # 尝试多个可能的路径
    alt_paths = [
        sgf_path,
        "Go SGF/CSP01.SGF",
        "./Go SGF/CSP01.SGF",
        "../Go SGF/CSP01.SGF",
        "CSP01.SGF"
    ]
    
    actual_path = None
    for path in alt_paths:
        if os.path.exists(path):
            actual_path = path
            break
    
    if actual_path:
        print(f"   找到SGF文件: {actual_path}")
        
        # 测试提取功能（不调用LLM和KataGo）
        print("   测试棋盘状态提取...")
        board, next_player, move_sequence = extract_board_and_moves(actual_path, 10)
        
        if board is not None:
            print(f"   ✅ 成功提取棋盘状态")
            print(f"      下一手: {'黑棋' if next_player == 'b' else '白棋'}")
            print(f"      棋盘大小: {board.side}×{board.side}")
            print(f"      着法序列: {len(move_sequence)}手")
            
            if move_sequence:
                print(f"      前3手: {' → '.join(move_sequence[:3])}")
                
                # 测试不同表示法
                print("\n   测试棋盘表示法:")
                for rep_type in ["simple", "coordinates", "matrix"]:
                    try:
                        text = board_to_text(board, rep_type)
                        lines = text.split('\n')
                        print(f"      {rep_type}: {lines[0][:50]}..." if lines else f"      {rep_type}: [空]")
                    except:
                        print(f"      {rep_type}: 转换失败")
        else:
            print("   ❌ 提取棋盘状态失败")
    else:
        print(f"   ⚠️  未找到SGF测试文件")
        print("      请将CSP01.SGF放在Go SGF目录中")
    
    # 测试完整评估流程（需要API密钥）
    print("\n3. 测试完整评估流程:")
    
    # 检查API密钥
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("   ⚠️  未设置DEEPSEEK_API_KEY环境变量，跳过LLM调用测试")
        print("      请在.env文件中设置DEEPSEEK_API_KEY")
    else:
        print("   ✅ 检测到API密钥")
        
        if actual_path:
            print("   注意：完整评估需要KataGo配置")
            print("   此测试仅演示流程，不实际调用外部服务")
        else:
            print("   ⚠️  需要SGF文件进行完整测试")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("\n使用说明:")
    print("1. 设置环境变量: DEEPSEEK_API_KEY, KATAGO_PATH等")
    print("2. 准备SGF棋谱文件")
    print("3. 导入并使用evaluate_single_position函数")
    print("\n示例:")
    print("  result = evaluate_single_position('path/to/sgf', 10)")
    print("  print(f'质量分数: {result[\"quality_metrics\"][\"quality_score\"]}')")


def main():
    """主函数"""
    print("=" * 60)
    print("LLM围棋评估系统")
    print("=" * 60)
    
    print("\n功能:")
    print("1. 解析SGF棋谱文件")
    print("2. 调用大语言模型分析围棋局面")
    print("3. 使用KataGo评估LLM推荐着法的质量")
    print("4. 生成详细的评估报告")
    
    print("\n配置要求:")
    print("✅ SGF棋谱文件")
    print("✅ DeepSeek API密钥")
    print("✅ KataGo引擎（可选，用于质量评估）")
    
    print("\n" + "=" * 60)
    
    # 运行测试
    response = input("\n是否运行功能测试？(y/n): ").strip().lower()
    
    if response in ['y', 'yes']:
        test_llm_evaluator()
    else:
        print("\n跳过测试。")
        print("\n快速开始:")
        print("  1. 设置环境变量")
        print("  2. 准备SGF文件")
        print("  3. 运行评估:")
        print("     from llm_evaluator import evaluate_single_position")
        print("     result = evaluate_single_position('your.sgf', 20)")
    
    print("\n程序结束。")


if __name__ == "__main__":
    main()