# Changelog

## [2.0.1] - 2026-07-24

### 首次发布
- 完整 PDF/文本翻译流水线：OCR 解析 → 术语扫描 → Agent 分页翻译 → 合并校验 → 双语导出
- AC 自动机术语匹配（pyahocorasick）＋ 词边界过滤
- PaddleOCR-VL-1.6 云 API 集成
- Risograph 风格双语对照 HTML ＋ 双语 Markdown 导出
- 5 页/Agent 并发翻译（并发 ≤ 8）
- 自动截断修复、表格逐行翻译、空值安全回退
