# Multi-Agent MCP Orchestrator 実装計画

## 1. 概要

複数のAIエージェント（LLM）が協調してタスクを遂行するためのMCPサーバーを実装する。
OpenCodeとCodexの両方で利用可能な汎用MCPサーバーとして設計し、エージェント間の役割分担・通信・成果物の統合を自動化する。

### 利用LLMと役割

| エージェント | モデル | 役割 |
|---|---|---|
| Agent A (Planner) | Kimi K2.7 Code | 全体設計、アーキテクチャ決定、実装指示の管理 |
| Agent B (Coder) | Qwen3.7 Plus | MCPサーバー本体の実装（Python/TypeScript） |
| Agent C (Tester) | Mimo v2.5 Pro | テスト、コードレビュー、検証スクリプト |

---

## 2. アーキテクチャ

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

### ディレクトリ構成

```
rade/
├── docs/
│   └── 001-multi-agent-mcp-orchestrator.md  ← 本ファイル
├── src/
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── server.py           ← MCPサーバーエントリポイント
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── decompose.py
│   │   │   ├── assign.py
│   │   │   ├── communicate.py
│   │   │   ├── status.py
│   │   │   ├── artifact.py
│   │   │   ├── review.py
│   │   │   └── merge.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── task.py
│   │   │   ├── agent.py
│   │   │   └── artifact.py
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   ├── task_store.py
│   │   │   └── artifact_store.py
│   │   └── orchestrator.py     ← コアロジック
│   └── mcp_entry.py            ← MCPサーバー起動用エントリ
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

---

## 3. データモデル

### Task
```python
class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Task:
    id: str
    description: str
    status: TaskStatus
    assigned_agent: str | None
    parent_task_id: str | None
    subtasks: list[str]
    artifacts: list[str]
    created_at: datetime
    updated_at: datetime
```

### Agent
```python
@dataclass
class Agent:
    id: str
    name: str
    model: str          # 例: "kimi-k2.7-code", "qwen3.7-plus", "mimo-v2.5-pro"
    role: str           # "planner", "coder", "tester"
    status: str         # "idle", "busy"
    inbox: list[Message]
```

### Artifact
```python
@dataclass
class Artifact:
    id: str
    task_id: str
    agent_id: str
    file_path: str
    content: str
    type: str           # "code", "test", "doc", "review"
    version: int
