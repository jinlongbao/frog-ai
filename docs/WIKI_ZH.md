# Frog AI - 官方中文维基

欢迎来到 Frog AI 官方文档！Frog AI 是一个深度自治、跨平台的个人 AI 智能体应用。它不仅仅是一个聊天的“玩具”，更是一个**原生的桌面级专家**，能够主动**规划、执行、记忆并自我进化**。

---

## 📖 目录
1. [系统底层架构](#1-系统底层架构)
2. [插件开发规范 (`tool_writer`)](#2-插件开发规范)
3. [系统内置核心能力](#3-系统内置核心能力)
4. [远程控制与通信集成](#4-远程控制与通信集成)

---

## 1. 系统底层架构
Frog AI 采用了高速解耦的架构设计，由后端的 Python 核心推理引擎 (`frog-core`) 和前端的 Electron 显示层 (`frog-shell`) 组成。

### 无管道沙盒引擎 (Pipeless Subprocess Sandbox)
为了执行 AI 自动生成的代码而不污染宿主机系统或导致 UI 卡顿，Frog AI 使用了极其严苛的子进程沙盒引擎。
- Python 插件绝对隔离运行。
- 大量的数据通信放弃了容易产生死锁的传统管道，改为物理磁盘丢包 (`stdout.txt`)。
- 强制性的 30 秒硬件资源热熔断机制，彻底杜绝僵尸进程。

---

## 2. 插件开发规范
Frog AI 原生支持热插拔功能。如果 AI 发现自己缺少某种能力，它可以自动调用代码引擎，将自己写的跨平台 Python 脚本打包入 `generated_tools/` 目录中。

### 插件结构
一个标准的插件通常需要包含两个文件：
* `manifest.json`: 向大语言模型 (LLM) 声明该工具的名称、用途和需要的参数。
* `index.py`: 实际的执行沙盒逻辑。

**Manifest 规范 (JSON Schema):**
```json
{
  "id": "my_tool",
  "name": "我的自定义工具",
  "description": "做一些很棒的事情。",
  "version": "1.0.0",
  "entry": "index.py",
  "parameters": {
    "type": "object",
    "properties": {
      "target": { "type": "string", "description": "处理目标。" }
    },
    "required": ["target"]
  }
}
```

**Index.py 规范:**
```python
def execute(params: dict, context: dict) -> dict:
    target = params.get("target")
    return {"status": "success", "result": f"目标已锁定: {target}"}
```

---

## 3. 系统内置核心能力

Frog AI 出厂即自带了一套“专家”级别的核心宏技能：
- **`fs_expert`**: 安全地跨操作系统边界进行目录搜索、文件读取与处理。
- **`shell_executor`**: 在宿主机上异步、安全地执行 bash / powershell 指令。
- **`document_generator`**: 绕过繁琐的代码拼接，直接向桌面输出排版精美的 `.docx` 或 `.pptx` 报告。
- **`gui_expert`**: 系统底层键鼠模拟，不仅能盲打输出，还可以绕过中英文剪贴板障碍。
- **`eyes_expert`**: 原生的屏幕视觉捕获器，将本地电脑转化为多模态 AI 可视的桌面画布。

---

## 4. 远程控制与通信集成

### Telegram 远程操控
Frog AI 原生打通了 Telegram Bot API，使它成为你可以随身携带的超级指令台。
* 您发送给认证机器人的任何文本指令，都会在您家里的 PC 上触发本底 `ReAct` 自治引擎。
* **`send_telegram_file`**: 当你请求获取桌面文件时，Frog 会先调用 `fs_expert` 寻找该文件的物理路径，然后通过底层的照片/文件管道秒传回你的手机端！

### 企业微信与其他通信集成
借助标准的 Webhook 规范和通用的 `messenger_bot` 架构，Frog 能够轻易被整合进各种企业的内部通知流。

---
*Wiki 结束。环境配置与部署流程，请移步官方 `README.md`。*
