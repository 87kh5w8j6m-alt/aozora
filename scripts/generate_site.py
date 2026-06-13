import json
import os
import calendar
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

    # --- アコーディオンメニューの生成 ---
    years_map = defaultdict(dict)
    for month_str, posts_in_month in archive_map.items():
        y, m = month_str.split('-')
        years_map[y][m] = len(posts_in_month)
    
    archive_accordion_html = ""
    for year in sorted(years_map.keys(), reverse=True):
        archive_accordion_html += f'<li><button class="accordion-btn">📅 {year}年</button>\n'
        archive_accordion_html += '<ul class="accordion-content">\n'
        for month in sorted(years_map[year].keys(), reverse=True):
            month_key = f"{year}-{month}"
            count = years_map[year][month]
            display_month = int(month) # 先頭の0を取る
            archive_accordion_html += f'<li><a href="archive_{month_key}.html">{display_month}月 ({count})</a></li>\n'
        archive_accordion_html += '</ul></li>\n'
    # ----------------------------------

    def make_day_heading(day_str, count):
        dt = datetime.strptime(day_str, "%Y-%m-%d")
        wd = ["月", "火", "水", "木", "金", "土", "日"][dt.weekday()]
        display_date = dt.strftime("%Y年%m月%d日")
        return f'<h3 class="archive-day-heading">{display_date}({wd}) <span class="day-post-count">| {count} posts</span></h3>'

    # ベースHTMLテンプレート (2カラムレイアウト向け)
    base_html = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>青空の記憶 - {title}</title>
    <link rel="icon" type="image/png" href="favicon.png">
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
            --icon-bg: #ddd;
            --sidebar-bg: #fdfdfd;
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
                --icon-bg: #444;
                --sidebar-bg: #182232;
            }}
        }}

        body {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 10px 20px;
        }}

        /* 2カラムレイアウト用のGrid定義 */
        .layout-container {{
            display: grid;
            grid-template-columns: minmax(300px, 350px) 1fr;
            gap: 2rem;
            margin-top: 1.5rem;
            align-items: start;
        }}

        /* 左カラム：サイドバー */
        .sidebar {{
            position: sticky;
            top: 20px;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            background: var(--sidebar-bg);
            border: 1px solid var(--post-border);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 10px rgba(0,0,0,0.02);
            box-sizing: border-box;
        }}

        /* 右カラム：メインコンテンツ */
        .main-content {{
            min-width: 0; /* フレックス/グリッドアイテムの縮小を可能にする */
        }}

        /* サイドバー用メニューリスト */
        .sidebar-menu {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            padding: 0;
            margin: 0;
            list-style: none;
        }}
        .sidebar-menu > li > a {{
            display: block;
            padding: 0.5rem 0.8rem;
            text-decoration: none;
            border-radius: 6px;
            transition: background 0.2s;
            font-weight: bold;
        }}
        .sidebar-menu > li > a:hover {{
            background: var(--heading-bg);
        }}

        /* アコーディオンメニュー用のスタイル */
        .accordion-btn {{
            background: none;
            border: none;
            width: 100%;
            text-align: left;
            padding: 0.5rem 0.8rem;
            font-size: 1em;
            font-weight: bold;
            color: inherit;
            cursor: pointer;
            border-radius: 6px;
            transition: background 0.2s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .accordion-btn:hover {{
            background: var(--heading-bg);
        }}
        .accordion-btn::after {{
            content: '▼';
            font-size: 0.8em;
            transition: transform 0.3s;
        }}
        .accordion-btn.active::after {{
            transform: rotate(180deg);
        }}
        .accordion-content {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
            padding-left: 0;
            margin: 0;
            list-style: none;
        }}
        .accordion-content li a {{
            display: block;
            font-weight: normal;
            font-size: 0.9em;
            padding: 0.4rem 0.8rem 0.4rem 2.2rem;
            text-decoration: none;
            border-radius: 6px;
            color: var(--meta-text);
            transition: background 0.2s;
        }}
        .accordion-content li a:hover {{
            background: var(--heading-bg);
        }}

        .post {{ border-bottom: 1px solid var(--post-border); padding: 1em 0; }}
        .post-meta {{ font-size: 0.8em; color: var(--meta-text); }}
        .post-stats {{ font-size: 0.8em; color: var(--stats-text); margin-top: 0.5em; }}
        .post-image {{ max-width: 100%; border-radius: 8px; margin-top: 0.5em; }}
        
        /* 検索ボックス */
        .search-box {{
            display: flex;
            gap: 0.5rem;
            margin-bottom: 0;
        }}
        .search-box input {{
            flex: 1;
            margin-bottom: 0;
            padding: 6px 12px;
        }}
        .search-box button {{
            padding: 6px 12px;
            margin-bottom: 0;
        }}
        
        .post-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 0.6em; }}
        .author-meta {{ display: flex; flex-direction: column; gap: 2px; }}
        .author-icon {{ width: 42px; height: 42px; border-radius: 50%; object-fit: cover; flex-shrink: 0; }}
        .author-icon-placeholder {{ width: 42px; height: 42px; border-radius: 50%; background-color: var(--icon-bg); flex-shrink: 0; }}
        
        .archive-day-heading {{
            margin-top: 1.5rem;
            padding: 0.3em 0.6em;
            background: var(--heading-bg);
            border-left: 5px solid var(--heading-border);
            border-radius: 0 4px 4px 0;
            font-size: 1.2em;
            display: flex;
            align-items: baseline;
            gap: 0.6em;
        }}
        .day-post-count {{ font-size: 0.7em; color: var(--meta-text); font-weight: normal; }}
        .post-author {{ font-size: 0.95em; margin-bottom: 0; line-height: 1.2; }}
        .post-author strong {{ color: var(--text-main); }}
        .post-author span {{ color: var(--author-span); font-size: 0.85em; margin-left: 0.4em; }}
        .repost-badge {{ color: #17bf63; font-size: 0.85em; font-weight: bold; margin-bottom: 0.4em; }}

        .all-years-btn {{
            display: inline-block;
            padding: 0.8em 2em;
            background-color: var(--heading-border);
            color: #fff !important;
            text-decoration: none;
            border-radius: 6px;
            font-weight: bold;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: opacity 0.2s, transform 0.2s;
        }}
        .all-years-btn:hover {{ opacity: 0.9; transform: translateY(-1px); text-decoration: none; }}

        #page-top-btn {{
            position: fixed; bottom: 20px; right: 20px; display: none;
            padding: 10px 16px; background-color: var(--heading-border); color: #fff;
            border: none; border-radius: 50px; cursor: pointer; z-index: 1000;
            opacity: 0.8; font-size: 0.9em; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: opacity 0.3s, transform 0.2s;
        }}
        #page-top-btn:hover {{ opacity: 1; transform: translateY(-2px); color: #fff; text-decoration: none; }}

        /* トースト通知 */
        #toast-notification {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            background-color: #333;
            color: #fff;
            padding: 12px 24px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 9999;
            transition: transform 0.3s ease, opacity 0.3s ease;
            opacity: 0;
            pointer-events: none;
        }}
        #toast-notification.show {{
            transform: translateX(-50%) translateY(0);
            opacity: 1;
        }}

        /* レスポンシブ対応 (タブレット・スマホ) */
        @media (max-width: 768px) {{
            .layout-container {{
                grid-template-columns: 1fr;
            }}
            .sidebar {{
                position: static;
                width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <header style="margin-bottom: 1.5rem;">
        <h1 style="margin-bottom: 0.5rem;"><a href="index.html" style="text-decoration: none; color: inherit;">青空の記憶</a></h1>
    </header>
    
    <!-- 2カラムコンテンツ部 -->
    <div class="layout-container">
        <!-- 左カラム: 各種メニュー、検索、カレンダー -->
        <aside class="sidebar">
            <section>
                <h4 style="margin-top: 0; margin-bottom: 0.8rem; font-size: 1.1em; border-bottom: 2px solid var(--heading-border); padding-bottom: 4px;">メニュー</h4>
                <ul class="sidebar-menu">
                    <li><a href="index.html">🏠 ホーム</a></li>
                    <li><a href="images.html">🖼️ 画像一覧</a></li>
                    <li><a href="ranking.html">🔥 ランキング</a></li>
                    {archive_accordion}
                </ul>
            </section>

            <section>
                <h4 style="margin-top: 0; margin-bottom: 0.8rem; font-size: 1.1em; border-bottom: 2px solid var(--heading-border); padding-bottom: 4px;">キーワード検索</h4>
                <div class="search-box">
                    <input type="text" id="sidebar-search-input" placeholder="アーカイブから探す..." onkeydown="if(event.key==='Enter') executeSidebarSearch()">
                    <button onclick="executeSidebarSearch()">🔍</button>
                </div>
            </section>

            <section id="sidebar-calendar-container">
                <!-- ここにカレンダーウィジェットが挿入されます -->
                {calendar_widget}
            </section>
        </aside>

        <!-- 右カラム: メインコンテンツ -->
        <main class="main-content">
            <h2>{title}</h2>
            {content}
        </main>
    </div>

    <footer>
        <p style="text-align: center; margin-top: 3rem;">&copy; 2026 青空の記憶</p>
    </footer>

    <button id="page-top-btn" onclick="scrollToTop()">↑ トップ</button>
    <div id="toast-notification"></div>

    <script>
        // スムーススクロールトップ
        window.addEventListener('scroll', function() {{
            const btn = document.getElementById('page-top-btn');
            if (window.scrollY > 400) {{
                btn.style.display = 'block';
            }} else {{
                btn.style.display = 'none';
            }}
        }});
        function scrollToTop() {{ window.scrollTo({{ top: 0, behavior: 'smooth' }}); }}

        // カスタムトースト通知表示用
        function showToast(message) {{
            const toast = document.getElementById('toast-notification');
            toast.innerText = message;
            toast.classList.add('show');
            setTimeout(() => {{
                toast.classList.remove('show');
            }}, 3000);
        }}

        // サイドバー検索の実行 (search.htmlにクエリを引き継いで遷移する)
        function executeSidebarSearch() {{
            const query = document.getElementById('sidebar-search-input').value.trim();
            if (query) {{
                window.location.href = `search.html?q=${{encodeURIComponent(query)}}`;
            }}
        }}

        // アコーディオンメニューの制御
        document.addEventListener('DOMContentLoaded', function() {{
            const accordions = document.querySelectorAll('.accordion-btn');
            accordions.forEach(acc => {{
                acc.addEventListener('click', function() {{
                    this.classList.toggle('active');
                    const content = this.nextElementSibling;
                    if (content.style.maxHeight) {{
                        content.style.maxHeight = null;
                    }} else {{
                        content.style.maxHeight = content.scrollHeight + "px";
                    }}
                }});
            }});
        }});
    </script>
</body>
</html>
"""

    search_data = []
    for post in sorted_posts:
        search_data.append({
            "text": post.get("text", "").lower(),
            "createdAt": post.get("createdAt"),
            "post": post 
        })
    with open("search_index.json", "w", encoding="utf-8") as f:
        json.dump(search_data, f, ensure_ascii=False)

    # 検索ページ用コンテンツ (サイドバーの検索インプットから自動発火するように修正)
    search_page_content = """
    <div class="search-box">
        <input type="text" id="global-search-input" placeholder="全投稿からキーワード検索..." onkeydown="if(event.key==='Enter') executeSearch()">
        <button onclick="executeSearch()">検索</button>
    </div>
    <div id="search-status" style="margin-bottom: 1em; color: var(--meta-text); font-size: 0.9em;"></div>
    <div id="search-results"></div>
    <script>
        let searchIndex = null;
        
        // ページロード時にURLパラメータからクエリがあれば自動検索
        window.addEventListener('DOMContentLoaded', () => {
            const params = new URLSearchParams(window.location.search);
            const q = params.get('q');
            if (q) {
                document.getElementById('global-search-input').value = q;
                executeSearch();
            }
        });

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
                    statusDiv.innerHTML = "検索用データの読み込みに失敗しました。"; return;
                }
            }
            let matches = searchIndex.filter(item => item.text.includes(query));
            statusDiv.innerHTML = `<strong>${matches.length}</strong> 件見つかりました。（最新順）`;
            if (matches.length > 0) {
                matches.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
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
                let resultHtml = ""; let currentDay = ""; const limit = Math.min(matches.length, 200);
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
                if(matches.length > 200) { resultHtml += `<div style="padding: 1em; text-align: center; color: var(--search-msg-text); background: var(--search-msg-bg); border-radius: 8px;">※結果が多すぎるため、最新の200件のみ表示しています。</div>`; }
                resultsDiv.innerHTML = resultHtml;
            } else { resultsDiv.innerHTML = "<p>該当する投稿はありませんでした。</p>"; }
        }
        function renderPostInJS(post) {
            const text = post.text ? post.text.replace(/\\n/g, "<br>") : "";
            const d = new Date(post.createdAt);
            const jstDate = new Date(d.toLocaleString('en-US', { timeZone: 'Asia/Tokyo' }));
            const yyyy = jstDate.getFullYear(); const mm = String(jstDate.getMonth() + 1).padStart(2, '0');
            const dd = String(jstDate.getDate()).padStart(2, '0'); const hh = String(jstDate.getHours()).padStart(2, '0');
            const min = String(jstDate.getMinutes()).padStart(2, '0'); const sec = String(jstDate.getSeconds()).padStart(2, '0');
            const dateStr = `${yyyy}-${mm}-${dd} ${hh}:${min}:${sec}`;
            const stats = `❤️ ${post.likeCount || 0} | 🔄 ${post.repostCount || 0} | 💬 ${post.replyCount || 0}`;
            let imagesHtml = "";
            if (post.embed && post.embed['$type'] === 'app.bsky.embed.images#view') {
                post.embed.images.forEach(img => { imagesHtml += `<img src="${img.thumb}" class="post-image" loading="lazy">`; });
            }
            let postUrl = "#";
            try { const parts = post.uri.split("/"); postUrl = `https://bsky.app/profile/${parts[2]}/post/${parts[4]}`; } catch (e) {}
            const authorHandle = post.author || "unknown"; const authorName = post.authorName || "";
            const displayName = authorName ? authorName : `@${authorHandle}`;
            const avatarUrl = post.authorAvatar || post.avatar;
            const iconHtml = avatarUrl ? `<img src="${avatarUrl}" class="author-icon" loading="lazy" alt="">` : '<div class="author-icon-placeholder"></div>';
            const authorHtml = `<div class="post-header">${iconHtml}<div class="author-meta"><div class="post-author"><strong>${displayName}</strong><span>@${authorHandle}</span></div><div class="post-meta"><a href="${postUrl}" target="_blank">${dateStr}</a></div></div></div>`;
            const repostHtml = post.isRepost ? '<div class="repost-badge">🔄 リポスト</div>' : "";
            return `<div class="post">${repostHtml}${authorHtml}<div class="post-text">${text}</div>${imagesHtml}<div class="post-stats">${stats}</div></div>`;
        }
    </script>
    """

    # === カレンダーUIのパーツ構成 ===
    cal = calendar.Calendar(firstweekday=0) # 月曜始まり
    weekdays_header = ["月", "火", "水", "木", "金", "土", "日"]
    
    if archive_map:
        oldest_month = min(archive_map.keys())
        newest_month = max(archive_map.keys())
        
        sy, sm = map(int, oldest_month.split('-'))
        ey, em = map(int, newest_month.split('-'))
        all_months = []
        y, m = sy, sm
        while (y < ey) or (y == ey and m <= em):
            all_months.append(f"{y}-{m:02d}")
            m += 1
            if m > 12:
                m = 1
                y += 1
    else:
        all_months = []

    cal_widget_html = f"""
    <style>
        .calendar-ui {{
            background: var(--heading-bg, #f0f4f8);
            border: 1px solid var(--post-border);
            border-radius: 12px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.03);
            padding: 1rem;
            font-size: 0.9em;
        }}
        .cal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.8rem;
        }}
        .cal-header button {{
            background: #0056b3;
            color: #fff;
            border: none;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            font-size: 1em;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: opacity 0.2s;
            padding: 0;
            line-height: 1;
        }}
        .cal-header button:hover {{ opacity: 0.8; }}
        .cal-header button:disabled {{ background: #ccc; cursor: not-allowed; opacity: 0.5; }}
        .cal-title {{ font-size: 1.1em; font-weight: bold; color: #0056b3; margin: 0; }}
        
        .cal-table-wrapper table {{ width: 100%; border-collapse: separate; border-spacing: 2px; margin: 0; table-layout: fixed; }}
        .cal-table-wrapper th {{ text-align: center; font-size: 0.8em; padding: 4px 0; border: none; background: transparent; color: var(--meta-text); font-weight: bold; }}
        .cal-table-wrapper th.w-sat {{ color: #7b94ce; }}
        .cal-table-wrapper th.w-sun {{ color: #d08282; }}
        .cal-table-wrapper td {{
            text-align: center; vertical-align: middle; height: 32px; border-radius: 4px; font-weight: bold; border: none; padding: 0; font-size: 0.95em;
        }}
        .cal-table-wrapper td a {{
            display: flex; align-items: center; justify-content: center; width: 100%; height: 100%;
            text-decoration: none; color: inherit; border-radius: 4px;
        }}
        /* ポストなしの色 */
        .cal-td-no-post {{ background-color: #e2e2e2; color: #fff; }}
        .cal-td-no-post.w-sat {{ background-color: #bac4dc; }}
        .cal-td-no-post.w-sun {{ background-color: #e2c6c6; }}
        /* ポストありの色 */
        .cal-td-has-post {{ background-color: #8c8c8c; color: #fff; }}
        .cal-td-has-post.w-sat {{ background-color: #7b94ce; }}
        .cal-td-has-post.w-sun {{ background-color: #d08282; }}
        .cal-td-has-post:hover {{ filter: brightness(0.9); }}
        
        .cal-footer {{ text-align: center; margin-top: 1rem; border-top: 1px solid var(--post-border); padding-top: 0.8rem; }}
        .cal-footer a {{ color: #0056b3; font-weight: bold; text-decoration: none; font-size: 0.95em; }}
        .cal-footer a:hover {{ text-decoration: underline; }}
        
        @media (prefers-color-scheme: dark) {{
            .cal-header button {{ background: #38bdf8; }}
            .cal-title {{ color: #38bdf8; }}
            .cal-td-no-post {{ background-color: #444; color: #888; }}
            .cal-td-no-post.w-sat {{ background-color: #3b4b72; color: #777; }}
            .cal-td-no-post.w-sun {{ background-color: #6e4040; color: #777; }}
            .cal-footer a {{ color: #38bdf8; }}
        }}
    </style>
    <div class="calendar-ui">
        <div class="cal-header">
            <button id="cal-prev" onclick="changeMonth(-1)">&#10094;</button>
            <h2 id="cal-title" class="cal-title"></h2>
            <button id="cal-next" onclick="changeMonth(1)">&#10095;</button>
        </div>
        <div id="cal-tables">
    """

    for month_str in all_months:
        y, m = map(int, month_str.split("-"))
        month_cal = cal.monthdayscalendar(y, m)
        
        cal_widget_html += f'<div class="month-table" data-month="{month_str}" style="display: none;">\n'
        cal_widget_html += '<div class="cal-table-wrapper"><table>\n'
        cal_widget_html += '<tr>'
        for i, wd in enumerate(weekdays_header):
            cls = 'w-sat' if i == 5 else 'w-sun' if i == 6 else ''
            cal_widget_html += f'<th class="{cls}">{wd}</th>'
        cal_widget_html += '</tr>\n'
        
        for week in month_cal:
            cal_widget_html += '<tr>\n'
            for i, day in enumerate(week):
                if day == 0:
                    cal_widget_html += '<td></td>'
                else:
                    date_key = f"{y}-{m:02d}-{day:02d}"
                    cls_day = 'w-sat' if i == 5 else 'w-sun' if i == 6 else ''
                    
                    if date_key in archive_map_daily:
                        count = len(archive_map_daily[date_key])
                        cal_widget_html += f'<td class="cal-td-has-post {cls_day}"><a href="archive_{date_key}.html" title="{count}件のポスト">{day}</a></td>'
                    else:
                        cal_widget_html += f'<td class="cal-td-no-post {cls_day}">{day}</td>'
            cal_widget_html += '</tr>\n'
        cal_widget_html += '</table></div>\n</div>\n'

    cal_widget_html += f"""
        </div>
        <div class="cal-footer">
            <a href="#" id="one-year-ago-link">1年前の今日のポストを見る</a>
        </div>
    </div>
    <script>
        const monthTables = document.querySelectorAll('.month-table');
        let currentMonthIndex = monthTables.length - 1;

        function showMonth(index) {{
            if (index < 0 || index >= monthTables.length) return;
            
            monthTables.forEach(t => t.style.display = 'none');
            const targetTable = monthTables[index];
            targetTable.style.display = 'block';
            
            const monthStr = targetTable.getAttribute('data-month');
            const [y, m] = monthStr.split('-');
            document.getElementById('cal-title').innerText = `${{y}}年${{parseInt(m)}}月`;
            
            currentMonthIndex = index;
            document.getElementById('cal-prev').disabled = (index === 0);
            document.getElementById('cal-next').disabled = (index === monthTables.length - 1);
        }}

        function changeMonth(dir) {{
            showMonth(currentMonthIndex + dir);
        }}

        const availableDays = {json.dumps(list(archive_map_daily.keys()))};
        
        const today = new Date();
        const targetYear = today.getFullYear() - 1;
        const targetMonth = String(today.getMonth() + 1).padStart(2, '0');
        const targetDay = String(today.getDate()).padStart(2, '0');
        const targetDateStr = `${{targetYear}}-${{targetMonth}}-${{targetDay}}`;
        
        const linkEl = document.getElementById('one-year-ago-link');
        if (availableDays.includes(targetDateStr)) {{
            linkEl.href = `archive_${{targetDateStr}}.html`;
        }} else {{
            linkEl.href = "#";
            linkEl.onclick = function(e) {{
                e.preventDefault();
                showToast(`1年前の今日 (${{targetYear}}年${{parseInt(targetMonth)}}月${{parseInt(targetDay)}}日) はポストがありません。`);
            }};
        }}

        if (monthTables.length > 0) {{
            const currentRealMonth = `${{today.getFullYear()}}-${{String(today.getMonth() + 1).padStart(2, '0')}}`;
            let targetIdx = monthTables.length - 1;
            for (let i = 0; i < monthTables.length; i++) {{
                if (monthTables[i].getAttribute('data-month') === currentRealMonth) {{
                    targetIdx = i;
                    break;
                }}
            }}
            showMonth(targetIdx);
        }}
    </script>
    """

    # 1. 検索ページの書き出し
    with open("search.html", "w", encoding="utf-8") as f:
        f.write(base_html.format(title="全件検索", content=search_page_content, calendar_widget=cal_widget_html, archive_accordion=archive_accordion_html))

    # 2. トップページ (index.html) の書き出し
    index_content = ""
    current_day = None
    for post in sorted_posts[:100]:
        dt_jst = get_jst_datetime(post["createdAt"])
        day_str = dt_jst.strftime("%Y-%m-%d")
        if day_str != current_day:
            current_day = day_str
            count = len(archive_map_daily[day_str])
            index_content += make_day_heading(day_str, count)
        index_content += render_post(post)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(base_html.format(title="最新投稿", content=index_content, calendar_widget=cal_widget_html, archive_accordion=archive_accordion_html))

    # 3. 画像一覧の書き出し
    img_content = "".join([render_post(p) for p in sorted_posts if p.get("embed") and p["embed"].get("$type") == "app.bsky.embed.images#view"])
    with open("images.html", "w", encoding="utf-8") as f:
        f.write(base_html.format(title="画像一覧", content=img_content, calendar_widget=cal_widget_html, archive_accordion=archive_accordion_html))

    # 4. ランキングの書き出し
    author_counts = Counter([p.get("author") for p in sorted_posts if p.get("author")])
    if author_counts:
        my_handle = author_counts.most_common(1)[0][0]
    else:
        my_handle = None
    original_posts = [p for p in sorted_posts if p.get("author") == my_handle and not p.get("isRepost")]
    top_liked = sorted(original_posts, key=lambda x: x["likeCount"], reverse=True)[:50]
    ranking_content = "".join([render_post(p) for p in top_liked])
    with open("ranking.html", "w", encoding="utf-8") as f:
        f.write(base_html.format(title="いいねランキング トップ50", content=ranking_content, calendar_widget=cal_widget_html, archive_accordion=archive_accordion_html))

    # 5. 月別アーカイブの書き出し
    archive_list = "<ul>" + "".join([f'<li><a href="archive_{m}.html">{m}</a> ({len(posts)}件)</li>' for m, posts in sorted(archive_map.items(), reverse=True)]) + "</ul>"
    with open("archive.html", "w", encoding="utf-8") as f:
        f.write(base_html.format(title="月別アーカイブ一覧", content=archive_list, calendar_widget=cal_widget_html, archive_accordion=archive_accordion_html))
        
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
            f.write(base_html.format(title=f"アーカイブ: {month}", content=m_content, calendar_widget=cal_widget_html, archive_accordion=archive_accordion_html))

    # 6. カレンダー単体（別ページ）の書き出し
    with open("archive_daily.html", "w", encoding="utf-8") as f:
        # このページ内ではカレンダーウィジェットが中央（content）に表示されるように空にします
        f.write(base_html.format(title="日別カレンダー", content=cal_widget_html, calendar_widget="", archive_accordion=archive_accordion_html))

    # 7. 日別アーカイブの書き出し
    for day, d_posts in archive_map_daily.items():
        count = len(d_posts)
        d_content = make_day_heading(day, count) + "".join([render_post(p) for p in d_posts])
        mm_dd = day[5:] 
        dt_sample = datetime.strptime(day, "%Y-%m-%d")
        display_mm_dd = dt_sample.strftime("%m月%d日")
        button_html = f"""
        <div style="text-align: center; margin-top: 3.5em; margin-bottom: 2em;">
            <a href="archive_all_{mm_dd}.html" class="all-years-btn">
                🗓️ すべての年の {display_mm_dd} のポストを見る
            </a>
        </div>
        """
        d_content += button_html
        with open(f"archive_{day}.html", "w", encoding="utf-8") as f:
            f.write(base_html.format(title=f"アーカイブ: {day}", content=d_content, calendar_widget=cal_widget_html, archive_accordion=archive_accordion_html))

    # 8. 同日アーカイブ（過去すべての年の同日）の書き出し
    for mm_dd, sd_posts in archive_map_same_day.items():
        m, d = mm_dd.split("-")
        display_title = f"{int(m)}月{int(d)}日のすべての年の投稿"
        sd_content = ""
        current_year = None
        for post in sd_posts:
            dt_jst = get_jst_datetime(post["createdAt"])
            year_str = dt_jst.strftime("%Y年")
            if year_str != current_year:
                current_year = year_str
                full_date_str = dt_jst.strftime("%Y-%m-%d")
                year_day_count = len(archive_map_daily[full_date_str])
                sd_content += f'<h3 class="archive-day-heading">{year_str}{int(m)}月{int(d)}日 <span class="day-post-count">| {year_day_count} posts</span></h3>'
            sd_content += render_post(post)
        with open(f"archive_all_{mm_dd}.html", "w", encoding="utf-8") as f:
            f.write(base_html.format(title=display_title, content=sd_content, calendar_widget=cal_widget_html, archive_accordion=archive_accordion_html))

if __name__ == "__main__":
    data_path = "data/posts.json"
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            posts = json.load(f)
        generate_html(posts)
    else:
        print("No data found.")
