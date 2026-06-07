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

    print("Fetching posts from Bluesky...")
    
    # ページネーション用の初期設定
    params = {"actor": did, "limit": 100}
    cursor = None
    new_count = 0
    total_fetched = 0

    # すべての投稿を取得するためのループ
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
        total_fetched += len(feed)

        # 投稿データをデータベース(辞書)にマッピングして保存
        for item in feed:
            post = item["post"]
            uri = post["uri"]
            
            if uri not in posts_db:
                record = post["record"]
                post_data = {
                    "uri": uri,
                    "cid": post["cid"],
                    "author": post["author"]["handle"],
                    "text": record.get("text", ""),
                    "createdAt": record.get("createdAt"),
                    "replyCount": post.get("replyCount", 0),
                    "repostCount": post.get("repostCount", 0),
                    "likeCount": post.get("likeCount", 0),
                    "indexedAt": post["indexedAt"],
                    "embed": post.get("embed"),
                }
                posts_db[uri] = post_data
                new_count += 1

        # 次のページがあるか（カーソルが存在するか）確認
        cursor = data.get("cursor")
        if not cursor:
            # カーソルがなければ全件取得完了
            break

        # API制限を避けるため、ゆっくり取得（1.5秒待機）
        print(f"Fetched {total_fetched} posts so far... waiting 1.5 seconds.")
        time.sleep(1.5)

    os.makedirs("data", exist_ok=True)
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(posts_db, f, ensure_ascii=False, indent=2)

    print(f"Successfully fetched a total of {total_fetched} posts.")
    print(f"Added {new_count} new posts to the archive.")

if __name__ == "__main__":
    fetch_posts()
