# AI 热点 · 每日智能摘要

聚合 AI 前沿资讯，自动生成智能摘要，一键搜索追踪最新动态。

## 功能

- **多源聚合**：自动采集 Hacker News、Reddit、ArXiv、Timelines 等平台的 AI 相关内容
- **智能摘要**：支持 AI 生成摘要（Claude/OpenAI/HuggingFace）或提取式摘要（默认）
- **全文搜索**：实时搜索标题、摘要、标签
- **分类筛选**：按 LLM / 多模态 / Agent / 工具 / 论文 分类浏览
- **自动更新**：GitHub Actions 每 6 小时自动采集最新资讯
- **零成本部署**：GitHub Pages 免费托管

## 快速开始

### 1. Fork 本仓库

点击右上角 **Fork** 按钮，将本仓库复制到你的 GitHub 账号下。

### 2. 启用 GitHub Pages

进入仓库 Settings → Pages，在 **Source** 中选择 **GitHub Actions**。

### 3. 配置 AI 摘要（可选）

默认使用提取式摘要（无需 API Key），效果已可用。如需 AI 生成摘要，在仓库 Settings → Secrets and variables → Actions 中添加以下任一密钥：

| 密钥 | API | 获取地址 |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude API | https://console.anthropic.com |
| `OPENAI_API_KEY` | OpenAI API | https://platform.openai.com |
| `HF_TOKEN` | Hugging Face Inference API（免费） | https://huggingface.co/settings/tokens |

然后手动触发 Workflow，选择 `summary_method: ai`。

### 4. 首次运行

进入 Actions → Fetch AI News → **Run workflow**，手动触发首次数据采集。之后每 6 小时自动更新。

### 5. 访问网站

部署完成后，访问 `https://<你的用户名>.github.io/ai-hot-news/`

## 本地开发

```bash
# 安装 Python（无需额外依赖，仅使用标准库）

# 获取示例数据（无需 API）
python scripts/fetch_news.py

# 使用 AI 摘要（可选）
export ANTHROPIC_API_KEY=sk-xxx
export SUMMARY_METHOD=ai
python scripts/fetch_news.py

# 启动本地服务
python -m http.server 8000
# 访问 http://localhost:8000
```

## 项目结构

```
ai-hot-news/
├── index.html              # 主页
├── styles.css              # 样式
├── js/
│   └── app.js              # 前端应用逻辑
├── data/
│   └── news.json           # 新闻数据（由脚本生成）
├── scripts/
│   └── fetch_news.py       # 新闻采集 & 摘要生成
├── .github/workflows/
│   └── fetch-news.yml      # 自动更新 workflow
└── README.md
```

## 数据来源

- [Hacker News](https://news.ycombinator.com/) — Firebase API（免费）
- [Reddit](https://www.reddit.com/r/artificial/) — JSON API（免费）
- [ArXiv](https://arxiv.org/) — API（免费）
- [Timelines AI](https://timelines.ai/) — API（免费）

## License

MIT
