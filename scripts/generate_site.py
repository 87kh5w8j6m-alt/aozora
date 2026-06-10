import json
import os
import calendar # ★ カレンダー生成用に追加
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
    
    avatar_url = post.get("authorAvatar") or post.get("avatar")
    if avatar_url:
        icon_html = f'<img src="{avatar_url}" class="author-icon" loading="lazy" alt="">'
    else:
        icon_html = '<div class="author-icon-placeholder"></div>'

    author_html = f"""
    <div class="post-header">
        {icon_html}
        <div class="author-meta">
            <div class="post-author"><strong>{display_name}</strong><span>@{author_handle}</span></div>
            <div class="post-meta"><a href="{post_url}" target="_blank">{date}</a></div>
        </div>
    </div>
    """

    repost_html = ""
    if post.get("isRepost"):
        repost_html = '<div class="repost-badge">🔄 リポスト</div>'

    return f"""
    <div class="post">
        {repost_html}
        {author_html}
        <div class="post-text">{text}</div>
        {images_html}
        <div class="post-stats">{stats}</div>
    </div>
    """

def generate_html(posts):
    sorted_posts = sorted(posts.values(), key=lambda x: x["createdAt"], reverse=True)
    
    archive_map = defaultdict(list)
    archive_map_daily = defaultdict(list)
    archive_map_same_day = defaultdict(list)
    
    for post in sorted_posts:
        dt_jst = get_jst_datetime(post["createdAt"])
        month = dt_jst.strftime("%Y-%m")
        archive_map[month].append(post)
        
        day = dt_jst.strftime("%Y-%m-%d")
        archive_map_daily[day].append(post)
        
        mm_dd = dt_jst.strftime("%m-%d")
        archive_map_same_day[mm_dd].append(post)

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
            --meta-text: #
