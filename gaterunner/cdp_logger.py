# cdp_logger.py
"""
Chrome DevTools Protocol (CDP) Logger

Attaches to a Playwright Page to capture detailed browser activity:
- Network requests including POST data  
- JavaScript evaluation and dynamic script creation
- Page navigation and redirect chains

Usage:
    dump_cdp = await attach_cdp_logger(page, output_directory)
    # ... perform browser actions ...
    await dump_cdp()  # Saves cdp_log.json to output directory

The logged data is useful for:
- Debugging complex redirects and POST chains
- Analyzing dynamically generated JavaScript
- Understanding request/response patterns
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any, Callable

# ─── Constants ───────────────────────────────────────────────
MAX_SCRIPT_PREVIEW_LEN = 200  # Characters to include in script preview
CDP_LOG_FILENAME = "cdp_log.json"


async def attach_cdp_logger(page, out_dir: str) -> Callable[[], Any]:
    """
    Attach CDP session to page for comprehensive logging.
    
    @param page: Playwright page instance
    @param out_dir: Directory where logs will be saved
    @return: Async function to call when ready to save logs
    @raises Exception: If CDP session cannot be established
    """
    try:
        sess = await page.context.new_cdp_session(page)
        await sess.send("Network.enable")
        await sess.send("Page.enable") 
        await sess.send("Debugger.enable")
    except Exception as e:
        print(f"[WARN] Could not attach CDP logger: {e}")
        # Return no-op function
        return lambda: None

    logs: Dict[str, List[Dict[str, Any]]] = {
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
            script_content = src["scriptSource"]
            logs["eval_scripts"].append({
                "scriptId": ev["scriptId"],
                "length": len(script_content),
                "first200": script_content[:MAX_SCRIPT_PREVIEW_LEN]
            })
        except Exception as e:
            # Script may have been garbage collected or session closed
            logs["eval_scripts"].append({
                "scriptId": ev["scriptId"],
                "length": 0,
                "first200": f"<error: {e}>",
                "error": str(e)
            })

    sess.on("Debugger.scriptParsed",
            lambda ev: asyncio.create_task(_on_script(ev)))

    # ── caller awaits this to save file ──────────────────────────
    async def dump():
        """Save collected CDP logs to file."""
        try:
            Path(out_dir).mkdir(parents=True, exist_ok=True)
            path = Path(out_dir) / CDP_LOG_FILENAME
            
            # Add metadata to logs
            logs["metadata"] = {
                "total_redirects": len(logs["redirects"]),
                "total_requests": len(logs["requests"]), 
                "total_eval_scripts": len(logs["eval_scripts"]),
                "page_url": page.url if not page.is_closed() else "<closed>"
            }
            
            path.write_text(json.dumps(logs, indent=2, ensure_ascii=False))
            print(f"[INFO] CDP logs saved: {path}")
        except Exception as e:
            print(f"[WARN] Failed to save CDP logs: {e}")

    return dump
