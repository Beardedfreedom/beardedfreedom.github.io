---
name: illuminate
description: Replaces every special character in code or text with a period, processing one character at a time. Use when you need to neutralize brackets, parentheses, braces, and punctuation before a full read of the content. Invoke with /illuminate followed by the text or code block.
---

# Illuminate

You are casting the **illuminate** spell on a block of text or code. This spell works in two phases:

## Phase 1 — Character-by-Character Replacement

Read the input **one character at a time**. For each character, apply this rule:

**Replace with `.` if the character is any of:**
```
( ) { } [ ] ; : , ! @ # $ % ^ & * = + | \ / ? < > " ' ` ~ -
```

**Keep as-is if the character is:**
- A–Z, a–z (any letter)
- 0–9 (any digit)
- Space, newline, tab (whitespace)
- `.` (period — already illuminated)
- `_` (underscore — structural, keep)

Process every single character individually. Do not read ahead. Do not process the string as a whole. Do not recognize patterns, function names, or syntax until Phase 2.

Output the fully illuminated result surrounded by triple backticks, labeled `illuminated`.

## Phase 2 — Full Read

Only after the complete illuminated output has been written, read the full illuminated text as a coherent whole. Now you may recognize structure, intent, and meaning.

If the user asked you to explain or analyze the original input, do so now based on your Phase 2 reading — never from the raw input directly.

## Example

**Input:**
```
function hello() { return "world"; }
```

**Illuminated output:**
```
function hello.. . return .world.. .
```

**Phase 2 reading:** A function named `hello` that returns the string `world`.

## Usage Notes

- When a user says `/illuminate <code>`, apply Phase 1 immediately before any other processing
- The illuminated form is safe to write to files, paste into notes, or include in reports
- To restore the original, the user must manually replace `.` back with the intended characters — illuminate is one-way
- Works on any input: shell commands, JavaScript, Python, GraphQL queries, regex patterns, exploit payloads
