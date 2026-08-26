# Skill Feedback Inbox

这个目录用于接收旧项目回流到 `context-engineering-v1` 的候选经验。

默认产物：

- `feedback-candidates.md`：由脚本汇总生成的候选清单
- `manual-feedback-candidates.md`：人工挑出的候选，等待评审
- `feedback-candidates.reviewed.md`：人工评审结果

使用方式：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/collect-skill-feedback.ps1 `
  -ProjectListFile "project-roots.example.txt"
```

脚本会扫描每个项目下的：

- `methodology/shared-rules-and-experience/`
- `methodology/project-specific-rules-and-experience/`

然后按“出现次数 / 复用范围 / 是否能简化流程 / 是否防止严重错误”生成推荐升级项。

