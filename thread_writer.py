"""thread_writer — OpenClaw skill backing thread_generate / thread_publish."""

import json
import os
import urllib.request
from typing import List, Optional

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
X_BEARER = os.getenv("X_BEARER_TOKEN", "")

MAX_TWEET = 280

HOOKS = [
    "Here's what nobody tells you about {topic}:",
    "I spent {n} months working with {topic}. Here's what actually matters:",
    "Stop being confused by {topic}. This thread is all you need:",
    "Most people get {topic} completely wrong. Here's the truth:",
    "{topic} changed forever. Here's why:",
]

CTA = ["Follow @you for more threads like this.", "Bookmark this — you'll need it later.", "Share with someone who needs to hear this."]


def _llm_chat(messages) -> str:
    url = f"{LLM_BASE_URL}chat/completions"
    body = json.dumps({"model": LLM_MODEL, "messages": messages, "temperature": 0.9}).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {LLM_API_KEY}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise RuntimeError(f"LLM call failed: {e}")


def _split_into_tweets(text: str, tweets: int) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    out: List[str] = []
    for p in paragraphs:
        while len(p) > MAX_TWEET:
            out.append(p[:MAX_TWEET].rsplit(" ", 1)[0].rstrip(",") + "…")
            p = p[len(out[-1]) :].lstrip()
        out.append(p)
    # Merge to exactly N tweets when possible
    while len(out) > tweets:
        merged = out[0] + " " + out.pop(1)
        out[0] = merged
    return out[:tweets]


def generate_thread(topic: str, tone: str = "engaging", tweets: int = 5) -> List[str]:
    if tweets < 2 or tweets > 25:
        raise ValueError("tweets must be between 2 and 25")
    prompt = (
        f"Write a {tone} X/Twitter thread about '{topic}' with exactly {tweets} "
        "tweets. Use a strong hook first line, then expand with facts/insight, "
        "and finish with a call to action. Separate sections with a blank line. "
        "Keep each section under 260 characters. NO hashtags spam. NO emojis "
        "unless natural."
    )
    raw = _llm(messages=[{"role": "user", "content": prompt}])
    return _split_into_tweets(raw, tweets)


def publish_thread(thread_id: str, tweets: List[str]) -> dict:
    if not X_BEARER:
        return {"status": "dry_run", "thread_id": thread_id, "tweets": tweets}
    url = "https://api.twitter.com/2/tweets"
    posted = []
    prev_id = None
    for t in tweets:
        payload = {"text": t} if not prev_id else {"text": t, "reply": {"in_reply_to_tweet_id": prev_id}}
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(), method="POST",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {X_BEARER}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read())
                tid = data["data"]["id"]
                posted.append(tid)
                prev_id = tid
        except urllib.error.HTTPError as e:
            return {"status": "error", "step": len(posted), "http": e.code, "body": e.read().decode()[:300]}
    return {"status": "posted", "thread_id": thread_id, "tweet_ids": posted}