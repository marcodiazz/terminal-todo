# Terminal Todo

A beautiful, keyboard-driven terminal-based todo application built with [Textual](https://textual.textualize.io/).

## Features

- 📋 Multiple tabs for organizing tasks
- ✅ Mark tasks as complete/incomplete
- 🎨 Dark/Light theme toggle
- ⌨️ Vim-style keyboard navigation
- 💾 Persistent storage
- 🎯 Compact mode for cleaner view

## Installation

### From source (local)

```bash
git clone https://github.com/marcodiazz/terminal-todo.git
cd terminal-todo
pip install -e .
```

### From GitHub (direct install)

```bash
pip install git+https://github.com/marcodiazz/terminal-todo.git
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
