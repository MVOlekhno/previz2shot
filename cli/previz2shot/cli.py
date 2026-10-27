"""previz2shot CLI: grey layout video -> FLUX.2 Klein first frame -> LTX-2.5 L2R video.

Backends:
  cloud  Comfy Cloud (https://cloud.comfy.org), needs COMFY_API_KEY (default)
  api    your own deployment: COMFY_BASE_URL (+ optional COMFY_API_KEY)
  local  self-hosted ComfyUI: COMFY_BASE_URL, default http://127.0.0.1:8188
"""
import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import requests

WORKFLOWS = Path(__file__).resolve().parents[2] / "workflows"
KLEIN_WF = WORKFLOWS / "flux2_klein_first_frame_api.json"
LTX_WF = WORKFLOWS / "ltx25_l2r_twostage_kf_api.json"
DONE = {"completed", "success"}
FAILED = {"failed", "error", "cancelled"}


class ComfyClient:
    def __init__(self, backend):
        self.backend = backend
        default = "https://cloud.comfy.org" if backend == "cloud" else "http://127.0.0.1:8188"
        self.base = os.environ.get("COMFY_BASE_URL", default).rstrip("/")
        key = os.environ.get("COMFY_API_KEY")
        if backend == "cloud" and not key:
            sys.exit("COMFY_API_KEY is required for --backend cloud")
        self.headers = {"X-API-Key": key} if key else {}

    def check_balance(self):
        floor = os.environ.get("COMFY_MIN_BALANCE_CENTS")
        if self.backend != "cloud" or not floor:
            return
        r = requests.get(self.base + "/api/billing/balance", headers=self.headers, timeout=30)
        r.raise_for_status()
        balance = r.json()["effective_balance_cents"]
        if balance < float(floor):
            sys.exit(f"Balance {balance} cents below COMFY_MIN_BALANCE_CENTS={floor}; not submitting.")

    def upload(self, path, mime):
        with open(path, "rb") as fh:
            r = requests.post(self.base + "/api/upload/image", headers=self.headers,
                              files={"image": (os.path.basename(path), fh, mime)},
                              data={"overwrite": "true"}, timeout=600)
        r.raise_for_status()
        return r.json()["name"]

    def run(self, workflow, poll_s=5):
        self.check_balance()
        r = requests.post(self.base + "/api/prompt", headers=self.headers,
                          json={"prompt": workflow}, timeout=60)
        body = r.json()
        if "prompt_id" not in body:
            sys.exit("Prompt rejected: " + json.dumps(body)[:2000])
        prompt_id = body["prompt_id"]
        if self.backend == "local":
            return self._wait_local(prompt_id, poll_s)
        while True:
            status = requests.get(f"{self.base}/api/job/{prompt_id}/status",
                                  headers=self.headers, timeout=30).json()
            if status["status"] in DONE:
                break
            if status["status"] in FAILED:
                sys.exit("Job failed: " + str(status.get("error_message", ""))[:2000])
            time.sleep(poll_s)
        history = requests.get(f"{self.base}/api/history_v2/{prompt_id}",
                               headers=self.headers, timeout=30).json()[prompt_id]
        return history["outputs"]

    def _wait_local(self, prompt_id, poll_s):
        while True:
            history = requests.get(f"{self.base}/history/{prompt_id}", timeout=30).json()
            if prompt_id in history:
                return history[prompt_id]["outputs"]
            time.sleep(poll_s)

    def download_first(self, outputs, node_id, dest):
        view = "/api/view" if self.backend != "local" else "/view"
        for files in outputs.get(node_id, {}).values():
            for item in files if isinstance(files, list) else []:
                if isinstance(item, dict) and "filename" in item:
                    params = {k: item.get(k, "") for k in ("filename", "subfolder", "type")}
                    r = requests.get(self.base + view, headers=self.headers, params=params, timeout=600)
                    r.raise_for_status()
                    Path(dest).write_bytes(r.content)
                    return dest
        sys.exit(f"No file output from node {node_id}")


def load_workflow(path):
    return copy.deepcopy(json.loads(Path(path).read_text()))


def set_input(workflow, node_id, name, value):
    if node_id not in workflow:
        sys.exit(f"Node {node_id} not found in workflow")
    workflow[node_id]["inputs"][name] = value


def extract_first_frame(video, dest):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
                    "-frames:v", "1", str(dest)], check=True)
    return dest


def stylize(client, frame_png, prompt, tag, dest):
    wf = load_workflow(KLEIN_WF)
    set_input(wf, "l1", "image", client.upload(frame_png, "image/png"))
    set_input(wf, "5", "text", prompt)
    set_input(wf, "10", "filename_prefix", f"previz2shot/klein_{tag}")
    return client.download_first(client.run(wf), "10", dest)


def render(client, layout_mp4, first_frame, prompt, tag, dest):
    wf = load_workflow(LTX_WF)
    set_input(wf, "8", "file", client.upload(layout_mp4, "video/mp4"))
    set_input(wf, "10", "image", client.upload(first_frame, "image/png"))
    set_input(wf, "5", "text", prompt)
    set_input(wf, "22", "filename_prefix", f"previz2shot/l2r_{tag}")
    return client.download_first(client.run(wf), "22", dest)


def main():
    parser = argparse.ArgumentParser("previz2shot")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="layout video -> styled video")
    run.add_argument("--layout", required=True, help="grey playblast .mp4 (1920x1088)")
    run.add_argument("--prompt", required=True)
    run.add_argument("--out", required=True, help="output .mp4")
    run.add_argument("--first-frame", help="skip FLUX.2 Klein and use this styled PNG")
    run.add_argument("--backend", choices=["cloud", "api", "local"], default="cloud")
    args = parser.parse_args()

    client = ComfyClient(args.backend)
    tag = uuid.uuid4().hex[:8]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        first = args.first_frame
        if not first:
            frame = extract_first_frame(args.layout, Path(tmp) / "layout_f1.png")
            first = stylize(client, frame, args.prompt, tag, out.with_suffix(".first_frame.png"))
            print("first frame:", first)
        render(client, args.layout, first, args.prompt, tag, out)
    print("wrote", out)


if __name__ == "__main__":
    main()
