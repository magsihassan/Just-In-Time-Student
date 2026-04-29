# JIT Compiler Explorer

A full compiler construction project built in Python with a sleek, dark-themed modern web interface. This tool visually demonstrates all 6 classical phases of a compiler.

## Features

- **Lexical Analysis**: Token stream visualization with highlighted tokens.
- **Syntax Analysis**: Simple AST rendering.
- **Semantic Analysis**: Symbol table generation and scope depth indicators.
- **Intermediate Code Generation (ICG)**: Three-Address Code (TAC) list.
- **Code Optimization**: Side-by-side Before/After diff highlighting optimizations (Constant Folding & Dead Code Elimination).
- **Code Generation**: Assembly-like output with syntax highlighting.
- **Modern UI**: Dark themed aesthetic powered by CodeMirror, matching the premium compiler explorer vibe.

## Tech Stack
- **Backend**: Python (pure Python for compiler logic), Flask (REST API).
- **Frontend**: HTML5, Vanilla JS, CSS. No build step or Node.js required. CodeMirror for the source editor.

## Getting Started

1. **Install dependencies**:
   Ensure you have Python 3 installed. Then, install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the server**:
   Start the Flask application:
   ```bash
   python app.py
   ```

3. **Open the Explorer**:
   Navigate to [http://localhost:5000](http://localhost:5000) in your web browser.

## Sample Programs

The explorer comes with 4 sample programs available from the dropdown menu:
1. **Simple Arithmetic**
2. **Factorial (Recursive)**
3. **Fibonacci (Loop)**
4. **Max of Two**

Select a program and click "Compile" to watch the compilation pipeline in action!
