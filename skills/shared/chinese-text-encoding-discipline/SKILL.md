---
name: chinese-text-encoding-discipline
description: 中文文本/中文路径乱码的定位与根治——全链路 UTF-8 唯一口径、7 环检查表、各语言落地清单与编码自检脚本 适用场景：乱码、中文路径、中文文件名。勿用于：直接改权威区、push到远程。
version: 1.0.0
metadata:
  hermes:
    tags: [encoding, utf-8, gbk, 乱码, 中文路径, subprocess, pre-commit]
    category: software-development
    source_card: rules/chinese-text-encoding-discipline.md
---

# 中文文本与中文路径编码纪律

> 权威卡：记忆中枢 `rules/chinese-text-encoding-discipline.md`（V1.1）。
> 本技能是它的可执行形态：**定位步骤 + 7 环检查表 + 各语言落地片段 + 自检脚本**。

## 何时用（触发）

- 出现乱码：GUI 显示、日志、文件名、软件界面、导出报表
- 涉及**中文文件名 / 中文目录路径 / 非 ASCII 路径**
- 跨语言子进程传中文（C# ↔ Python、PowerShell ↔ Python、Node ↔ 子进程）
- 编译/链接含中文源码路径（MSVC/GCC），或 CAD/Office COM 传递中文串
- **要生成含中文的脚本文件**（`.ps1` / `.bat` / `.vbs` / `.py` / `.cs`）

## 五条铁律（违反即有代价）

1. **全链路 UTF-8 唯一口径**——禁止 GBK 中间态（用 GBK 做中转修 UTF-8 会**不可逆丢字**）。
2. **跨边界两端都要显式声明编码**，禁止依赖任何默认值：.NET 默认 = 系统 ACP（中文 Windows = 936/GBK）；Python 重定向时默认值**随调用者环境漂移**。
3. **Windows 文件/路径一律走宽字符（W 版 / Unicode）API**，禁 ANSI 的 A 版（`fopen` / `CreateFileA`）。
4. **禁止用「我本机跑没事」当判据**——必须双环境（`PYTHONUTF8=1` / 全 unset）各跑一次。
5. **业务中文路径不改名**（改名破坏用户既有引用），只能改代码去适配它。

## 定位步骤（先判类型，再动手改）

1. **先到底层数据源确认真身**：用 CLI / 直接读文件看中文是否完好。
   - 完好 ⇒ 链路某环**解码**错了，改那一环即可
   - 已坏 ⇒ 有损替换，**数据已丢**，只能改流程防复发
2. **判可逆性**（决定还能不能救）：
   - 出现"可看的汉字"如 `闃块噷鐧剧偧` ⇒ UTF-8 字节被按 GBK 解码，**单程、可逆**（`s.encode('gbk').decode('utf-8')`）
   - 出现 `?` / `�` / 方块 ⇒ 有损替换，**不可逆**
3. **二分定位**：
   - 同一脚本"某人跑正常、另一人跑乱码" ⇒ **环境泄漏**（`PYTHONUTF8` / `PYTHONIOENCODING` 被调用者带进子进程）
   - 只在某个宿主程序里乱 ⇒ 该宿主的**解码端**没显式指定
4. **"乱码名 + 关联字段全空 + 时间 0001/1/1"** 三连 ⇒ 按乱码 key 查字典未命中的特征组合（metadata 查询类 bug）。

## 全链路 7 环检查表（逐环核对，缺一即漏）

| # | 环节 | 必须做 | 典型错误 |
|:--|:--|:--|:--|
| 1 | 源码文件 | 统一 UTF-8；`.ps1` 带 BOM、`.vbs` 纯 ASCII（见下表） | 文件是 GBK 却按 UTF-8 解析 |
| 2 | 编译器/解释器 | MSVC `/utf-8`；GCC `-finput-charset=UTF-8 -fexec-charset=UTF-8`；Python `PYTHONUTF8=1`；Java `-Dfile.encoding=UTF-8` | 靠系统代码页碰运气 |
| 3 | 运行时字符串类型 | 用语言**原生 Unicode 类型**（C# `string` / Py `str` / Go `string` / Rust `PathBuf` / C++ `std::filesystem::path`） | 手搓 `char*` 拼路径 |
| 4 | 文件/路径 API | 宽字符 W 版：`_wfopen`、`std::filesystem`、`Path` 类 | `CreateFileA` / `fopen` |
| 5 | 文件读写 | **显式** `encoding="utf-8"` / `Encoding.UTF8` | `Encoding.Default`、无 `encoding` 的 `open()` |
| 6 | **进程边界（最高频）** | **两端都钉死**（见下） | 只改宿主解码端 |
| 7 | 终端/日志/命令行 | `chcp 65001` / `[Console]::OutputEncoding`；**避免命令行传中文路径**，改响应文件/环境变量/UTF-8 配置文件 | 命令行直接塞中文路径 |

## 各语言落地片段（可直接复制）

**Python**
```python
from pathlib import Path
Path(p).read_text(encoding="utf-8")          # 禁止 open(p) 不带 encoding
Path(p).write_text(s, encoding="utf-8")
print(json.dumps(o, ensure_ascii=False))      # + 环境 PYTHONIOENCODING=utf-8
```

