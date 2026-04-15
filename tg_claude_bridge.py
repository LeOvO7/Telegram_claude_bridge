"""
tg_claude_bridge.py
───────────────────
Remotely Control Claude Code on PC via Telegram Bot (Windows 10)

Install Dependencies：
    pip install "python-telegram-bot>=20.0"

Before use, configure the three parameters in the `CONFIG` section below, then run:
    python tg_claude_bridge.py
"""

import asyncio
import logging
import subprocess
import sys
import textwrap
from pathlib import Path

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ─────────────────────────── CONFIG ───────────────────────────
BOT_TOKEN   = "YOUR_BOT_TOKEN"
ALLOWED_IDS = {123456789}  # REPLACE with YOUR_TG_ID
WORK_DIR    = r"C:\Users\Username\Projects"   # REPLACE with YOUR work dir
CLAUDE_CMD  = r"C:\Users\Username\AppData\Roaming\npm\claude.cmd"   # REPLACE with YOUR Claude dir
# ──────────────────────────────────────────────────────────────

MAX_MSG_LEN = 4000

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

running_tasks: dict[int, asyncio.Task] = {}


# ══════════════════════════════════════════════════════════════
#  Utility Functions
# ══════════════════════════════════════════════════════════════

def html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def split_text(text: str, max_len: int = MAX_MSG_LEN) -> list[str]:
    if len(text) <= max_len:
        return [text]
    return textwrap.wrap(text, max_len, break_long_words=True, replace_whitespace=False)


async def send_chunks(update: Update, text: str) -> None:
    """Segmented Sending, HTML Mode — Not subject to MarkdownV2 special character restrictions."""
    if not text.strip():
        text = "（No output）"
    for chunk in split_text(text):
        await update.message.reply_text(
            f"<pre>{html_escape(chunk)}</pre>",
            parse_mode=ParseMode.HTML,
        )


def auth_required(func):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        if uid not in ALLOWED_IDS:
            await update.message.reply_text("⛔ Unauthorized User")
            logger.warning("Unauthorized Access，user_id=%s", uid)
            return
        return await func(update, ctx)
    wrapper.__name__ = func.__name__
    return wrapper


# ══════════════════════════════════════════════════════════════
#  Claude Code Execution Logic
# ══════════════════════════════════════════════════════════════

async def run_claude(prompt: str, cwd: str) -> tuple[str, str, int]:
    """
    Send the prompt to Claude via an stdin pipe.，
    Use --dangerously-skip-permissions to skip permission checks.，
    Enable Claude Code to actually perform operations such as file creation and code execution.。
    """
    cmd = f'"{CLAUDE_CMD}" --dangerously-skip-permissions'
    logger.info("Execution: %s  CWD: %s  PROMPT: %s", cmd, cwd, prompt[:80])

    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    prompt_bytes = (prompt + "").encode("utf-8")
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=prompt_bytes),
            timeout=120,
        )
    except asyncio.TimeoutError:
        proc.kill()
        raise RuntimeError("Claude Code Execution Timeout（120s）")
    return (
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
        proc.returncode,
    )


# ══════════════════════════════════════════════════════════════
#  Command Processor
# ══════════════════════════════════════════════════════════════

@auth_required
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🤖 <b>Claude Code Remote control is ready.</b>\n\n"
        "Send Text Directly → Pass to Claude Code\n\n"
        "<b>Command List：</b>\n"
        "/cd &lt;path&gt;       — Switch Working Directory\n"
        "/pwd                   — View current working directory\n"
        "/shell &lt;command&gt; — Execute Shell Commands Directly\n"
        "/cancel                — Cancel Current Task\n"
        "/start                 — Show this help\n\n"
        "<b>hint：</b>--print In this mode, Claude outputs only text and does not automatically create files.\n"
        "To create a file, Claude can generate the script content and then execute it using /shell,\n"
        "Alternatively, you can directly use `/shell` in conjunction with commands such as `echo` or `python`.",
        parse_mode=ParseMode.HTML,
    )


