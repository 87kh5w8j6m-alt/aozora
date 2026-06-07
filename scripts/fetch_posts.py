import os
import json
import requests
import time
from datetime import datetime

def fetch_posts():
    handle = os.environ.get("BSKY_HANDLE")
    app_password = os.environ.get("BSKY_APP_PASSWORD")
    
    if not handle or not app_password:
        print("Error: BSKY_HANDLE and BSKY_APP_PASSWORD must be set in GitHub Secrets.")
        return

    print(f"Attempting to login as {handle}...")

    # Create session
    resp = requests.post(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        json={"identifier": handle, "password": app_password}
    )
    
    if resp.status_code != 200:
        print(f"Login Failed! Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        return

    session = resp.json()
    access_token = session.get("accessJwt")
    did = session.get("did")

    if not access_token:
        print("Error: accessJwt not found in response.")
        return

    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Load existing data
    data_path = "data/posts.json"
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            posts_db = json.load(f)
    else:
        posts_db = {}

    # 【自動判定】既存データに "isRepost" フィールドがなければ、初回フルスキャンモードにします
    has_repost_field = any("isRepost" in p for p in posts_db.values())
    is_initial_full_fetch = not has_repost_field

    if is_initial_full_fetch:
        print("【初回モード】データ構造更新のため、過去の投稿をすべてスキャンします（数分かかります）")
    else:
        print("【日常モード】最近の投稿のみを効率的に取得します")

    print("Fetching posts from Bluesky...")
    
    params = {"actor": did, "limit": 100}
    cursor = None
    new_count = 0
    total_fetched = 0
    page_count = 0

    while True:
        if cursor:
            params["cursor"] = cursor

        resp = requests.get(
            "https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed",
            params=params,
            headers=headers
        )
        
        if resp.status_code != 200:
            print(f"Failed to fetch posts: {resp.text}")
            break

        data = resp.json()
        feed = data.get("feed", [])
        if not feed:
            break
            
        total_fetched += len(feed)
        page_count += 1

        for item in feed:
            post = item["post"]
            uri = post["uri"]
            record = post["record"]
            
            # 🔄 リポスト判定のロジック
            reason = item.get("reason")
            is_repost = reason and reason.get("$type") == "app.bsky.feed.defs#reasonRepost"
            
            post_data = {
                "uri": uri,
                "cid": post["cid"],
                "author": post["author"]["handle"],
                "authorName": post["author"].get("displayName", ""), # 表示名（名前）を追加
                "text": record.get("text", ""),
                "createdAt": record.get("createdAt"),
                "replyCount": post.get("replyCount", 0),
                "repostCount": post.get("repostCount", 0),
                "likeCount": post.get("likeCount", 0),
                "indexedAt": post["indexedAt"],
                "embed": post.get("embed"),
                "isRepost": bool(is_repost), # リポストフラグを保存
            }
            
            if uri not in posts_db:
                new_count += 1
                
            # 既存データも含め、新しいデータ構造（isRepost等）で上書き更新します
            posts_db[uri] = post_data

        cursor = data.get("cursor")
        if not cursor:
            break

        # 日常モードかつ5ページ（500件）以上進んだら、安全にループを抜けます
        if not is_initial_full_fetch and page_count >= 5:
            print("最近の投稿の同期が完了しました。")
            break

        print(f"Fetched {total_fetched} posts so far... waiting 1.5 seconds.")
        time.sleep(1.5)

    os.makedirs("data", exist_ok=True)
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(posts_db, f, ensure_ascii=False, indent=2)

    print(f"Successfully fetched a total of {total_fetched} posts.")
    print(f"Added/Updated archive successfully.")

if __name__ == "__main__":
    fetch_posts()
