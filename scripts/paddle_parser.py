#!/usr/bin/env python3
"""
PaddleOCR-VL-1.6 PDF parser for gxpcode-translator.
Uploads PDF to PaddleOCR cloud API, polls for results, downloads markdown + images.

Usage:
  python paddle_parser.py --input_path <pdf_path> --save_dir <output_dir>

Output:
  <save_dir>/markdown/<pdf_name>_p001.md  ... per-page markdown
  <save_dir>/recognition_json/<pdf_name>.json  ... full elements JSON
  <save_dir>/images/                        ... downloaded images
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
MODEL = "PaddleOCR-VL-1.6"

SKILL_DIR = Path(__file__).resolve().parent.parent  # scripts → skill root
CONFIG_PATH = SKILL_DIR / "config.json"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_path", required=True, help="Path to PDF file")
    parser.add_argument("--save_dir", required=True, help="Output directory")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    save_dir = Path(args.save_dir)
    md_dir = save_dir / "markdown"
    json_dir = save_dir / "recognition_json"
    img_dir = save_dir / "images"
    md_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    config = load_config()
    token = config.get("paddleocr_token", "")
    if not token:
        print("Error: paddleocr_token not found in config.json")
        sys.exit(1)

    pdf_name = input_path.stem
    headers = {"Authorization": f"bearer {token}"}

    # ── Submit job ──
    print(f"⏳ PDF 解析中... (已提交 API)")
    print(f"   File: {input_path.name}")

    data = {
        "model": MODEL,
        "optionalPayload": json.dumps({
            "useDocOrientationClassify": False,
            "useDocUnwarping": False,
            "useChartRecognition": False,
        })
    }
    with open(input_path, "rb") as f:
        job_response = requests.post(JOB_URL, headers=headers, data=data, files={"file": f})

    if job_response.status_code != 200:
        print(f"Error: Job submission failed: {job_response.text}")
        sys.exit(1)

    job_data = job_response.json()
    job_id = job_data.get("data", {}).get("jobId")
    if not job_id:
        print(f"Error: No jobId in response: {job_data}")
        sys.exit(1)
    print(f"   Job ID: {job_id}")

    # ── Poll for results ──
    total_pages = 0
    while True:
        result_response = requests.get(f"{JOB_URL}/{job_id}", headers=headers)
        assert result_response.status_code == 200
        result_data = result_response.json()
        job_data = result_data.get("data", {})
        state = job_data.get("state", "unknown")

        if state == "pending":
            print("⏳ 轮询中... 等待处理")
        elif state == "running":
            progress = job_data.get("extractProgress", {})
            total_pages = progress.get("totalPages", 0)
            extracted = progress.get("extractedPages", 0)
            print(f"⏳ 轮询中... {extracted}/{total_pages} 页")
        elif state == "done":
            progress = job_data.get("extractProgress", {})
            extracted = progress.get("extractedPages", 0)
            start = progress.get("startTime", "")
            end = progress.get("endTime", "")
            print(f"✅ 解析完成: {extracted} 页, start={start}, end={end}")
            result_url = job_data.get("resultUrl", {})
            jsonl_url = result_url.get("jsonUrl", "")
            if not jsonl_url:
                print("Error: No jsonUrl in result")
                sys.exit(1)
            break
        elif state == "failed":
            error_msg = job_data.get("errorMsg", "Unknown error")
            print(f"Error: Job failed: {error_msg}")
            sys.exit(1)

        time.sleep(5)

    # ── Download results ──
    jsonl_response = requests.get(jsonl_url)
    jsonl_response.raise_for_status()
    lines = jsonl_response.text.strip().split("\n")

    page_num = 0
    all_elements = []
    element_index = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue
        parsed = json.loads(line)
        result = parsed.get("result", {})
        if not result:
            continue

        for res in result.get("layoutParsingResults", []):
            md_block = res.get("markdown", {})
            md_text = md_block.get("text", "")
            if not md_text:
                continue

            # Save per-page markdown
            md_filename = md_dir / f"{pdf_name}_p{page_num + 1:03d}.md"
            with open(md_filename, "w", encoding="utf-8") as f:
                f.write(md_text)

            # Build elements for this page
            elements = []
            paragraphs = md_text.strip().split("\n\n")
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                # Detect element type
                label = "text"
                if para.startswith("## "):
                    label = "heading"
                elif para.startswith("# "):
                    label = "title"
                elif para.startswith("|") and para.endswith("|"):
                    label = "tab"
                elif para.startswith("!["):
                    label = "figure"

                elements.append({
                    "index": element_index,
                    "page": page_num + 1,
                    "label": label,
                    "text": para,
                    "en": para,
                })
                element_index += 1

            all_elements.append({
                "page": page_num + 1,
                "md_path": str(md_filename),
                "elements": elements,
            })

            # Download images
            images = md_block.get("images", {})
            for img_rel_path, img_url in images.items():
                img_save_path = img_dir / img_rel_path
                img_save_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    img_bytes = requests.get(img_url).content
                    with open(img_save_path, "wb") as f:
                        f.write(img_bytes)
                except Exception as e:
                    print(f"   ⚠️ 图片下载失败: {img_rel_path} — {e}")

            page_num += 1

    # ── Save recognition_json ──
    json_path = json_dir / f"{pdf_name}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "file": str(input_path),
            "total_pages": page_num,
            "pages": all_elements,
        }, f, ensure_ascii=False, indent=2)

    print(f"   产出: {page_num} 页 markdown, {element_index} 个元素")
    print(f"   {md_dir}")
    print(f"   {json_path}")


if __name__ == "__main__":
    main()
