#!/usr/bin/env python3
"""Fetch AI-related news from multiple free APIs and save as JSON.

Sources (no API keys required):
  - Hacker News API (official Firebase API)
  - Reddit API (JSON endpoints for r/artificial, r/MachineLearning)
  - Timelines AI (timelines.ai) — public RSS-to-JSON
  - ArXiv API — recent cs.AI papers

Output: ../data/news.json (ready for GitHub Pages)
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
import re
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CACHE_TTL = 3600  # 1 hour minimum between fetches

# ---------- Helpers ----------

def json_get(url, timeout=15):
    """Fetch URL and parse JSON."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "AIHotNews/1.0 (github; contact@example.com)",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as e:
        print(f"  [WARN] Failed to fetch {url}: {e}", file=sys.stderr)
        return None


def extract_tags(title, text):
    """Simple keyword-based tag extraction."""
    title_lower = (title + " " + (text or "")).lower()
    tags = []
    keyword_map = {
        "llm": ["llm", "gpt", "claude", "gemini", "llama", "mistral", "language model",
                "transformer", "bert", "t5", "openai", "anthropic", "large language model",
                "foundation model", "pretrain", "fine-tun"],
        "vision": ["vision", "image", "video", "diffusion", "stable diffusion", "midjourney",
                   "dall-e", "visual", "object detection", "segmentation", "gan"],
        "agent": ["agent", "autonomous", "tool use", "function calling", "planning",
                  "multi-agent", "agentic", "react", "langgraph", "crewai"],
        "tool": ["tool", "framework", "library", "sdk", "api", "platform", "deploy",
                 "inference", "serving", "vllm", "tgi", "ollama", "langchain", "llamaindex",
                 "vector database", "rag", "embedding"],
        "paper": ["paper", "arxiv", "research", "benchmark", "state-of-the-art",
                  "sota", "dataset", "evaluation", "novel method"],
    }
    for tag, keywords in keyword_map.items():
        for kw in keywords:
            if kw in title_lower:
                tags.append(tag)
                break
    return list(set(tags)) or ["ai"]


def score_to_str(score):
    """Format score for display."""
    if score is None:
        return ""
    if isinstance(score, (int, float)):
        if score > 1000:
            return f"🔥 {score // 1000}.{score % 1000 // 100}k"
        return f"{score}"
    return str(score)


def clean_html(text):
    """Remove HTML tags."""
    return re.sub(r"<[^>]+>", "", text) if text else ""


# ---------- Source: Hacker News ----------

