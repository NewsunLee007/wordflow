import argparse
import csv
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import ssl
from pathlib import Path

# 全局忽略 SSL 证书验证 (解决 macOS 下的 CERTIFICATE_VERIFY_FAILED 错误)
ssl._create_default_https_context = ssl._create_unverified_context

# 配置
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
CSV_FILE = "../外研版七年级下册_全册词表_导入版.csv"
OUTPUT_JS = "../data/prebuilt_data.js"
FAILURE_LOG = "../data/prebuild_failures.json"

if not API_KEY:
    print("请先设置 DEEPSEEK_API_KEY 环境变量！")
    print("export DEEPSEEK_API_KEY='你的_sk_xxx'")
    sys.exit(1)

def call_deepseek(word, pos, meaning, mode="normal"):
    examples_count = 3
    detail_instruction = "提供标准深度的解析，语言生动易懂。"
    if mode == "simple":
        examples_count = 2
        detail_instruction = "提供精简的解析，语言简练，适合快速浏览。"
    elif mode == "detailed":
        examples_count = 4
        detail_instruction = "提供极其详细、深入的解析，提供更多背景知识和相关考点，适合教师备课使用。"

    prompt = f"""你是一个专业的初中英语教师，请针对外研版七年级英语单词/短语 "{word}" (词性: {pos}, 释义: {meaning}) 提供一份高质量的教学解析。
请务必只返回合法的JSON对象（不要有markdown代码块等额外文本），严格符合以下结构：
{{
  "emoji": "用1个最生动贴切的emoji表情表示这个词",
  "etymology": "词源与构词法（解释前缀、后缀、词根等，或提供一个有趣的故事帮助记忆。{detail_instruction}）",
  "memory": "趣味记忆法（谐音、联想、顺口溜等。{detail_instruction}）",
  "usage": "核心搭配与考点（列出常考短语、固定搭配或易错点。{detail_instruction}）",
  "examples": [ // 必须提供恰好 {examples_count} 个例句，并包含初中生能理解的语境
    {{
      "en": "适合七年级学生的经典例句(英文)。要求：语境生动，不要太简单，但也别超出初一词汇大纲。", 
      "zh": "地道且自然的中文翻译"
    }} // ... 请提供 {examples_count} 个例句
  ]
}}"""
    data = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that strictly outputs JSON."},
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }).encode("utf-8")

    req = urllib.request.Request("https://api.deepseek.com/v1/chat/completions", data=data)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {API_KEY}")

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                content = res_json["choices"][0]["message"]["content"]
                # 简单清洗 markdown
                content = content.replace("```json", "").replace("```", "").strip()
                return json.loads(content)
        except Exception as e:
            print(f"  [重试 {attempt+1}/3] API 请求失败: {e}")
            time.sleep(2)
            
    return None

def main():
    parser = argparse.ArgumentParser(description="批量预生成单词的 AI 解析数据")
    parser.add_argument("--mode", choices=["simple", "normal", "detailed"], default="normal", help="AI 生成的详略模式")
    args = parser.parse_args()
    mode = args.mode

    csv_path = Path(__file__).parent / CSV_FILE
    if not csv_path.exists():
        print(f"找不到词表文件: {csv_path.resolve()}")
        print("请先将 '外研版七年级下册_全册词表_导入版.csv' 放到项目根目录！")
        sys.exit(1)
        
    out_dir = Path(__file__).parent / "../data"
    out_dir.mkdir(exist_ok=True)
    out_js_path = out_dir / "prebuilt_data.js"
    fail_log_path = out_dir / "prebuild_failures.json"

    # 读取已有数据，支持断点续跑
    vocab_list = []
    ai_cache = {}
    
    if out_js_path.exists():
        # 提取 __AI_CACHE__，使用更鲁棒的分隔符避免 JSON 内部含有分号导致截断失败
        try:
            content = out_js_path.read_text("utf-8")
            if "window.__AI_CACHE__ = " in content:
                json_str = content.split("window.__AI_CACHE__ = ")[1].split("\n\nwindow.__IMAGE_MAP__ = ")[0]
                json_str = json_str.strip().rstrip(";")
                ai_cache = json.loads(json_str)
                print(f"已加载 {len(ai_cache)} 条现有缓存。")
        except Exception as e:
            print("读取现有 js 失败:", e)

    failures = []

    # 解析 CSV 
    # 格式：textbook, grade, term, unit, word, meaning, phonetic, pos
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if not row or len(row) < 8: continue
            if i == 0 and ("word" in row[4].lower() or "单词" in row[4]):
                continue # 表头
            
            textbook, grade, term, unit, word, meaning, phonetic, pos = [col.strip() for col in row[:8]]
            item = {
                "textbook": textbook,
                "grade": grade,
                "term": term,
                "unit": unit,
                "word": word,
                "meaning": meaning,
                "phonetic": phonetic,
                "pos": pos
            }
            vocab_list.append(item)

    total = len(vocab_list)
    print(f"CSV 共 {total} 条词汇，开始预生成 AI 解析...")

    for idx, item in enumerate(vocab_list):
        word = item["word"]
        # 使用复合 key 保持与代码 getWordKey 兼容
        # 格式：textbook|grade|term|unit|word
        key = f"{item['textbook']}|{item['grade']}|{item['term']}|{item['unit']}|{item['word']}"
        
        if key in ai_cache:
            print(f"[{idx+1}/{total}] 跳过已生成: {word}")
            continue
            
        print(f"[{idx+1}/{total}] 正在生成: {word} ... ", end="")
        sys.stdout.flush()
        
        res = call_deepseek(word, item["pos"], item["meaning"], mode=mode)
        if res:
            ai_cache[key] = res
            print("成功")
            
            # 每生成 5 个保存一次，防止意外中断
            if (idx + 1) % 5 == 0:
                save_js(vocab_list, ai_cache, out_js_path)
        else:
            print("失败")
            failures.append(word)

    save_js(vocab_list, ai_cache, out_js_path)
    
    if failures:
        with open(fail_log_path, "w", encoding="utf-8") as f:
            json.dump(failures, f, ensure_ascii=False, indent=2)
        print(f"\n生成结束！有 {len(failures)} 个单词失败，已记录到 {fail_log_path}。")
    else:
        print("\n生成结束！全部成功。")

def save_js(vocab_list, ai_cache, path):
    content = f"""// 自动生成的离线数据
window.__VOCAB__ = {json.dumps(vocab_list, ensure_ascii=False, indent=2)};

window.__AI_CACHE__ = {json.dumps(ai_cache, ensure_ascii=False, indent=2)};

window.__IMAGE_MAP__ = {{}};

window.__AUDIO_MAP__ = {{}};
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    main()
