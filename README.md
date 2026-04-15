# Telegram Claude Code Bridge

This is a Python script used to remotely control Claude Code on a PC (Windows) via a Telegram Bot. It allows you to send prompts directly through Telegram to have Claude Code perform tasks in your local working directory, such as creating files, modifying code, and executing terminal commands.

## Features

* **Remote Control**: Interact with your local Claude Code from anywhere via Telegram.
* **Access Control**: Only authorized Telegram IDs in the whitelist can use the bot, preventing unauthorized access.
* **State Management**: Support for switching working directories (`/cd`) and viewing the current directory (`/pwd`).
* **Native Shell Support**: Execute local terminal commands directly using the `/shell` command.
* **Async & Chunked Handling**: Supports asynchronous task cancellation (`/cancel`) and automatically splits long outputs (over 4000 characters) with HTML escaping.

## Prerequisites

* Windows 10
* Python 3.8+
* Node.js and Claude Code installed globally
* A Telegram Bot Token 

Install Python dependencies:

```bash
pip install "python-telegram-bot>=20.0"
```


## Configuration
Before running the script, open tg_claude_bridge.py and modify the following parameters in the CONFIG section:

```Python
BOT_TOKEN = "YOUR_BOT_TOKEN"
ALLOWED_IDS = {123456789}
WORK_DIR = r"C:\Users\Username\Projects"
CLAUDE_CMD = r"C:\Users\Username\AppData\Roaming\npm\claude.cmd"
```
* BOT_TOKEN: Your Telegram Bot Token.
* ALLOWED_IDS: Your Telegram User ID (integer). Only this ID will be able to interact with the bot.
* WORK_DIR: The default initial working directory path.
* CLAUDE_CMD: The full absolute path to claude.cmd on your local system.

## Getting Started
Run the script using Python:

```Bash
python tg_claude_bridge.py
```

## Command List
The following commands are supported when interacting with the bot in Telegram:
* /start: Show the help message and available commands.
* /pwd: View the current local working directory.
* /cd <path>: Switch the working directory. Supports both absolute and relative paths.
* /shell <command>: Execute a Windows command line instruction directly in the current directory and return the result.
* /cancel: Cancel the currently running Claude Code task.
* Direct Text: Any text sent directly to the bot is treated as a prompt and passed to Claude Code for execution.

## Security & Operational Notes
* Unattended Execution: The script calls Claude Code with the --dangerously-skip-permissions flag. This means Claude will modify files or run commands without secondary confirmation.
* Timeout Control: Claude Code tasks have a default 120-second timeout, and /shell tasks have a 60-second timeout to prevent processes from hanging indefinitely.
* Error Handling: Standard output and standard error are captured separately, ensuring that both successful results and error stacks are returned to Telegram.
