# MOP - Multi-Agent Orchestrator Platform

MOPは、複数のAIエージェント（LLM）が協調してタスクを遂行するためのMCPサーバーです。OpenCodeとCodexの両方で利用可能な汎用MCPサーバーとして設計し、エージェント間の役割分担・通信・成果物の統合を自動化します。

## アーキテクチャ

```
User Request
    │
    ▼
┌─────────────────────────────────────┐
│         MCP Orchestrator Server      │
│  (Python FastMCP / TypeScript SDK)   │
│                                      │
│  tools:                              │
│    decompose_task                    │
│    assign_agent                      │
│    agent_communicate                 │
│    get_task_status                   │
│    submit_artifact                   │
│    review_code                       │
│    merge_results                     │
│                                      │
│  resources:                          │
│    task://{task_id}/status           │
│    agent://{agent_id}/inbox          │
│    artifact://{artifact_id}          │
└─────────────────────────────────────┘
    │           │           │
    ▼           ▼           ▼
 Agent A    Agent B    Agent C
 (Planner)  (Coder)    (Tester)
 Kimi K2.7  Qwen3.7    Mimo v2.5
```

## エージェント構成

| エージェント | モデル | 役割 |
|---|---|---|
| Agent A (Planner) | Kimi K2.7 Code | 全体設計、アーキテクチャ決定、実装指示の管理 |
| Agent B (Coder) | Qwen3.7 Plus | MCPサーバー本体の実装（Python/TypeScript） |
| Agent C (Tester) | Mimo v2.5 Pro | テスト、コードレビュー、検証スクリプト |

## セットアップ

### 1. 仮想環境の作成

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. 依存関係インストール

```bash
pip install -r requirements.txt
```

### 3. MCPサーバー起動

```bash
python src/mcp_entry.py
```

起動すると、stdio経由でMCPサーバーが待機します。

```
╭──────────────────────────────────────────────╮
│              FastMCP 3.4.4                    │
│  🖥  Server: mop                              │
╰──────────────────────────────────────────────╯
INFO  Starting MOP server with transport 'stdio'
```

### 4. OpenCode設定

`~/.config/opencode/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "mop": {
      "type": "local",
      "command": ["python3", "/home/konoha/develop/rade/src/mcp_entry.py"],
      "enabled": true
    }
  }
}
```

### 5. Codex設定

`codex.json`:

```json
{
  "mcpServers": {
    "mop": {
      "command": "python",
      "args": ["src/mcp_entry.py"]
    }
  }
}
```

## プロジェクト構成

```
rade/
├── docs/
│   └── 001-multi-agent-mcp-orchestrator.md
├── src/
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── server.py           # MCPサーバーエントリポイント
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── decompose.py    # decompose_taskツール
│   │   │   ├── assign.py       # assign_agentツール
│   │   │   ├── communicate.py  # agent_communicateツール
│   │   │   ├── status.py       # get_task_statusツール
│   │   │   ├── artifact.py     # submit_artifactツール
│   │   │   ├── review.py       # review_codeツール
│   │   │   └── merge.py        # merge_resultsツール
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── task.py         # Taskモデル定義
│   │   │   ├── agent.py        # Agentモデル定義
│   │   │   └── artifact.py     # Artifactモデル定義
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   ├── task_store.py   # タスクストア実装
│   │   │   └── artifact_store.py # アーティファクトストア実装
│   │   └── orchestrator.py     # コアロジック
│   └── mcp_entry.py            # MCPサーバー起動用エントリ
├── tests/
│   ├── test_decompose.py
│   ├── test_assign.py
│   ├── test_communicate.py
│   ├── test_merge.py
│   └── test_orchestrator.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

## 実装担当

### Agent A — Kimi K2.7 Code（Planner）
- `src/orchestrator/tools/decompose.py` — decompose_task の全実装
- `src/orchestrator/tools/assign.py` — assign_agent の全実装
- `src/orchestrator/tools/merge.py` — merge_results の全実装
- `src/orchestrator/orchestrator.py` — コアロジック（タスク管理、状態遷移、進行管理）
- `src/orchestrator/models/task.py` — Taskモデル定義
- `src/orchestrator/models/agent.py` — Agentモデル定義
- `src/orchestrator/storage/task_store.py` — タスクストア実装

### Agent B — Qwen3.7 Plus（Coder）
- `src/orchestrator/tools/communicate.py` — agent_communicate の全実装
- `src/orchestrator/tools/status.py` — get_task_status の全実装
- `src/orchestrator/tools/artifact.py` — submit_artifact の全実装
- `src/orchestrator/models/artifact.py` — Artifactモデル定義
- `src/orchestrator/storage/artifact_store.py` — アーティファクトストア実装
- `src/orchestrator/server.py` — MCPサーバーエントリポイント（全ツールの登録）
- `src/mcp_entry.py` — サーバー起動用エントリポイント

### Agent C — Mimo v2.5 Pro（Tester）
- `src/orchestrator/tools/review.py` — review_code の全実装
- `tests/test_decompose.py` — decompose_task のテスト
- `tests/test_assign.py` — assign_agent のテスト
- `tests/test_communicate.py` — agent_communicate のテスト
- `tests/test_merge.py` — merge_results のテスト
- `tests/test_orchestrator.py` — 統合テスト
- `pyproject.toml` — プロジェクト設定（テストフレームワーク、依存関係）
- `requirements.txt` — Python依存パッケージ一覧
- `README.md` — プロジェクト概要と実行方法

## MCPツール定義

### decompose_task
- **説明**: ユーザーリクエストをサブタスクに分解する
- **パラメーター**: `request: str` — ユーザーからの要求
- **戻り値**: `Task`（分解結果のルートタスク、subtasksに子タスクIDリスト）

### assign_agent
- **説明**: 特定のタスクをエージェントに割り当てる
- **パラメーター**: `task_id: str`, `agent_id: str`
- **戻り値**: 更新後の`Task`

### agent_communicate
- **説明**: エージェント間でメッセージを送受信する
- **パラメーター**: `from_agent: str`, `to_agent: str`, `message_type: str`, `content: str`, `task_id: str | None`
- **戻り値**: `Message`

### get_task_status
- **説明**: タスクの状態を取得する
- **パラメーター**: `task_id: str`
- **戻り値**: `Task`（ステータス、進捗、成果物一覧含む）

### submit_artifact
- **説明**: エージェントが成果物（コード・テスト・ドキュメント）を提出する
- **パラメーター**: `task_id: str`, `agent_id: str`, `file_path: str`, `content: str`, `type: str`
- **戻り値**: `Artifact`

### review_code
- **説明**: 提出された成果物に対してレビューを実施する
- **パラメーター**: `artifact_id: str`, `reviewer_agent_id: str`
- **戻り値**: `Review`（コメント、承認/却下、修正提案）

### merge_results
- **説明**: サブタスクの成果物を統合する
- **パラメーター**: `task_id: str`
- **戻り値**: 統合後の`Task`（artifactsにマージ結果含む）

## 使用例

Pythonコードから直接利用する例:

```python
import asyncio
from orchestrator.orchestrator import Orchestrator
from orchestrator.storage.artifact_store import ArtifactStore

