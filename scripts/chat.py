import json

import httpx

API = "http://localhost:8000/v1/chat/stream"


def stream_once(history: list[dict]) -> tuple[str, dict]:
    event, reply, done = None, [], {}
    with httpx.stream("POST", API, json={"messages": history}, timeout=httpx.Timeout(10, read=120)) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data = json.loads(line[5:].strip())
                if event == "token":
                    print(data["text"], end="", flush=True)
                    reply.append(data["text"])
                elif event == "done":
                    done = data
                elif event == "error":
                    print(f"\n[error] {data['message']}")
    print()
    return "".join(reply), done


def main() -> None:
    history, calls, total = [], 0, 0.0
    print("WorkPilot CLI · /cost /reset /exit")
    while True:
        q = input("you> ").strip()
        if q == "/exit":
            break
        if q == "/reset":
            history.clear()
            print("[history 已清空]")
            continue
        if q == "/cost":
            print(f"[本会话] {calls} 次调用，累计成本 {total:.6f}")
            continue
        if not q:
            continue
        history.append({"role": "user", "content": q})
        reply, done = stream_once(history)
        history.append({"role": "assistant", "content": reply})
        calls += 1
        total += done.get("cost") or 0
        print(f"[tokens {done.get('usage', {}).get('total_tokens')} | cost {done.get('cost')} "
              f"| ttft {done.get('ttft_ms')}ms | total {done.get('latency_ms')}ms]")


if __name__ == "__main__":
    main()
