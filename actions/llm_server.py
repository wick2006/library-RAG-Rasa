import requests
import json

def generate_ollama_reply(topic, kg_context):
    print("-> 正在调用 Ollama 生成回复...")
    
    prompt = f"""
    你是一个专业的图书馆智能助理。用户正在寻找关于【{topic}】方向的书籍。
    我从图书馆知识图谱中为你检索到了以下真实的书籍资料：
    {json.dumps(kg_context, ensure_ascii=False, indent=2)}
    
    请根据以上资料，用自然、专业且友好的语气向用户推荐。
    要求：
    1. 必须基于提供的资料进行推荐，绝对不能虚构或编造图谱中没有的书籍。
    2. 顺便提一下书籍的作者，评分和亮点简介。
    3. 排版清晰，可以直接给用户阅读。
    """
    
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "qwen",  # 本地模型名称
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json().get("response", "抱歉，我大脑卡壳了，请稍后再试。")
    except Exception as e:
        print(f"Ollama 请求失败: {e}")
        # 兜底逻辑：如果大模型挂了，直接把结构化数据扔给用户
        return f"[系统提示：大模型服务未开启，回退为结构化数据]\n为您找到以下书籍：\n{kg_context}"


def generate_author_reply(author_name, kg_context):
    print("-> 正在调用 Ollama 生成作者介绍...")
    
    prompt = f"""
    你是一个专业的图书馆助理。用户正在询问关于作家/学者【{author_name}】的信息。
    我从知识图谱中为你提取了该作者的全方位档案（包含生平、馆藏著作以及与其他人物的关联）：
    
    {json.dumps(kg_context, ensure_ascii=False, indent=2)}
    
    请根据以上资料，为用户生成一段专业、生动的人物介绍。
    要求：
    1. 必须提及作者的主要研究领域和生平亮点。
    2. 如果该作者有馆藏著作，请顺带推荐。
    3. 重点：如果资料中提到了该作者与其他人物的关联（如受谁影响、与谁同领域等），请以“学术脉络”或“趣闻”的形式巧妙地融入回答中，展现知识图谱的深度。
    4. 严禁编造资料中未提供的书籍或人物关系。
    """
    
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "qwen2.5:7b",
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json().get("response", "抱歉，生成回复时出现错误。")
    except Exception as e:
        print(f"Ollama 请求失败: {e}")
        return f"[系统提示：大模型服务未开启]\n查找到作者资料：\n{kg_context}"