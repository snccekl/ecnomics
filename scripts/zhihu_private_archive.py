#!/usr/bin/env python3
"""Create a local-only private archive of a Zhihu user's answers.

This script is intended for personal, local use. It reads your own Zhihu cookie
from ZHIHU_COOKIE, fetches answers visible to your account, optionally fetches
comments and images, and writes a local HTML/JSON archive under private_archive/.
The output directory is ignored by Git in this project.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


DEFAULT_USER_TOKEN = "huang-wei-yan-30"
DEFAULT_OUTPUT = Path("private_archive/huang-yanzhen")
USER_AGENT = (
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


class ContentExtractor(HTMLParser):
  def __init__(self) -> None:
    super().__init__()
    self.text_parts: list[str] = []
    self.images: list[str] = []
    self._skip_depth = 0

  def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
    if tag in {"script", "style"}:
      self._skip_depth += 1
      return
    if self._skip_depth:
      return
    attrs_map = dict(attrs)
    if tag == "img":
      src = attrs_map.get("data-original") or attrs_map.get("data-actualsrc") or attrs_map.get("src")
      if src and src.startswith(("http://", "https://")):
        self.images.append(src)
    if tag in {"p", "br", "div", "li", "h1", "h2", "h3", "blockquote"}:
      self.text_parts.append("\n")

  def handle_endtag(self, tag: str) -> None:
    if tag in {"script", "style"} and self._skip_depth:
      self._skip_depth -= 1
    if not self._skip_depth and tag in {"p", "div", "li", "blockquote"}:
      self.text_parts.append("\n")

  def handle_data(self, data: str) -> None:
    if not self._skip_depth:
      stripped = data.strip()
      if stripped:
        self.text_parts.append(stripped)

  def text(self) -> str:
    text = " ".join(part if part != "\n" else "\n" for part in self.text_parts)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_filename(value: str) -> str:
  value = re.sub(r"https?://", "", value.strip().lower())
  value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
  return value.strip("-")[:90] or "item"


def parse_content(content_html: str) -> tuple[str, list[str]]:
  parser = ContentExtractor()
  parser.feed(content_html or "")
  seen: set[str] = set()
  images = []
  for src in parser.images:
    if src not in seen:
      seen.add(src)
      images.append(src)
  return parser.text(), images


def request_json(url: str, cookie: str, referer: str, timeout: int = 30) -> dict[str, Any]:
  req = urllib.request.Request(
    url,
    headers={
      "accept": "application/json, text/plain, */*",
      "cookie": cookie,
      "referer": referer,
      "user-agent": USER_AGENT,
      "x-requested-with": "fetch",
    },
  )
  try:
    with urllib.request.urlopen(req, timeout=timeout) as response:
      charset = response.headers.get_content_charset() or "utf-8"
      text = response.read().decode(charset, errors="replace")
      return json.loads(text)
  except urllib.error.HTTPError as exc:
    body = exc.read().decode("utf-8", errors="replace")[:500]
    raise RuntimeError(f"HTTP {exc.code} for {url}\n{body}") from exc
  except json.JSONDecodeError as exc:
    raise RuntimeError(f"Response is not JSON for {url}") from exc


def fetch_answers(user_token: str, cookie: str, limit: int, delay: float) -> list[dict[str, Any]]:
  answers: list[dict[str, Any]] = []
  seen: set[str] = set()
  offset = 0
  referer = f"https://www.zhihu.com/people/{user_token}/answers"
  include = (
    "data[*].content,excerpt,created_time,updated_time,voteup_count,comment_count,"
    "question.id,question.title"
  )

  while len(answers) < limit:
    page_size = min(20, limit - len(answers))
    params = urllib.parse.urlencode(
      {
        "include": include,
        "offset": offset,
        "limit": page_size,
        "sort_by": "created",
      }
    )
    url = f"https://www.zhihu.com/api/v4/members/{user_token}/answers?{params}"
    payload = request_json(url, cookie, referer)
    batch = payload.get("data") or []
    if not batch:
      break
    before = len(answers)
    for item in batch:
      answer_id = str(item.get("id") or "")
      if answer_id and answer_id not in seen:
        seen.add(answer_id)
        answers.append(item)
    print(f"Fetched answer list page offset={offset}, added={len(answers) - before}, total={len(answers)}", flush=True)
    if payload.get("paging", {}).get("is_end"):
      break
    offset += len(batch)
    time.sleep(delay)
  return answers


def fetch_comments(answer_id: str, cookie: str, delay: float, max_comments: int) -> list[dict[str, str]]:
  comments: list[dict[str, str]] = []
  offset = 0
  referer = f"https://www.zhihu.com/answer/{answer_id}"
  endpoints = [
    "https://www.zhihu.com/api/v4/answers/{answer_id}/root_comments?{params}",
    "https://www.zhihu.com/api/v4/answers/{answer_id}/comments?{params}",
  ]

  while len(comments) < max_comments:
    page_size = min(20, max_comments - len(comments))
    params = urllib.parse.urlencode({"order": "normal", "limit": page_size, "offset": offset, "status": "open"})
    last_error: Exception | None = None
    payload: dict[str, Any] | None = None
    for endpoint in endpoints:
      try:
        payload = request_json(endpoint.format(answer_id=answer_id, params=params), cookie, referer)
        break
      except Exception as exc:
        last_error = exc
    if payload is None:
      raise RuntimeError(f"Could not fetch comments for answer {answer_id}: {last_error}")

    batch = payload.get("data") or []
    if not batch:
      break
    for item in batch:
      author = item.get("author") or {}
      content_html = item.get("content") or item.get("content_html") or ""
      text, _ = parse_content(content_html)
      if text:
        comments.append(
          {
            "author": author.get("name") or "评论",
            "text": text,
            "created": str(item.get("created_time") or ""),
            "vote_count": str(item.get("vote_count") or ""),
          }
        )
    if payload.get("paging", {}).get("is_end"):
      break
    offset += len(batch)
    time.sleep(delay)
  return comments


def download_image(url: str, output_dir: Path, cookie: str, referer: str) -> str:
  output_dir.mkdir(parents=True, exist_ok=True)
  parsed = urllib.parse.urlparse(url)
  suffix = Path(parsed.path).suffix
  if suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
    suffix = ".jpg"
  filename = clean_filename(parsed.path or url)[:70] + suffix
  target = output_dir / filename
  if target.exists():
    return str(target)
  req = urllib.request.Request(
    url,
    headers={"cookie": cookie, "referer": referer, "user-agent": USER_AGENT},
  )
  with urllib.request.urlopen(req, timeout=30) as response:
    target.write_bytes(response.read())
  return str(target)


def normalize_answer(
  answer: dict[str, Any],
  cookie: str,
  output_dir: Path,
  include_comments: bool,
  max_comments: int,
  download_images: bool,
  delay: float,
) -> dict[str, Any]:
  question = answer.get("question") or {}
  answer_id = str(answer.get("id") or "")
  title = question.get("title") or answer.get("title") or f"知乎回答 {answer_id}"
  source = f"https://www.zhihu.com/question/{question.get('id')}/answer/{answer_id}"
  content_html = answer.get("content") or ""
  body_text, images = parse_content(content_html)
  body = [part.strip() for part in re.split(r"\n{2,}", body_text) if part.strip()]
  image_items = [{"src": src, "alt": title, "caption": ""} for src in images]

  if download_images:
    saved = []
    for item in image_items:
      try:
        saved_path = download_image(item["src"], output_dir / "images", cookie, source)
        saved.append({"src": saved_path, "alt": item["alt"], "caption": item["caption"], "original": item["src"]})
        time.sleep(delay)
      except Exception as exc:
        saved.append({**item, "caption": f"download failed: {exc}"})
    image_items = saved

  comments = []
  if include_comments and answer_id:
    try:
      comments = fetch_comments(answer_id, cookie, delay, max_comments)
    except Exception as exc:
      comments = [{"author": "归档提示", "text": f"评论抓取失败：{exc}"}]

  created_time = answer.get("created_time") or answer.get("updated_time") or 0
  date = time.strftime("%Y-%m-%d", time.localtime(int(created_time))) if created_time else ""

  return {
    "id": f"zhihu-answer-{answer_id}",
    "title": title,
    "date": date,
    "source": source,
    "voteup_count": answer.get("voteup_count"),
    "comment_count": answer.get("comment_count"),
    "excerpt": answer.get("excerpt") or (body[0][:200] if body else ""),
    "body": body,
    "images": image_items,
    "comments": comments,
  }


def render_archive_html(items: list[dict[str, Any]], user_token: str) -> str:
  cards = []
  for item in items:
    body = "\n".join(f"<p>{html.escape(paragraph)}</p>" for paragraph in item.get("body", []))
    comments = "\n".join(
      "<blockquote><strong>{}</strong><p>{}</p></blockquote>".format(
        html.escape(comment.get("author", "评论")),
        html.escape(comment.get("text", "")),
      )
      for comment in item.get("comments", [])
    )
    images = "\n".join(
      '<figure><img src="{}" alt="{}" loading="lazy"><figcaption>{}</figcaption></figure>'.format(
        html.escape(image.get("src", "")),
        html.escape(image.get("alt", "")),
        html.escape(image.get("caption", "")),
      )
      for image in item.get("images", [])
    )
    cards.append(
      f"""
      <article class="card">
        <header>
          <h2>{html.escape(item.get("title", ""))}</h2>
          <p>{html.escape(item.get("date", ""))} · 赞同 {html.escape(str(item.get("voteup_count", "")))} · 评论 {html.escape(str(item.get("comment_count", "")))}</p>
          <a href="{html.escape(item.get("source", ""))}" target="_blank" rel="noreferrer">知乎原文</a>
        </header>
        <p class="excerpt">{html.escape(item.get("excerpt", ""))}</p>
        <section class="images">{images}</section>
        <details open><summary>正文</summary>{body}</details>
        <details><summary>评论 {len(item.get("comments", []))}</summary>{comments}</details>
      </article>
      """
    )

  return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>知乎私人归档 - {html.escape(user_token)}</title>
  <style>
    body {{ margin: 0; background: #f6f4ee; color: #202629; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif; }}
    main {{ width: min(980px, calc(100% - 28px)); margin: 0 auto; padding: 32px 0 60px; }}
    h1 {{ font-size: clamp(34px, 6vw, 72px); margin: 0 0 12px; }}
    .card {{ margin: 18px 0; padding: 22px; border: 1px solid #ded8ce; border-radius: 8px; background: #fffdf8; }}
    .card header {{ display: grid; gap: 8px; }}
    .card h2 {{ margin: 0; font-size: 26px; }}
    .card p {{ line-height: 1.85; }}
    .card header p, .excerpt {{ color: #677173; }}
    a {{ color: #2f6f73; font-weight: 750; }}
    details {{ margin-top: 16px; border-top: 1px solid #ded8ce; padding-top: 12px; }}
    summary {{ cursor: pointer; font-weight: 800; }}
    blockquote {{ margin: 12px 0; border-left: 3px solid #2f6f73; padding-left: 12px; }}
    .images {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    figure {{ margin: 0; }}
    img {{ max-width: 100%; border-radius: 8px; }}
    figcaption {{ color: #677173; font-size: 13px; }}
    @media (max-width: 720px) {{ .images {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main>
    <h1>知乎私人归档</h1>
    <p>用户：{html.escape(user_token)} · 条目：{len(items)} · 仅供本机私人检索</p>
    {''.join(cards)}
  </main>
</body>
</html>
"""


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument("--user-token", default=DEFAULT_USER_TOKEN)
  parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
  parser.add_argument("--limit", type=int, default=800)
  parser.add_argument("--delay", type=float, default=1.2)
  parser.add_argument("--include-comments", action="store_true")
  parser.add_argument("--max-comments", type=int, default=50)
  parser.add_argument("--download-images", action="store_true")
  parser.add_argument(
    "--no-resume",
    action="store_true",
    help="Ignore existing archive.json and rebuild from scratch",
  )
  args = parser.parse_args()

  cookie = os.environ.get("ZHIHU_COOKIE", "").strip()
  if not cookie:
    raise SystemExit("Set ZHIHU_COOKIE first. Example: export ZHIHU_COOKIE='z_c0=...; d_c0=...'")

  args.output.mkdir(parents=True, exist_ok=True)
  raw_answers = fetch_answers(args.user_token, cookie, args.limit, args.delay)
  archive_json = args.output / "archive.json"
  items = []
  done_ids: set[str] = set()
  if archive_json.exists() and not args.no_resume:
    items = json.loads(archive_json.read_text(encoding="utf-8"))
    done_ids = {str(item.get("id")) for item in items}
    print(f"Resuming existing archive with {len(items)} saved items", flush=True)

  for index, answer in enumerate(raw_answers, start=1):
    expected_id = f"zhihu-answer-{answer.get('id')}"
    if expected_id in done_ids:
      print(f"[{index}/{len(raw_answers)}] skipped existing {expected_id}", flush=True)
      continue
    item = normalize_answer(
      answer=answer,
      cookie=cookie,
      output_dir=args.output,
      include_comments=args.include_comments,
      max_comments=args.max_comments,
      download_images=args.download_images,
      delay=args.delay,
    )
    items.append(item)
    done_ids.add(item["id"])
    archive_json.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output / "index.html").write_text(render_archive_html(items, args.user_token), encoding="utf-8")
    print(f"[{index}/{len(raw_answers)}] archived {item['id']} {item['title']}", flush=True)
    time.sleep(args.delay)

  archive_json.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
  (args.output / "index.html").write_text(render_archive_html(items, args.user_token), encoding="utf-8")
  print(f"Done: {args.output / 'index.html'}")


if __name__ == "__main__":
  main()