def fetch_hacker_news(limit=30):
    """Fetch top stories from HN, filter AI-related."""
    print("[HN] Fetching top stories...", file=sys.stderr)
    ids = json_get("https://hacker-news.firebaseio.com/v0/topstories.json")
    if not ids:
        return []

    items = []
    for item_id in ids[:80]:  # Check top 80
        item = json_get(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json")
        if not item or not item.get("title"):
            continue
        title = item["title"]
        tags = extract_tags(title, "")
        if "ai" not in tags and len(tags) == 1:
            continue  # Skip non-AI stories

        url = item.get("url", f"https://news.ycombinator.com/item?id={item_id}")
        points = item.get("score", 0)
        text = clean_html(item.get("text", ""))[:500]

        items.append({
            "title": title,
            "summary": text or title,
            "full_text": text or "",
            "source": "hacker news",
            "url": url,
            "published_at": datetime.fromtimestamp(
                item.get("time", time.time()), tz=timezone.utc
            ).isoformat(),
            "tags": tags,
            "score": score_to_str(points),
            "item_id": f"hn:{item_id}",
        })
        if len(items) >= limit:
            break

    print(f"  -> {len(items)} AI-related stories", file=sys.stderr)
    return items


# ---------- Source: Reddit ----------

def fetch_reddit(subreddits=("artificial", "MachineLearning"), limit=15):
    """Fetch hot posts from AI subreddits."""
    items = []
    for sub in subreddits:
        print(f"[Reddit] r/{sub}...", file=sys.stderr)
        data = json_get(f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}")
        if not data:
            continue
        for post in data.get("data", {}).get("children", []):
            p = post.get("data", {})
            title = p.get("title", "")
            tags = extract_tags(title, p.get("selftext", ""))
            if "ai" not in tags and len(tags) == 1:
                continue

            selftext = clean_html(p.get("selftext", ""))[:500]
            items.append({
                "title": title,
                "summary": selftext or title,
                "full_text": selftext or "",
                "source": "reddit",
                "url": f"https://www.reddit.com{p.get('permalink', '')}",
                "published_at": datetime.fromtimestamp(
                    p.get("created_utc", time.time()), tz=timezone.utc
                ).isoformat(),
                "tags": tags,
                "score": score_to_str(p.get("score", 0)),
                "item_id": f"reddit:{p.get('id', '')}",
            })
    print(f"  -> {len(items)} AI posts", file=sys.stderr)
    return items


# ---------- Source: ArXiv ----------

def fetch_arxiv(max_results=20):
    """Fetch recent cs.AI papers from ArXiv API."""
    print("[ArXiv] Fetching recent papers...", file=sys.stderr)
    url = (
        "http://export.arxiv.org/api/query?"
        "search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending"
        f"&max_results={max_results}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "AIHotNews/1.0"})
    items = []
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            xml = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [WARN] ArXiv API error: {e}", file=sys.stderr)
        return []

    # Simple XML parsing (no external deps)
    entries = re.findall(r"<entry>(.*?)</entry>", xml, re.DOTALL)
    for entry in entries:
        title_match = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
        summary_match = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
        id_match = re.search(r"<id>(.*?)</id>", entry)
        published_match = re.search(r"<published>(.*?)</published>", entry)

        if not title_match:
            continue
        title = clean_html(title_match.group(1)).strip()
        summary = clean_html(summary_match.group(1)).strip()[:500] if summary_match else ""
        paper_url = id_match.group(1).strip() if id_match else ""
        published = published_match.group(1).strip() if published_match else ""

        tags = extract_tags(title, summary)
        tags.append("paper")

        items.append({
            "title": title,
            "summary": summary or title,
            "full_text": "",
            "source": "arxiv",
            "url": paper_url,
            "published_at": published,
            "tags": list(set(tags)),
            "score": "📄",
            "item_id": f"arxiv:{paper_url.split('/')[-1] if paper_url else ''}",
        })

    print(f"  -> {len(items)} papers", file=sys.stderr)
    return items


# ---------- Source: Timelines AI ----------

def fetch_timelines(limit=15):
    """Fetch AI news from Timelines AI public feed."""
    print("[Timelines] Fetching AI news...", file=sys.stderr)
    data = json_get(
        f"https://timelines.ai/api/public/news?limit={limit}&category=ai"
    )
    if not data:
        # Fallback: try different API endpoint
        data = json_get("https://timelines.ai/api/headlines?limit=20")

    if not data or isinstance(data, dict) and data.get("error"):
        print("  [WARN] Timelines API unavailable", file=sys.stderr)
        return []

    items = []
    entries = data if isinstance(data, list) else data.get("items", data.get("data", []))
    for entry in entries:
        title = entry.get("title", entry.get("headline", ""))
        if not title:
            continue
        tags = extract_tags(title, entry.get("description", ""))
        summary = entry.get("description", entry.get("summary", ""))[:500]
        items.append({
            "title": title,
            "summary": summary or title,
            "full_text": entry.get("content", "")[:500] if entry.get("content") else "",
            "source": "timelines",
            "url": entry.get("url", entry.get("link", "")),
            "published_at": entry.get("published_at", entry.get("date", datetime.now(timezone.utc).isoformat())),
            "tags": tags,
            "score": entry.get("score", ""),
            "item_id": f"tl:{entry.get('id', '')}",
        })
    print(f"  -> {len(items)} items", file=sys.stderr)
    return items


# ---------- Summarization Integration ----------

def generate_summaries(items, method="extractive"):
    """Generate/improve summaries for items.

    method: 'extractive' (default, no deps), or 'ai' (requires API key)
    """
    if method == "ai":
        try:
            return _summarize_with_ai(items)
        except Exception as e:
            print(f"[WARN] AI summarization failed: {e}", file=sys.stderr)
            print("[INFO] Falling back to extractive summarization", file=sys.stderr)

    # Extractive: use first 2-3 sentences
    for item in items:
        text = item.get("summary", item.get("title", ""))
        sentences = re.split(r"(?<=[.!?])\s+", text)
        if len(sentences) > 3:
            item["summary"] = " ".join(sentences[:3])
        item["summary_type"] = "extractive"

    return items


def _summarize_with_ai(items):
    """Use an LLM API to generate summaries.

    Supports: Anthropic Claude API, OpenAI API, or Hugging Face Inference API.
    Set ANTHROPIC_API_KEY, OPENAI_API_KEY, or HF_TOKEN env vars.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("HF_TOKEN")
    if not api_key:
        print("[INFO] No AI API key found, using extractive summarization", file=sys.stderr)
        raise Exception("No API key")

    if os.environ.get("ANTHROPIC_API_KEY"):
        return _summarize_with_claude(items, api_key)
    elif os.environ.get("OPENAI_API_KEY"):
        return _summarize_with_openai(items, api_key)
    else:
        return _summarize_with_hf(items, api_key)


def _summarize_with_claude(items, api_key):
    """Summarize using Anthropic Claude API."""
    import json as _json
    for item in items:
        title = item["title"]
        text = item.get("full_text") or item.get("summary", "")
        prompt = _json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 200,
            "messages": [{
                "role": "user",
                "content": f"Summarize this AI news in 2 sentences in Chinese:\n\nTitle: {title}\n\n{text[:2000]}"
            }]
        })
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=prompt.encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = _json.loads(resp.read())
                item["summary"] = result["content"][0]["text"]
                item["summary_type"] = "ai"
        except Exception as e:
            print(f"  [WARN] Claude API error for '{title[:40]}': {e}", file=sys.stderr)
            item["summary_type"] = "extractive"
    return items


def _summarize_with_openai(items, api_key):
    """Summarize using OpenAI API."""
    import json as _json
    for item in items:
        title = item["title"]
        text = item.get("full_text") or item.get("summary", "")
        prompt = _json.dumps({
            "model": "gpt-4o-mini",
            "max_tokens": 200,
            "messages": [{
                "role": "user",
                "content": f"Summarize this AI news in 2 sentences in Chinese:\n\nTitle: {title}\n\n{text[:2000]}"
            }]
        })
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=prompt.encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = _json.loads(resp.read())
                item["summary"] = result["choices"][0]["message"]["content"]
                item["summary_type"] = "ai"
        except Exception as e:
            print(f"  [WARN] OpenAI API error for '{title[:40]}': {e}", file=sys.stderr)
            item["summary_type"] = "extractive"
    return items


def _summarize_with_hf(items, api_key):
    """Summarize using Hugging Face Inference API (free tier)."""
    import json as _json
    for item in items:
        text = item.get("summary", item.get("title", ""))[:1000]
        if len(text) < 100:
            item["summary_type"] = "extractive"
            continue
        payload = _json.dumps({
            "inputs": text,
            "parameters": {"max_length": 150, "min_length": 40},
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api-inference.huggingface.co/models/facebook/bart-large-cnn",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = _json.loads(resp.read())
                if isinstance(result, list) and len(result) > 0:
                    item["summary"] = result[0].get("summary_text", item["summary"])
                    item["summary_type"] = "ai"
        except Exception as e:
            print(f"  [WARN] HF API error for '{item['title'][:40]}': {e}", file=sys.stderr)
            item["summary_type"] = "extractive"
    return items


# ---------- Translation ----------

def translate_items(items, method="extractive"):
    """Add Chinese translations (title_zh, summary_zh) to all items.

    When AI API is available (method='ai'), translates using the API.
    Otherwise copies originals as fallback.
    """
    if method == "ai" and (
        os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
    ):
        try:
            return _translate_with_ai(items)
        except Exception as e:
            print(f"[WARN] AI translation failed: {e}", file=sys.stderr)

    # Fallback: copy originals
    for item in items:
        item["title_zh"] = item.get("title", "")
        item["summary_zh"] = item.get("summary", "")
    print(f"  -> {len(items)} items copied as-is (no AI translation)", file=sys.stderr)
    return items


def _translate_with_ai(items):
    """Translate titles & summaries to Chinese using AI API (batched)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise Exception("No API key")

    if os.environ.get("ANTHROPIC_API_KEY"):
        return _translate_with_claude(items, api_key)
    else:
        return _translate_with_openai(items, api_key)


def _translate_with_claude(items, api_key):
    """Batch-translate titles and summaries via Claude."""
    import json as _json
    batch = []
    for i, item in enumerate(items):
        batch.append({
            "id": i,
            "title": item["title"],
            "summary": item.get("summary", "")[:300],
        })

    prompt = _json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4000,
        "messages": [{
            "role": "user",
            "content": (
                "Translate each AI news item below to Chinese. "
                "For each item, provide:\n"
                "- title_zh: Chinese translation of the title (keep technical terms in English)\n"
                "- summary_zh: Chinese summary (2 sentences)\n\n"
                f"Return ONLY valid JSON array, each element has 'id', 'title_zh', 'summary_zh':\n"
                + _json.dumps(batch, ensure_ascii=False)
            )
        }]
    })

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=prompt.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = _json.loads(resp.read())
            content = result["content"][0]["text"]
            # Extract JSON from response
            json_match = re.search(r"\[.*\]", content, re.DOTALL)
            if json_match:
                translations = _json.loads(json_match.group(0))
                for t in translations:
                    idx = t["id"]
                    items[idx]["title_zh"] = t.get("title_zh", items[idx]["title"])
                    items[idx]["summary_zh"] = t.get("summary_zh", items[idx].get("summary", ""))
                print(f"  -> {len(translations)} items translated via Claude", file=sys.stderr)
    except Exception as e:
        print(f"  [WARN] Batch translation failed: {e}, falling back", file=sys.stderr)
        for item in items:
            item["title_zh"] = item.get("title", "")
            item["summary_zh"] = item.get("summary", "")
    return items


