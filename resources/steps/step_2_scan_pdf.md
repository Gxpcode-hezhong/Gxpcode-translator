# Step 2 — 术语扫描（PDF路径）

> **加载触发器**：PDF 路径 Step 1a 截断修复完成后加载。
> **前置依赖**：Step 1a 完成，`paddleocr/markdown/` 下存在完整 `*_p*.md` 文件。
> **产出**：分页术语映射 `_scan/` 目录 → Step 3 按批次注入 Agent。Agent 之间术语不可见。

---

## 按页扫描（带进度）

遍历所有逐页 md，对每页单独调用术语扫描。必须向用户展示进度：

```
🔍 术语扫描中... 1/10  3_p001.md → 86 matches
🔍 术语扫描中... 2/10  3_p002.md → 41 matches
...
✅ 术语扫描完成: 10 页, 79 个唯一术语
```

```powershell
$tempJson = "$outDir/_term_scan.json"
$pageFiles = Get-ChildItem "$paddleDir/markdown" -Filter "*_p*.md" | Sort-Object Name
$totalPages = $pageFiles.Count
$pageNum = 0
foreach ($page in $pageFiles) {
    $pageNum++
    Write-Output "🔍 术语扫描中... $pageNum/$totalPages"
    $text = Get-Content $page.FullName -Raw -Encoding UTF8
    & $pyExe "$SkillDir\scripts\lib\term_matcher.py" --output "$tempJson" $text
    $data = Get-Content $tempJson -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Output "   $($page.Name): $($data.match_count) 个术语命中"
    $allMatches += $data.matches
}
```

---

## 按页输出术语映射

每页术语扫描结果独立保存，**不做全局合并去重**。

```
_scan/
├── <file>_p001.json   # 第1页命中的术语
├── <file>_p002.json   # 第2页命中的术语
└── ...
```

Step 3 主流程按 5 页切分后，为该批 Agent 合并所属页的术语映射（批次内去重，跨批次不共享）。

---

## 术语匹配实现

脚本：`scripts/lib/term_matcher.py`

**设计原则**：pyahocorasick AC 自动机，术语一次遍历完成全部匹配。长词优先，大小写不敏感，词边界过滤（`_is_word_boundary()`——匹配位置前后必须为非字母字符）。

**输出 JSON**：
```json
{
  "source_text": "原文",
  "matches": [{"start": 0, "end": 20, "en": "sterilization filter", "cn": "除菌过滤器"}],
  "match_count": 1
}
```

流程中仅消费 `matches` 字段提取 `en→cn` 映射对。

---

## 词典维护

1. 直接编辑 `Gxpcode-dict.csv`（推荐用 Excel 打开 CSV 编辑）
2. 新增行追加到文件末尾即可
3. 修改后无需重建索引，下次翻译自动生效

**CSV 格式**：
```csv
en,cn,explain
sterilization filter,除菌过滤器,
qualification,确认,
```
