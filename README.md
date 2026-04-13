<div align="center">

<img src="docs/banner.png" alt="Hermes WebUI 马鞍" width="800">

# Hermes WebUI — 马鞍 Saddle

**The Saddle for Hermes — 给你的本地 AI Agent 一张脸**  
*Give your local AI agent a face*

[![License: MIT](https://img.shields.io/badge/License-MIT-cyan.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org)
[![Hermes](https://img.shields.io/badge/Hermes-Agent-purple.svg)](https://github.com/NousResearch/hermes-agent)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-green.svg)](https://ollama.ai)

</div>

---

## 这是什么？/ What is this?

[Hermes](https://github.com/NousResearch/hermes-agent) 是一个强大的开源 AI Agent，但它只能在终端里用。**Hermes WebUI（马鞍）** 给它加了一个好看的网页界面——你可以在浏览器里驱动 Agent 执行任务，编辑它的记忆，管理它的技能，还能给它起名字、换头像、改主题色。

[Hermes](https://github.com/NousResearch/hermes-agent) is a powerful open-source AI Agent that lives in the terminal. **Hermes WebUI** gives it a proper web interface — drive the agent to execute real tasks in the browser, edit its memory, manage skills, and make it truly yours with a custom name, avatar, and color theme.

> **Hermes WebUI 不替代 Hermes，它是你使用 Hermes 的界面。**  
> *Hermes WebUI doesn't replace Hermes — it's the interface you use it through.*

### 🤖 真正的 Agent，不只是聊天 / Real Agent, Not Just Chat

WebUI 直接调用本地 Hermes CLI，让 Agent 真正执行操作：

- 📁 **文件操作** — 创建、读取、修改文件
- 💻 **代码执行** — 运行 Python、Bash 脚本
- 🌐 **浏览器控制** — 自动化网页操作
- 🧠 **任务规划** — 多步骤任务自动完成
- 🔧 **技能调用** — 使用所有已安装的 Hermes Skills

只需在运行 WebUI 的机器上安装 Hermes，WebUI 就会自动检测并启用 Agent 模式。

*The WebUI calls the local Hermes CLI directly, enabling real agent actions — file operations, code execution, browser control, and more. Install Hermes on the same machine as the WebUI, and Agent mode activates automatically.*

---

## 截图 / Screenshots

<div align="center">
<img src="docs/screenshot.png" alt="Hermes WebUI Screenshot" width="800">
</div>

---

## 核心亮点 / Highlights

### 🧠 与 Hermes CLI 共享同一个大脑
WebUI 和命令行读写的是**完全相同的文件**。在网页里改了记忆，终端里立刻生效；在终端里跑了任务，网页里也能看到。没有同步延迟，没有数据孤岛。

**Shares the same brain as Hermes CLI.** The WebUI and CLI read/write the exact same files. Edit memory in the browser, see it in the terminal instantly — and vice versa. No sync delay, no data silos.

### 🎨 完全属于你的 Agent 身份
给你的 Agent 起任何名字（支持中文、emoji、符号），上传任意头像，从 5 种主题色中选一个或者自定义颜色。整个界面会实时跟着变。

**A fully personalized agent identity.** Name it anything — Chinese, emoji, symbols all work. Upload any avatar. Pick from 5 color themes or go fully custom. The entire UI updates in real-time.

### 🔒 100% 本地运行，数据不出门
所有数据存在你自己的机器上（`~/.hermes/` 和 `~/.hermes-webui/`），没有云端服务器，没有账号注册，没有数据上传。断网也能用。

**Runs 100% locally.** All data lives on your machine (`~/.hermes/` and `~/.hermes-webui/`). No cloud server, no account, no data upload. Works offline.

### 🤖 支持所有 Ollama 模型
Gemma、Llama、Qwen、DeepSeek……只要 Ollama 能跑的模型，Hermes WebUI 都支持，随时切换，无需重启。

**Works with any Ollama model.** Gemma, Llama, Qwen, DeepSeek — if Ollama can run it, Hermes WebUI supports it. Switch models on the fly without restarting.

### ⚡ 一键启动，开箱即用
Windows 双击 `start-windows.bat`，Linux/Mac 运行 `./scripts/start.sh`，自动创建虚拟环境、安装依赖、启动服务。

**One-click start.** Double-click `start-windows.bat` on Windows or run `./scripts/start.sh` on Linux/Mac. Auto-creates venv, installs deps, starts the server.

### 🚀 即开即用 / Zero-Config Setup

**Windows 和 macOS 均提供全自动安装向导**，只需一步操作，自动完成环境检测、依赖安装、模型配置：

*Both Windows and macOS provide fully automated setup wizards — one click and everything is configured automatically.*

#### 🪟 Windows 安装流程

```
双击 start-windows.bat
    ↓
[1] 检测 WSL2 → 如未安装，提示安装方法
    ↓
[2] 检测 Hermes → 自动 pip3 install hermes-agent
    ↓
[3] 检测 Ollama → 自动 curl -fsSL https://ollama.com/install.sh | sh
    ↓
[4] 检测模型 → 提示选择 gemma3:4b/12b 或 llama3.2:3b，自动下载
    ↓
[5] 启动 WebUI → 自动打开浏览器访问 localhost:8080
```

**Windows 特点：**
- ✅ WSL2 自动检测与路径转换（`C:\` → `/mnt/c/`）
- ✅ Hermes CLI 自动安装
- ✅ Ollama 自动安装与启动
- ✅ 模型自动下载与管理
- ✅ 支持远程 Ollama 服务器配置

#### 🍎 macOS 安装流程

```
运行 ./scripts/install.sh
    ↓
[1] 检测硬件 → Apple Silicon/Intel、内存、Metal GPU
    ↓
[2] 性能评分 → 计算配置得分，判断本地/远程模式
    ↓
[3] 安装 Ollama → 自动下载安装（可选）
    ↓
[4] 智能推荐 → 根据配置推荐最优模型
    ↓
[5] 配置远程 → 低配机型可选择局域网 Ollama 服务器
```

**macOS 智能模型推荐：**

| 配置 | 性能评分 | 推荐模型 | 说明 |
|-----|---------|---------|------|
| Apple Silicon + 16GB | 80-100 | gemma3:12b | 充分利用神经网络引擎 |
| Apple Silicon + 8GB | 60-80 | gemma3:4b | 平衡性能与内存 |
| Intel + 16GB | 50-70 | gemma3:4b | 适合大多数任务 |
| Intel + 8GB | 30-50 | llama3.2:3b | 轻量级，响应快 |
| 低配/老机型 | <30 | llama3.2:1b 或**远程** | 推荐连接局域网服务器 |

#### 🔗 远程 Ollama 支持

低配机器（如老旧 Mac）可以使用局域网内其他电脑的 Ollama：

**Windows:** 运行 `start-windows.bat` 时选择「使用远程 Ollama」
**macOS:** 安装脚本自动检测低配置，提示选择远程模式
**手动配置:** 编辑 `~/.hermes/config.yaml`:

```yaml
ollama_base_url: http://192.168.1.100:11434
```

*Low-powered machines can use a remote Ollama server on your local network. The setup wizard will auto-detect and configure this for you.*

---

## 功能列表 / Features

| 功能 | 说明 |
|------|------|
| 💬 **聊天界面** Chat | 干净的对话界面，支持多会话、历史记录、延迟显示 |
| 🧠 **记忆编辑器** Memory Editor | 直接在浏览器里查看和编辑 SOUL.md、MEMORY.md、USER.md |
| ⚡ **技能浏览器** Skill Browser | 查看所有已安装的 Hermes Skill 及描述，支持 ZIP 导入 |
| 🎨 **动态主题** Dynamic Theme | 5 种预设主题色 + 自定义颜色，实时更新整个界面 |
| 👤 **身份定制** Identity | Agent 名称、头像、副标题，User 名称、头像，全部可配置 |
| 🔄 **模型切换** Model Switcher | 顶栏下拉菜单，随时切换 Ollama 模型 |
| 🌐 **中英双语** i18n | 界面支持中文和英文切换 |
| 🐳 **Docker 支持** Docker | 提供完整的 docker-compose 配置 |
| 🔄 **一键自动更新** Auto-update | Support 页面检测 GitHub 新版本，一键拉取更新 |

---

## 快速开始 / Quick Start

### 环境要求 / Prerequisites

| 组件 | 必需 | 说明 |
|------|------|------|
| [Python 3.10+](https://www.python.org) | ✅ | 运行后端服务 |
| [Ollama](https://ollama.ai) | ✅ | 本地模型推理 |
| [Hermes](https://github.com/NousResearch/hermes-agent) | ✅ **推荐** | Agent 执行引擎（文件操作、代码执行等）|

> **没有 Hermes CLI 也能启动**，但只能查看记忆和技能，无法执行 Agent 任务。  
> *WebUI starts without Hermes CLI, but Agent execution requires it.*

### 安装并启动 / Install & Start

```bash
# 1. 克隆项目
git clone https://github.com/songchao4218/hermes-webui.git
cd hermes-webui

# 2. 启动（首次运行自动安装所有依赖）
# Windows: 双击 start-windows.bat（全自动安装向导）
# macOS:   ./scripts/install.sh（智能硬件检测+模型推荐）
# Linux:   ./scripts/start.sh
```

**启动方式 / Launch:**

| 平台 | 命令 | 说明 |
|-----|------|------|
| Windows | 双击 `start-windows.bat` | 全自动向导：检测 WSL2 → 安装 Hermes → 安装 Ollama → 下载模型 → 启动服务 |
| macOS | `./scripts/install.sh` | 智能检测：硬件评分 → 推荐模型 → 自动安装 → 配置远程（可选）|
| Linux | `./scripts/start.sh` | 标准启动，需提前安装 Hermes 和 Ollama |

然后打开浏览器访问 **http://localhost:8080**

*Then open your browser at **http://localhost:8080***

首次启动会进入引导设置向导，帮你配置 Agent 名称、头像和主题色。  
*On first launch, an onboarding wizard guides you through setting up your agent's name, avatar, and theme.*

### 下载模型 / Pull a Model

**Windows/macOS 用户：** 安装向导会自动提示并下载推荐模型。

**Linux/其他平台手动下载：**

```bash
# 推荐
ollama pull gemma3:12b

# 其他选择
ollama pull llama3.2:3b
ollama pull qwen2.5:7b
ollama pull deepseek-r1:8b
```

---

## 记忆系统 / Memory System

Hermes WebUI 直接读写 Hermes 的记忆文件，CLI 和 WebUI 共享同一份数据：

*Hermes WebUI reads and writes Hermes memory files directly — CLI and WebUI share the same data:*

| 文件 | 用途 | 路径 |
|------|------|------|
| `SOUL.md` | Agent 的个性、价值观、行为规则 | `~/.hermes/SOUL.md` |
| `MEMORY.md` | 累积的知识和上下文 | `~/.hermes/memories/MEMORY.md` |
| `USER.md` | 用户信息 | `~/.hermes/memories/USER.md` |

在网页的 Memory 标签页里编辑这些文件，Hermes CLI 会立即看到变化。  
*Edit these in the Memory tab, and Hermes CLI sees the changes immediately.*

---

## 架构 / Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Browser   │────▶│   FastAPI    │────▶│   Ollama    │
│             │◀────│   Backend    │◀────│  (Local)    │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────▼───────┐
                    │  ~/.hermes/  │  ◀── Shared with Hermes CLI
                    │  ├─ SOUL.md  │
                    │  ├─ memories/│
                    │  ├─ skills/  │
                    │  └─ state.db │
                    └──────────────┘
                           │
                    ┌──────▼───────┐
                    │  ~/.hermes-webui/│  ◀── Hermes WebUI config & identity
                    │  ├─ persona.json
                    │  ├─ avatar/  │
                    │  └─ sessions/│
                    └──────────────┘
```

---

## 配置 / Configuration

Hermes WebUI 会自动读取 Hermes 的配置，通常不需要手动配置。如需自定义：

*Hermes WebUI auto-detects settings from Hermes config. For manual overrides:*

```yaml
# config/hermes-webui.yaml 或 ~/.hermes-webui/config.yaml

server:
  host: 0.0.0.0
  port: 8080

# 手动指定 Ollama 地址（远程服务器或 WSL 网络）
ollama_url: http://192.168.1.100:11434
```

### Docker / Docker Compose

```bash
docker-compose up -d
# WebUI: http://localhost:8080
# Ollama: http://localhost:11434
```

---

## 项目结构 / Project Structure

```
hermes-webui/
├── backend/
│   ├── app.py              # FastAPI 后端，所有 API 接口
│   ├── hermes_bridge.py    # 与 Hermes 记忆/技能系统的桥接层
│   ├── wsl_bridge.py       # WSL2 Windows 路径转换桥接
│   └── requirements.txt
├── frontend/
│   ├── index.html          # 单文件前端（聊天、技能、记忆、设置）
│   └── assets/
│       └── i18n.js         # 国际化文本
├── config/
│   └── hermes-webui.yaml   # 配置模板
├── scripts/
│   ├── install.sh          # 跨平台安装脚本（自动检测 WSL/macOS/Linux）
│   ├── install-macos.sh    # macOS 专用安装向导（硬件检测+模型推荐）
│   └── start.sh            # 启动脚本
├── docs/
│   ├── DESIGN.md           # UI 设计系统文档
│   └── banner.png
├── start-windows.bat       # Windows 完整安装向导（自动安装 Hermes/Ollama/模型）
├── start.bat               # Windows 简单启动（旧版）
└── docker-compose.yml
```

---

## 路线图 / Roadmap

- [x] 聊天界面 + 记忆同步
- [x] Agent / User 身份定制（名称、头像、主题色）
- [x] 引导式设置向导
- [x] 记忆编辑器（SOUL.md / MEMORY.md / USER.md）
- [x] 技能浏览器 + ZIP 导入
- [x] 模型切换器
- [x] 多会话 + 历史持久化
- [x] 动态主题引擎
- [x] Docker 支持
- [x] 中英双语界面
- [x] 流式响应（SSE）
- [x] **Windows 全自动安装向导**（WSL2 + Hermes + Ollama + 模型）
- [x] **WSL2 Windows 路径自动转换**
- [x] **macOS 即开即用**（硬件检测 + 智能模型推荐 + 远程 Ollama）
- [x] **一键自动更新**（Support 页面检测并拉取 GitHub 最新版本）
- [ ] 语音输入 / 输出
- [ ] 移动端适配

---

## 致谢 / Credits

- [Hermes](https://github.com/NousResearch/hermes-agent) — Agent 框架
- [Ollama](https://ollama.ai) — 本地模型推理
- [FastAPI](https://fastapi.tiangolo.com) — 后端框架
- [Tailwind CSS](https://tailwindcss.com) — 前端样式
- [Google Stitch](https://stitch.withgoogle.com) — UI 设计灵感

---

## 许可证 / License

MIT — 随便用，随便改。详见 [LICENSE](LICENSE)。  
*MIT — use it, fork it, build on it. See [LICENSE](LICENSE).*

---

<div align="center">

**你的 Agent，你的数据，你的机器。**  
*Your agent. Your data. Your machine.*

</div>