```

---

## 4. MCPツール定義

### 4.1 decompose_task
- **説明**: ユーザーリクエストをサブタスクに分解する
- **パラメーター**:
  - `request: str` — ユーザーからの要求
- **戻り値**: `Task`（分解結果のルートタスク、subtasksに子タスクIDリスト）
- **実装者**: **Agent A (Kimi K2.7 Code) のみ実装**
- **制約**: このツールはLLMの分解結果をそのまま構造化して返す。分解ロジックの変更はAgent Aのみが行う。

### 4.2 assign_agent
- **説明**: 特定のタスクをエージェントに割り当てる
- **パラメーター**:
  - `task_id: str`
  - `agent_id: str`
- **戻り値**: 更新後の`Task`
- **実装者**: **Agent A (Kimi K2.7 Code) のみ実装**
- **制約**: 割り当てルールの変更はAgent Aのみ。

### 4.3 agent_communicate
- **説明**: エージェント間でメッセージを送受信する
- **パラメーター**:
  - `from_agent: str`
  - `to_agent: str`
  - `message_type: str` — "request" | "response" | "review" | "question"
  - `content: str`
  - `task_id: str | None`
- **戻り値**: `Message`
- **実装者**: **Agent B (Qwen3.7 Plus) のみ実装**
- **制約**: 通信プロトコルの実装詳細（メッセージキュー、永続化）はAgent Bのみ。Agent A, Cはこのファイルを編集しない。

### 4.4 get_task_status
- **説明**: タスクの状態を取得する
- **パラメーター**:
  - `task_id: str`
- **戻り値**: `Task`（ステータス、進捗、成果物一覧含む）
- **実装者**: **Agent B (Qwen3.7 Plus) のみ実装**
- **制約**: なし

### 4.5 submit_artifact
- **説明**: エージェントが成果物（コード・テスト・ドキュメント）を提出する
- **パラメーター**:
  - `task_id: str`
  - `agent_id: str`
  - `file_path: str`
  - `content: str`
  - `type: str`
- **戻り値**: `Artifact`
- **実装者**: **Agent B (Qwen3.7 Plus) のみ実装**
- **制約**: なし

### 4.6 review_code
- **説明**: 提出された成果物に対してレビューを実施する
- **パラメーター**:
  - `artifact_id: str`
  - `reviewer_agent_id: str`
- **戻り値**: `Review`（コメント、承認/却下、修正提案）
- **実装者**: **Agent C (Mimo v2.5 Pro) のみ実装**
- **制約**: レビューロジックの変更はAgent Cのみ。

### 4.7 merge_results
- **説明**: サブタスクの成果物を統合する
- **パラメーター**:
  - `task_id: str`
- **戻り値**: 統合後の`Task`（artifactsにマージ結果含む）
- **実装者**: **Agent A (Kimi K2.7 Code) のみ実装**
- **制約**: マージ戦略の変更はAgent Aのみ。

---

## 5. エージェント別実装担当一覧

### Agent A — Kimi K2.7 Code（Planner）
**実装するファイル（これら以外は編集禁止）**:
- `src/orchestrator/tools/decompose.py` — decompose_task の全実装
- `src/orchestrator/tools/assign.py` — assign_agent の全実装
- `src/orchestrator/tools/merge.py` — merge_results の全実装
- `src/orchestrator/orchestrator.py` — コアロジック（タスク管理、状態遷移、進行管理）
- `src/orchestrator/models/task.py` — Taskモデル定義
- `src/orchestrator/models/agent.py` — Agentモデル定義
- `src/orchestrator/storage/task_store.py` — タスクストア実装

**担当外（編集禁止）**:
- communicate.py, status.py, artifact.py, review.py
- artifact_store.py
- 全テストコード
- README.md

### Agent B — Qwen3.7 Plus（Coder）
**実装するファイル（これら以外は編集禁止）**:
- `src/orchestrator/tools/communicate.py` — agent_communicate の全実装
- `src/orchestrator/tools/status.py` — get_task_status の全実装
- `src/orchestrator/tools/artifact.py` — submit_artifact の全実装
- `src/orchestrator/models/artifact.py` — Artifactモデル定義
- `src/orchestrator/storage/artifact_store.py` — アーティファクトストア実装
- `src/orchestrator/server.py` — MCPサーバーエントリポイント（全ツールの登録）
- `src/mcp_entry.py` — サーバー起動用エントリポイント

**担当外（編集禁止）**:
- decompose.py, assign.py, merge.py, review.py
- task.py, agent.py
- task_store.py
- orchestrator.py（コアロジック）
- 全テストコード
- README.md

### Agent C — Mimo v2.5 Pro（Tester）
**実装するファイル（これら以外は編集禁止）**:
- `src/orchestrator/tools/review.py` — review_code の全実装
- `tests/test_decompose.py` — decompose_task のテスト
- `tests/test_assign.py` — assign_agent のテスト
- `tests/test_communicate.py` — agent_communicate のテスト
- `tests/test_merge.py` — merge_results のテスト
- `tests/test_orchestrator.py` — 統合テスト
- `pyproject.toml` — プロジェクト設定（テストフレームワーク、依存関係）
- `requirements.txt` — Python依存パッケージ一覧
- `README.md` — プロジェクト概要と実行方法

**担当外（編集禁止）**:
- decompose.py, assign.py, merge.py
- communicate.py, status.py, artifact.py
- server.py, mcp_entry.py
- 全モデル定義、全ストア実装
- orchestrator.py

---

## 6. エージェント間通信フロー

### 6.1 通常のタスク遂行フロー

```
User: "Implement a REST API for user management"

