import os
import sys
import uuid
import threading
import json
import webbrowser
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, send_from_directory

load_dotenv()

from extractor import extract_pdf_content
from ai_analyzer import analyze_documents
from report_builder import build_pdf_report

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(os.path.dirname(__file__), 'output')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

jobs = {}

def process_files(job_id, doc1_path, doc2_path):
    status = jobs[job_id]

    try:
        status["step"] = "Extracting Document 1..."
        status["progress"] = 15
        doc1 = extract_pdf_content(doc1_path)
        status["pages_1"] = doc1["pages"]
        status["images_1"] = len(doc1["images"])
        status["log"].append(f"Extracted Doc 1: {doc1['pages']} pages, {len(doc1['images'])} images")

        status["step"] = "Extracting Document 2..."
        status["progress"] = 30
        doc2 = extract_pdf_content(doc2_path)
        status["pages_2"] = doc2["pages"]
        status["images_2"] = len(doc2["images"])
        status["log"].append(f"Extracted Doc 2: {doc2['pages']} pages, {len(doc2['images'])} images")

        status["step"] = "Running AI analysis..."
        status["progress"] = 50
        ddr_data = analyze_documents(
            doc1_text=doc1["text"],
            doc2_text=doc2["text"],
            doc1_images=doc1["images"],
            doc2_images=doc2["images"],
        )
        obs_count = len(ddr_data.get("area_observations", []))
        status["observations"] = obs_count
        status["overall_severity"] = ddr_data.get("severity_assessment", {}).get("overall", "N/A")
        status["log"].append(f"AI analysis complete: {obs_count} areas identified")

        status["step"] = "Building PDF report..."
        status["progress"] = 75
        all_images = doc1["images"] + doc2["images"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"DDR_Report_{timestamp}_{job_id[:8]}.pdf"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        build_pdf_report(ddr_data, all_images, output_path)
        status["output_file"] = output_filename
        status["log"].append(f"PDF generated: {output_filename}")

        status["step"] = "Complete"
        status["progress"] = 100
        status["done"] = True

    except Exception as e:
        status["step"] = "Error"
        status["error"] = str(e)
        status["log"].append(f"ERROR: {e}")
        status["done"] = True


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/processing/<job_id>')
def processing(job_id):
    return render_template('processing.html', job_id=job_id)


@app.route('/analyze', methods=['POST'])
def analyze():
    if 'doc1' not in request.files or 'doc2' not in request.files:
        return jsonify({"error": "Both PDF documents are required"}), 400

    doc1_file = request.files['doc1']
    doc2_file = request.files['doc2']

    if not doc1_file.filename.endswith('.pdf') or not doc2_file.filename.endswith('.pdf'):
        return jsonify({"error": "Both files must be PDFs"}), 400

    job_id = uuid.uuid4().hex
    doc1_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_doc1.pdf")
    doc2_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_doc2.pdf")

    doc1_file.save(doc1_path)
    doc2_file.save(doc2_path)

    jobs[job_id] = {
        "step": "Queued",
        "progress": 0,
        "done": False,
        "error": None,
        "log": [],
        "output_file": None,
        "pages_1": 0,
        "pages_2": 0,
        "images_1": 0,
        "images_2": 0,
        "observations": 0,
        "overall_severity": "",
    }

    thread = threading.Thread(target=process_files, args=(job_id, doc1_path, doc2_path))
    thread.daemon = True
    thread.start()

    return jsonify({"job_id": job_id})


@app.route('/status/<job_id>')
def get_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(
        app.config['OUTPUT_FOLDER'],
        filename,
        as_attachment=True,
        download_name=filename
    )


@app.route('/cleanup/<job_id>', methods=['POST'])
def cleanup(job_id):
    job = jobs.get(job_id)
    if job and job.get("output_file"):
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], job["output_file"])
        if os.path.exists(filepath):
            os.remove(filepath)
    for ext in ["_doc1.pdf", "_doc2.pdf"]:
        fpath = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}{ext}")
        if os.path.exists(fpath):
            os.remove(fpath)
    jobs.pop(job_id, None)
    return jsonify({"ok": True})


if __name__ == '__main__':
    port = 5000
    print(f"\n  DDR App running at http://localhost:{port}")
    print("  Opening browser...\n")
    webbrowser.open(f"http://localhost:{port}")
    app.run(debug=False, port=port)
