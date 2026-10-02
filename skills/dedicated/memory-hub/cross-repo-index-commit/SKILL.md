---
name: "cross-repo-index-commit"
description: 在中枢/其他独立 git 仓库执行 INDEX 登记、跨库改文件并 git 提交，用命令行等效绕开 IDE 工具目录限制，保两侧一致性 适用场景：跨仓库提交、跨库登记、跨库提交。勿用于：工作目录内可 Edit、push 到远程。
---

# Cross-Repo Index Commit（跨独立仓库在线维护）

当 Edit/Write 工具被限制在 SkillHub 工作目录，而需改动中枢（独立仓库）文件并 git 提交时，
用命令行等效完成：读锚点 → 插入/替换 → git add/commit，并同步 `INDEX.md` 登记。

## 触发

- 需在中枢/其他独立 git 仓库登记 INDEX、增改卡文件并提交。
- 需要保持 SkillHub 与中枢两侧的一致性（本次链路已用本技能完成多次登记）。

## 核心边界（先读）

1. **先走 IDE 工具，命令行兜底**：若目标在当前工作目录（可用 Edit/Write），优先 IDE 工具；仅当目录受限（跨仓）才用命令行。
2. **绝不 push / 改全局 git config**：只做本地 read + replace + add/commit；push 或改全局配置需人工批准。
3. **commit 职责独立**：ingest 自动 commit 卡内容 / 手工 commit INDEX 登记，避免杂混。
4. **保持市场 per-path 幂等**：锚点为空先 `git log -- <file>` 确认是否已被自动提交，避免重复 commit。
5. **触发词粒度（实测经验）**：trigger/forgot 用**短 token 词**（如 `跨库登记`、`中枢 INDEX`），勿用含空格的整句短语（如 `跨库登记中枢 INDEX`）——真实 query 会因词序变动/中间插词破坏子串命中。改短 token 后对真实意图更鲁棒。

## 工作流

1. **定位锚点**：`git log --oneline -3 -- <file>` / `Select-String -Path INDEX.md -Pattern <slug>` 找插入点。

2. **读改（命令行使）**：

   ```powershell
   $lines = [IO.File]::ReadAllLines($p)         # 全量读
   # 定位锚点行 index → 插入/替换
   [IO.File]::WriteAllLines($p, $out, (New-Object Text.UTF8Encoding($true)))
   ```

3. **校验**：`Get-Content $p | Select-String <new>` 确认新行已落。

4. **提交**：

   ```powershell
   git add <file>
   git commit -m @'
   docs(INDEX): 登记 <slug>，一句话说明
   '@
   git status --short
   ```

## 门禁清单（执行前确认）

- [ ] 目标确在当前工作目录之外（才走命令行，否则用 Edit/Write）
- [ ] 不 push、不改全局 git config、不自动执行仓库脚本
- [ ] commit 前确认未被 ingest 自动提交过，避免重复
- [ ] 提交后 `git status --short` 校验干净

## Pitfalls（踩过的反模式）

### `git add` 不捕获 `rm` 后的"D"——必须显式 add 删除路径才能进 commit

**症状**：`rm` 一个 tracked 文件后，`git status` 显示 `D <path>`；但 `git add <other-file>` 后再 `git commit`，**`D` 行未被提交进 commit**——commit 只包含 `git add` 的目标，文件保留在工作区未提交状态。

**根因**：`git add <path>` 只把指定路径的变化纳入暂存区；删除文件的变化不会自动被"其它 add"捎带。

**判定**：commit 后立刻 `git status --short`——若仍有 `D <path>` 行 = 本次 commit 漏了该删除。`git show --stat <sha>` 看本次 commit 的文件列表是否完整。

**修正**：**显式 `git add <deleted-path>`**（Git 允许 add 一个已删除文件——会把删除操作纳入暂存区）。或 `git add -A` 整仓扫，但仅在无他人未提交改动时安全。

**反面案例（2026-09-09）**：清理 D 端 5 个 untracked 时，`git add package.json package-lock.json` + `git rm tmp/orphan_paths.txt`（**漏了**）→ commit `72b83cb` 只含 2 文件新增；`tmp/orphan_paths.txt` 仍以 `D` 状态留工作区。下一次 commit `5b9e88b` 才把它补进——拆成两个 commit 让 history 凌乱。

**最佳实践**：rm 后立刻 `git add <deleted-path>`——**rm 与 add 配对**，不分离两步。

**批量场景（多 add + 多 rm 时易踩）**：一次 `git add A B` + 一次 `rm X` 后只 `git commit`（不带 `git add X`）= A B 入库、X 留工作区 `D` 状态，commit 拆成两次。**正确做法是先 `git add A B X` 再 commit**——或在脚本中**所有 rm 操作完成后统一 `git add -A` 再 commit**（前提：无人并行未提交改动）。判定：commit 后 `git show --stat <sha>` 看文件列表是否完整、有 `D` 残留即漏 add。

### 跨仓 commit 前必须确认目标仓有 origin（孤立 commit 的处理）

**症状**：在无 origin 的废弃仓（如 `D:\AIwork\...` 个人试验场）做清理 commit 后，**该 commit 仅本地存在**——永远不会被任何人读到，也无法通过 `git push` 同步到任何 remote。

**判定**：`git remote -v` 输出为空 = 无 origin，本地 commit 即孤立。这种仓适合保留作为历史快照，但 commit 信息应明示其孤立属性（如 `chore(discarded): ...`），不指望跨人/跨机可见。

**行动**：孤立 commit **仍要 commit**（保留审计痕迹），但 commit message 标明 `chore(discarded):` 前缀，让未来 review 能一眼识别这是"本地清理"而非"可同步变更"。

## 收敛标准

- 目标文件新行已落经 `Select-String` 实证。
- `git log --oneline -2` 显示本次登记 commit；工作区干净。
- 两侧（SkillHub + 中枢）INDEX 一致可核。
