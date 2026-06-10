#!/usr/bin/env python3
"""Telegram bot for G25 ancestry analysis."""

from __future__ import annotations

import io
import logging
import os
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from telegram import BotCommand, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from closest_script import get_ancient_populations, get_population_average, search_population
from closest_script import run_closest
from nnls_script import run_nnls
from pca_script import run_pca


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = Path(os.getenv("LOG_DIR", BASE_DIR / "logs"))
TEMP_DIR = Path(os.getenv("TEMP_DIR", BASE_DIR / "temp"))
ANCIENT_REF_PATH = Path(
    os.getenv("ANCIENT_REF_PATH", BASE_DIR / "Data" / "Global25_PCA_scaled (Ancient Individuals).csv")
)
MODERN_REF_PATH = Path(
    os.getenv("MODERN_REF_PATH", BASE_DIR / "Data" / "Global25_PCA_modern_scaled.csv")
)
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
BOT_TOKEN = os.getenv("BOT_TOKEN")

LOG_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("g25-bot")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Set it as an environment variable.")


def load_reference_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load reference datasets once on startup."""
    if not ANCIENT_REF_PATH.exists():
        raise FileNotFoundError(f"Ancient reference file not found: {ANCIENT_REF_PATH}")
    if not MODERN_REF_PATH.exists():
        raise FileNotFoundError(f"Modern reference file not found: {MODERN_REF_PATH}")

    ancient = pd.read_csv(ANCIENT_REF_PATH, index_col=0)
    modern = pd.read_csv(MODERN_REF_PATH, index_col=0)
    ancient["Population"] = ancient.index.astype(str).str.split(":").str[0]
    logger.info("Loaded %s ancient rows and %s modern rows", len(ancient), len(modern))
    return ancient, modern


ancient_df, modern_df = load_reference_data()
ANCIENT_POPULATIONS = get_ancient_populations(ancient_df)

ANALYSIS_INPUT, SEARCH_INPUT, SEARCH_SELECT, COMPARE_FIRST, COMPARE_SECOND = range(5)

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["/nnls", "/closest", "/pca"],
        ["/search", "/compare", "/population_stats"],
        ["/history", "/help", "/cancel"],
    ],
    resize_keyboard=True,
    input_field_placeholder="Choose a command",
)


def add_history(context: ContextTypes.DEFAULT_TYPE, entry: dict) -> None:
    history = context.user_data.setdefault("history", [])
    history.append({"time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), **entry})
    del history[:-10]


def numeric_reference_columns() -> list[str]:
    return modern_df.select_dtypes(include=[np.number]).columns.tolist()


async def send_long_message(update: Update, text: str) -> None:
    for start in range(0, len(text), 3900):
        await update.message.reply_text(text[start : start + 3900])


async def send_files(update: Update, paths: Iterable[str | Path]) -> None:
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            continue
        with path.open("rb") as file_obj:
            await update.message.reply_document(file_obj)
        path.unlink(missing_ok=True)


async def parse_csv(update: Update) -> pd.DataFrame:
    """Read a pasted CSV or uploaded CSV document."""
    message = update.message
    if message.document:
        document = message.document
        size_limit = MAX_FILE_SIZE_MB * 1024 * 1024
        if document.file_size and document.file_size > size_limit:
            raise ValueError(f"File is too large. Please upload a CSV under {MAX_FILE_SIZE_MB} MB.")
        if document.file_name and not document.file_name.lower().endswith(".csv"):
            raise ValueError("Please upload a .csv file.")

        telegram_file = await document.get_file()
        path = TEMP_DIR / f"{document.file_unique_id}.csv"
        await telegram_file.download_to_drive(str(path))
        try:
            df = pd.read_csv(path, index_col=0)
        finally:
            path.unlink(missing_ok=True)
    elif message.text:
        df = pd.read_csv(io.StringIO(message.text), index_col=0)
    else:
        raise ValueError("Please paste CSV text or upload a CSV file.")

    numeric = df.select_dtypes(include=[np.number])
    if numeric.empty:
        raise ValueError("I could not find numeric PCA columns in that CSV.")

    ref_cols = numeric_reference_columns()
    common_cols = [col for col in ref_cols if col in numeric.columns]
    if common_cols:
        numeric = numeric[common_cols]
    elif len(numeric.columns) != len(ref_cols):
        raise ValueError(
            f"Your CSV has {len(numeric.columns)} numeric columns, but the reference data expects {len(ref_cols)}."
        )

    return numeric.fillna(numeric.mean(numeric_only=True))


def format_nnls_results(results: dict) -> str:
    lines = ["NNLS ancestry estimate", ""]
    for sample_name, components in results.items():
        lines.append(str(sample_name))
        lines.append("-" * min(36, max(12, len(str(sample_name)))))
        if not components:
            lines.append("No component above the display threshold.")
        for population, coefficient in components.items():
            lines.append(f"{population:<28} {coefficient * 100:6.2f}%")
        lines.append("")
    return "\n".join(lines).strip()


def format_population_data(name: str, avg_df: pd.DataFrame, stats: dict) -> str:
    lines = [
        f"Population: {name}",
        f"Dataset: {stats['type'].title()}",
        f"Samples averaged: {stats['n']}",
        "",
        "PCA coordinates:",
    ]
    for index, value in enumerate(avg_df.iloc[0].tolist(), 1):
        lines.append(f"PC{index:02d}: {value:.6f}")
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Welcome to Eurogene G25 Bot.\n\n"
        "Send one of the commands below to analyze G25 coordinates, search populations, or compare references.",
        reply_markup=MAIN_KEYBOARD,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Commands\n"
        "/nnls - Estimate ancient ancestry components from a G25 CSV.\n"
        "/closest - Find genetically closest ancient and modern references.\n"
        "/pca - Create a PCA plot against modern references.\n"
        "/search - Search a population and get averaged coordinates.\n"
        "/compare - Compare two populations by Euclidean distance.\n"
        "/population_stats - Show dataset counts.\n"
        "/history - Show your last analyses.\n"
        "/cancel - Stop the current operation.\n\n"
        "CSV format: rows are samples, columns are G25 PCA coordinates. You can paste CSV text or upload a .csv file.",
        reply_markup=MAIN_KEYBOARD,
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("analysis", None)
    await update.message.reply_text("Cancelled. Choose another command when you are ready.", reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END


async def analysis_start(update: Update, context: ContextTypes.DEFAULT_TYPE, kind: str) -> int:
    context.user_data["analysis"] = kind
    labels = {
        "nnls": "NNLS ancestry estimate",
        "closest": "closest population search",
        "pca": "PCA plot",
    }
    await update.message.reply_text(
        f"Send your G25 CSV for {labels[kind]}.\n\n"
        "You can upload a .csv file or paste CSV text directly here.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ANALYSIS_INPUT


async def nnls_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await analysis_start(update, context, "nnls")


async def closest_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await analysis_start(update, context, "closest")


async def pca_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await analysis_start(update, context, "pca")


async def analysis_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    kind = context.user_data.get("analysis")
    try:
        df = await parse_csv(update)
        await update.message.reply_text("Got it. Running the analysis now...")

        if kind == "nnls":
            results, plots = run_nnls(df, ancient_df.drop(columns=["Population"], errors="ignore"), save_plot=True)
            await send_long_message(update, format_nnls_results(results))
            await send_files(update, plots)
        elif kind == "closest":
            text, plots = run_closest(df, ancient_df, modern_df, save_plot=True)
            await send_long_message(update, text)
            await send_files(update, plots)
        elif kind == "pca":
            plot = run_pca(df, modern_df, save_plot=True)
            await send_files(update, [plot])
        else:
            await update.message.reply_text("Please start with /nnls, /closest, or /pca.")
            return ConversationHandler.END

        add_history(context, {"type": kind, "samples": len(df)})
        await update.message.reply_text("Done. Choose another command any time.", reply_markup=MAIN_KEYBOARD)
    except Exception as exc:
        logger.exception("%s analysis failed", kind)
        await update.message.reply_text(f"I could not process that CSV: {exc}", reply_markup=MAIN_KEYBOARD)
    finally:
        context.user_data.pop("analysis", None)
    return ConversationHandler.END


async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Type a population name to search.\nExample: Persian, Albanian, Turkey_N",
        reply_markup=ReplyKeyboardRemove(),
    )
    return SEARCH_INPUT


async def search_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.message.text.strip()
    results = search_population(query, ancient_df, modern_df)
    matches = results["all"]
    if not matches:
        await update.message.reply_text("No close matches found. Try another spelling or use /cancel.")
        return SEARCH_INPUT

    context.user_data["search_matches"] = matches
    lines = [f"Matches for '{query}':", ""]
    for index, name in enumerate(matches, 1):
        dataset = "ancient" if name in results["ancient"] else "modern"
        lines.append(f"{index}. {name} ({dataset})")
    lines.append("")
    lines.append("Reply with a number to view coordinates.")
    await update.message.reply_text("\n".join(lines))
    return SEARCH_SELECT


async def search_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        selected = context.user_data["search_matches"][int(update.message.text.strip()) - 1]
    except (KeyError, ValueError, IndexError):
        await update.message.reply_text("Please reply with one of the listed numbers.")
        return SEARCH_SELECT

    avg_df, stats = get_population_average(selected, ancient_df, modern_df)
    if avg_df is None:
        await update.message.reply_text("I found the name but could not load its coordinates.", reply_markup=MAIN_KEYBOARD)
        return ConversationHandler.END

    await send_long_message(update, format_population_data(selected, avg_df, stats))
    add_history(context, {"type": "search", "population": selected})
    await update.message.reply_text("Search complete.", reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END


async def compare_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Type the first population name.", reply_markup=ReplyKeyboardRemove())
    return COMPARE_FIRST


async def compare_first(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["compare_first"] = update.message.text.strip()
    await update.message.reply_text("Now type the second population name.")
    return COMPARE_SECOND


def resolve_population(name: str) -> str | None:
    results = search_population(name, ancient_df, modern_df, max_results=1)
    return results["all"][0] if results["all"] else None


async def compare_second(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    first_query = context.user_data.get("compare_first", "")
    second_query = update.message.text.strip()
    first = resolve_population(first_query)
    second = resolve_population(second_query)

    if not first or not second:
        await update.message.reply_text(
            "I could not confidently match one of those populations. Try /compare again with a different spelling.",
            reply_markup=MAIN_KEYBOARD,
        )
        return ConversationHandler.END

    first_df, first_stats = get_population_average(first, ancient_df, modern_df)
    second_df, second_stats = get_population_average(second, ancient_df, modern_df)
    common_cols = first_df.columns.intersection(second_df.columns)
    distance = float(np.linalg.norm(first_df[common_cols].iloc[0] - second_df[common_cols].iloc[0]))

    await update.message.reply_text(
        f"Population comparison\n\n"
        f"1. {first} ({first_stats['type']}, n={first_stats['n']})\n"
        f"2. {second} ({second_stats['type']}, n={second_stats['n']})\n\n"
        f"Euclidean distance: {distance:.6f}",
        reply_markup=MAIN_KEYBOARD,
    )
    add_history(context, {"type": "compare", "populations": f"{first} vs {second}"})
    return ConversationHandler.END


async def population_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    modern_pops = modern_df.index.astype(str).str.split(":").str[0].nunique()
    await update.message.reply_text(
        "Dataset stats\n\n"
        f"Ancient samples: {len(ancient_df)}\n"
        f"Ancient populations: {len(ANCIENT_POPULATIONS)}\n"
        f"Modern samples: {len(modern_df)}\n"
        f"Modern populations: {modern_pops}\n"
        f"PCA columns: {len(numeric_reference_columns())}",
        reply_markup=MAIN_KEYBOARD,
    )


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    items = context.user_data.get("history", [])
    if not items:
        await update.message.reply_text("No history yet.", reply_markup=MAIN_KEYBOARD)
        return
    lines = ["Recent activity", ""]
    for item in items:
        detail = item.get("population") or item.get("populations") or f"{item.get('samples', '?')} sample(s)"
        lines.append(f"{item['time']} - {item['type']}: {detail}")
    await update.message.reply_text("\n".join(lines), reply_markup=MAIN_KEYBOARD)


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Choose a command from the menu or type /help.", reply_markup=MAIN_KEYBOARD)


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Open the bot menu"),
            BotCommand("help", "Show help and CSV format"),
            BotCommand("nnls", "Run NNLS ancestry estimate"),
            BotCommand("closest", "Find closest populations"),
            BotCommand("pca", "Create a PCA plot"),
            BotCommand("search", "Search population coordinates"),
            BotCommand("compare", "Compare two populations"),
            BotCommand("population_stats", "Show dataset stats"),
            BotCommand("history", "Show recent activity"),
            BotCommand("cancel", "Cancel current operation"),
        ]
    )


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    analysis_conv = ConversationHandler(
        entry_points=[
            CommandHandler("nnls", nnls_start),
            CommandHandler("closest", closest_start),
            CommandHandler("pca", pca_start),
        ],
        states={ANALYSIS_INPUT: [MessageHandler(filters.Document.ALL | (filters.TEXT & ~filters.COMMAND), analysis_process)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    search_conv = ConversationHandler(
        entry_points=[CommandHandler("search", search_start)],
        states={
            SEARCH_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_input)],
            SEARCH_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_select)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    compare_conv = ConversationHandler(
        entry_points=[CommandHandler("compare", compare_start)],
        states={
            COMPARE_FIRST: [MessageHandler(filters.TEXT & ~filters.COMMAND, compare_first)],
            COMPARE_SECOND: [MessageHandler(filters.TEXT & ~filters.COMMAND, compare_second)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("population_stats", population_stats))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(analysis_conv)
    app.add_handler(search_conv)
    app.add_handler(compare_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    logger.info("Bot is running with polling")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