def _translate_with_openai(items, api_key):
    """Batch-translate titles and summaries via OpenAI."""
    import json as _json
    batch = []
    for i, item in enumerate(items):
        batch.append({
            "id": i,
            "title": item["title"],
            "summary": item.get("summary", "")[:300],
        })

    prompt = _json.dumps({
        "model": "gpt-4o-mini",
        "max_tokens": 4000,
        "messages": [{
            "role": "user",
            "content": (
                "Translate each AI news item below to Chinese. "
                "For each item, provide:\n"
                "- title_zh: Chinese translation of the title\n"
                "- summary_zh: Chinese summary (2 sentences)\n\n"
                f"Return ONLY valid JSON array, each element has 'id', 'title_zh', 'summary_zh':\n"
                + _json.dumps(batch, ensure_ascii=False)
            )
        }]
    })

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=prompt.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = _json.loads(resp.read())
            content = result["choices"][0]["message"]["content"]
            json_match = re.search(r"\[.*\]", content, re.DOTALL)
            if json_match:
                translations = _json.loads(json_match.group(0))
                for t in translations:
                    idx = t["id"]
                    items[idx]["title_zh"] = t.get("title_zh", items[idx]["title"])
                    items[idx]["summary_zh"] = t.get("summary_zh", items[idx].get("summary", ""))
                print(f"  -> {len(translations)} items translated via OpenAI", file=sys.stderr)
    except Exception as e:
        print(f"  [WARN] Batch translation failed: {e}, falling back", file=sys.stderr)
        for item in items:
            item["title_zh"] = item.get("title", "")
            item["summary_zh"] = item.get("summary", "")
    return items


