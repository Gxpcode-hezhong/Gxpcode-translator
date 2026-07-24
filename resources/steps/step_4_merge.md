# Step 4 — 合并、校验与自检

> **加载触发器**：翻译完成后加载。PDF 路径强制加载，text 路径仅做自检。
> **输入**：`pages/<file>_p*_trans.md`（PDF）或单次译文（text）。

---

## 4.1 text 路径 — 自检

| # | 检查项 | 内容 |
|---|---|---|
| 4.1 | 朗读感 | 译文是否通顺自然 |
| 4.2 | 拆长句 | 英文长句拆分后中文是否合理 |
| 4.3 | "待XX"排查 | 如 `to be steamed` ≠ "待蒸汽灭菌" |
| 4.4 | "被XX"排查 | 中文尽量用主动语态 |
| 4.5 | 语境匹配 | 术语译法是否符合段落上下文 |
| 4.6 | 不通过 → 修正后重检，最多 2 轮 | |

---

## 4.2 PDF 路径 — 合并逐页译文

翻译完成后，逐页译文分散在 `pages/` 目录下。使用 `scripts/step4_merge.py` 将其映射为 element-indexed JSON，自动处理跨页续段。

```powershell
& $PythonExe `
  "$SkillDir\scripts\step4_merge.py" `
  --elements "$paddleDir/recognition_json/<file>.json" `
  --pages-dir "$outDir/pages" `
  --out "$outDir/translated.json"
```

### merge 出口表（3 种结果）

| 出口 | 条件 | 主流程动作 |
|---|---|---|
| exit 0 无告警 | 全部通过 | → 直接导出 Step 5 |
| exit 0 有告警 | 验表不通过（`_fix_pages.json` 存在） | → 读 `_fix_pages.json` → 重译问题页 → 回写 → 重新 merge（最多 2 轮） |
| exit 2 | 完整性不通过（缺页/空页，`_retry_pages.json` 存在） | → 读 `_retry_pages.json` → 起 Agent 补跑缺失页 → 重新 merge（最多 2 轮） |

> **循环上限**：同一问题最多 2 轮修复。2 轮后仍失败 → 报告用户，标注遗留问题，跳过继续导出。

### merge 三项校验（内置，顺序执行）

| 顺序 | 校验项 | 失败时 |
|---|---|---|
| ① | 完整性（缺页/空文件） | exit 2，写 `_retry_pages.json` |
| ② | 合并（按元素对齐） | 打印 `[missing]`/`[continuation]`，不阻塞 |
| ③④ | 元素类型分布 + 表格行数 | return False，写 `_fix_pages.json` |

---

## 4.3 表格行数校验（merge 后必检）

> **触发**：`step4_merge.py` 完成后、导出 HTML/MD 前，必须执行。

对 translated.json 中所有 `label=tab` 的元素，对比 EN 和 ZH 的 `<tr>` 数量：

```python
import json
with open("translated.json") as f:
    data = json.load(f)
for el in data["elements"]:
    if el.get("label") == "tab":
        en_tr = el["en"].count("<tr>")
        zh_tr = el["zh"].count("<tr>")
        if en_tr != zh_tr:
            print(f"⚠️  elem[{el['index']}] page={el['page']} TR mismatch: EN={en_tr} ZH={zh_tr}")
```

| 结果 | 处理 |
|---|---|
| 全部一致 | 通过，继续导出 |
| 存在不一致 | 输出差异列表，暂停导出，等待人工确认 |

---

## 故障排查

### F01: term_matcher.py 输出 JSON 解析失败

**症状**：PowerShell `ConvertFrom-Json` 报错 "传入的对象无效"，部分页的 `match_count` 为空。

**根因**：Windows 控制台默认 GBK 编码无法处理 ™、®、†、• 等 Unicode 字符，`&` 管道捕获时二次污染。

**修复步骤**：

| 优先级 | 动作 | 说明 |
|---|---|---|
| P0 | 确认 `term_matcher.py` 版本 ≥ 当前（含 `--output` 支持） | 源头 UTF-8 输出 |
| P1 | 调用侧使用 `--output <path>` 传文件，而非 `&` 管道 | `& $pyExe $termPy --output "$json" $text` |
| P2 | 读回时指定 UTF-8 | `Get-Content $json -Raw -Encoding UTF8 \| ConvertFrom-Json` |

### F02: 段落对齐错位（HTML 中部分段落单栏显示）

**症状**：HTML 中某些段落只有英文列（EN），中文列为空或缺失。

**根因**：
- `translated.txt` 中段落数与 paddleocr elements 数不一致。常见原因：
  - 标题 `## ...` 与正文之间无空行 → `split_paragraphs()` 合并
  - paddleocr 将长文本跨页拆为多个 element，翻译合为一段 → 数量减 1

**修复步骤**：

| 优先级 | 动作 | 说明 |
|---|---|---|
| P0 | 看 HTML 顶部警告卡片 | 直接知道哪些元素缺译文 |
| P1 | 检查对应位置 `translated.txt` 有无空行缺失 | `\n## ` 应为 `\n\n## ` |
| P2 | 补齐空行或补翻译 → 重生成 HTML | 段落数 = 元素数 = 警告消失 |

**预防**：
1. 翻译 Prompt 规则 5：段落/标题间必须有空行
2. HTML 自动诊断：`split_paragraphs()` 发现不匹配时注入可见警告卡片
3. 每次生成后检查 HTML 顶部是否出现红色卡片