async def main():
    store = ArtifactStore()
    orch = Orchestrator(artifact_store=store)

    # タスクを分解
    task = await orch.decompose_task('Build a calculator API')
    print(f'Subtasks: {task.subtasks}')

    # エージェントを割り当て
    await orch.assign_agent(task.subtasks[0], 'B-Qwen')

    # エージェント間で通信
    await orch.agent_communicate(
        'B-Qwen', 'A-Kimi', 'question',
        'What auth method?', task.subtasks[0]
    )

    # ステータス確認
    status = await orch.get_task_status(task.subtasks[0])
    print(f'Status: {status.status.value}')

asyncio.run(main())
```

### 全ワークフロー例

```python
import asyncio
from orchestrator.orchestrator import Orchestrator
from orchestrator.storage.artifact_store import ArtifactStore
from orchestrator.tools.artifact import create_submit_artifact
from orchestrator.tools.review import ReviewTool
from orchestrator.models.task import TaskStatus

async def full_workflow():
    store = ArtifactStore()
    orch = Orchestrator(artifact_store=store)

    # 1. タスク分解
    task = await orch.decompose_task('Build a REST API')

    # 2. エージェント割り当て
    for i, sid in enumerate(task.subtasks):
        agents = ['A-Kimi', 'B-Qwen', 'B-Qwen', 'C-Mimo']
        await orch.assign_agent(sid, agents[i % 4])

    # 3. 成果物提出
    submit = create_submit_artifact(store, orch)
    for sid in task.subtasks:
        await submit(
            task_id=sid, agent_id='B-Qwen',
            file_path=f'src/{sid}.py',
            content=f'# Code for {sid}',
            type='code'
        )

    # 4. コードレビュー
    review_tool = ReviewTool(store)
    artifacts = store.list_all()
    review = await review_tool.review_code(
        artifacts[0].id, 'C-Mimo'
    )
    print(f'Review: {review.status.value}')

    # 5. サブタスク完了
    for sid in task.subtasks:
        orch.update_task_status(sid, TaskStatus.COMPLETED)

    # 6. 成果物統合
    merged = await orch.merge_results(task.id)
    print(f'Merged: {merged.status.value}, {len(merged.artifacts)} artifacts')

asyncio.run(full_workflow())
```

## MCPツール一覧

| ツール | 説明 | 担当エージェント |
|---|---|---|
| `decompose_task` | リクエストをサブタスクに分解 | Agent A |
| `assign_agent` | タスクをエージェントに割り当て | Agent A |
| `agent_communicate` | エージェント間メッセージ送受信 | Agent B |
| `get_task_status` | タスクステータス取得 | Agent B |
| `submit_artifact` | 成果物提出 | Agent B |
| `review_code` | コードレビュー実施 | Agent C |
| `merge_results` | 成果物統合 | Agent A |

### MCPリソース

| リソース | 説明 |
|---|---|
| `task://{task_id}/status` | タスクのステータス情報を取得 |
| `agent://{agent_id}/inbox` | エージェントの受信箱メッセージ一覧 |
| `artifact://{artifact_id}` | 成果物の内容を取得 |

## 開発

### テスト実行

```bash
pytest tests/ -v
```

### コードフォーマット

```bash
black src/ tests/
```

### 静的解析

```bash
flake8 src/ tests/
mypy src/
```

## ライセンス

MIT License