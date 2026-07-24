# Step 2 — 术语扫描（文本路径）

> **加载触发器**：文本输入时加载。
> **前置依赖**：Step 0 配置完成。
> **产出**：全文术语映射 → 注入 Step 3 翻译。

---

## 单次扫描

全文只扫一次。调用 `scripts/lib/term_matcher.py`。

```powershell
& $PythonExe "$SkillDir\scripts\lib\term_matcher.py" --output "$tempJson" "$sourceText"
```

从输出 JSON 的 `matches` 字段提取 `en→cn` 映射对，传给 Step 3。

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
