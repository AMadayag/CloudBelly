#!/usr/bin/env python3
"""
Generate a PDF test report from the testing Lambda JSON response.
Usage: python scripts/generate_report.py response.json test_report.pdf
"""

import json
import sys
from fpdf import FPDF


def generate_pdf(input_path: str, output_path: str) -> None:
    with open(input_path) as f:
        raw = json.load(f)

    body = json.loads(raw.get("body", "{}"))

    summary = body.get("summary", {})
    results = body.get("results", [])
    timestamp = body.get("timestamp", "unknown")
    base_url = body.get("base_url", "unknown")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, "CloudBelly - E2E Test Report", ln=True, align="C")

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Generated: {timestamp}", ln=True, align="C")
    pdf.cell(0, 6, f"API: {base_url}", ln=True, align="C")
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Summary", ln=True)
    pdf.set_font("Helvetica", "", 11)

    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    errored = summary.get("errored", 0)

    overall = "PASSED" if failed == 0 and errored == 0 else "FAILED"

    if overall == "PASSED":
        pdf.set_text_color(0, 150, 0)
    else:
        pdf.set_text_color(200, 0, 0)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, f"Overall: {overall}", ln=True)
    pdf.set_text_color(0, 0, 0)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(
        0,
        6,
        f"Total: {total}  |  Passed: {passed}  |  Failed: {failed}  |  "
        f"Errors: {errored}",
        ln=True,
    )
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Test Results", ln=True)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(120, 7, "Test Name", border=1, fill=True)
    pdf.cell(30, 7, "Status", border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 10)
    for result in results:
        name = result.get("name", "")
        status = result.get("status", "")
        error = result.get("error", "")

        if status == "PASS":
            pdf.set_text_color(0, 130, 0)
        else:
            pdf.set_text_color(200, 0, 0)

        pdf.cell(120, 7, name[:65], border=1)
        pdf.cell(30, 7, status, border=1, align="C")
        pdf.ln()

        if error:
            pdf.set_text_color(150, 0, 0)
            pdf.set_font("Helvetica", "I", 9)
            pdf.cell(10, 6, "", border=0)
            pdf.cell(140, 6, f"  {error[:80]}", border=0, ln=True)
            pdf.set_font("Helvetica", "", 10)

    pdf.set_text_color(0, 0, 0)

    pdf.output(output_path)
    print(f"Report written to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_report.py <input.json> <output.pdf>")
        sys.exit(1)
    generate_pdf(sys.argv[1], sys.argv[2])
