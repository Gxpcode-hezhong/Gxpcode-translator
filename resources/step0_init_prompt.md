# Step 0 — 首次配置

触发条件：`config.json` 中 `configured` 为 `false`。进入任何路由前先执行。

必须以对话形式依次询问用户以下 5 项配置，不得跳过。每项提供默认值和示例。

交互约定：所有带默认值的项，用户回复 `Y` / `y` / `默认` 即采用默认值。领域（第 3 项）无默认值，必须用户显式填写。

---

## 1. 输出目录

询问："请输入翻译输出目录，回复 Y 使用默认值 [默认: ./translation-output]"
- 用户回复 `Y` / `y` / `默认` → 采用默认值
- 自动创建目录及 logs 子目录

## 2. 术语库路径

询问："请选择术语词典 CSV 文件，回复 Y 使用内置术语库 [默认: Gxpcode-dict.csv]"
- 示例：`Gxpcode-dict.csv`（内置制药） / `/path/to/my-dict.csv`（自定义）
- 用户回复 `Y` / `y` / `默认` → 使用内置 `Gxpcode-dict.csv`

## 3. 领域（强制必填，无默认值）

询问："翻译所属专业领域是什么？（必填，对翻译质量影响重大）"
- 示例：`制药` / `半导体` / `医疗器械` / `化工` / `生物技术` / `法律` / `金融`
- 不可为空，为空或回复 `Y` 则重新提示
- 用户不确定时，引导其描述文档主题以确定领域

## 4. 领域子模块（可空）

询问："领域内的细分方向是什么？可填写多个，回复 Y 跳过 [可空]（不建议跳过）"
- 示例：`GMP` / `药品研发` / `药品注册` / `工艺验证` / `临床前研究`
- 用户回复 `Y` / `y` / `默认` / `无` → 跳过
- 支持多个，用 `、` 或 `,` 分隔

## 5. PaddleOCR Token（PDF 翻译必填）

> 仅当用户计划翻译 PDF 时需要。纯文本翻译可跳过。

询问："是否需要 PDF 翻译？若需要，请访问 https://aistudio.baidu.com/paddleocr 注册/登录后获取 API Token，粘贴至此处。回复 Y 跳过（将无法使用 PDF 翻译功能）"

引导步骤：
1. 打开 https://aistudio.baidu.com/paddleocr
2. 登录百度 AI Studio 账号（如无账号需先注册）
3. 进入 PaddleOCR 服务页面，在"API 调用"或"令牌管理"中复制 Token
4. 将 Token 粘贴至此处

- 用户粘贴非空字符串 → 写入 `paddleocr_token`
- 用户回复 `Y` / `y` / `跳过` / `默认` → `paddleocr_token` 留空，PDF 功能不可用
- 若用户后续需要 PDF 翻译，可手动编辑 `config.json` 添加 `paddleocr_token` 字段

---

全部完成后，写入 `config.json` 并将 `configured` 设为 `true`，输出配置摘要供用户确认。`skill_dir` 和 `python_exe` 由首次配置自动检测写入。

写入方式：

```powershell
$configPath = "$env:USERPROFILE\.workbuddy\skills\gxpcode-translator\config.json"
$config = Get-Content $configPath | ConvertFrom-Json
$config.output_dir = $outDir
$config.dict_path = $dictPath
$config.domain = $domain
$config.subdomain = $subdomain
$config.configured = $true
$config | ConvertTo-Json | Set-Content $configPath -Encoding UTF8
```
