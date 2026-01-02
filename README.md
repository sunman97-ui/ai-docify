[![PyPI version](https://badge.fury.io/py/ai-docify.svg)](https://badge.fury.io/py/ai-docify)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
# ai-docify 🤖

**A simple, secure, and cost-aware CLI tool for generating high-quality NumPy/Sphinx style docstrings using AI.**

`ai-docify` helps you document your Python code instantly using either cloud-based models (OpenAI) or local privacy-focused models (Ollama). It is designed to be **safe** (using AST parsing), **transparent** (pre-flight cost checks), and **non-destructive**.

---

## ✨ Key Features

* **💰 Cost-Aware Design**: Calculates and displays the **estimated input token cost** via `tiktoken` *before* you spend a penny.
* **🔒 Privacy-First**: Switch seamlessly between **OpenAI** (Cloud) and **Ollama** (Local) with a single flag. Keep proprietary code on your machine when needed.
* **🛡️ AST-Powered Safety**: Unlike other tools that "guess" where to put text, `ai-docify` parses your code's Abstract Syntax Tree to surgically inject docstrings without breaking indentation or logic.
* **↩️ The "Undo" Button**: Includes a `strip` command to safely remove all docstrings if you change your mind.
* **✌️ Dual Generation Modes**: Choose between `rewrite` for speed/coverage, or `inject` for surgical precision.
* **⚡ "Lean" Architecture**: Optimized prompt engineering ensures high-quality documentation without wasting tokens on conversational fluff.

---

## 🚀 Installation

Install `ai-docify` directly from PyPI:

```bash
pip install ai-docify

```

### Prerequisites

* **Python 3.8+**
* **[Ollama](https://ollama.com/)** (Optional, required only if using local models)

### Setup (OpenAI Only)

If you plan to use OpenAI models, set your API key as an environment variable:

**Mac/Linux:**

```bash
export OPENAI_API_KEY=sk-your-api-key-here

```

**Windows (PowerShell):**

```powershell
$env:OPENAI_API_KEY="sk-your-api-key-here"

```

*(Alternatively, you can create a `.env` file in your project root)*

---

## 💻 VS Code Extension

Prefer a GUI? This CLI powers the **AI Docify for VS Code** extension.
👉 **[Download AI Docify for VS Code](https://github.com/sunman97-ui/ai-docify-vscode)

---

## 📖 Usage

### 1. Generating Documentation

You must specify the **Provider**, **Model**, and **Mode**.

#### `inject` Mode (Recommended)

*Best for: Surgical precision and preserving formatting.*
Uses AST parsing to find functions and classes, injecting docstrings exactly where they belong without touching a single line of your actual code.

```bash
ai-docify generate my_script.py --provider openai --model gpt-5-mini --mode inject

```

#### `rewrite` Mode

*Best for: Speed and heavy refactoring.*
Asks the AI to rewrite the file with docs included. Good for initial drafts or undocumented legacy files.

```bash
# Using a local model (Free)
ai-docify generate my_script.py --provider ollama --model llama3 --mode rewrite

```

### 2. The Safety Check 🛡️

Before generating anything, the tool will pause and show you an exact cost estimate:

```text
🤖 ai-docify: Checking my_script.py in INJECT mode

📊 Estimation (Input Only):
   Tokens: 350
   Est. Cost: $0.00009

Do you want to proceed? [y/n]:

```

### 3. Stripping Docstrings (Undo) ↩️

Need to start over? The `strip` command uses AST parsing to cleanly remove all docstrings from a file, leaving your logic intact. It saves the clean version to a `stripped_scripts/` folder by default.

```bash
ai-docify strip my_script.py

```

### 4. Cleaning Output

To remove all generated files from the default `ai_output/` directory:

```bash
ai-docify clean

```

---

## ⚙️ Supported Models

`ai-docify` comes pre-configured with pricing and token limits for popular models.

**OpenAI:**

* `o3-2025-04-16`
* `gpt-5` / `gpt-5-mini` /  `gpt-5-nano`
* `gpt-5.2`

**Ollama (Local):**

* `llama3.1:8b`
* `qwen2.5-coder:7b`
* (Any model pulled via `ollama pull` works with the `--provider ollama` flag)

*Missing a model? Feel free to open an Issue or Pull Request to update the internal pricing configuration!*

---

## 🤝 Contributing

We welcome contributions! Whether it's a bug fix, a new feature, or a better prompt template:

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/NewModel`)
3. Commit your Changes (`git commit -m 'Add GPT-6 support'`)
4. Push to the Branch (`git push origin feature/NewModel`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
