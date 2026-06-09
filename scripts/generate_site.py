import json
import os
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter

# 日本時間 (JST) のタイムゾーンを定義
JST = timezone(timedelta(hours=+9), 'JST')

def get_jst_datetime(iso_str):
    """ISO文字列(UTC)を読み込み、JSTのdatetimeオブジェクトに変換する"""
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return dt.astimezone(JST)

def format_date(iso_str):
    """JSTに変換した上で、表示用の文字列にフォーマットする"""
    dt_jst = get_jst_datetime(iso_str)
    return dt_jst.strftime("%Y-%m-%d %H:%M:%S")

def render_post(post):
    text = post["text"].replace("\n", "<br>")
    date = format_date(post["createdAt"])
    stats = f"❤️ {post['likeCount']} | 🔄 {post['repostCount']} | 💬 {post['replyCount']}"
    
    images_html = ""
    if post.get("embed") and post["embed"].get("$type") == "app.bsky.embed.images#view":
        for img in post["embed"]["images"]:
            images_html += f'<img src="{img["thumb"]}" class="post-image" loading="lazy">'
            
    try:
        parts = post["uri"].split("/")
        did = parts[2]
        rkey = parts[4]
        post_url = f"https://bsky.app/profile/{did}/post/{rkey}"
    except:
        post_url = "#"

    author_handle = post.get("author", "unknown")
    author_name = post.get("authorName", "")
    display_name = author_name if author_name else f"@{author_handle}"
    author_html = f'<div class="post-author"><strong>{display_name}</strong><span>@{author_handle}</span></div>'

    repost_html = ""
    if post.get("isRepost"):
        repost_html = '<div class="repost-badge">🔄 リポスト</div>'

    return f"""
    <div class="post">
        {repost_html}
        {author_html}
        <div class="post-meta"><a href="{post_url}" target="_blank">{date}</a></div>
        <div class="post-text">{text}</div>
        {images_html}
        <div class="post-stats">{stats}</div>
    </div>
    """

