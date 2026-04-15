# Telegram Claude Code Bridge

This is a Python script used to remotely control Claude Code on a PC (Windows 10) via a Telegram Bot. It allows you to send prompts directly through Telegram to have Claude Code perform tasks in your local working directory, such as creating files, modifying code, and executing terminal commands.

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
* A Telegram Bot Token (obtained via @BotFather)

Install Python dependencies:

```bash
pip install "python-telegram-bot>=20.0"
