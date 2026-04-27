import json
import requests
import os
import hashlib

# 计算数据指纹（用于判断是否变动）
def get_data_fingerprint():
    signals = ""
    for filename in ['./bangumi.json', './movies.json']:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 监控前20个项目的标题+进度变动
                for item in data[:20]:
                    title = item.get('title', '')
                    progress = item.get('new_ep', {}).get('index_show', '')
                    signals += f"{title}:{progress}"
    if not signals: return None
    return hashlib.md5(signals.encode()).hexdigest()

def analyze():
    current_hash = get_data_fingerprint()
    hash_path = './last_hash.txt' # 放在根目录
    
    if os.path.exists(hash_path):
        with open(hash_path, 'r') as f:
            if f.read() == current_hash:
                print(">>> 追番进度未变动，跳过 AI 分析。")
                return

    # 提取精简信息
    def get_minimal_data(path):
        if not os.path.exists(path): return []
        with open(path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
            return [{"t": i['title'], "p": i.get('new_ep', {}).get('index_show', ''), "s": i.get('styles', [])[:2]} for i in raw[:12]]

    b_list = get_minimal_data('./bangumi.json')
    m_list = get_minimal_data('./movies.json')

    api_key = os.getenv("ARK_API_KEY")
    endpoint = os.getenv("ENDPOINT_ID")
    
    prompt = {
        "model": endpoint,
        "messages": [
            {
                "role": "system", 
                "content": "你是一个影评人。请根据提供的番剧和电影简报(t:标题, p:进度, s:风格)分析审美倾向。返回JSON：{'preference_summary': '...', 'weekly_report': '...', 'recommendation': '...'}"
            },
            {
                "role": "user", 
                "content": f"番剧:{json.dumps(b_list, ensure_ascii=False)}\n电影:{json.dumps(m_list, ensure_ascii=False)}"
            }
        ],
        "response_format": { "type": "json_object" }
    }

    try:
        response = requests.post(
            "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=prompt
        )
        res_json = response.json()['choices'][0]['message']['content']
        # 结果存放在根目录
        with open('./ai_report.json', 'w', encoding='utf-8') as f:
            f.write(res_json)
        
        with open(hash_path, 'w') as f:
            f.write(current_hash)
        print(">>> AI 分析完成。")
    except Exception as e:
        print(f"失败: {e}")

if __name__ == "__main__":
    analyze()
