#!/usr/bin/env python3
"""Import authorized Zhihu exports into assets/data.js.

Expected input JSON:
[
  {
    "id": "answer-123",
    "title": "标题",
    "date": "2026-07-28",
    "url": "https://www.zhihu.com/question/.../answer/...",
    "summary": "短摘要",
    "body": ["正文第一段", "正文第二段"],
    "images": [
      {"src": "assets/images/example.jpg", "alt": "说明", "caption": "注释"}
    ],
    "comments": [
      {"author": "评论者", "text": "评论内容"}
    ],
    "tags": ["知乎", "财经"]
  }
]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


BLOGGER_ID = "huang-yanzhen"
DATA_PREFIX = "window.ECNOMICS_DATA = "


def slugify(value: str) -> str:
  value = value.strip().lower()
  value = re.sub(r"https?://", "", value)
  value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
  value = value.strip("-")
  return value[:80] or "zhihu-item"


def normalize_text_list(value: Any) -> list[str]:
  if value is None:
    return []
  if isinstance(value, str):
    lines = [line.strip() for line in value.splitlines()]
    return [line for line in lines if line]
  if isinstance(value, list):
    return [str(item).strip() for item in value if str(item).strip()]
  return [str(value).strip()]


def normalize_images(value: Any) -> list[dict[str, str]]:
  if not isinstance(value, list):
    return []

  images = []
  for item in value:
    if isinstance(item, str):
      images.append({"src": item, "alt": "", "caption": ""})
    elif isinstance(item, dict) and item.get("src"):
      images.append(
        {
          "src": str(item.get("src", "")),
          "alt": str(item.get("alt", "")),
          "caption": str(item.get("caption", "")),
        }
      )
  return images


def normalize_comments(value: Any) -> list[dict[str, str]]:
  if not isinstance(value, list):
    return []

  comments = []
  for item in value:
    if isinstance(item, str):
      text = item.strip()
      if text:
        comments.append({"author": "评论", "text": text})
    elif isinstance(item, dict):
      text = str(item.get("text", "")).strip()
      if text:
        comments.append(
          {
            "author": str(item.get("author", "评论")).strip() or "评论",
            "text": text,
          }
        )
  return comments


def normalize_post(item: dict[str, Any]) -> dict[str, Any]:
  source = str(item.get("url") or item.get("source") or "").strip()
  title = str(item.get("title") or "未命名知乎内容").strip()
  raw_id = str(item.get("id") or source or title)
  body = normalize_text_list(item.get("body") or item.get("content"))
  summary = str(item.get("summary") or item.get("quote") or "").strip()
  if not summary and body:
    summary = body[0][:180]

  return {
    "id": f"huang-yanzhen-{slugify(raw_id)}",
    "bloggerId": BLOGGER_ID,
    "title": title,
    "date": str(item.get("date") or item.get("created") or "2026-07-28"),
    "source": source,
    "sourceLabel": str(item.get("sourceLabel") or "发表于知乎"),
    "quote": summary,
    "body": body,
    "images": normalize_images(item.get("images")),
    "comments": normalize_comments(item.get("comments")),
    "tags": normalize_text_list(item.get("tags")) or ["知乎", "财经"],
  }


def load_site_data(path: Path) -> dict[str, Any]:
  text = path.read_text(encoding="utf-8").strip()
  if not text.startswith(DATA_PREFIX):
    raise ValueError(f"{path} does not start with {DATA_PREFIX!r}")
  json_like = text[len(DATA_PREFIX) :].removesuffix(";").strip()
  return json.loads(json_like)


def write_site_data(path: Path, data: dict[str, Any]) -> None:
  rendered = json.dumps(data, ensure_ascii=False, indent=2)
  path.write_text(f"{DATA_PREFIX}{rendered};\n", encoding="utf-8")


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument("input", type=Path, help="Authorized Zhihu export JSON")
  parser.add_argument(
    "--data",
    type=Path,
    default=Path("assets/data.js"),
    help="Target site data file",
  )
  parser.add_argument(
    "--replace-blogger",
    action="store_true",
    help="Replace existing Huang Yanzhen posts instead of merging by id",
  )
  args = parser.parse_args()

  incoming = json.loads(args.input.read_text(encoding="utf-8"))
  if not isinstance(incoming, list):
    raise ValueError("Input JSON must be a list of posts")

  site_data = load_site_data(args.data)
  normalized = [normalize_post(item) for item in incoming]

  existing_posts = site_data.get("posts", [])
  if args.replace_blogger:
    existing_posts = [post for post in existing_posts if post.get("bloggerId") != BLOGGER_ID]

  posts_by_id = {post["id"]: post for post in existing_posts}
  for post in normalized:
    posts_by_id[post["id"]] = post

  site_data["posts"] = list(posts_by_id.values())
  write_site_data(args.data, site_data)
  print(f"Imported {len(normalized)} authorized Zhihu records into {args.data}")


if __name__ == "__main__":
  main()
