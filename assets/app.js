(function () {
  const data = window.ECNOMICS_DATA;
  const app = document.querySelector("#app");
  const formatter = new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  });

  function byDateDesc(left, right) {
    return new Date(right.date) - new Date(left.date);
  }

  function postById(id) {
    return data.posts.find((post) => post.id === id);
  }

  function bloggerById(id) {
    return data.bloggers.find((blogger) => blogger.id === id);
  }

  function tagList(tags) {
    return tags.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("");
  }

  function linkList(links) {
    if (!links || !links.length) return "";
    return `
      <div class="profile-links">
        ${links
          .map(
            (link) =>
              `<a href="${escapeHtml(link.url)}" target="_blank" rel="noreferrer">${escapeHtml(link.label)}</a>`
          )
          .join("")}
      </div>
    `;
  }

  function formatDate(date) {
    return formatter.format(new Date(`${date}T00:00:00`));
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function renderHero() {
    return `
      <section class="hero">
        <div class="hero-copy">
          <p class="eyebrow">Public market commentary archive</p>
          <h1>ecnomics</h1>
          <p>${escapeHtml(data.site.description)}</p>
          <div class="hero-actions">
            <a class="button primary" href="#/timeline">查看时间线</a>
            <a class="button" href="#/about">维护说明</a>
          </div>
        </div>
        <div class="market-panel" aria-label="站点概览">
          <div>
            <span>${data.bloggers.length}</span>
            <small>博主分类</small>
          </div>
          <div>
            <span>${data.posts.length}</span>
            <small>已收录发言</small>
          </div>
          <div>
            <span>${uniqueTags().length}</span>
            <small>观察标签</small>
          </div>
        </div>
      </section>
    `;
  }

  function renderHome() {
    const cards = data.bloggers
      .map((blogger) => {
        const count = data.posts.filter((post) => post.bloggerId === blogger.id).length;
        return `
          <a class="blogger-card" href="#/blogger/${blogger.id}" style="--accent:${blogger.color}">
            <span class="avatar">${escapeHtml(blogger.avatar)}</span>
            <span class="blogger-meta">
              <strong>${escapeHtml(blogger.name)}</strong>
              <small>@${escapeHtml(blogger.handle)} · ${count} 条发言</small>
            </span>
            <p>${escapeHtml(blogger.summary)}</p>
            <span class="tag-row">${tagList(blogger.tags)}</span>
          </a>
        `;
      })
      .join("");

    return `
      ${renderHero()}
      <section class="section-heading">
        <p class="eyebrow">Blogger categories</p>
        <h2>按博主进入分类</h2>
      </section>
      <section class="blogger-grid">${cards}</section>
      ${renderPostSection("最新发言", data.posts.slice().sort(byDateDesc).slice(0, 6))}
    `;
  }

  function renderBlogger(id) {
    const blogger = bloggerById(id);
    if (!blogger) return renderNotFound();

    const posts = data.posts
      .filter((post) => post.bloggerId === blogger.id)
      .sort(byDateDesc);

    return `
      <section class="profile" style="--accent:${blogger.color}">
        <span class="avatar large">${escapeHtml(blogger.avatar)}</span>
        <div>
          <p class="eyebrow">Blogger</p>
          <h1>${escapeHtml(blogger.name)}</h1>
          <p>${escapeHtml(blogger.summary)}</p>
          <div class="tag-row">${tagList(blogger.tags)}</div>
          ${linkList(blogger.links)}
        </div>
      </section>
      ${renderPostSection(`${escapeHtml(blogger.name)}的发言`, posts)}
    `;
  }

  function renderTimeline() {
    return `
      <section class="section-heading compact">
        <p class="eyebrow">Timeline</p>
        <h1>全部发言时间线</h1>
      </section>
      <div class="search-wrap">
        <input id="search" type="search" placeholder="搜索标题、正文、博主或标签" autocomplete="off" />
      </div>
      <section id="post-results">
        ${renderPostList(data.posts.slice().sort(byDateDesc))}
      </section>
    `;
  }

  function renderPostSection(title, posts) {
    return `
      <section class="section-heading">
        <p class="eyebrow">Notes</p>
        <h2>${title}</h2>
      </section>
      ${renderPostList(posts)}
    `;
  }

  function renderPostList(posts) {
    if (!posts.length) {
      return `<p class="empty">还没有收录内容。更新 assets/data.js 后，这里会自动显示。</p>`;
    }

    return `
      <div class="post-list">
        ${posts
          .map((post) => {
            const blogger = bloggerById(post.bloggerId);
            const source = post.source
              ? `<a href="${escapeHtml(post.source)}" target="_blank" rel="noreferrer">${escapeHtml(post.sourceLabel || "原文")}</a>`
              : `<span>${escapeHtml(post.sourceLabel || "来源待补充")}</span>`;
            return `
              <article class="post-card">
                <div class="post-head">
                  <a href="#/blogger/${blogger.id}" class="post-author" style="--accent:${blogger.color}">
                    <span class="avatar tiny">${escapeHtml(blogger.avatar)}</span>
                    ${escapeHtml(blogger.name)}
                  </a>
                  <time datetime="${escapeHtml(post.date)}">${formatDate(post.date)}</time>
                </div>
                <h3>${escapeHtml(post.title)}</h3>
                ${renderStats(post)}
                <div class="post-foot">
                  <span class="tag-row">${tagList(post.tags)}</span>
                  <span class="post-actions">
                    <a href="#/post/${escapeHtml(post.id)}">阅读</a>
                    ${source}
                  </span>
                </div>
              </article>
            `;
          })
          .join("")}
      </div>
    `;
  }

  function renderPost(id) {
    const post = postById(id);
    if (!post) return renderNotFound();
    const blogger = bloggerById(post.bloggerId);
    const source = post.source
      ? `<a href="${escapeHtml(post.source)}" target="_blank" rel="noreferrer">${escapeHtml(post.sourceLabel || "原文")}</a>`
      : "";

    return `
      <article class="article-page">
        <nav class="crumbs">
          <a href="#/blogger/${blogger.id}">${escapeHtml(blogger.name)}</a>
          <span>/</span>
          <a href="#/timeline">时间线</a>
        </nav>
        <header style="--accent:${blogger.color}">
          <p class="eyebrow">Article</p>
          <h1>${escapeHtml(post.title)}</h1>
          <div class="article-meta">
            <time datetime="${escapeHtml(post.date)}">${formatDate(post.date)}</time>
            <span>${escapeHtml(blogger.name)}</span>
            ${source}
          </div>
          ${renderStats(post)}
        </header>
        ${renderImages(post.images)}
        ${renderBody(post.body, true)}
        ${renderComments(post.comments, true)}
      </article>
    `;
  }

  function renderStats(post) {
    const stats = [];
    if (post.voteupCount != null) stats.push(`赞同 ${post.voteupCount}`);
    if (post.commentCount != null) stats.push(`知乎评论 ${post.commentCount}`);
    if (post.comments && post.comments.length) stats.push(`已归档评论 ${post.comments.length}`);
    if (post.images && post.images.length) stats.push(`图片 ${post.images.length}`);
    if (!stats.length) return "";
    return `<div class="stats">${stats.map((stat) => `<span>${escapeHtml(stat)}</span>`).join("")}</div>`;
  }

  function renderImages(images) {
    if (!images || !images.length) return "";
    return `
      <div class="image-grid">
        ${images
          .map(
            (image) => `
              <figure>
                <img src="${escapeHtml(image.src)}" alt="${escapeHtml(image.alt || "")}" loading="lazy" />
                ${image.caption ? `<figcaption>${escapeHtml(image.caption)}</figcaption>` : ""}
              </figure>
            `
          )
          .join("")}
      </div>
    `;
  }

  function renderBody(body, expanded = false) {
    if (!body || !body.length) return "";
    return `
      <details class="article-body" ${expanded ? "open" : ""}>
        <summary>阅读全文</summary>
        <div>
          ${body.map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")}
        </div>
      </details>
    `;
  }

  function renderComments(comments, expanded = false) {
    if (!comments || !comments.length) return "";
    return `
      <details class="comments" ${expanded ? "open" : ""}>
        <summary>${comments.length} 条评论</summary>
        <div>
          ${comments
            .map(
              (comment) => `
                <blockquote>
                  <strong>${escapeHtml(comment.author || "评论")}</strong>
                  <p>${escapeHtml(comment.text)}</p>
                </blockquote>
              `
            )
            .join("")}
        </div>
      </details>
    `;
  }

  function renderAbout() {
    return `
      <section class="section-heading compact">
        <p class="eyebrow">About</p>
        <h1>维护这个资料库</h1>
      </section>
      <section class="about-panel">
        <p>${escapeHtml(data.site.ownerNote)}</p>
        <pre><code>{
  id: "unique-post-id",
  bloggerId: "macro-notes",
  title: "发言标题",
  date: "2026-07-28",
  source: "https://example.com/original",
  sourceLabel: "原文链接",
  quote: "发言摘录或你的整理摘要",
  body: [
    "正文第一段",
    "正文第二段"
  ],
  images: [
    {
      src: "assets/images/example.jpg",
      alt: "图片说明",
      caption: "可选图片注释"
    }
  ],
  comments: [
    {
      author: "评论者",
      text: "评论摘要或经授权的短摘录"
    }
  ],
  tags: ["宏观", "政策"]
}</code></pre>
      </section>
    `;
  }

  function renderNotFound() {
    return `
      <section class="section-heading compact">
        <p class="eyebrow">404</p>
        <h1>没有找到这个页面</h1>
        <p><a class="button primary" href="#/">回到首页</a></p>
      </section>
    `;
  }

  function uniqueTags() {
    return Array.from(new Set(data.posts.flatMap((post) => post.tags))).sort();
  }

  function wireTimelineSearch() {
    const search = document.querySelector("#search");
    const results = document.querySelector("#post-results");
    if (!search || !results) return;

    search.addEventListener("input", () => {
      const keyword = search.value.trim().toLowerCase();
      const posts = data.posts.filter((post) => {
        const blogger = bloggerById(post.bloggerId);
        const haystack = [
          post.title,
          post.quote || "",
          ...(post.body || []),
          ...(post.comments || []).map((comment) => `${comment.author || ""} ${comment.text || ""}`),
          post.date,
          blogger.name,
          blogger.handle,
          ...post.tags
        ]
          .join(" ")
          .toLowerCase();
        return haystack.includes(keyword);
      });
      results.innerHTML = renderPostList(posts.sort(byDateDesc));
    });
  }

  function render() {
    const route = window.location.hash.replace(/^#\/?/, "");
    const [section, id] = route.split("/");

    if (!route) app.innerHTML = renderHome();
    else if (section === "blogger") app.innerHTML = renderBlogger(id);
    else if (section === "post") app.innerHTML = renderPost(id);
    else if (section === "timeline") app.innerHTML = renderTimeline();
    else if (section === "about") app.innerHTML = renderAbout();
    else app.innerHTML = renderNotFound();

    wireTimelineSearch();
    app.focus({ preventScroll: true });
  }

  window.addEventListener("hashchange", render);
  render();
})();
