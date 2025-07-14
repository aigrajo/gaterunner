# cdp_logger.py
"""
Attach to a Playwright Page, then call await dump() at the end.
Logs go to cdp_log.json inside the run's output directory.
"""
import asyncio, json
from pathlib import Path


async def attach_cdp_logger(page, out_dir: str):
    sess = await page.context.new_cdp_session(page)
    await sess.send("Network.enable")
    await sess.send("Page.enable")
    await sess.send("Debugger.enable")

    logs = {
        "redirects": [],      # script-driven navigations
        "eval_scripts": [],   # code created by eval / new Function
        "requests": []        # full request list inc. POST bodies
    }

    # ── redirects ────────────────────────────────────────────────
    sess.on(
        "Page.frameRequestedNavigation",
        lambda e: logs["redirects"].append({
            "when": "before",
            "url":   e["url"],
            "reason": e.get("reason", ""),
            "loaderId": e.get("loaderId") or e.get("frameId") or "?"
        })
    )
    sess.on(
        "Page.frameNavigated",
        lambda e: logs["redirects"].append({
            "when": "after",
            "url":   e["frame"]["url"],
            "loaderId": e["frame"].get("loaderId") or e["frame"].get("id") or "?"
        })
    )

    # ── network (incl. POST body) ────────────────────────────────
    async def _on_req(ev):
        req = {
            "id": ev["requestId"],
            "url": ev["request"]["url"],
            "method": ev["request"]["method"],
            "postData": None,
        }
        if ev["request"].get("hasPostData"):
            try:
                body = await sess.send(
                    "Network.getRequestPostData", {"requestId": ev["requestId"]}
                )
                req["postData"] = body.get("postData")
            except Exception:
                pass
        logs["requests"].append(req)

    sess.on("Network.requestWillBeSent",
            lambda ev: asyncio.create_task(_on_req(ev)))

    # ── eval / Function payloads ─────────────────────────────────
    async def _on_script(ev):
        if ev.get("url"):          # external script → ignore
            return
        try:
            src = await sess.send("Debugger.getScriptSource",
                                   {"scriptId": ev["scriptId"]})
            logs["eval_scripts"].append({
                "scriptId": ev["scriptId"],
                "length": len(src["scriptSource"]),
                "first200": src["scriptSource"][:200]
            })
        except Exception:
            pass

    sess.on("Debugger.scriptParsed",
            lambda ev: asyncio.create_task(_on_script(ev)))

    # ── caller awaits this to save file ──────────────────────────
    async def dump():
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        path = Path(out_dir) / "cdp_log.json"
        path.write_text(json.dumps(logs, indent=2, ensure_ascii=False))
        print(f"[CDP] log saved -> {path}")

    return dump
