import json
import requests
import os
import hashlib

# 计算当前数据的指纹（只监控标题和进度字符串）
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
    # 1. 检查变动，决定是否调用 AI
    current_hash = get_data_fingerprint()
    hash_path = './public/last_hash.txt'
    
    if os.path.exists(hash_path):
        with open(hash_path, 'r') as f:
            if f.read() == current_hash:
                print(">>> 追番列表与进度未发生实质变动，跳过 AI 分析以节省 Token。")
                return

    # 2. 准备极致精简的数据（只发标题、进度和前2个风格）
    def get_minimal_data(path):
        if not os.path.exists(path): return []
        with open(path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
            return [{"t": i['title'], "p": i.get('new_ep', {}).get('index_show', ''), "s": i.get('styles', [])[:2]} for i in raw[:12]]

    b_list = get_minimal_data('./bangumi.json')
    m_list = get_minimal_data('./movies.json')

    # 3. 调用 AI 接口
    api_key = os.getenv("ARK_API_KEY")
    endpoint = os.getenv("ENDPOINT_ID")
    
    if not api_key or not endpoint:
        print("错误：缺少环境变量 ARK_API_KEY 或 ENDPOINT_ID")
        return

    prompt = {
        "model": endpoint,
        "messages": [
            {
                "role": "system", 
                "content": "你是一个资深影评人。我会提供最近追番(t:标题, p:进度, s:风格)和电影清单。请根据进度变动（如某部番完结了、或新追了某类型片）分析我的审美趋势。返回JSON格式：{'preference_summary': '一句话总结', 'weekly_report': '犀利点评', 'recommendation': '交叉推荐一部作品'}"
            },
            {
                "role": "user", 
                "content": f"番剧数据:{json.dumps(b_list, ensure_ascii=False)}\n电影数据:{json.dumps(m_list, ensure_ascii=False)}"
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
        # 保存结果
        res_json = response.json()['choices'][0]['message']['content']
        with open('./public/ai_report.json', 'w', encoding='utf-8') as f:
            f.write(res_json)
        
        # 只有分析成功才更新指纹
        with open(hash_path, 'w') as f:
            f.write(current_hash)
        print(">>> AI 综合分析完成。")
    except Exception as e:
        print(f"AI 分析失败: {e}")

if __name__ == "__main__":
    analyze()
