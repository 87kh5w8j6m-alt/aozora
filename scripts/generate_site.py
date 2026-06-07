import json
import os
from datetime import datetime, timezone, timedelta
from collections import defaultdict

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

    # 元Postの投稿アカウント情報を組み立て
    author_handle = post.get("author", "unknown")
    author_name = post.get("authorName", "")
    display_name = author_name if author_name else f"@{author_handle}"
    author_html = f'<div class="post-author"><strong>{display_name}</strong><span>@{author_handle}</span></div>'

    # リポスト時のバッジ表示
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
    
    # Base template: 日付見出し用のスタイル (.archive-day-heading) を追加
    base_html = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>青空の記憶 - {title}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/water.css@2/out/water.css">
    <style>
        .post {{ border-bottom: 1px solid #ccc; padding: 1em 0; }}
        .post-meta {{ font-size: 0.8em; color: #666; }}
        .post-stats {{ font-size: 0.8em; color: #444; margin-top: 0.5em; }}
        .post-image {{ max-width: 100%; border-radius: 8px; margin-top: 0.5em; }}
        nav {{ margin-bottom: 2em; }}
        .search-box {{ margin-bottom: 2em; }}
         /* 月別アーカイブ内の日付見出し用スタイル */
        .archive-day-heading {{
            margin-top: 2.5em;
            padding: 0.3em 0.6em;
            background: #f0f4f8;
            border-left: 5px solid #0076d1;
            border-radius: 0 4px 4px 0;
            font-size: 1.2em;
        }}
        /* 👤 投稿アカウント用のスタイル */
        .post-author {{
            font-size: 0.95em;
            margin-bottom: 0.2em;
        }}
        .post-author strong {{
            color: var(--text-main);
        }}
        .post-author span {{
            color: #666;
            font-size: 0.85em;
            margin-left: 0.4em;
        }}
        /* 🔄 リポストバッジ用のスタイル */
        .repost-badge {{
            color: #17bf63;
            font-size: 0.85em;
            font-weight: bold;
            margin-bottom: 0.4em;
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
            <a href="archive_daily.html">日別アーカイブ</a>
        </nav>
    </header>
    <main>
        <h2>{title}</h2>
        {content}
    </main>
    <footer>
        <p>&copy; 2026 青空の記憶</p>
    </footer>
    <script>
        function search( ) {{
            const query = document.getElementById('search-input').value.toLowerCase();
            const posts = document.querySelectorAll('.post');
            posts.forEach(post => {{
                const text = post.innerText.toLowerCase();
                post.style.display = text.includes(query) ? 'block' : 'none';
            }});
        }}
    </script>
</body>
</html>
"""

    # Index
    search_html = '<div class="search-box"><input type="text" id="search-input" placeholder="キーワード検索..." onkeyup="search()"></div>'
    index_content = search_html + "".join([render_post(p) for p in sorted_posts[:100]])
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(base_html.format(title="最新投稿", content=index_content))

    # Images
    img_content = "".join([render_post(p) for p in sorted_posts if p.get("embed") and p["embed"].get("$type") == "app.bsky.embed.images#view"])
    with open("images.html", "w", encoding="utf-8") as f:
        f.write(base_html.format(title="画像一覧", content=img_content))

    # Ranking
    top_liked = sorted(sorted_posts, key=lambda x: x["likeCount"], reverse=True)[:50]
    ranking_content = "<h3>いいねランキング</h3>" + "".join([render_post(p) for p in top_liked])
    with open("ranking.html", "w", encoding="utf-8") as f:
        f.write(base_html.format(title="ランキング", content=ranking_content))

    # 月別 & 日別アーカイブのデータ振り分け
    archive_map = defaultdict(list)
    archive_map_daily = defaultdict(list)
    
    for post in sorted_posts:
        dt_jst = get_jst_datetime(post["createdAt"])
        
        # 月別用 (YYYY-MM)
        month = dt_jst.strftime("%Y-%m")
        archive_map[month].append(post)
        
        # 日別用 (YYYY-MM-DD)
        day = dt_jst.strftime("%Y-%m-%d")
        archive_map_daily[day].append(post)
    
    # ─── 月別アーカイブの生成 (改修部分) ───
    archive_list = "<ul>" + "".join([f'<li><a href="archive_{m}.html">{m}</a> ({len(posts)}件)</li>' for m, posts in sorted(archive_map.items(), reverse=True)]) + "</ul>"
    with open("archive.html", "w", encoding="utf-8") as f:
        f.write(base_html.format(title="月別アーカイブ", content=archive_list))
        
    for month, m_posts in archive_map.items():
        m_content = ""
        current_day = None
        
        for post in m_posts:
            dt_jst = get_jst_datetime(post["createdAt"])
            day_str = dt_jst.strftime("%Y-%m-%d")
            
            # ループ内で日付が変わったタイミングを検知して見出しを挿入
            if day_str != current_day:
                current_day = day_str
                m_content += f'<h3 class="archive-day-heading">{day_str}</h3>'
                
            m_content += render_post(post)
            
        with open(f"archive_{month}.html", "w", encoding="utf-8") as f:
            f.write(base_html.format(title=f"アーカイブ: {month}", content=m_content))

    # ─── 日別アーカイブの生成 ───
    archive_daily_list = "<ul>" + "".join([f'<li><a href="archive_{d}.html">{d}</a> ({len(posts)}件)</li>' for d, posts in sorted(archive_map_daily.items(), reverse=True)]) + "</ul>"
    with open("archive_daily.html", "w", encoding="utf-8") as f:
        f.write(base_html.format(title="日別アーカイブ", content=archive_daily_list))
        
    for day, d_posts in archive_map_daily.items():
        d_content = "".join([render_post(p) for p in d_posts])
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
