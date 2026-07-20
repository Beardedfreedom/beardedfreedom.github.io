---
name: rainboweffect
description: Apply rainbow text rendering to any text, output, code, or finding. Words (letter sequences) get one solid random rainbow color per word. Non-letter characters, symbols, numbers, and punctuation each get their own individual random color. Use whenever the user says /rainboweffect, asks to "rainbow this", "make it rainbow", or wants any content colorized with the rainbow effect. Always run the script and display the rendered output.
---

# Rainbow Effect

Transforms text so that:
- **Words** (contiguous letter sequences) → entire word rendered in one solid random rainbow hue
- **Everything else** (numbers, punctuation, symbols, special chars) → each character gets its own individual random color

## How to Run

Script: `~/.claude/skills/rainboweffect/scripts/rainbow.py`

```bash
# Pipe text in
echo "Your text here" | python3 ~/.claude/skills/rainboweffect/scripts/rainbow.py

# Multi-line content
cat somefile.txt | python3 ~/.claude/skills/rainboweffect/scripts/rainbow.py

# Pass as argument
python3 ~/.claude/skills/rainboweffect/scripts/rainbow.py "ATeUyiWeaRzOsFnZVF8vLz still present"
```

Uses ANSI 24-bit true-color escape codes. Renders in any modern terminal (macOS Terminal, iTerm2, VS Code terminal, Claude Code).

## Steps When Invoked

1. Identify the text to colorize (previous output, user-provided text, a file, a finding)
2. Run the script via Bash tool — pipe or pass the content
3. The terminal output IS the rainbow rendering — display it to the user
4. For long content, pipe through the script directly rather than truncating

## Color Logic

- 16-color rainbow palette: red → orange → amber → lime → cyan → blue → indigo → violet → magenta → pink
- Each word randomly picks one color from the palette (with ±20 RGB jitter so repeated words look distinct)
- Non-letter chars each independently pick a random palette color
- Spaces, newlines, tabs pass through unchanged (no color on whitespace)
