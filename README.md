# 🕵️‍♂️ BlackStory AI

**BlackStory AI** is an advanced interactive mystery game powered by Artificial Intelligence. It brings the classic "Black Stories" experience to life, allowing you to either watch AI agents solve mysteries or step into the shoes of the detective yourself.

## 🌟 Features

*   **Multiple Game Modes**: Experience the mystery in four distinct ways.
*   **Dynamic Story Generation**: Every game features a unique, AI-generated mystery based on your chosen difficulty.
*   **Multi-Model Support**: Powered by **Google Gemini** and **Ollama**, allowing you to mix and match different AI models for the Narrator and Detectives.
*   **Premium Web Interface**: A beautiful, dark-themed UI with glassmorphism effects, real-time streaming responses, and smooth animations.
*   **Hint System**: Stuck? Ask "Watson" for a subtle hint to get back on track.

## 🎮 Game Modes

### 1. 🤖 Single Player (AI vs AI)
Sit back and watch the show! An **AI Detective** interrogates the **AI Narrator** to solve the mystery. Perfect for seeing how different models reason and deduce.

### 2. 👤 Interactive (User vs AI)
**YOU are the Detective!**
*   The AI Narrator presents a mystery.
*   You ask Yes/No questions via the chat interface.
*   Use the **"💡 Pista"** button if you need a nudge from Watson.
*   Submit your final solution when you think you've cracked the case.

### 3. ⚔️ Fight Mode (1v1)
Two AI Detectives compete against each other!
*   **Detective 1** vs **Detective 2**.
*   They take turns asking questions.
*   The first one to solve the mystery wins the round.
*   A great way to benchmark different AI models against each other.

### 4. 🧠 Council Mode (3 Agents)
A collaborative effort by a specialized team of three AI agents:
*   **The Visionary**: Proposes wild, creative, and out-of-the-box theories.
*   **The Skeptic**: Analyzes theories critically, finding logical flaws and missing evidence.
*   **The Leader**: Synthesizes the debate and decides on the best question to ask the Narrator.
*   *Note: In Hard difficulty, the Council is forced to guess after a set number of questions!*

## 🚀 Installation & Setup

### Prerequisites
*   Python 3.10+
*   `uv` package manager (recommended) or `pip`
*   A Google Gemini API Key (for Gemini models)
*   Ollama installed locally (optional, for local models)

### Steps

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/black-stories-ai.git
    cd black-stories-ai
    ```

2.  **Install dependencies**:
    ```bash
    uv sync
    # OR
    pip install -r requirements.txt
    ```

3.  **Configure Environment**:
    Create a `.env` file in the root directory:
    ```ini
    # .env
    GEMINI_API_KEY=your_gemini_api_key_here
    OLLAMA_HOST=http://localhost:11434  # Optional
    ```

## 🖥️ Usage

### Web Interface (Recommended)
Run the Flask application to launch the full experience:

```bash
uv run web/app.py
# OR
python web/app.py
```

Open your browser and navigate to: `http://127.0.0.1:5000`

### Command Line Interface (CLI)
You can also run a simple Single Player session directly from the terminal:

```bash
python main.py -narrador gemini:gemini-2.5-flash -detective gemini:gemini-2.5-flash -dificultad media
```

## 🛠️ Technologies

*   **Backend**: Python, Flask
*   **Frontend**: HTML5, CSS3 (Glassmorphism), JavaScript (Vanilla)
*   **AI Integration**: Google Generative AI SDK, Ollama API
*   **Package Management**: `uv`

## 📄 License

This project is open-source and available under the MIT License.
