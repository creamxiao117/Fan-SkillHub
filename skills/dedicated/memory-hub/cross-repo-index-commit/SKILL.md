---
name: "cross-repo-index-commit"
description: 在中枢/其他独立 git 仓库执行 INDEX 登记、跨库改文件并 git 提交，用命令行等效绕开 IDE 工具目录限制，保两侧一致性。 适用场景：跨仓库提交、跨库登记、跨库提交。勿用于：工作目录内可 Edit、push 到远程。
...
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

## 收敛标准

- 目标文件新行已落经 `Select-String` 实证。
- `git log --oneline -2` 显示本次登记 commit；工作区干净。
- 两侧（SkillHub + 中枢）INDEX 一致可核。