# ---------- Main ----------

def main():
    print("=" * 50, file=sys.stderr)
    print("AI Hot News — Fetching Pipeline", file=sys.stderr)
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}", file=sys.stderr)
    print("=" * 50, file=sys.stderr)

    all_items = []
    seen_ids = set()

    # Fetch from all sources
    sources = [
        ("Hacker News", fetch_hacker_news),
        ("Reddit", fetch_reddit),
        ("ArXiv", fetch_arxiv),
        ("Timelines", fetch_timelines),
    ]

    for name, fetcher in sources:
        print(f"\n[{name}]", file=sys.stderr)
        try:
            items = fetcher()
            for item in items:
                item_id = item.get("item_id", item["url"])
                if item_id not in seen_ids:
                    seen_ids.add(item_id)
                    all_items.append(item)
        except Exception as e:
            print(f"  [ERROR] {name} failed: {e}", file=sys.stderr)

    # Deduplicate by URL
    seen_urls = set()
    unique_items = []
    for item in all_items:
        url = item.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_items.append(item)

    print(f"\n{'=' * 50}", file=sys.stderr)
    print(f"Total unique items: {len(unique_items)}", file=sys.stderr)

    # Generate summaries
    print("\n[Summary] Generating summaries...", file=sys.stderr)
    summarization_method = os.environ.get("SUMMARY_METHOD", "extractive")
    unique_items = generate_summaries(unique_items, method=summarization_method)

    # Translate to Chinese
    print("\n[Translate] Adding Chinese translations...", file=sys.stderr)
    unique_items = translate_items(unique_items, method=summarization_method)

    # Sort by score/recency
    def sort_key(item):
        try:
            return datetime.fromisoformat(item["published_at"])
        except:
            return datetime.min.replace(tzinfo=timezone.utc)
    unique_items.sort(key=sort_key, reverse=True)

    # Build output
    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(unique_items),
        "items": unique_items,
    }

    # Write
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DATA_DIR / "news.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✓ Saved {len(unique_items)} items to {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
