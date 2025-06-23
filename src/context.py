import os
from src.clienthints import (
    parse_chromium_version,
    parse_chromium_ua,
    extract_high_entropy_hints,
    parse_chromium_full_version,
)

async def create_context(playwright, gate_args):
    context_args = {}
    user_agent = None
    if "GeolocationGate" in (gate_args or {}):
        geo = gate_args["GeolocationGate"].get("geolocation")
        if geo:
            context_args["geolocation"] = geo
    if "UserAgentGate" in (gate_args or {}):
        user_agent = gate_args["UserAgentGate"].get("user_agent")
        if user_agent:
            context_args["user_agent"] = user_agent

    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(**context_args)

    # Push JS to spoof high-entropy Client Hints
    if user_agent:
        brand, brand_v = parse_chromium_ua(user_agent)
        chromium_v = parse_chromium_version(user_agent)
        entropy = extract_high_entropy_hints(user_agent)

        with open("src/js/spoof_useragent.js", "r", encoding="utf-8") as fh:
            template = fh.read()

        js_script = template.format(
            chromium_v=chromium_v or "",
            brand=brand or "",
            brand_v=brand_v or "",
            architecture=entropy.get("architecture", ""),
            bitness=entropy.get("bitness", ""),
            wow64=str(entropy.get("wow64", False)).lower(),
            model=entropy.get("model", ""),
            mobile=str("mobile" in user_agent.lower()).lower(),
            platform=entropy.get("platform", ""),
            platformVersion=entropy.get("platformVersion", ""),
            uaFullVersion=parse_chromium_full_version(user_agent) or "",
        )
        await context.add_init_script(js_script)

    # Stealth – hide webdriver flag
    await context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return browser, context
