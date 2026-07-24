# Step 1 — PDF 解析与预处理

> **加载触发器**：检测到 PDF 输入时加载。
> **前置依赖**：Step 0 配置已完成（config.json 存在且 configured=true）。

通过 paddleocr-parser 按页解析 PDF，产出逐页 Markdown + elements JSON。随后启动截断修复。

---

## 1.0 前置检查

| 场景 | 检查方式 | 处理 |
|---|---|---|
| 文件路径为空 | `!pdf_path` | 提示用户提供 PDF 文件 |
| 文件不存在 | `!path.exists()` | 提示用户检查路径 |
| 非 PDF 文件 | `path.suffix.lower() != ".pdf"` | 提示提供 `.pdf` 文件 |

检查通过 → 步骤 1.1。

---

## 1.1 PDF 加密检测（强制，解析前执行）

> **检测方法**：用 `pdfplumber` 尝试打开 PDF。加密文件会抛出异常。

```powershell
& $PythonExe -c @"
import sys, pdfplumber
try:
    with pdfplumber.open(r"<PDF路径>") as pdf:
        pass
    print("PASS: PDF is not encrypted")
except Exception as e:
    msg = str(e).lower()
    if 'encrypt' in msg or 'password' in msg:
        print("BLOCKED: PDF is encrypted or password-protected")
    else:
        print(f"BLOCKED: Cannot open PDF — {e}")
    sys.exit(1)
"@
```

| 结果 | 处理 |
|---|---|
| `PASS` | 继续步骤 1.2 |
| `BLOCKED` | **立即终止**，提示用户：文件已加密，请提供未加密版本 |

---

## 1.2 paddleocr-parser 按页解析

**1.2.1** 从 `config.json` 读取 token：`$config.paddleocr_token`。若为空 → 提示用户运行首次配置。

**1.2.2** 读取配置并创建输出目录：

```powershell
$config = Get-Content "$SkillDir\config.json" | ConvertFrom-Json
$ts = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$slug = "<PDF文件名（去扩展名，取前20字符）>"
$outRoot = if ($config.output_dir.StartsWith(".")) { Join-Path (Get-Location) $config.output_dir } else { $config.output_dir }
if (-not (Test-Path $outRoot)) { New-Item -ItemType Directory -Force -Path $outRoot | Out-Null }
$outDir = "$outRoot/$ts-$slug"
$paddleDir = "$outDir/paddleocr"
New-Item -ItemType Directory -Force -Path $paddleDir, "$outDir/pages" | Out-Null

& $PythonExe `
  "$SkillDir/scripts/paddle_parser.py" `
  --input_path "<PDF路径>" --save_dir "$paddleDir"
```

**1.2.3** 向用户显示进度：

```
⏳ PDF 解析中... (已提交 API)
⏳ 轮询中... 3/10 页
✅ 解析完成: 10 页, 86 个元素
```

**1.2.4** 确认产出：

```
paddleocr/
├── markdown/<file>.md         # 合并版（预留，不用于翻译）
├── markdown/<file>_p001.md    # 第1页 → 独立翻译
├── markdown/<file>_p002.md    # 第2页 → 独立翻译
├── markdown/<file>_p003.md    # ...
└── recognition_json/<file>.json  # 全文 elements
```

---

## 1.3 截断修复（强制关卡，不可跳过）

> **执行铁律**：paddleocr 解析完成后，必须在术语扫描和翻译开始前执行本步骤。Agent 分发翻译任务前，必须确认本步骤已执行。

> paddleocr-parser 的 markdown 输出可能截断超长表格（标注 `[truncated]`），但 `recognition_json` 中保存了完整文本。翻译开始前集中修复，Agent 读到的文件永远是完整的。

```powershell
& $PythonExe `
  "$SkillDir\scripts\step1a_fix_truncations.py" `
  --paddleocr-dir "$paddleDir" `
  --elements "$paddleDir/recognition_json/<file>.json"
```

**检测规则**：`step1a_fix_truncations.py` 自动扫描所有 `*_p*.md`：
- 含 `[truncated]` → 截断
- `<table>` / `</table>` 数量不等 → 截断

截断页调用 `step1b_rebuild_page.py` 从 elements JSON 重建完整文本并**覆盖原始 md 文件**。

```
⚠️  Truncated: file_p005.md → rebuilding from JSON…
   ✅ file_p005.md fixed (423 → 1847 chars)
⚠️  Truncated: file_p069.md → rebuilding from JSON…
   ✅ file_p069.md fixed (1562 → 3120 chars)

✅ Truncation fix complete: 2/79 pages fixed
```

> **关键**：修复后所有 `*_p*.md` 为完整文本。下游 Agent 直接翻译 md 文件，无需感知截断概念。

---

## 产出

| 数据 | 路径 | 用途 |
|---|---|---|
| elements JSON | `recognition_json/<file>.json` | 下游 HTML/MD 导出 |
| 逐页原文 | `markdown/<file>_p*.md` | Step 2 术语扫描 + Step 3 翻译 |
