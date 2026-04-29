# 图书馆智能问答与推荐系统开发与部署文档

本文档提供了基于图增强检索生成（Graph RAG）架构的图书馆智能问答系统的完整搭建、开发与运行流程。系统实现了从底层知识图谱检索到上层大模型自然语言生成的全链路闭环，并支持前端可视化页面的 API 接入。

---

## 1. 系统架构与核心技术栈

本系统采用微服务解耦架构，各模块通过网络端口进行通信：

* **前端展示层**: Vue.js 3 + Axios (运行于 8080 端口)，通过 REST API 与后端通信。
* **对话控制层**: Rasa Open Source 3.x (运行于 5005 端口)，负责意图识别 (NLU)、实体提取与多轮对话状态追踪。
* **业务逻辑层**: Rasa Action Server (运行于 5055 端口)，作为中间件执行 Python 脚本，桥接数据库与大模型。
* **图谱数据层**: Neo4j 图数据库 (运行于 7687 端口)，存储"书籍-介绍-作者-类别-研究方向"本体网络。
* **自然语言生成层**: Ollama (运行于 11434 端口)，本地部署 Qwen3.1 大语言模型，负责将检索到的结构化数据转化为自然的人性化回复。

---

## 2. 环境依赖与安装指引

建议在独立的 Python 虚拟环境（Python 3.9）中进行部署，以避免依赖冲突。

### 2.1 基础环境初始化

# 创建并激活虚拟环境
python3 -m venv library_env
source library_env/bin/activate  # Windows使用: library_env\Scripts\activate

# 升级 pip 并安装核心组件
pip install --upgrade pip
pip install rasa neo4j requests

### 2.2 部署 Neo4j 数据库

提供两种启动方式，推荐使用 Docker 以保证环境一致性：

Docker 方式:
docker run --name neo4j_library -p 7474:7474 -p 7687:7687 -d -e NEO4J_AUTH=neo4j/12345678 neo4j:latest

本地压缩包方式:
cd neo4j-community-4.4.3/bin
./neo4j console

注：可视化管理界面地址为 http://localhost:7474，代码连接端口为 7687。

### 2.3 部署 Ollama 大模型推理服务

前往 Ollama 官网安装客户端。在终端拉取并后台运行模型：
ollama run qwen
---

## 3. 标准项目目录结构

在使用 rasa init 初始化项目后，必须严格遵守以下目录规范。特别注意：Rasa 核心配置文件必须放置在项目根目录，不可移入子文件夹，否则会导致编译与运行失败。

```text

library_graph_rag/
├── data/                       # Rasa NLU与对话流训练数据
│   ├── nlu.yml                 # 意图分类与实体标注语料
│   ├── rules.yml               # 确定性对话规则
│   └── stories.yml             # 上下文对话流示例
├── actions/                    # 业务逻辑服务模块 (Action Server)
│   ├── __init__.py
│   ├── actions.py              # 动作分发与槽位管理调度中心
│   ├── neo4j_connector.py      # 图谱 Cypher 查询封装
│   └── llm_server.py           # 大模型 Prompt 构建与 API 调用
├── kg_module/                  # 知识图谱独立构建模块
│   ├── schema_cypher.py        # 数据库节点唯一性约束初始化
│   ├── import_data.py          # 结构化数据批量导入脚本
│   └── raw_data/               
│       └── books.csv           # 原始书籍数据底表
├── frontend/                   # 前端工程目录
│   └── lib_agent_vue/          # Vue.js 源码
├── config.yml                  # [核心] Rasa NLU 管道与策略配置
├── domain.yml                  # [核心] 意图、实体、槽位及动作的全局声明
├── endpoints.yml               # [核心] 外部服务路由 (Action Server 等)
├── credentials.yml             # [核心] 接入渠道配置 (REST API 等)
└── requirements.txt            # Python 依赖清单

```
---

## 4. 核心逻辑实现与避坑指南

### 4.1 知识图谱检索逻辑升级 (neo4j_connector.py)

为避免用户提问的领域词汇在"研究方向 (Topic)"或"类别 (Category)"中产生匹配遗漏，Cypher 查询语句需支持多关系链路的模糊匹配。

