import json
import httpx

BASE = "http://127.0.0.1:8000"


def run_turn(message: str, session_id=None):
    body = {"message": message}
    if session_id:
        body["session_id"] = session_id
    sid = session_id
    with httpx.stream("POST", f"{BASE}/api/chat", json=body, timeout=300) as r:
        event = None
        for line in r.iter_lines():
            if not line:
                continue
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
                if event == "session":
                    sid = data["session_id"]
                    print(f"  [session] {sid} mode={data['mode']}")
                elif event == "step":
                    print(f"  [step] {data['title']}: {data['detail'][:100]}")
                elif event == "prd":
                    print(f"  [prd] v{data['version']} changed={data['changed_sections']} summary={data['change_summary'][:80]}")
                elif event == "message_delta":
                    pass
                elif event == "done":
                    print(f"  [done] {data}")
                elif event == "error":
                    print(f"  [ERROR] {data}")
    return sid


print("== Turn 1: create ==")
sid = run_turn("做一个给宠物主人的遛狗社交App，能找附近的遛狗搭子")
print("session:", sid)

print("== Turn 2: revise (add export / add community features) ==")
run_turn("再加一个宠物健康记录功能，并把目标用户细分到一二线城市养狗白领", sid)

print("== PRD check ==")
prd = httpx.get(f"{BASE}/api/sessions/{sid}/prd", timeout=30).json()
print("version:", prd.get("version"), "| product:", (prd.get("data") or {}).get("product_name"))
print("features:", [f.get("name") for f in (prd.get("data") or {}).get("features", [])][:6])

print("== versions ==")
vs = httpx.get(f"{BASE}/api/sessions/{sid}/prd/versions", timeout=30).json()
for v in vs:
    print(" v", v["version"], v["changed_sections"], v["change_summary"][:60])

print("== health ==")
print(httpx.get(f"{BASE}/api/health", timeout=10).json())
