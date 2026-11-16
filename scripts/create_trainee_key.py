#!/usr/bin/env python3
"""
Creates a restricted LiteLLM *virtual key* for a trainee (or for yourself while testing).

The key can only call the listed model aliases, has a small spend budget, a rate limit and an expiry. The provider
key (OpenCode / OpenRouter ...) never leaves the gateway: if a trainee leaks or abuses the virtual key you delete one
key, nothing else changes.

  python scripts/create_trainee_key.py                          # 1 key: formation-fast only, $0.50, 30 req/min, 1 day
  python scripts/create_trainee_key.py --count 20 --budget 0.50 --rpm 30 --hours 8
  python scripts/create_trainee_key.py --url http://localhost:14000 --alias workshop-room-a
Needs LITELLM_MASTER_KEY in the environment or in .env (the admin key: keep it to yourself).
"""

import argparse
import os
import sys
from pathlib import Path

import httpx


def master_key() -> str:
    if os.getenv("LITELLM_MASTER_KEY"):
        return os.environ["LITELLM_MASTER_KEY"]
    env = Path(__file__).parent.parent / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("LITELLM_MASTER_KEY="):
                return line.split("=", 1)[1].strip()
    sys.exit("LITELLM_MASTER_KEY not found (environment or .env)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://localhost:14000", help="gateway base URL (without /v1)")
    ap.add_argument("--models", nargs="+", default=["formation-fast"], help="model aliases the key may call")
    ap.add_argument("--budget", type=float, default=0.50, help="max spend in USD for this key (a dual-track question costs about $0.01)")
    ap.add_argument("--rpm", type=int, default=30, help="max requests per minute (one dual-track question = 4-8 requests: too low a limit makes answers wait on retries)")
    ap.add_argument("--hours", type=int, default=24, help="key lifetime in hours")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--alias", default="trainee", help="name prefix shown in the gateway's key list")
    args = ap.parse_args()

    headers = {"Authorization": f"Bearer {master_key()}"}
    print(f"{'alias':<14} key")
    for i in range(1, args.count + 1):
        name = f"{args.alias}-{i:02d}" if args.count > 1 else args.alias
        r = httpx.post(f"{args.url}/key/generate", headers=headers, timeout=30, json={
            "key_alias": name, "models": args.models, "max_budget": args.budget, "rpm_limit": args.rpm,
            "duration": f"{args.hours}h", "metadata": {"purpose": "formation trainee"}})
        if r.status_code != 200:
            sys.exit(f"gateway refused: HTTP {r.status_code} {r.text[:200]}")
        print(f"{name:<14} {r.json()['key']}")
    print(f"\nEach key: models={args.models}, budget=${args.budget}, {args.rpm} requests/min, expires in {args.hours}h.\n"
          "Trainee .env:  LITELLM_URL=http://<your-ip>:14000/v1   LITELLM_MASTER_KEY=<their key>")


if __name__ == "__main__":
    main()
