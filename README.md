# ai-docify 🤖

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**A simple, secure, and cost-aware CLI tool for generating high-quality NumPy/Sphinx style docstrings using AI.**

`ai-docify` helps you document your Python code instantly using either cloud-based models (OpenAI) or local privacy-focused models (Ollama). It is designed to be safe, transparent, and non-destructive.

---

## ✨ Key Features

- **💰 Cost-Aware Design**: Unlike other tools, `ai-docify` calculates and displays the **estimated input token cost** via `tiktoken` *before* you spend a penny.
- **🔒 Privacy-First**: Switch seamlessly between **OpenAI** (Cloud) and **Ollama** (Local) with a single flag. Keep proprietary code on your machine when needed.
- **🛡️ Non-Destructive**: Your original files are never touched. Documented code is safely written to a dedicated `ai_output/` directory.
- **⚡ "Lean" Templates**: Optimized prompts ensure high-quality documentation without wasting tokens on unnecessary conversational fluff.
- **⚙️ Future-Proof Config**: Easily add support for new models (e.g., GPT-6, Llama-4) just by updating the `pricing.json` configuration file.

---

## 🚀 Installation

Currently, `ai-docify` is available via source installation.

### Prerequisites

- Python 3.8 or higher
- [Ollama](https://ollama.com/) (Optional, for local models)

### Steps

1. **Clone the repository**

   ```bash

   git clone https://github.com/sunman97-ui/ai-docify.git
   
   ```

   ```bash

   cd ai-docify

    ```

2. **Create a Virtual Environment** (Recommended)

```bash
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# Mac/Linux
python3 -m venv venv
source venv/bin/activate

```

1. **Install the package**

```bash
pip install -e .

```

1. **Setup Environment Variables**
Create a `.env` file in the root directory (copy from `.env.example` if available):

```ini
OPENAI_API_KEY=sk-your-api-key-here

```

---

## 📖 Usage

The CLI requires you to specify the **Provider** and the **Model** explicitly to prevent accidental costs.

### 1. Using OpenAI (Cloud)

*Best for: High accuracy, complex logic, and standard pricing.*

```bash
ai-docify my_script.py --provider openai --model gpt-5-nano

```

### 2. Using Ollama (Local)

*Best for: Privacy, zero cost, and offline development.*

```bash
# Ensure you have pulled the model first: ollama pull llama3.1:8b
ai-docify my_script.py --provider ollama --model llama3.1:8b

```

### The Safety Check 🛡️

Before generating anything, the tool will pause and show you an estimation:

```text
🤖 ai-docify: Checking my_script.py

📊 Estimation:
   Tokens: 350
   Est. Cost: $0.00009

Do you want to proceed? [y/n]:

```

### The Final Report 📉

After the documentation is generated, `ai-docify` provides a transparent receipt of your actual usage, including hidden "reasoning tokens" used by advanced models:

```text
✅ Successfully generated documentation!
   Output saved to: ai_output\my_script.doc.py

📉 Final Usage Report:
   Input Tokens:     318
   Output Tokens:    2820
   (Includes 2048 reasoning tokens)
   Total Cost:       $0.00114

---

## ⚙️ Configuration

`ai-docify` is built to be extensible. You define which models are allowed and how much they cost.

**Location:** `src/ai_docify/config/pricing.json`

To add a new model, simply edit this file:

```json
{
  "openai": {
    "new-model-name": {
      "input_cost_per_million": 1.50,
      "output_cost_per_million": 2.00
    }
  }
}

```

---

## 🗺️ Roadmap

We are actively working on making cost tracking even more precise:

- [x] **Pre-Run Estimation:** Calculate input tokens and estimated cost using `tiktoken`.
- [x] **Post-Run Analysis:** Reports `output_tokens`, `reasoning_tokens` (for complex models), and the **Total Combined Cost** (Input + Output) after generation.
- [ ] **Batch Processing:** Support for documenting entire directories.

## 🤝 Contributing

Contributions are welcome! Whether it's a bug fix, a new feature, or a better prompt template:

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

### 👣 Final Step: Add a LICENSE file

Since the README mentions the MIT License, you must create a file named `LICENSE` in your root folder.

**Content for `LICENSE`:**

```text
MIT License

Copyright (c) 2025 John Spencer

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

```
