import json
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict

def format_date(iso_str):
    # Blueskyからの日時（UTC）を読み込む
    dt_utc = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    # 日本時間（UTC+9）に変換
    jst = timezone(timedelta(hours=9))
    dt_jst = dt_utc.astimezone(jst)
    return dt_jst.strftime("%Y-%m-%d %H:%M:%S")

def render_post(post):
    text = post["text"].replace("\n", "  
")
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

def generate_html(posts ):
    sorted_posts = sorted(posts.values(), key=lambda x: x["createdAt"], reverse=True)
    
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
    </style>
</head>
<body>
    <header>
        <h1>青空の記憶</h1>
        <nav>
            <a href="index.html">ホーム</a> | 
            <a href="images.html">画像一覧</a> | 
            <a href="ranking.html">ランキング</a> | 
            <a href="archive.html">アーカイブ</a>
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

    # Archive
    archive_map = defaultdict(list)
    for post in sorted_posts:
        dt_utc = datetime.fromisoformat(post["createdAt"].replace("Z", "+00:00"))
        jst = timezone(timedelta(hours=9))
        dt_jst = dt_utc.astimezone(jst)
        month = dt_jst.strftime("%Y-%m")
        archive_map[month].append(post)
    
    archive_list = "<ul>" + "".join([f'<li><a href="archive_{m}.html">{m}</a> ({len(m_posts)}件)</li>' for m, m_posts in sorted(archive_map.items(), reverse=True)]) + "</ul>"
    with open("archive.html", "w", encoding="utf-8") as f:
        f.write(base_html.format(title="月別アーカイブ", content=archive_list))
        
    for month, m_posts in archive_map.items():
        m_content = "".join([render_post(p) for p in m_posts])
        with open(f"archive_{month}.html", "w", encoding="utf-8") as f:
            f.write(base_html.format(title=f"アーカイブ: {month}", content=m_content))

if __name__ == "__main__":
    data_path = "data/posts.json"
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            posts = json.load(f)
        generate_html(posts)
    else:
        print("No data found.")