**.NET / C# 子进程管道（两端钉死）**
```csharp
var psi = new ProcessStartInfo(psi_path) {
    RedirectStandardOutput = true,
    StandardOutputEncoding = Encoding.UTF8,   // ← 不设 = 按 ACP(936) 解码 → 乱码
    StandardErrorEncoding  = Encoding.UTF8,
};
psi.Environment["PYTHONUTF8"] = "1";          // ← 子进程输出端也钉死
psi.Environment["PYTHONIOENCODING"] = "utf-8";
```

**PowerShell 调原生子进程**
```powershell
$old = [Console]::OutputEncoding
try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $env:PYTHONIOENCODING = 'utf-8'
    # 调用子进程…
} finally { [Console]::OutputEncoding = $old; Remove-Item Env:PYTHONIOENCODING -EA SilentlyContinue }
```
> 必须在 **回显之前**还原编码，否则这段日志会以第二种编码写进外层文件——把同一个坑换个地方再踩。

**C / C++**
```cpp
// 源码 UTF-8 with BOM（MSVC）+ /utf-8 + std::filesystem::path + 宽字符 API
std::ofstream f(std::filesystem::path(L"中文目录/中文名.txt"));   // 不用 fopen
// CMake/编译：/utf-8  或  -finput-charset=UTF-8 -fexec-charset=UTF-8
```

**脚本文件编码表（生成脚本前先选对，事后改易出错）**

| 扩展名 | 编码 | 原因 |
|:--|:--|:--|
| `.py` `.md` `.json` `.yaml` `.txt` | UTF-8 **无 BOM** | BOM 会破坏解析（部分工具/JSON） |
| `.ps1` | UTF-8 **with BOM** | PowerShell 5.1 无 BOM 时按 ANSI 解析，中文必爆 |
| `.bat` `.cmd` | ANSI(GBK) + CRLF | cmd.exe 按当前代码页解析 |
| `.vbs` | **纯 ASCII** | WScript 按 ANSI 解析，中文等同乱码源 |
| `.cs` | UTF-8 with BOM | MSVC 推荐 |

## 收尾自检（必跑，退出码 0 才算完成）

```bash
python <skill>/scripts/check_encoding.py <本次改动的文件或目录>   # 本技能自带副本
python hub-engine/scripts/check_encoding.py <...>                # 记忆中枢权威副本
```

四道检查：① 非 UTF-8 编码（报实际编码）② BOM 合规（按扩展名）③ 乱码串残留（UTF-8→GBK 高频字对）④ 中文路径 round-trip（写→读回逐字符相等）。

**自动化门禁（已装）**：工程根 `hub-engine/scripts/pre-commit` 与中枢 `hub-engine/scripts/pre-commit-hub-cards` 均在提交时跑本检查，staged 文件非 UTF-8 / 含乱码串 → **直接阻断提交**（退出码 4；绕行只能 `git commit --no-verify`）。

## Pitfalls（真实踩坑）

- **只改一端**：只设宿主 `StandardOutputEncoding` 不改子进程环境 ⇒ 环境一泄漏就复发，表现为"时好时坏"。
- **`.ps1` 无 BOM**：在 PS5.1 下按 ANSI 解析，中文注释/字符串直接坏掉，且**报错位置会错乱到别的行**。
- **`Encoding.Default` / 无 `encoding` 的 `open()`**：在中文 Windows 上是 GBK，看着能跑，换台机/换环境就乱。
- **命令行传中文路径**：MSVC/GCC/链接器经 ANSI 命令行会掉字 ⇒ 改用响应文件（`@rsp`）、环境变量或 UTF-8 配置文件。
- **用 GBK"修"UTF-8**：`?`/`�` 一旦写入就不可逆，源数据已丢。
- **改业务中文路径名**：会打断用户既有的 CAD/Excel/脚本引用 —— 编码问题只能靠改代码解决，不能靠改名解决。
- **只看乱码表面**：乱码常伪装成"数据丢失/功能失效/记录不存在"，先到底层确认真身再动手。

## 验证判据（怎么证明修好了，而不是"看着好了"）

1. **round-trip**：中文名写入 → 读回 → 与原文**逐字符相等**（不是"看着像"）
2. **乱码串 0 命中**：历史乱码串在日志/界面中出现次数为 0
3. **双环境各跑一遍**（`PYTHONUTF8=1` / 全 unset），两份输出都正确
4. **端到端全链路**（新增→编辑→读回→删除）中文名原样保留
5. 确认**没有把外层日志/其他子进程带坏**（改编码只作用于目标调用窗口，`try/finally` 还原）

## References

- `scripts/check_encoding.py` —— 编码自检脚本（四道检查，退出码 0/1，可进 CI/pre-commit）
- 权威卡：记忆中枢 `rules/chinese-text-encoding-discipline.md`
- 同族经验卡：`dotnet-subprocess-utf8-gbk-mojibake`、`subprocess-stdout-encoding-ambient-env-leak`、`powershell-script-encoding-bom-ascii-safe-quote-pitfall`、`vbs-ascii-constraint`
- 关联规则：`rules/multi-language-style-config`（编码规范节）、`rules/agent-code-discipline-iron-rule`（R7 编码自检）
