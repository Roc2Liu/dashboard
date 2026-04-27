import json
import requests
import os
import hashlib

# 1. 计算指纹
def get_data_fingerprint():
    signals = ""
    # 路径统一为根目录
    for filename in ['./bangumi.json', './movies.json']:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    for item in data[:20]:
                        signals += f"{item.get('title','')}:{item.get('new_ep',{}).get('index_show','')}"
                except:
                    continue
    return hashlib.md5(signals.encode()).hexdigest() if signals else None

def analyze():
    current_hash = get_data_fingerprint()
    hash_path = './last_hash.txt'
    
    # 检查是否变动
    if os.path.exists(hash_path):
        with open(hash_path, 'r') as f:
            if f.read() == current_hash:
                print(">>> 数据无变动，跳过 AI 分析。")
                return

    # 2. 准备精简数据
    def get_minimal(path):
        if not os.path.exists(path): return []
        with open(path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
            return [{"t": i.get('title',''), "p": i.get('new_ep',{}).get('index_show',''), "s": i.get('styles',[])[:2]} for i in raw[:12]]

    b_data = get_minimal('./bangumi.json')
    m_data = get_minimal('./movies.json')

    api_key = os.getenv("ARK_API_KEY")
    endpoint = os.getenv("ENDPOINT_ID")
    
    if not api_key or not endpoint:
        print("错误：缺少 API Key 或 Endpoint ID")
        return

    # 3. 调用 AI
    prompt = {
        "model": endpoint,
        "messages": [
            {"role": "system", "content": "你是一个毒舌影评人。请根据提供的番剧和电影简报分析我的审美倾向。返回JSON：{'preference_summary': '...', 'weekly_report': '...', 'recommendation': '...'}"},
            {"role": "user", "content": f"番剧:{json.dumps(b_data, ensure_ascii=False)}\n电影:{json.dumps(m_data, ensure_ascii=False)}"}
        ],
        "response_format": { "type": "json_object" }
    }

    try:
        res = requests.post("https://ark.cn-beijing.volces.com/api/v3/chat/completions", 
                           headers={"Authorization": f"Bearer {api_key}"}, json=prompt)
        content = res.json()['choices'][0]['message']['content']
        with open('./ai_report.json', 'w', encoding='utf-8') as f:
            f.write(content)
        with open(hash_path, 'w') as f:
            f.write(current_hash)
        print(">>> AI 分析完成并保存。")
    except Exception as e:
        print(f"AI 分析过程出错: {e}")

if __name__ == "__main__":
    analyze()
