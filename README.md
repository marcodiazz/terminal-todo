# Terminal Todo

A beautiful, keyboard-driven terminal-based todo application built with [Textual](https://textual.textualize.io/).

![Screenshot](./assets/todo.png)  
 

## Features

- 📋 Multiple tabs for organizing tasks
- ✅ Mark tasks as complete/incomplete
- 🎨 Dark/Light theme toggle
- ⌨️ Vim-style keyboard navigation
- 💾 Persistent storage

## Installation

The installation is **permanent** - once installed, the `todo` command will be available even after restarting your computer.

### Windows

```powershell
# 1. Install Python (if not already installed)
# Download from: https://www.python.org/downloads/
# ⚠️ IMPORTANT: Check "Add Python to PATH" during installation

# 2. Install pipx
python -m pip install --user pipx
python -m pipx ensurepath

# 3. Restart your terminal (PowerShell or CMD)

# 4. Install terminal-todo
pipx install git+https://github.com/marcodiazz/terminal-todo.git

# 5. Use the command
todo
```

**Note for Windows users:** After step 3, close and reopen your terminal for the PATH changes to take effect.

### macOS/Linux

```bash
# 1. Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install pipx
brew install pipx
pipx ensurepath

# 3. Restart your terminal

# 4. Install terminal-todo
pipx install git+https://github.com/marcodiazz/terminal-todo.git

# 5. Use the command
todo
```

### Alternative: From source (for development)

```bash
git clone https://github.com/marcodiazz/terminal-todo.git
cd terminal-todo
pip install -e .
```

## Usage

Simply run:

```bash
todo
```

## Keyboard Shortcuts

- `a` - Add new task
- `t` - Create new tab
- `r` - Remove current tab
- `q` - Delete selected task
- `d` - Toggle dark/light theme
- `c` - Toggle compact mode
- `h/l` or `←/→` - Navigate between tabs
- `j/k` or `↑/↓` - Navigate between tasks
- `Space` - Toggle task completion
- `Esc` - Close modal or unfocus input

## Data Storage

Tasks are automatically saved to `~/.terminal-todo/data.json`

## License

MIT
