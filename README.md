---
name: gxpcode-translator
description: 专业翻译工具 — 支持文本和 PDF 输入，PDF 输出双语对照 HTML + Markdown。触发关键词：翻译、术语保护、更新术语、词典、glossary、保留特定词。
agent_created: true
allowed-tools:
  - Read
  - Write
  - Edit
  - PowerShell
  - WebFetch
---

# gxpcode-translator

专业翻译工具，支持文本/PDF 输入。核心组件：AC 自动机术语匹配 + PaddleOCR API 解析 + LLM 翻译 + 双语对照导出。

## 快速开始

安装后首次使用会自动触发首次配置，依次询问 5 项：

| # | 配置项 | 类型 | 说明 |
|---|---|---|---|
| 1 | `output_dir` | 选填（有默认值） | 翻译输出目录 |
| 2 | `dict_path` | 选填（有默认值） | 术语词典 CSV 路径 |
| 3 | `domain` | **必填** | 翻译领域，如"制药" |
| 4 | `subdomain` | 选填 | 领域子模块，如"GMP、药品注册" |
| 5 | `paddleocr_token` | PDF 路由必填 | PaddleOCR API 令牌，从 https://aistudio.baidu.com/paddleocr 获取 |

## 工作流

```
文本输入 → 术语扫描 → AI 翻译 → 日志
PDF 输入 → OCR 解析 → 截断修复 → 术语扫描 → Agent 分页翻译 → 合并校验 → 双语导出 → 日志
```

| 步骤 | 文本 | PDF | 说明 |
|---|---|---|---|
| 配置 | Step 0 | Step 0 | 首次运行自动引导 |
| 解析 | — | Step 1 + 1a | PaddleOCR API 按页解析 + 截断修复 |
| 术语 | Step 2_text | Step 2_pdf | AC 自动机扫描，匹配词典术语 |
| 翻译 | Step 3_text | Step 3_pdf | LLM 翻译（PDF 按 5 页/Agent 并发） |
| 校验 | 自检 | Step 4 | merge + 类型分布 + 表格行数 |
| 导出 | — | Step 5 | 双语对照 HTML + Markdown |
| 日志 | Step 5c | Step 5c | 翻译记录写入 output_dir/logs/ |

### 输出

| 产出 | 路径 |
|---|---|
| HTML | `{output_dir}/{ts}-{slug}/Gxpcode-{title}.html` |
| Markdown | `{output_dir}/{ts}-{slug}/Gxpcode-{title}.md` |
| 日志 | `{output_dir}/logs/{ts}_trans.md` |

## 术语词典

CSV 格式（UTF-8 with BOM），三列 `en,cn,explain`：

```csv
en,cn,explain
sterilization filter,除菌过滤器,
qualification,确认,
```

- 直接编辑 CSV 追加术语，无需重建索引
- AC 自动机长词优先匹配，词边界过滤防误命中
- 脚本：`scripts/lib/term_matcher.py`

## 翻译规则

1. 禁止"待XX"机械直译（如 "to be X" ≠ "待X"）
2. 禁止"被XX"被动结构，中文用主动语态
3. 术语使用词典指定译法
4. 段落间必须有空行，保持原文结构
5. 表格仅翻译 `<td>` 内文本，`<tr>` 行数与原文一致

## 脚本清单

| 脚本 | 用途 |
|---|---|
| `scripts/lib/term_matcher.py` | AC 自动机术语匹配 |
| `scripts/paddle_parser.py` | PaddleOCR-VL-1.6 API 解析 |
| `scripts/step1a_fix_truncations.py` | 截断检测与修复 |
| `scripts/step1b_rebuild_page.py` | 从 elements JSON 重建单页文本 |
| `scripts/step4_merge.py` | 逐页译文合并为 element-indexed JSON |
| `scripts/step5a_export_html.py` | 生成双语对照 HTML |
| `scripts/step5b_export_md.py` | 生成双语对照 Markdown |
| `scripts/step5c_write_log.py` | 翻译日志写入 |

## 依赖

```bash
pip install pyahocorasick pdfplumber requests
```

PaddleOCR 使用百度 AI Studio 云端 API，无需本地 GPU。

---

> 术语词典持续维护中。反馈或问题请联系 zhonghe1991@qq.com。