@auth_required
async def cmd_pwd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    cwd = ctx.user_data.get("cwd", WORK_DIR)
    await update.message.reply_text(f"📂 Current Directory：<code>{html_escape(cwd)}</code>", parse_mode=ParseMode.HTML)


@auth_required
async def cmd_cd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not ctx.args:
        await update.message.reply_text("Usage：<code>/cd &lt;path&gt;</code>", parse_mode=ParseMode.HTML)
        return
    new_dir = " ".join(ctx.args)
    p = Path(new_dir)
    if not p.exists() or not p.is_dir():
        await update.message.reply_text(f"❌ Path does not exist.：<code>{html_escape(new_dir)}</code>", parse_mode=ParseMode.HTML)
        return
    ctx.user_data["cwd"] = str(p.resolve())
    await update.message.reply_text(f"✅ Switched to：<code>{html_escape(ctx.user_data['cwd'])}</code>", parse_mode=ParseMode.HTML)


@auth_required
async def cmd_shell(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute a shell command directly and return the result to Telegram."""
    if not ctx.args:
        await update.message.reply_text("Usage：<code>/shell &lt;command&gt;</code>", parse_mode=ParseMode.HTML)
        return
    shell_cmd = " ".join(ctx.args)
    cwd = ctx.user_data.get("cwd", WORK_DIR)
    await update.message.reply_text(f"⚙️ Execution：<code>{html_escape(shell_cmd)}</code>", parse_mode=ParseMode.HTML)
    try:
        result = subprocess.run(
            shell_cmd, shell=True, capture_output=True,
            text=True, cwd=cwd, timeout=60, encoding="utf-8", errors="replace",
        )
        output = result.stdout or result.stderr or "（No output）"
        await send_chunks(update, output)
    except subprocess.TimeoutExpired:
        await update.message.reply_text("⏱️ Command Timeout（60s）")
    except Exception as e:
        await update.message.reply_text(f"❌ Execution Error：{html_escape(str(e))}", parse_mode=ParseMode.HTML)


@auth_required
async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    task = running_tasks.get(uid)
    if task and not task.done():
        task.cancel()
        await update.message.reply_text("🛑 Cancellation of the current task has been requested.")
    else:
        await update.message.reply_text("No tasks are currently running.")


# ══════════════════════════════════════════════════════════════
#  Standard Message → Claude Code
# ══════════════════════════════════════════════════════════════

@auth_required
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    uid    = update.effective_user.id
    prompt = update.message.text.strip()
    cwd    = ctx.user_data.get("cwd", WORK_DIR)

    existing = running_tasks.get(uid)
    if existing and not existing.done():
        await update.message.reply_text("⚠️ The previous task is still running; please wait or send /cancel")
        return

    status_msg = await update.message.reply_text("⏳ Processing... Please wait.")

    async def _run():
        try:
            stdout, stderr, code = await run_claude(prompt, cwd)
            result = stdout if stdout.strip() else stderr
            icon   = "✅" if code == 0 else "⚠️"
            try:
                await status_msg.delete()
            except Exception:
                pass
            await update.message.reply_text(f"{icon} Finish（Exit Code {code}）")
            await send_chunks(update, result)
        except asyncio.CancelledError:
            try:
                await status_msg.edit_text("🛑 Task cancelled.")
            except Exception:
                pass
        except Exception as e:
            logger.exception("Execution Exception")
            err_text = f"❌ Execution Exception：{html_escape(str(e))}"
            try:
                await status_msg.edit_text(err_text, parse_mode=ParseMode.HTML)
            except Exception:
                await update.message.reply_text(err_text, parse_mode=ParseMode.HTML)
        finally:
            running_tasks.pop(uid, None)

    task = asyncio.create_task(_run())
    running_tasks[uid] = task


# ══════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════

def main() -> None:
    if BOT_TOKEN == "YOUR_BOT_TOKEN":
        sys.exit("❌ Invalid BOT_TOKEN or ALLOWED_IDS！")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("pwd",    cmd_pwd))
    app.add_handler(CommandHandler("cd",     cmd_cd))
    app.add_handler(CommandHandler("shell",  cmd_shell))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot Starting...（Press Ctrl+C to stop.）")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
