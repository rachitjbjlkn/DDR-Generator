# DDR (Detailed Diagnostic Report) Generator

Reads two PDF documents (Inspection Report + Thermal Report) and generates a structured, client-ready DDR report as a downloadable PDF.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

Set your Groq API key (free at https://console.groq.com):

```bash
# Windows PowerShell
$env:GROQ_API_KEY = "your_key_here"

# Run
python main.py inspection.pdf thermal.pdf
```

### Test without API key

```bash
python main.py inspection.pdf thermal.pdf --mock
```

## Output

Generated reports are saved in the `output/` directory.
