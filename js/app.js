/* ==========================================
   AI Hot News — Application
   ========================================== */

(function () {
    'use strict';

    // ---------- State ----------
    let newsData = [];
    let filteredData = [];
    let activeFilter = 'all';
    let searchQuery = '';

    // ---------- DOM refs ----------
    const grid = document.getElementById('newsGrid');
    const emptyState = document.getElementById('emptyState');
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const statusText = document.getElementById('statusText');
    const updateTime = document.getElementById('updateTime');
    const modal = document.getElementById('modal');
    const modalBody = document.getElementById('modalBody');
    const modalClose = document.getElementById('modalClose');
    const filterBtns = document.querySelectorAll('.filter-btn');
    const refreshLink = document.getElementById('refreshLink');

    // ---------- Utils ----------
    function formatDate(dateStr) {
        const d = new Date(dateStr);
        const now = new Date();
        const diff = (now - d) / 1000;
        if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
        if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
        if (diff < 604800) return `${Math.floor(diff / 86400)} 天前`;
        return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
    }

    function sourceClass(source) {
        const map = {
            'hacker news': 'source-hn',
            'reddit': 'source-reddit',
            'newsapi': 'source-newsapi',
            'arxiv': 'source-arxiv',
            'timelines': 'source-timelines',
        };
        return map[source.toLowerCase()] || 'source-default';
    }

    function sourceLabel(source) {
        const map = {
            'hacker news': 'Y Combinator',
            'reddit': 'Reddit',
            'newsapi': 'News',
            'arxiv': 'ArXiv',
            'timelines': 'Timelines',
        };
        return map[source.toLowerCase()] || source;
    }

    function extractDomain(url) {
        try { return new URL(url).hostname.replace('www.', ''); } catch { return url; }
    }

    // ---------- Render ----------
    function render() {
        const data = filteredData;

        if (data.length === 0) {
            grid.innerHTML = '';
            emptyState.classList.add('visible');
            return;
        }
        emptyState.classList.remove('visible');

        grid.innerHTML = data.map((item, idx) => `
            <article class="news-card" data-index="${idx}" style="animation-delay: ${(idx % 12) * 0.05}s">
                <div class="news-card-header">
                    <span class="news-source ${sourceClass(item.source)}">
                        ${sourceLabel(item.source)}
                    </span>
                    <span class="news-date">${formatDate(item.published_at)}</span>
                </div>
                <h3>${escapeHtml(item.title)}</h3>
                <p class="news-summary">${escapeHtml(item.summary)}</p>
                <div class="news-card-footer">
                    <div class="news-tags">
                        ${(item.tags || []).slice(0, 3).map(t =>
                            `<span class="news-tag">${escapeHtml(t)}</span>`
                        ).join('')}
                        <span class="summary-badge ${item.summary_type === 'ai' ? 'badge-ai' : 'badge-extractive'}">
                            ${item.summary_type === 'ai' ? 'AI' : '摘要'}
                        </span>
                    </div>
                    <span class="news-score">${item.score || ''}</span>
                </div>
            </article>
        `).join('');

        // Click to open modal
        grid.querySelectorAll('.news-card').forEach(card => {
            card.addEventListener('click', () => {
                const idx = parseInt(card.dataset.index);
                openModal(filteredData[idx]);
            });
        });
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // ---------- Filter & Search ----------
    function applyFilters() {
        let data = newsData;

        // Filter by category
        if (activeFilter !== 'all') {
            data = data.filter(item =>
                (item.tags || []).some(t => t.toLowerCase() === activeFilter.toLowerCase())
            );
        }

        // Search
        if (searchQuery.trim()) {
            const q = searchQuery.trim().toLowerCase();
            data = data.filter(item =>
                (item.title || '').toLowerCase().includes(q) ||
                (item.summary || '').toLowerCase().includes(q) ||
                (item.tags || []).some(t => t.toLowerCase().includes(q))
            );
        }

        filteredData = data;
        render();
    }

    // ---------- Modal ----------
    function openModal(item) {
        document.body.style.overflow = 'hidden';
        modalBody.innerHTML = `
            <h2>${escapeHtml(item.title)}</h2>
            <div class="modal-meta">
                <span class="news-source ${sourceClass(item.source)}">${sourceLabel(item.source)}</span>
                <span>${new Date(item.published_at).toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
                <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener">原文链接 ↗</a>
            </div>
            <div class="modal-section">
                <h4>AI 摘要</h4>
                <p>${escapeHtml(item.summary)}</p>
            </div>
            ${item.full_text ? `
            <div class="modal-section">
                <h4>全文概览</h4>
                <p>${escapeHtml(item.full_text)}</p>
            </div>` : ''}
            ${(item.tags || []).length > 0 ? `
            <div class="modal-section">
                <h4>标签</h4>
                <div class="news-tags">
                    ${item.tags.map(t => `<span class="news-tag">${escapeHtml(t)}</span>`).join('')}
                </div>
            </div>` : ''}
            <div class="modal-section">
                <h4>来源</h4>
                <p><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener">${extractDomain(item.url)}</a></p>
            </div>
        `;
        modal.classList.add('open');
    }

    function closeModal() {
        modal.classList.remove('open');
        document.body.style.overflow = '';
    }

    modalClose.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => { if (e.target === modal) closeModal(); });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });

    // ---------- Load Data ----------
    async function loadData() {
        statusText.textContent = '正在加载最新 AI 资讯…';
        try {
            const resp = await fetch('data/news.json?' + Date.now());
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();
            newsData = data.items || data;
            updateTime.textContent = `更新于 ${data.updated_at ? new Date(data.updated_at).toLocaleString('zh-CN') : '—'}`;
            statusText.textContent = `共 ${newsData.length} 条 AI 热点`;
            applyFilters();
        } catch (err) {
            statusText.textContent = '⚠ 加载失败，使用示例数据';
            console.warn('Failed to load news.json:', err);
            // Fallback sample data
            newsData = getSampleData();
            applyFilters();
        }
    }

    // ---------- Events ----------
    searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value;
        applyFilters();
    });

    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') applyFilters();
    });

    searchBtn.addEventListener('click', applyFilters);

    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeFilter = btn.dataset.filter;
            applyFilters();
        });
    });

    refreshLink.addEventListener('click', (e) => {
        e.preventDefault();
        loadData();
    });

    // ---------- Init ----------
    document.addEventListener('DOMContentLoaded', loadData);

    // ---------- Sample Data ----------
    function getSampleData() {
        return [
            {
                title: 'OpenAI 发布 GPT-5：推理能力大幅提升，支持多模态',
                summary: 'OpenAI 发布了 GPT-5 模型，在数学推理、代码生成和多模态理解方面取得了显著进步。新模型支持文本、图像和音频输入，在多个基准测试中超越了前代产品。',
                source: 'newsapi',
                url: 'https://openai.com',
                published_at: new Date().toISOString(),
                tags: ['llm', '多模态'],
                summary_type: 'ai',
                score: '🔥 12.3k',
            },
            {
                title: 'Claude 3.5 Opus 发布：Anthropic 最强模型登场',
                summary: 'Anthropic 发布了 Claude 3.5 Opus，在编程、推理和长文本理解方面达到业界领先水平。支持 200K token 上下文窗口，在 SWE-bench 上取得最高分。',
                source: 'hacker news',
                url: 'https://anthropic.com',
                published_at: new Date(Date.now() - 3600000).toISOString(),
                tags: ['llm', 'tool'],
                summary_type: 'ai',
                score: '🔥 8.7k',
            },
            {
                title: 'Google DeepMind 推出 Gemini 2.0：原生多模态 Agent 框架',
                summary: 'Google DeepMind 发布了 Gemini 2.0，这是首个原生多模态 Agent 框架。该模型能够自主规划、执行复杂任务，并支持工具调用和实时交互。',
                source: 'reddit',
                url: 'https://deepmind.google',
                published_at: new Date(Date.now() - 7200000).toISOString(),
                tags: ['llm', 'agent', '多模态'],
                summary_type: 'ai',
                score: '🔥 6.5k',
            },
            {
                title: 'Meta 开源 Llama 4：高效的小型语言模型系列',
                summary: 'Meta 发布了 Llama 4 系列模型，包括 8B 和 70B 参数版本。这些模型在推理效率方面进行了优化，可在消费级 GPU 上运行，同时保持了强大的性能。',
                source: 'reddit',
                url: 'https://meta.com',
                published_at: new Date(Date.now() - 14400000).toISOString(),
                tags: ['llm', 'tool'],
                summary_type: 'ai',
                score: '🔥 4.2k',
            },
            {
                title: 'AI Agent 框架对比：LangGraph vs CrewAI vs AutoGen',
                summary: '本文深入对比了当前主流的 AI Agent 框架，从架构设计、多 Agent 协作、工具集成和部署便利性等方面进行了全面评估，帮助开发者选择合适的框架。',
                source: 'timelines',
                url: 'https://example.com/langgraph-vs-crewai',
                published_at: new Date(Date.now() - 21600000).toISOString(),
                tags: ['agent', 'tool'],
                summary_type: 'extractive',
                score: '📝 3.1k',
            },
            {
                title: 'LLM 量化技术最新进展：4-bit 推理达到全精度 99%',
                summary: '研究人员提出了新的量化方法，使得 4-bit 量化的大语言模型在推理任务上达到了接近全精度模型的性能。这项突破将大幅降低 LLM 部署成本，使在边缘设备上运行成为可能。',
                source: 'arxiv',
                url: 'https://arxiv.org',
                published_at: new Date(Date.now() - 28800000).toISOString(),
                tags: ['llm', 'paper'],
                summary_type: 'ai',
                score: '📄 2.8k',
            },
            {
                title: 'Stability AI 发布 Stable Diffusion 4：视频生成重大突破',
                summary: 'Stability AI 发布了 Stable Diffusion 4，实现了高质量的视频生成能力。新模型支持文本到视频、图像到视频，以及视频编辑功能，在一致性和质量上超越了之前的开源模型。',
                source: 'reddit',
                url: 'https://stability.ai',
                published_at: new Date(Date.now() - 36000000).toISOString(),
                tags: ['vision', '多模态'],
                summary_type: 'ai',
                score: '🔥 5.6k',
            },
            {
                title: 'RAG 技术演进：从简单检索到 Agentic RAG',
                summary: '检索增强生成（RAG）技术正在快速演进。本文介绍了从基础的向量检索到 Agentic RAG 的演变路径，包括多跳检索、自适应检索和工具增强等最新进展。',
                source: 'timelines',
                url: 'https://example.com/rag-evolution',
                published_at: new Date(Date.now() - 43200000).toISOString(),
                tags: ['llm', 'tool'],
                summary_type: 'extractive',
                score: '📝 2.1k',
            },
        ];
    }

})();