cypher_query = """
MATCH (b:Book)-[:COVERS_TOPIC|BELONGS_TO]->(node)
WHERE node.name CONTAINS $topic
RETURN DISTINCT b.title AS title, b.summary AS summary, b.rating AS rating
ORDER BY b.rating DESC
LIMIT 3
"""

注意：必须使用 DISTINCT 关键字，防止当一本书同时满足两个条件时产生重复数据返回。

### 4.2 意图识别的泛化增强 (data/nlu.yml)

为确保 NLU 引擎能够准确提取实体，训练语料必须包含长句和短句（尤其是常见的短指令形式），否则会导致实体提取失败。

version: "3.1"
nlu:
  - intent: recommend_by_topic
    examples: |
      - 我想看关于[人工智能](topic)的研究书籍
      - 帮我找几本[赛博朋克](topic)相关的书
      - 搜索研究方向是[人工智能](topic)的文献
      - 查询[科幻](topic)类书籍
      - [计算机科学](topic)类书籍
      - 找一本[科幻](topic)小说
      - 查询[计算机科学](topic)

### 4.3 槽位内存泄漏的处理 (actions.py)

Rasa 默认会记忆之前提取到的实体槽位（Slot）。为防止"跨轮对话污染"（即用户输入新话题时，系统由于未识别出新实体而沿用旧话题），必须在单次动作执行完毕后强制清空槽位。

from rasa_sdk.events import SlotSet

class ActionRecommendByTopic(Action):
    def name(self) -> Text:
        return "action_recommend_by_topic"

    def run(self, dispatcher, tracker, domain):
        # ... (获取数据与调用 LLM 逻辑) ...
        
        dispatcher.utter_message(text=reply)
        # 核心修复：执行完本次动作后，清空 topic 槽位，避免影响下一轮对话
        return [SlotSet("topic", None)]

### 4.4 前端 REST API 通道开启

必须在 credentials.yml 中显式开启 REST 通道，允许前端通过 HTTP 请求进行交互：

rest:
  # 留空即代表启用默认的 REST webhook 接口

---

## 5. 系统启动与联调规范

系统组件存在明确的依赖关系，必须按照以下顺序依次启动。建议开启四个独立的终端窗口。

步骤一：启动底层服务
确保 Neo4j 数据库运行正常，且 Ollama 推理服务在后台监听 11434 端口。

步骤二：启动业务中间件 (Action Server)
在项目根目录运行以下命令，启动自定义动作服务。
rasa run actions

验证标准：终端输出 Action endpoint is up and running on http://0.0.0.0:5055

步骤三：启动 Rasa 核心 API 服务
在项目根目录运行以下命令，将 Rasa 以 API 模式启动。必须携带跨域参数，否则前端请求会被浏览器 CORS 策略拦截。
rasa run --enable-api --cors "*"

验证标准：终端输出 Rasa server is up and running on http://0.0.0.0:5005

步骤四：启动前端项目
进入前端工程目录并启动本地开发服务器。
cd frontend/lib_agent_vue
npm install
npm run serve

访问地址：在浏览器中打开 http://localhost:8080 即可与系统进行对话测试。

---

## 6. 常见故障排查表 (Troubleshooting)

| 故障现象 | 根本原因分析 | 解决路径 |
| :--- | :--- | :--- |
| 执行 Action 提示 no endpoint is configured | Rasa 主进程找不到动作服务器的地址。 | 打开 endpoints.yml，取消 action_endpoint 的注释，设置 url: "http://localhost:5055/webhook"。 |
| 执行 Action 报 AuthError (Unauthorized) | Python 连接 Neo4j 数据库的密码错误。 | 检查 actions/neo4j_connector.py 中的 PASSWORD 变量，确保与启动 Docker 时设置的密码完全一致。 |
| 系统一直卡在旧的检索词上重复回复 | 槽位未能正确重置或新实体提取失败。 | 1. 确认 actions.py 返回了 [SlotSet("topic", None)]。2. 在 nlu.yml 中补充用户实际使用的短句语料并重新执行 rasa train。 |
| 前端无法收到回复或控制台报 CORS 错误 | 未以 API 模式启动或未配置跨域允许。 | 确保启动 Rasa 的命令为 rasa run --enable-api --cors "*"。 |
| 运行时提示模型或配置文件缺失 | 配置文件未在项目根目录。 | 将 config.yml、domain.yml、endpoints.yml 移至项目顶级目录，切勿放在自定义的子文件夹中。 |