def generate_html(posts):
    sorted_posts = sorted(posts.values(), key=lambda x: x["createdAt"], reverse=True)
    
    # ─── 月別 & 日別アーカイブのデータ振り分けを先に行う（件数カウントのため） ───
    archive_map = defaultdict(list)
    archive_map_daily = defaultdict(list)
    
    for post in sorted_posts:
        dt_jst = get_jst_datetime(post["createdAt"])
        month = dt_jst.strftime("%Y-%m")
        archive_map[month].append(post)
        day = dt_jst.strftime("%Y-%m-%d")
        archive_map_daily[day].append(post)

    # 見出しを生成する補助関数
    def make_day_heading(day_str, count):
        dt = datetime.strptime(day_str, "%Y-%m-%d")
        wd = ["月", "火", "水", "木", "金", "土", "日"][dt.weekday()]
        display_date = dt.strftime("%Y年%m月%d日")
        return f'<h3 class="archive-day-heading">{display_date}({wd}) <span class="day-post-count">| {count} posts</span></h3>'

    base_html = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>青空の記憶 - {title}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css@2/out/water.css">
    <style>
        :root {{
            --post-border: #ccc;
            --meta-text: #666;
            --stats-text: #444;
            --heading-bg: #f0f4f8;
            --heading-border: #0076d1;
            --author-span: #666;
            --search-msg-bg: #f9f9f9;
            --search-msg-text: #666;
        }}
        @media (prefers-color-scheme: dark) {{
            :root {{
                --post-border: #444;
                --meta-text: #aaa;
                --stats-text: #ccc;
                --heading-bg: #1e293b;
                --heading-border: #38bdf8;
                --author-span: #aaa;
                --search-msg-bg: #2d2d2d;
                --search-msg-text: #ccc;
            }}
        }}

        .post {{ border-bottom: 1px solid var(--post-border); padding: 1em 0; }}
        .post-meta {{ font-size: 0.8em; color: var(--meta-text); }}
        .post-stats {{ font-size: 0.8em; color: var(--stats-text); margin-top: 0.5em; }}
        .post-image {{ max-width: 100%; border-radius: 8px; margin-top: 0.5em; }}
        nav {{ margin-bottom: 2em; }}
        .search-box {{ margin-bottom: 2em; display: flex; gap: 0.5em; }}
        .search-box input {{ flex: 1; }}
        .archive-day-heading {{
            margin-top: 2.5em;
            padding: 0.3em 0.6em;
            background: var(--heading-bg);
            border-left: 5px solid var(--heading-border);
            border-radius: 0 4px 4px 0;
            font-size: 1.2em;
            display: flex;
            align-items: baseline;
            gap: 0.6em;
        }}
        .day-post-count {{
            font-size: 0.7em;
            color: var(--meta-text);
            font-weight: normal;
        }}
        .post-author {{ font-size: 0.95em; margin-bottom: 0.2em; }}
        .post-author strong {{ color: var(--text-main); }}
        .post-author span {{ color: var(--author-span); font-size: 0.85em; margin-left: 0.4em; }}
        .repost-badge {{ color: #17bf63; font-size: 0.85em; font-weight: bold; margin-bottom: 0.4em; }}
        
        /* トップに戻るボタンのスタイル */
        #page-top-btn {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            display: none;
            padding: 10px 16px;
            background-color: var(--heading-border);
            color: #fff;
            border: none;
            border-radius: 50px;
            cursor: pointer;
            z-index: 1000;
            opacity: 0.8;
            font-size: 0.9em;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: opacity 0.3s, transform 0.2s;
        }}
        #page-top-btn:hover {{
            opacity: 1;
            transform: translateY(-2px);
            color: #fff; /* ホバー時の文字色を強制的に白に */
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <header>
        <h1>青空の記憶</h1>
        <nav>
            <a href="index.html">ホーム</a> | 
            <a href="images.html">画像一覧</a> | 
            <a href="ranking.html">ランキング</a> | 
            <a href="archive.html">月別アーカイブ</a> | 
            <a href="archive_daily.html">日別アーカイブ</a> | 
            <a href="search.html">🔍 検索</a>
        </nav>
    </header>
    <main>
        <h2>{title}</h2>
        {content}
    </main>
    <footer>
        <p>&copy; 2026 青空の記憶</p>
    </footer>

    <button id="page-top-btn" onclick="scrollToTop()">⇧</button>

    <script>
        // スクロール検知でボタンの表示/非表示を切り替え
        window.addEventListener('scroll', function() {{
            const btn = document.getElementById('page-top-btn');
            if (window.scrollY > 400) {{
                btn.style.display = 'block';
            }} else {{
                btn.style.display = 'none';
            }}
        }});

        // 一番上へ滑らかにスクロールする関数
        function scrollToTop() {{
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}
    </script>
</body>
</html>
"""

    # ─── 検索用インデックスデータの作成 ───
    search_data = []
    for post in sorted_posts:
        search_data.append({
            "text": post.get("text", "").lower(),
            "createdAt": post.get("createdAt"),
            "post": post 
        })
    with open("search_index.json", "w", encoding="utf-8") as f:
        json.dump(search_data, f, ensure_ascii=False)

    # ─── 検索専用ページ (search.html) の生成 ───
    search_page_content = """
    <div class="search-box">
        <input type="text" id="global-search-input" placeholder="全投稿からキーワード検索..." onkeydown="if(event.key==='Enter') executeSearch()">
        <button onclick="executeSearch()">検索</button>
    </div>
    <div id="search-status" style="margin-bottom: 1em; color: var(--meta-text); font-size: 0.9em;"></div>
    <div id="search-results"></div>

    <script>
        let searchIndex = null;

        async function executeSearch() {
            const query = document.getElementById('global-search-input').value.toLowerCase().trim();
            const statusDiv = document.getElementById('search-status');
            const resultsDiv = document.getElementById('search-results');

            if (!query) return;

            statusDiv.innerHTML = "検索データを読み込み中...";
            resultsDiv.innerHTML = "";

            if (!searchIndex) {
                try {
                    const res = await fetch('search_index.json');
                    searchIndex = await res.json();
                } catch (error) {
                    statusDiv.innerHTML = "検索用データの読み込みに失敗しました。";
                    console.error(error);
                    return;
                }
            }

            // テキストで絞り込み
            let matches = searchIndex.filter(item => item.text.includes(query));
            statusDiv.innerHTML = `<strong>${matches.length}</strong> 件見つかりました。（最新順）`;

            if (matches.length > 0) {
                // 新しい順に並び替え
                matches.sort((a, b) => b.createdAt.localeCompare(a.createdAt));

                // 日ごとのヒット件数を集計 (JST基準)
                const dayCounts = {};
                matches.forEach(item => {
                    const d = new Date(item.post.createdAt);
                    const jstDate = new Date(d.toLocaleString('en-US', { timeZone: 'Asia/Tokyo' }));
                    const yyyy = jstDate.getFullYear();
                    const mm = String(jstDate.getMonth() + 1).padStart(2, '0');
                    const dd = String(jstDate.getDate()).padStart(2, '0');
                    const dayKey = `${yyyy}-${mm}-${dd}`;
                    dayCounts[dayKey] = (dayCounts[dayKey] || 0) + 1;
                });

                let resultHtml = "";
                let currentDay = "";
                const limit = Math.min(matches.length, 200);
                const weekdays = ["日", "月", "火", "水", "木", "金", "土"];

                for (let i = 0; i < limit; i++) {
                    const post = matches[i].post;
                    
                    const d = new Date(post.createdAt);
                    const jstDate = new Date(d.toLocaleString('en-US', { timeZone: 'Asia/Tokyo' }));
                    const yyyy = jstDate.getFullYear();
                    const mm = String(jstDate.getMonth() + 1).padStart(2, '0');
                    const dd = String(jstDate.getDate()).padStart(2, '0');
                    const dayKey = `${yyyy}-${mm}-${dd}`;
                    const wd = weekdays[jstDate.getDay()];
                    
                    if (dayKey !== currentDay) {
                        const count = dayCounts[dayKey];
                        const displayDay = `${yyyy}年${mm}月${dd}日(${wd})`;
                        resultHtml += `<h3 class="archive-day-heading">${displayDay} <span class="day-post-count">| ${count} posts</span></h3>`;
                        currentDay = dayKey;
                    }
                    
                    resultHtml += renderPostInJS(post);
                }

                if(matches.length > 200) {
                    resultHtml += `<div style="padding: 1em; text-align: center; color: var(--search-msg-text); background: var(--search-msg-bg); border-radius: 8px;">※結果が多すぎるため、最新の200件のみ表示しています。</div>`;
                }
                resultsDiv.innerHTML = resultHtml;
            } else {
                resultsDiv.innerHTML = "<p>該当する投稿はありませんでした。</p>";
            }
        }

        // Pythonの render_post と同じHTMLを生成するJS関数
        function renderPostInJS(post) {
            const text = post.text ? post.text.replace(/\\n/g, "<br>") : "";
            
            const d = new Date(post.createdAt);
            const jstDate = new Date(d.toLocaleString('en-US', { timeZone: 'Asia/Tokyo' }));
            const yyyy = jstDate.getFullYear();
            const mm = String(jstDate.getMonth() + 1).padStart(2, '0');
            const dd = String(jstDate.getDate()).padStart(2, '0');
            const hh = String(jstDate.getHours()).padStart(2, '0');
            const min = String(jstDate.getMinutes()).padStart(2, '0');
            const sec = String(jstDate.getSeconds()).padStart(2, '0');
            const dateStr = `${yyyy}-${mm}-${dd} ${hh}:${min}:${sec}`;
            
            const stats = `❤️ ${post.likeCount || 0} | 🔄 ${post.repostCount || 0} | 💬 ${post.replyCount || 0}`;
            
            let imagesHtml = "";
            if (post.embed && post.embed['$type'] === 'app.bsky.embed.images#view') {
                post.embed.images.forEach(img => {
                    imagesHtml += `<img src="${img.thumb}" class="post-image" loading="lazy">`;
                });
            }

            let postUrl = "#";
            try {
                const parts = post.uri.split("/");
                postUrl = `https://bsky.app/profile/${parts[2]}/post/${parts[4]}`;
            } catch (e) {}

            const authorHandle = post.author || "unknown";
            const authorName = post.authorName || "";
            const displayName = authorName ? authorName : `@${authorHandle}`;
            const authorHtml = `<div class="post-author"><strong>${displayName}</strong><span>@${authorHandle}</span></div>`;

            const repostHtml = post.isRepost ? '<div class="repost-badge">🔄 リポスト</div>' : "";

            return `
            <div class="post">
                ${repostHtml}
                ${authorHtml}
                <div class="post-meta"><a href="${postUrl}" target="_blank">${dateStr}</a></div>
                <div class="post-text">${text}</div>
                ${imagesHtml}
                <div class="post-stats">${stats}</div>
            </div>
            `;
        }
    </script>
    """
    with open("search.html", "w", encoding="utf-8") as f:
        f.write(base_html.format(title="全件検索", content=search_page_content))


    # ─── Index (ホーム) : 日付見出しと件数を追加 ───
    index_content = ""
    current_day = None
    for post in sorted_posts[:100]:
        dt_jst = get_jst_datetime(post["createdAt"])
        day_str = dt_jst.strftime("%Y-%m-%d")
        
        if day_str != current_day:
            current_day = day_str
            # 全投稿データから、その日の合計投稿数を取得
            count = len(archive_map_daily[day_str])
            index_content += make_day_heading(day_str, count)
            
        index_content += render_post(post)
        
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(base_html.format(title="最新投稿", content=index_content))

    # ─── Images ───
    img_content = "".join([render_post(p) for p in sorted_posts if p.get("embed") and p["embed"].get("$type") == "app.bsky.embed.images#view"])
    with open("images.html", "w", encoding="utf-8") as f:
        f.write(base_html.format(title="画像一覧", content=img_content))

    # ─── Ranking ───
    author_counts = Counter([p.get("author") for p in sorted_posts if p.get("author")])
    if author_counts:
        my_handle = author_counts.most_common(1)[0][0]
    else:
        my_handle = None

    original_posts = [
        p for p in sorted_posts 
        if p.get("author") == my_handle and not p.get("isRepost")
    ]
    
    top_liked = sorted(original_posts, key=lambda x: x["likeCount"], reverse=True)[:50]
    ranking_content = "".join([render_post(p) for p in top_liked])
    with open("ranking.html", "w", encoding="utf-8") as f:
        f.write(base_html.format(title="いいねランキング トップ50", content=ranking_content))

    # ─── 月別 & 日別アーカイブの生成 ───
    archive_list = "<ul>" + "".join([f'<li><a href="archive_{m}.html">{m}</a> ({len(posts)}件)</li>' for m, posts in sorted(archive_map.items(), reverse=True)]) + "</ul>"
    with open("archive.html", "w", encoding="utf-8") as f:
        f.write(base_html.format(title="月別アーカイブ", content=archive_list))
        
    for month, m_posts in archive_map.items():
        m_content = ""
        current_day = None
        for post in m_posts:
            dt_jst = get_jst_datetime(post["createdAt"])
            day_str = dt_jst.strftime("%Y-%m-%d")
            if day_str != current_day:
                current_day = day_str
                count = len(archive_map_daily[day_str])
                m_content += make_day_heading(day_str, count)
            m_content += render_post(post)
            
        with open(f"archive_{month}.html", "w", encoding="utf-8") as f:
            f.write(base_html.format(title=f"アーカイブ: {month}", content=m_content))

    archive_daily_list = "<ul>" + "".join([f'<li><a href="archive_{d}.html">{d}</a> ({len(posts)}件)</li>' for d, posts in sorted(archive_map_daily.items(), reverse=True)]) + "</ul>"
    with open("archive_daily.html", "w", encoding="utf-8") as f:
        f.write(base_html.format(title="日別アーカイブ", content=archive_daily_list))
        
    for day, d_posts in archive_map_daily.items():
        # 日別ページにも見出しを一つだけ付ける
        count = len(d_posts)
        d_content = make_day_heading(day, count) + "".join([render_post(p) for p in d_posts])
        with open(f"archive_{day}.html", "w", encoding="utf-8") as f:
            f.write(base_html.format(title=f"アーカイブ: {day}", content=d_content))

if __name__ == "__main__":
    data_path = "data/posts.json"
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            posts = json.load(f)
        generate_html(posts)
    else:
        print("No data found.")
