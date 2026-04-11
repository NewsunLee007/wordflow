# 预置数据生成脚本说明

本脚本用于在**发布给学生/课堂之前**，通过您的电脑联网并使用 DeepSeek API 批量预生成所有词汇的 AI 教学解析内容。
生成的离线数据将被打包进 `data/prebuilt_data.js` 文件，使得课堂电脑在**无需填写 API Key**、甚至**弱网环境**下也能直接流畅展示教学图谱。

## 前置条件

1. 确保您的电脑已安装 Python 3 (推荐 Python 3.8+)。
2. 将您准备好的 CSV 文件（文件名：`外研版七年级下册_全册词表_导入版.csv`）放到程序的根目录下（即与本 README 所在的 `scripts` 目录的上一级目录）。
   *CSV格式要求包含前8列：教材, 年级, 学期, 单元, 单词, 释义, 音标, 词性*。

## 运行步骤

1. 打开终端（Terminal / CMD）。
2. 进入本 `scripts` 目录。
3. 设置您的 DeepSeek API Key 环境变量：
   - macOS / Linux: 
     ```bash
     export DEEPSEEK_API_KEY="sk-您的API密钥"
     ```
   - Windows (CMD):
     ```cmd
     set DEEPSEEK_API_KEY=sk-您的API密钥
     ```
   - Windows (PowerShell):
     ```powershell
     $env:DEEPSEEK_API_KEY="sk-您的API密钥"
     ```
4. 运行脚本：
   ```bash
   # 默认模式（标准模式，生成3条例句）
   python prebuild_ai.py

   # 精简模式（生成2条例句，适合课堂快节奏）
   python prebuild_ai.py --mode simple

   # 详细模式（生成4条例句，解析更详细，适合备课）
   python prebuild_ai.py --mode detailed
   ```

## 断点续跑
脚本每次生成一个单词的解析后，会**增量保存**到 `../data/prebuilt_data.js` 中。
如果因为网络原因或 API 额度限制中断了脚本，您可以直接再次运行上述命令。脚本会自动读取已生成的数据，**自动跳过已成功的单词**，继续生成失败或未生成的单词。

## 常见问题
- **Q: 提示找不到 CSV 文件？**
  A: 请确保您把 CSV 文件放在了 `scripts/` 的上一层目录，并且文件名为 `外研版七年级下册_全册词表_导入版.csv`。
- **Q: 预生成后的图片和语音怎么办？**
  A: 当前生成的 JS 数据中 `window.__IMAGE_MAP__` 和 `window.__AUDIO_MAP__` 为空对象。后续若有需要，您可以通过类似的脚本调用 TTS 或文生图接口下载图片/音频资源，并将本地映射关系填入这两个对象即可实现纯离线的图像和语音。