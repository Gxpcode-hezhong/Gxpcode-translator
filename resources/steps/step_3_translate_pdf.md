# Step 3 — AI 翻译（PDF路径）

> **加载触发器**：Step 2 术语扫描完成后加载。
> **输入**：逐页原文 + 分页术语映射 `_scan/`（Step 2 产出）。
> **输出铁律**：翻译内容仅写入 `*_trans.md` 文件。对话框**仅显示进度**，不得输出译文内容。

---

## Agent 翻译（5 页/Agent，并发 ≤ 8）

Step 2 已产出 `_scan/` 分页术语映射。主流程按 5 页切分，每批起一个 Agent。Agent 收到分配页的原文 + 该批页的术语映射（批次内去重，跨批次不共享），仅负责翻译，不执行术语扫描。

**Agent Prompt 模板**：

```
你是{domain}领域({subdomain})专业翻译。将以下{source_lang}翻译为{target_lang}。

## 术语映射（必须使用以下译法）

{en_cn_map}

## 翻译规则

1. 禁用"待XX"机械直译（如 "to be steamed" ≠ "待蒸汽灭菌"，应为"需蒸汽灭菌"）
2. 禁用"被XX"被动结构，中文尽量用主动语态
3. 术语必须使用上方映射表中的指定译法
4. 保持原文段落结构，段落数量严格一致
5. **段落间必须有空行**：每个段落和标题（##）之间必须以空行分隔（`\n\n`），禁止 `## 标题\n正文` 无空行拼接
6. 公式（$...$）和 HTML 表格标签保持不变，仅翻译表格内文本内容
7. 图片链接（!\[\](...)）保持不变
8. 译文使用中文标点符号
9. **原文完整保证**：原文文件已经过系统预处理，保证内容完整无截断。你必须翻译原文中的每一行、每一个表格行（`<tr>`），不得自行判断内容是否截断或省略任何内容。

## 原文

{source_text}

## 译文（仅输出译文，不要任何解释）
```

---

## 调度器实现（主流程代码，非 Agent 指令）

> ⚠️ 以下内容仅供主流程编排参考。Agent 翻译时只能加载上一节的 Prompt 模板，严禁加载本节代码。

## 进度格式

```
🌐 翻译中... 1/10  3_p001.md → 已保存
🌐 翻译中... 2/10  3_p002.md → 已保存
...
✅ 翻译完成: 10/10 页
```

---

## 实现方式

```powershell
# 创建 pages 目录
New-Item -ItemType Directory -Force -Path "$outDir/pages" | Out-Null

# 逐页翻译（静默）+ 保存
$pageNum = 0
foreach ($page in $pageFiles) {
    $pageNum++
    Write-Output "🌐 翻译中... $pageNum/$totalPages  $($page.Name)"

    $sourceText = Get-Content $page.FullName -Raw -Encoding UTF8
    # [内部] 从 _scan/<file>_pXXX.json 读取该页术语映射，注入 Prompt
    # [内部] 构建 Prompt → LLM 翻译 → $translatedText

    # 保存该页译文 【立即落盘，不展示】
    $outName = ($page.BaseName -replace '\.md$', '') + "_trans.md"
    [System.IO.File]::WriteAllText("$outDir/pages/$outName", $translatedText, [System.Text.UTF8Encoding]::new($false))
}
Write-Output "✅ 翻译完成: $totalPages/$totalPages 页"
```

> **强制规则**：
> 1. 翻译内容永不输出到对话框
> 2. 每翻完一页，立即落盘
> 3. 对话框仅输出进度行（每页一行 + 完结一行）
> 4. Agent 不执行术语扫描——术语映射由主流程从 Step 2 `_scan/` 目录按页读取注入

---

## 表格拆行翻译（防截断）

> **触发条件**：处理某一页时，检测到 element `label == "tab"` 且 `<tr>` 行数 > 2。

大 HTML 表格（3000+ 字符）直接送 LLM 会截断。拆 `<tr>` 逐行翻译 → 校验 → 拼回。

```powershell
$tableText = $el.text
$rows = [regex]::Matches($tableText, '<tr>.*?</tr>', 'Singleline') | % { $_.Value }
$rowCount = $rows.Count

# 表头行翻译列名（带术语映射）
$transHeader = <LLM: "翻译表格列名，仅翻译<td>内文本。术语：${en_cn_map}`n`n${rows[0]}">

# 数据行逐行翻译（每行注入术语映射）
$transRows = @($transHeader)
for ($j = 1; $j -lt $rows.Count; $j++) {
    $rowPrompt = "你是{domain}领域({subdomain})专业翻译。仅翻译<td>内文本。术语：`n${en_cn_map}`n`n${rows[$j]}"
    $transRows += <LLM>
}

# 校验行数
if ($transRows.Count -ne $rowCount) { Write-Output "⚠️ 表格行数不匹配"; 回退重译 }

# 拼回（保留原 <table...> 外壳）
$before = $tableText.Substring(0, $tableText.IndexOf('<tr>'))
$el.translatedText = $before + ($transRows -join "")
```
