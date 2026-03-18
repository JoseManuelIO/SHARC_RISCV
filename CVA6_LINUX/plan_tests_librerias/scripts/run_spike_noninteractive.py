#!/usr/bin/env python3
import argparse
import selectors
import subprocess
import sys
import time
from pathlib import Path


def read_until(selector, stream, deadline, buffer, markers=None):
    while time.time() < deadline:
        events = selector.select(timeout=0.2)
        if not events:
            continue
        for key, _ in events:
            chunk = key.fileobj.read(4096)
            if not chunk:
                return buffer, False
            text = chunk.decode("utf-8", errors="ignore")
            stream.write(text)
            stream.flush()
            buffer.append(text)
            joined = "".join(buffer)
            if markers:
                for marker in markers:
                    if marker in joined:
                        return buffer, True
    return buffer, False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spike", required=True)
    parser.add_argument("--payload", required=True)
    parser.add_argument("--command", required=True)
    parser.add_argument("--expect", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--boot-timeout", type=float, default=20.0)
    parser.add_argument("--shutdown-timeout", type=float, default=10.0)
    args = parser.parse_args()

    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("w", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            [args.spike, args.payload],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )

        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ)

        output = []
        try:
            _, got_prompt = read_until(
                selector,
                log_file,
                time.time() + args.boot_timeout,
                output,
                markers=["# ", "Starting sshd: OK", "NFS preparation skipped, OK"],
            )
            if not got_prompt:
                print("ERROR: Linux boot marker not reached in Spike", file=sys.stderr)
                proc.kill()
                return 2

            proc.stdin.write((args.command + "\n").encode("utf-8"))
            proc.stdin.write(b"poweroff -f\n")
            proc.stdin.flush()

            read_until(
                selector,
                log_file,
                time.time() + args.shutdown_timeout,
                output,
                markers=["Power down"],
            )
            proc.wait(timeout=5)
        finally:
            selector.close()
            if proc.poll() is None:
                proc.kill()

        full_output = "".join(output)
        if args.expect not in full_output:
            print(f"ERROR: expected token not found: {args.expect}", file=sys.stderr)
            return 3
        if "Power down" not in full_output:
            print("ERROR: guest did not power down cleanly", file=sys.stderr)
            return 4

    return 0


if __name__ == "__main__":
    sys.exit(main())
