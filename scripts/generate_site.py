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

    return f"""
    <div class="post">
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
        day = dt_jst.strftime("%Y-%m-%
