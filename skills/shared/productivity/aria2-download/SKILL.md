# @version V1.0 / 2026-09-07 / Hermes / 多线程并行下载技能（aria2）
# @alias aria2-multi-thread-download

## 元数据

```yaml
name: aria2-download
slot: shared
invoke: user
scope: productivity

description_model: |
  当用户需要下载文件且明确要求多线程/加速下载时，或遇到大文件（>100MB）需并行下载时使用。
  触发词：多线程下载、加速下载、并行下载、aria2、大文件下载
description_human: |
  多线程并行下载工具（aria2），支持断点续传、分段并发、磁力链、BT。
trigger:
  - 多线程
  - 多线程下载
  - 加速下载
  - 并行下载
  - aria2
  - aria2c
  - 大文件下载
forgot:
  - 视频下载（B站/YouTube，优先 yt-dlp）
  - 小文件（<10MB，curl 更快）
weight: 1.0
```

## 技能内容

### 核心用法

```bash
# 基本用法：单线程（等价 curl，但更快）
aria2c <URL>

# 16线程并发下载（推荐默认）
aria2c -x16 -s16 <URL>

# 断点续传 + 16线程 + 进度显示
aria2c -x16 -s16 -c <URL>

# 指定输出文件名
aria2c -o filename.ext -x16 -s16 <URL>

# 多文件并行（URL 列表）
aria2c -Z -x16 -s16 url1.txt url2.txt

# 使用 referer 和 user-agent
aria2c --header="Referer: https://example.com" \
       --user-agent="Mozilla/5.0" \
       -x16 -s16 <URL>

# 限速（防止吃满带宽）
aria2c --max-download-limit=5M -x16 -s16 <URL>
```

### 参数说明

| 参数 | 含义 | 推荐值 |
|---|---|---|
| `-x16` | 单文件最大连接数（16线程） | 16（大文件）/ 4（小文件）|
| `-s16` | 拆分文件段数 | 16 |
| `-c` | 断点续传 | 始终加 |
| `-o filename` | 指定输出文件名 | — |
| `-d dir` | 指定输出目录 | — |
| `-j3` | 同时下载文件数（列表模式） | 3~5 |
| `--max-download-limit` | 单任务限速 | 5M~50M |
| `-h` | 显示完整帮助 | — |

### 场景分类

```
小文件（<10MB）     → curl 或 requests（更轻量）
视频/音频           → yt-dlp（已装，支持字幕/平台识别）
大文件（>100MB）    → aria2c -x16 -s16 -c（多线程+断点续传）
BT/磁力链           → aria2c（原生支持，curl 不支持）
Git clone（大仓库）  → git clone --depth=1（优先），aria2c 只用于 release 文件
```

### 安装验证

```bash
# Windows（已装 via Chocolatey）
aria2c --version
# → aria2 version 1.37.0

# Linux/macOS（如需）
sudo apt install aria2   # Debian/Ubuntu
sudo brew install aria2  # macOS
```

### 坑

- `aria2c` 不支持 HTTPS 代理时需加 `--https-proxy=<URL>`
- Windows 路径含空格要加引号：`aria2c -d "C:\path with space"`
- 多文件时加 `-Z`（非列表模式）为并行，`-j` 控制并发数
