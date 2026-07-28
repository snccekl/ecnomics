# ecnomics

`ecnomics` 是一个纯静态 GitHub Pages 网站，用来按财经博主分类收录公开发言。

## 本地预览

直接打开 `index.html` 即可预览。也可以在仓库根目录运行：

```bash
python3 -m http.server 8000
```

然后访问 `http://localhost:8000`。

## 维护内容

所有博主和发言都在 `assets/data.js` 里：

- `bloggers`：博主分类入口。
- `posts`：发言内容，使用 `bloggerId` 关联到博主。
- `source`：原文链接，可为空。
- `body`：正文段落数组，只有在你确认可转载或仅本地私用时建议填写。
- `images`：配图数组，可使用站内图片路径或已获授权的外部图片链接。
- `comments`：评论数组，可记录评论全文或摘要；公开发布前建议确认授权边界。
- `tags`：用于搜索和展示。

建议只公开发布短摘录、个人整理摘要、评论要点和原文链接。若要转载文章全文、评论全文或图片，请先确认来源平台规则和作者授权。

## 批量导入

如果你已经拿到授权导出的知乎内容，可以整理成 JSON 后批量导入：

```bash
python3 scripts/import_authorized_zhihu_export.py export.json --replace-blogger
```

`export.json` 示例：

```json
[
  {
    "id": "answer-123",
    "title": "文章标题",
    "date": "2026-07-28",
    "url": "https://www.zhihu.com/question/.../answer/...",
    "summary": "摘要",
    "body": ["正文第一段", "正文第二段"],
    "images": [
      {
        "src": "assets/images/example.jpg",
        "alt": "图片说明",
        "caption": "图片注释"
      }
    ],
    "comments": [
      {
        "author": "评论者",
        "text": "评论内容"
      }
    ],
    "tags": ["知乎", "财经"]
  }
]
```

## 本地私人知乎归档

如果只是你自己在本机检索，不发布到 GitHub Pages，可以使用私人归档脚本。输出目录是 `private_archive/`，已经写入 `.gitignore`。

先在浏览器登录知乎，然后从开发者工具里复制你自己的知乎 Cookie，再运行：

```bash
export ZHIHU_COOKIE='复制到的 Cookie'
python3 scripts/zhihu_private_archive.py --include-comments --max-comments 50
```

常用参数：

- `--limit 800`：最多抓取 800 条回答。
- `--include-comments`：抓取回答下的评论。
- `--max-comments 50`：每条回答最多保存 50 条评论。
- `--download-images`：把正文图片下载到本地归档目录。
- `--delay 1.2`：每次请求之间等待 1.2 秒，建议不要调得太低。

完成后打开：

```text
private_archive/huang-yanzhen/index.html
```

## 发布到 GitHub Pages

1. 将本仓库推送到 GitHub。
2. 在仓库设置里打开 `Settings > Pages`。
3. `Build and deployment` 选择 `GitHub Actions`。
4. 之后每次推送到 `main` 分支都会自动发布。
