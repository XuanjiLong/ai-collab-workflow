# Main-Agent Collaboration Playbook

[中文](#中文) | [English](#english)

## 中文

多 Agent 协作规范：Main Agent 调度 Coder 和 Reviewer，通过标准化契约、风险分层决策和自适应重试机制完成编码任务。

### 如何使用这套协议

#### 方式 1：集成到你的项目（推荐）

```bash
# 从 GitHub 安装（推荐）
cd ~/your-project
curl -sL https://raw.githubusercontent.com/XuanjiLong/ai-collab-workflow/main/install.sh | bash

# 或手动复制（如果已克隆到本地）
cd ~/your-project
mkdir -p .workflow && cd .workflow
cp -r ~/ai-collab-workflow/{docs,schemas,scripts,AGENTS.md} .

# 在项目根目录的 CLAUDE.md 中加入
cat >> CLAUDE.md << 'EOF'
## 工作流协议

当收到编码任务时，按 .workflow/AGENTS.md 协议执行：
1. 阅读 .workflow/docs/prompts/main_agent.system.md
2. 构建 TaskContract 并存入 .workflow/tasks/T-<id>/
3. 按 RUNBOOK 循环：code → review → decision
4. 使用 .workflow/docs/DISPATCH.md 的多会话模式调度 Coder/Reviewer
EOF

# 3. 开始使用
# 在 Claude Code 或其他 AI CLI 中说：
# “给 src/api/user.ts 增加邮箱格式校验，不改数据库 schema”
```

#### 方式 2：直接在 AI 会话中使用

```bash
# 在 Claude Code / Cursor / Codex CLI 中：
你: 阅读 ~/ai-collab-workflow/AGENTS.md、docs/RUNBOOK.md、
    docs/DISPATCH.md 和 docs/prompts/ 下的三份模板。
    之后按这个协议处理我的需求。

你: 给 src/api/user.ts 增加邮箱格式校验，不改数据库 schema。

# AI 会按协议：
# 1. 构建 TaskContract（评估复杂度、选权重 profile）
# 2. 以 Coder 角色编码（产出 patch + self_review）
# 3. 以 Reviewer 角色评审（打分 + verdict）
# 4. 执行 decision gate（auto_approve / human_optional / reject+rework）
# 5. 保存 artifact 到 .workflow/tasks/T-xxx/
```

#### 方式 3：多终端隔离执行（最高质量）

```bash
# 终端 1: Main Agent
claude-code
> 我是 Main Agent，按 docs/prompts/main_agent.system.md 行为
> [构建 task_contract.json]

# 终端 2: Coder
claude-code
> [粘贴 docs/prompts/coder.prompt.md 作为 system prompt]
> [粘贴 task_contract.json]
> [返回 coder_output.json]

# 终端 3: Reviewer
claude-code
> [粘贴 docs/prompts/reviewer.prompt.md 作为 system prompt]
> [粘贴 task_contract.json + coder_output.json]
> [返回 review_result.json]

# 回到终端 1
> [读取 review_result，执行 decision gate，写 decision_record.json]
```

详见 `docs/DISPATCH.md` 的完整调度说明。

### 核心文档

- **开始**: `AGENTS.md` - 协议总览
- **执行**: `docs/RUNBOOK.md` - 状态机循环
- **调度**: `docs/DISPATCH.md` - 如何调用 Coder/Reviewer
- **契约**: `docs/TASK_CONTRACT.md` - 数据结构定义
- **角色**: `docs/roles/coder.md` + `reviewer.md`
- **模板**: `docs/prompts/` - 可直接粘贴的 system prompt
- **示例**: `examples/full-run/` - 完整两轮 artifact
- **校验**: `python scripts/validate_artifact.py --examples --strict`

### 适用场景

- 标准化团队 AI 协作流程
- 跨 CLI 工具复用同一套协议（Claude Code / Cursor / Codex CLI）
- 需要审计追溯的编码任务

---

## English

Multi-agent collaboration protocol: Main Agent orchestrates Coder and Reviewer through standardized contracts, risk-based decision gates, and adaptive retry mechanisms.

### How to Use This Protocol

#### Option 1: Integrate into Your Project (Recommended)

```bash
# Install from GitHub (recommended)
cd ~/your-project
curl -sL https://raw.githubusercontent.com/XuanjiLong/ai-collab-workflow/main/install.sh | bash

# Or manual copy (if cloned locally)
cd ~/your-project
mkdir -p .workflow && cd .workflow
cp -r ~/ai-collab-workflow/{docs,schemas,scripts,AGENTS.md} .

# Add to your project's CLAUDE.md
cat >> CLAUDE.md << 'EOF'
## Workflow Protocol
When receiving coding tasks, follow .workflow/AGENTS.md protocol:
1. Read .workflow/docs/prompts/main_agent.system.md
2. Build TaskContract and save to .workflow/tasks/T-<id>/
3. Loop: code → review → decision (see RUNBOOK)
4. Use .workflow/docs/DISPATCH.md multi-session mode for Coder/Reviewer
EOF

# 3. Start using
# In Claude Code or other AI CLI:
# "Add email validation to src/api/user.ts, no DB schema changes"
```

#### Option 2: Direct Use in AI Session

```bash
# In Claude Code / Cursor / Codex CLI:
You: Read ~/ai-collab-workflow/AGENTS.md, docs/RUNBOOK.md,
     docs/DISPATCH.md and the three templates in docs/prompts/.
     Then follow this protocol for my requests.

You: Add email validation to src/api/user.ts, no DB schema changes.

# AI will follow the protocol:
# 1. Build TaskContract (assess complexity, select weight profile)
# 2. Act as Coder (produce patch + self_review)
# 3. Act as Reviewer (score + verdict)
# 4. Execute decision gate (auto_approve / human_optional / reject+rework)
# 5. Save artifacts to .workflow/tasks/T-xxx/
```

#### Option 3: Multi-Terminal Isolation (Highest Quality)

```bash
# Terminal 1: Main Agent
claude-code
> I am Main Agent, following docs/prompts/main_agent.system.md
> [build task_contract.json]

# Terminal 2: Coder
claude-code
> [paste docs/prompts/coder.prompt.md as system prompt]
> [paste task_contract.json]
> [return coder_output.json]

# Terminal 3: Reviewer
claude-code
> [paste docs/prompts/reviewer.prompt.md as system prompt]
> [paste task_contract.json + coder_output.json]
> [return review_result.json]

# Back to Terminal 1
> [read review_result, execute decision gate, write decision_record.json]
```

See `docs/DISPATCH.md` for complete dispatch instructions.

### Core Documents

- **Start**: `AGENTS.md` - Protocol overview
- **Execute**: `docs/RUNBOOK.md` - State machine loop
- **Dispatch**: `docs/DISPATCH.md` - How to invoke Coder/Reviewer
- **Contract**: `docs/TASK_CONTRACT.md` - Data structure definitions
- **Roles**: `docs/roles/coder.md` + `reviewer.md`
- **Templates**: `docs/prompts/` - Ready-to-paste system prompts
- **Examples**: `examples/full-run/` - Complete two-round artifacts
- **Validation**: `python scripts/validate_artifact.py --examples --strict`

### Best Fit

- Standardize AI collaboration across teams
- Reuse one protocol across CLI tools (Claude Code / Cursor / Codex CLI)
- Coding tasks requiring audit trails
