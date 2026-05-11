from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
import httpx
import os
import json
import re
import base64
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

app = FastAPI(title="Facebook Ads Preview")

FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN", "")
FB_AD_ACCOUNTS  = [a.strip() for a in os.getenv("FB_AD_ACCOUNTS", "").split(",") if a.strip()]
FB_API_VERSION  = "v21.0"
FB_BASE         = f"https://graph.facebook.com/{FB_API_VERSION}"

AD_FORMATS = [
    {"key": "DESKTOP_FEED_STANDARD",  "label": "🖥️ Feed Desktop"},
    {"key": "MOBILE_FEED_STANDARD",   "label": "📱 Feed Mobile"},
    {"key": "INSTAGRAM_STANDARD",     "label": "📸 IG Feed"},
    {"key": "INSTAGRAM_STORY",        "label": "📖 IG Story"},
    {"key": "FACEBOOK_STORY_MOBILE",  "label": "📖 FB Story"},
    {"key": "INSTAGRAM_REELS",        "label": "🎬 Reels"},
]


@app.get("/api/accounts")
async def get_accounts():
    """ดึงชื่อ Ad Account ทั้งหมด"""
    if not FB_ACCESS_TOKEN or not FB_AD_ACCOUNTS:
        raise HTTPException(500, "ยังไม่ได้ตั้งค่า credentials ใน .env")

    accounts = []
    async with httpx.AsyncClient(timeout=20) as client:
        for acct_id in FB_AD_ACCOUNTS:
            url = f"{FB_BASE}/act_{acct_id}"
            params = {"fields": "id,name,account_status", "access_token": FB_ACCESS_TOKEN}
            resp = await client.get(url, params=params)
            data = resp.json()
            if "error" not in data:
                status = data.get("account_status", 0)
                accounts.append({
                    "id": acct_id,
                    "name": data.get("name", f"Account {acct_id}"),
                    "active": status == 1,
                })
            else:
                accounts.append({"id": acct_id, "name": f"act_{acct_id}", "active": False})
    return {"accounts": accounts}


@app.get("/api/search")
async def search(
    q: str = Query(..., min_length=1),
    search_type: str = "ad",
    account_id: str = Query(...),
):
    if not FB_ACCESS_TOKEN:
        raise HTTPException(500, "ยังไม่ได้ตั้งค่า FB_ACCESS_TOKEN ใน .env")

    filtering = json.dumps([{"field": "name", "operator": "CONTAIN", "value": q}])

    async with httpx.AsyncClient(timeout=30) as client:
        if search_type == "campaign":
            url = f"{FB_BASE}/act_{account_id}/campaigns"
            params = {
                "fields": "id,name,status,objective",
                "filtering": filtering,
                "access_token": FB_ACCESS_TOKEN,
                "limit": 25,
            }
        else:
            url = f"{FB_BASE}/act_{account_id}/ads"
            params = {
                "fields": "id,name,status",
                "filtering": filtering,
                "access_token": FB_ACCESS_TOKEN,
                "limit": 25,
            }

        resp = await client.get(url, params=params)
        data = resp.json()

        if "error" in data:
            raise HTTPException(400, data["error"]["message"])

        results = [
            {
                "id": item["id"],
                "name": item["name"],
                "status": item.get("status", ""),
                "type": search_type,
                "objective": item.get("objective", ""),
            }
            for item in data.get("data", [])
        ]
        return {"results": results}


@app.get("/api/campaign-ads/{campaign_id}")
async def get_campaign_ads(campaign_id: str):
    async with httpx.AsyncClient(timeout=30) as client:
        url = f"{FB_BASE}/{campaign_id}/ads"
        params = {"fields": "id,name,status", "access_token": FB_ACCESS_TOKEN, "limit": 25}
        resp = await client.get(url, params=params)
        data = resp.json()
        if "error" in data:
            raise HTTPException(400, data["error"]["message"])
        return {"results": data.get("data", [])}


@app.get("/api/preview/{ad_id}")
async def get_previews(ad_id: str):
    async with httpx.AsyncClient(timeout=30) as client:
        previews = []
        for fmt in AD_FORMATS:
            url = f"{FB_BASE}/{ad_id}/previews"
            params = {"ad_format": fmt["key"], "access_token": FB_ACCESS_TOKEN}
            resp = await client.get(url, params=params)
            data = resp.json()
            if "data" in data and data["data"]:
                body = data["data"][0]["body"]
                src_match = re.search(r'src="([^"]+)"', body)
                src = src_match.group(1).replace("&amp;", "&") if src_match else ""
                previews.append({
                    "format": fmt["key"],
                    "label": fmt["label"],
                    "body": body,
                    "src": src,
                })
        return {"previews": previews}


@app.post("/api/screenshot")
async def screenshot(payload: dict):
    src = payload.get("src", "")
    if not src:
        raise HTTPException(400, "src URL required")

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 540, "height": 960})
        page = await ctx.new_page()
        try:
            await page.goto(src, wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(2000)
            img = await page.screenshot(type="png", full_page=True)
            return {"image": base64.b64encode(img).decode()}
        except Exception as e:
            raise HTTPException(500, f"Screenshot failed: {e}")
        finally:
            await browser.close()


app.mount("/", StaticFiles(directory="static", html=True), name="static")
