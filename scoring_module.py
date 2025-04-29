import requests
import re
import json

# API 信息（根据实际情况修改）
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
API_KEY = "7c867017-7d8b-45bf-91b1-40d19098e097"
MODEL_NAME = "ep-20250423093303-l5b9s"


def call_api(prompt):
    """调用大模型API，返回响应JSON（失败时返回None）"""
    API_ENDPOINT = BASE_URL
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "parameters": {
            "temperature": 0.7,
            "max_tokens": 5000
        }
    }

    try:
        response = requests.post(API_ENDPOINT, headers=headers, json=data, timeout=500)
        response.raise_for_status()
        return response.json()
    except Exception as err:
        print(f"API请求失败：{str(err)}")
        return None


def plagiarism_detection(paper_text):
    api_input = f"请评估以下论文的抄袭可能性（0 - 100分，0 = 无抄袭，100 = 完全抄袭）：{paper_text}"
    result = call_api(api_input)

    if not result:
        print("API请求失败，原创性评分设为0")
        return 0, "API请求失败"

    response_text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
    # 调整正则表达式以匹配新的响应文本

    match = re.search(r'抄袭可能性为\s*(\d+)\s*分', response_text)
    if not match:
        print(f"未找到抄袭分数，响应文本：{response_text}")
        return 0, "未匹配到抄袭分数"

    try:
        score = int(match.group(1))
        return 100 - score, "成功"  # 原创分 = 100 - 抄袭分
    except ValueError:
        print(f"抄袭分数格式错误：{match.group(1)}")
        return 0, "分数格式错误"


def format_check(paper_text):
    score = 0
    status = "成功"

    # 检查是否有明显章节标题（如"引言"、"案例分析"等）
    chapter_titles = ["引言", "案例分析", "总结", "讨论"]
    has_chapter = any(title in paper_text for title in chapter_titles)
    if has_chapter:
        score += 20  # 章节标题分（替代Markdown的#和##）
    else:
        status += " | 无明显章节标题"

    # 段落空行检查（段落间至少1空行，10分）
    if re.search(r'\n\n', paper_text):
        score += 10
    else:
        status += " | 段落无空行"

    # 标点规范检查（中文标点，10分）
    if re.search(r'[，。；：“”（）]', paper_text):
        score += 10
    else:
        status += " | 无中文标点"

    return score, status


def content_quality(paper_text):
    api_input = f"请评估以下论文的内容质量（0 - 100分）：{paper_text}"
    result = call_api(api_input)

    if not result:
        print("API请求失败，内容质量评分设为0")
        return 0, "API请求失败"

    response_text = result.get('choices', [{}])[0].get('message', {}).get('content', '')

    # 修改后的正则表达式（使用非捕获组，分数在group(1)）
    match = re.search(
        r'(?:内容质量(?:评估)?(?:可以打|评为|为|：)|可以给到|综合评分为?|论文(?:可以|的评分)?)\D*(\d+)\s*分',
        response_text
    )

    if not match:
        print(f"未找到内容质量分数，响应文本：{response_text}")
        return 0, "未匹配到内容质量分数"

    try:
        return int(match.group(1)), "成功"  # 直接提取第一个捕获组的数字
    except (IndexError, ValueError) as e:
        print(f"内容质量分数提取失败：{str(e)}，匹配组：{match.groups()}")
        return 0, "分数格式错误"

def citation_verification(paper_text):
    score = 0
    status = "成功"

    # 引用数量（至少1个，10分）：考虑诗句引用等形式
    citations = re.findall(r'[“‘](.*?)[”’]', paper_text)  # 匹配引号内的内容作为引用
    if len(citations) >= 1:
        score += 10
    else:
        status += f" | 引用数量不足（当前{len(citations)}个）"

    # 引用格式（通用标准，10分）：只要有引用即算通过
    if len(citations) > 0:
        score += 10
    else:
        status += " | 无有效引用"

    # 参考文献列表（存在独立章节，10分）：检查是否有"参考文献"标题
    if re.search(r'参考文献', paper_text, re.M):
        score += 10
    else:
        status += " | 无参考文献章节"

    return score, status


def comprehensive_score(paper_text):
    """计算综合评分，并返回各维度详情"""
    # 各维度原始得分及状态
    plagiarism_score, plagiarism_status = plagiarism_detection(paper_text)
    format_score, format_status = format_check(paper_text)
    content_score, content_status = content_quality(paper_text)
    citation_score, citation_status = citation_verification(paper_text)

    # 加权计算
    weights = {
        "plagiarism": 0.3,
        "format": 0.2,
        "content": 0.4,
        "citation": 0.1
    }
    weighted_plagiarism = plagiarism_score * weights["plagiarism"]
    weighted_format = format_score * weights["format"]
    weighted_content = content_score * weights["content"]
    weighted_citation = citation_score * weights["citation"]
    total_score = round(weighted_plagiarism + weighted_format + weighted_content + weighted_citation, 2)

    # 返回各维度详情
    return {
        "plagiarism": {
            "原始得分": plagiarism_score,
            "状态": plagiarism_status,
            "加权得分": weighted_plagiarism
        },
        "format": {
            "原始得分": format_score,
            "状态": format_status,
            "加权得分": weighted_format
        },
        "content": {
            "原始得分": content_score,
            "状态": content_status,
            "加权得分": weighted_content
        },
        "citation": {
            "原始得分": citation_score,
            "状态": citation_status,
            "加权得分": weighted_citation
        },
        "total": total_score
    }


def main():
    print("请输入需要评分的论文内容（输入'END'结束）：")
    paper_lines = []
    while True:
        line = input()
        if line.strip().upper() == 'END':
            break
        paper_lines.append(line)
    paper_text = '\n'.join(paper_lines)

    if not paper_text.strip():
        print("错误：输入内容为空")
        return

    # 获取各维度评分详情
    score_details = comprehensive_score(paper_text)

    # 打印各阶段分数
    print("\n===== 论文评分详情 =====")
    print(
        f"1. 原创性评分：\n   原始得分：{score_details['plagiarism']['原始得分']}\n   状态：{score_details['plagiarism']['状态']}\n   加权得分（30%）：{score_details['plagiarism']['加权得分']}")
    print(
        f"2. 格式规范性评分：\n   原始得分：{score_details['format']['原始得分']}\n   状态：{score_details['format']['状态']}\n   加权得分（20%）：{score_details['format']['加权得分']}")
    print(
        f"3. 内容质量评分：\n   原始得分：{score_details['content']['原始得分']}\n   状态：{score_details['content']['状态']}\n   加权得分（40%）：{score_details['content']['加权得分']}")
    print(
        f"4. 引用规范性评分：\n   原始得分：{score_details['citation']['原始得分']}\n   状态：{score_details['citation']['状态']}\n   加权得分（10%）：{score_details['citation']['加权得分']}")
    print(f"\n论文综合评分为：{score_details['total']} 分")


if __name__ == "__main__":
    main()