#!/usr/bin/env python3
"""
Generate a PDF report from a pytest --json-report output file.
Usage: python scripts/generate_unit_report.py report.json output.pdf [title]
"""

import json
import sys
from datetime import datetime
from fpdf import FPDF


def generate_pdf(input_path: str, output_path: str, title: str) -> None:
    with open(input_path) as f:
        data = json.load(f)

    summary = data.get("summary", {})
    tests = data.get("tests", [])
    duration = round(data.get("duration", 0), 2)
    timestamp = datetime.utcnow().isoformat() + "Z"

    total = summary.get("total", len(tests))
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    errored = summary.get("error", 0)

    overall = "PASSED" if failed == 0 and errored == 0 else "FAILED"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 12, f"CloudBelly - {title}", ln=True, align="C")

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Generated: {timestamp}", ln=True, align="C")
    pdf.cell(0, 6, f"Duration: {duration}s", ln=True, align="C")
    pdf.ln(8)

    # Overall result
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Summary", ln=True)

    if overall == "PASSED":
        pdf.set_text_color(0, 150, 0)
    else:
        pdf.set_text_color(200, 0, 0)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, f"Overall: {overall}", ln=True)
    pdf.set_text_color(0, 0, 0)

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(
        0, 6,
        f"Total: {total}  |  Passed: {passed}  |  "
        f"Failed: {failed}  |  Errors: {errored}",
        ln=True
    )
    pdf.ln(6)

    # Table header
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Test Results", ln=True)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(140, 7, "Test Name", border=1, fill=True)
    pdf.cell(30, 7, "Status", border=1, fill=True, align="C")
    pdf.ln()

    # Rows
    pdf.set_font("Helvetica", "", 9)
    for test in tests:
        nodeid = test.get("nodeid", "")
        # Strip the file path prefix, keep class::method
        name = nodeid.split("::")[-1] if "::" in nodeid else nodeid
        full_name = "::".join(nodeid.split("::")[1:]) if "::" in nodeid else nodeid

        outcome = test.get("outcome", "")
        if outcome == "passed":
            status = "PASS"
            pdf.set_text_color(0, 130, 0)
        elif outcome == "failed":
            status = "FAIL"
            pdf.set_text_color(200, 0, 0)
        else:
            status = "ERROR"
            pdf.set_text_color(150, 80, 0)

        pdf.cell(140, 7, full_name[:75], border=1)
        pdf.cell(30, 7, status, border=1, align="C")
        pdf.ln()

        # Print failure message if any
        call = test.get("call", {})
        if call and call.get("longrepr"):
            pdf.set_text_color(150, 0, 0)
            pdf.set_font("Helvetica", "I", 8)
            error_line = str(call["longrepr"]).split("\n")[-1][:90]
            pdf.cell(10, 5, "", border=0)
            pdf.cell(160, 5, f"  {error_line}", border=0, ln=True)
            pdf.set_font("Helvetica", "", 9)

    pdf.set_text_color(0, 0, 0)
    pdf.output(output_path)
    print(f"Report written to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_unit_report.py <report.json> "
              "<output.pdf> [title]")
        sys.exit(1)

    report_title = sys.argv[3] if len(sys.argv) > 3 else "Unit Test Report"
    generate_pdf(sys.argv[1], sys.argv[2], report_title)