Agent A (decompose_task):
  → Task分解: ["Design API spec", "Implement models", "Implement routes", "Write tests"]
  → assign_agent("Design API spec", "A-Kimi")
  → assign_agent("Implement models", "B-Qwen")
  → assign_agent("Implement routes", "B-Qwen")
  → assign_agent("Write tests", "C-Mimo")

Agent B (agent_communicate → Agent A):
  → "API spec not clear on auth, need clarification"

Agent A (agent_communicate → Agent B):
  → "Use JWT bearer token, spec in artifact://spec-1"

Agent B (submit_artifact → "models.py"):
  → submit_artifact(task_id, "B-Qwen", "src/models.py", "...", "code")

Agent C (review_code → artifact://models.py):
  → Review: "LGTM with minor nits" / "Needs changes: ..."

Agent B (submit_artifact → "models.py v2"):
  → Update based on review

Agent A (merge_results):
  → 全ての成果物を統合し、最終的な実装を完了
```

### 6.2 レビューフロー

```
Agent B → submit_artifact("routes.py")
Agent C → review_code("routes.py")
  → {status: "changes_requested", comments: ["Add input validation", "Fix error handling"]}
Agent B → agent_communicate("C-Mimo", "question", "What validation library?")
Agent C → agent_communicate("B-Qwen", "response", "Use Pydantic models")
Agent B → submit_artifact("routes.py v2")
Agent C → review_code("routes.py v2")
  → {status: "approved"}
```

---

## 7. セットアップ手順（README.mdに記載する内容）

```bash
# 依存関係インストール
pip install -r requirements.txt

# MCPサーバー起動
python src/mcp_entry.py

# OpenCode設定 (~/.config/opencode/opencode.json または .opencode/opencode.json)
# {
#   "mcpServers": {
#     "multi-agent-orchestrator": {
#       "command": "python",
#       "args": ["src/mcp_entry.py"]
#     }
#   }
# }

# Codex設定 (codex.json)
# {
#   "mcpServers": {
#     "multi-agent-orchestrator": {
#       "command": "python",
#       "args": ["src/mcp_entry.py"]
#     }
#   }
# }
```

---

## 8. 実装の優先順位

| Phase | 内容 | 担当 | 依存 |
|---|---|---|---|
| Phase 1 | プロジェクト設定 (pyproject.toml, requirements.txt) | **Agent C** | なし |
| Phase 2 | データモデル (Task, Agent, Artifact) | **Agent A** (Task, Agent) / **Agent B** (Artifact) | Phase 1 |
| Phase 3 | ストア実装 (task_store, artifact_store) | **Agent A** (task) / **Agent B** (artifact) | Phase 2 |
| Phase 4 | MCPサーバーエントリ (server.py, mcp_entry.py) | **Agent B** | Phase 3 |
| Phase 5 | コアオーケストレーター (orchestrator.py) | **Agent A** | Phase 4 |
| Phase 6 | 各ツール実装 | 各担当エージェント | Phase 5 |
| Phase 7 | テスト実装 | **Agent C** | Phase 6 |
| Phase 8 | README作成 | **Agent C** | Phase 7 |

---

## 9. 制約とルール

1. **ファイル編集境界**: 各エージェントは自身に割り当てられたファイルのみを編集できる。割り当て外のファイルは一切編集しない。
2. **インターフェース契約**: 各モジュール間のインターフェース（関数シグネチャ、クラス定義）はこのドキュメントに従う。変更が必要な場合はAgent Aが判断し、このドキュメントを更新する。
3. **コード品質**: 型アノテーション必須、エラーハンドリング必須、ログ出力必須。
4. **エージェント間調整**: インターフェースの不整合が生じた場合、agent_communicateツールを使ってAgent Aが調整する。
5. **テストカバレッジ**: Agent Cは各ツールの正常系・異常系のテストを実装する。カバレッジ80%以上を目標とする。
