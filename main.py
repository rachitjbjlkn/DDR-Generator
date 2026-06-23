import sys
import os
from datetime import datetime
from extractor import extract_pdf_content
from ai_analyzer import analyze_documents
from report_builder import build_pdf_report


def print_header():
    print()
    print("=" * 56)
    print("   DDR Report Generator - Detailed Diagnostic Report")
    print("=" * 56)
    print()


def main():
    print_header()

    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage:")
        print("  python main.py inspection.pdf thermal.pdf")
        print("  python main.py inspection.pdf thermal.pdf --mock")
        sys.exit(1)

    inspection_path = sys.argv[1]
    thermal_path = sys.argv[2]
    mock_mode = "--mock" in sys.argv

    for path in [inspection_path, thermal_path]:
        if not os.path.exists(path):
            print(f"  Error: File not found - {path}")
            sys.exit(1)

    if not mock_mode and not os.environ.get("GROQ_API_KEY"):
        print("  Error: GROQ_API_KEY environment variable not set.")
        print("  Get your free key at https://console.groq.com")
        print("  Or use --mock flag for testing without API key.")
        sys.exit(1)

    print("  Step 1/4 - Extracting inspection report...")
    inspection = extract_pdf_content(inspection_path)
    print(f"    [OK] {inspection['pages']} pages, {len(inspection['images'])} images found")

    print("  Step 2/4 - Extracting thermal report...")
    thermal = extract_pdf_content(thermal_path)
    print(f"    [OK] {thermal['pages']} pages, {len(thermal['images'])} images found")

    print("  Step 3/4 - Analyzing with Groq AI (llama-3.3-70b)...")
    ddr_data = analyze_documents(
        doc1_text=inspection["text"],
        doc2_text=thermal["text"],
        doc1_images=inspection["images"],
        doc2_images=thermal["images"],
    )
    obs_count = len(ddr_data.get("area_observations", []))
    print(f"    [OK] {obs_count} areas analyzed")

    all_images = inspection["images"] + thermal["images"]

    os.makedirs("output", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"output/DDR_Report_{timestamp}.pdf"

    print("  Step 4/4 - Building PDF report...")
    build_pdf_report(ddr_data, all_images, output_path)

    print(f"\n  [DONE] Report saved to: {output_path}")
    print()


if __name__ == "__main__":
    main()
