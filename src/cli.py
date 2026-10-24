import argparse
import json
from .safety_shift import fixture, offline_triage, live_triage, InputError


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()
    try:
        result = live_triage(fixture()) if args.live else offline_triage(fixture())
    except InputError as exc:
        print(json.dumps({"status":"BLOCKED","reason":str(exc)}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
