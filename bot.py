# bot.py
import os
import io
import pandas as pd
import difflib
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)
from nnls_script import run_nnls  # Your NNLS functions
from closest_script import run_closest  # Your closest finder functions
from pca_script import run_pca  # Your PCA functions

# ---------------- Bot Token ----------------
TOKEN = os.environ.get("BOT_TOKEN")  # Set this in Railway environment

# ---------------- Reference Data ----------------
ANCIENT_REF_PATH = "/Data/Global25_PCA_scaled (Ancient Individuals).csv"
MODERN_REF_PATH  = "/Data/Global25_PCA_scaled (Modern Populations).csv"

# Load references
ancient_df = pd.read_csv(ANCIENT_REF_PATH, index_col=0)
modern_df  = pd.read_csv(MODERN_REF_PATH, index_col=0)

# NNLS uses ancient_df only
ancient_df['Population'] = ancient_df.index.to_series().apply(lambda x: x.split(':')[0])
ancient_averages = ancient_df.groupby('Population').mean()
ANCIENT_POPULATIONS = list(ancient_averages.index)

# Closest finder uses BOTH: dynamically combine
both_df = pd.concat([ancient_df.drop(columns=['Population'], errors='ignore'), modern_df])
both_df = both_df[~both_df.index.duplicated(keep='first')]

# ---------------- Conversation States ----------------
NNLS_INPUT, NNLS_SELECT = range(2)
NNLS_CHOICE, NNLS_TARGET = range(2,4)
CLOSE_CHOICE, CLOSE_SAMPLE = range(4,6)
PCA_CHOICE, PCA_SAMPLE = range(6,8)

# ---------------- Helper Functions ----------------
def suggest_populations(user_input, populations, n=5):
    return difflib.get_close_matches(user_input, populations, n=n, cutoff=0.3)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

# ---------------- /nnls_suggest ----------------
async def nnls_suggest_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Type the population name you want to analyze (e.g., 'Turkey_N'):"
    )
    return NNLS_INPUT

async def nnls_suggest_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    suggestions = suggest_populations(user_input, ANCIENT_POPULATIONS, n=5)
    if not suggestions:
        await update.message.reply_text("No close matches found. Please try again.")
        return NNLS_INPUT

    context.user_data['suggestions'] = suggestions
    text = "Did you mean one of these?\n"
    for i, pop in enumerate(suggestions, 1):
        text += f"{i}. {pop}\n"
    text += "Reply with the number."
    await update.message.reply_text(text)
    return NNLS_SELECT

async def nnls_suggest_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        choice = int(update.message.text) - 1
        suggestions = context.user_data['suggestions']
        selected_pop = suggestions[choice]
    except (ValueError, IndexError):
        await update.message.reply_text("Invalid selection. Reply with the number.")
        return NNLS_SELECT

    target_df = ancient_averages.loc[[selected_pop]]

    # Run NNLS
    text_result, plot_files = run_nnls(target_df, ancient_df, save_plot=True)

    await update.message.reply_text(text_result[:4000])
    for plot_file in plot_files:
        with open(plot_file,'rb') as f:
            await update.message.reply_document(f)
        os.remove(plot_file)

    return ConversationHandler.END

# ---------------- /nnls ----------------
async def nnls_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "NNLS ancestry analysis (ancient populations).\nReply with 'paste' to paste CSV data or 'upload' to upload a file."
    )
    return NNLS_CHOICE

async def nnls_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.lower()
    context.user_data['nnls_choice'] = choice
    if choice == 'paste':
        await update.message.reply_text("Paste your TARGET CSV data:")
        return NNLS_TARGET
    elif choice == 'upload':
        await update.message.reply_text("Upload your TARGET CSV file:")
        return NNLS_TARGET
    else:
        await update.message.reply_text("Please reply with 'paste' or 'upload'.")
        return NNLS_CHOICE

async def nnls_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = context.user_data['nnls_choice']
    if choice == 'paste':
        csv_text = update.message.text
        context.user_data['target_df'] = pd.read_csv(io.StringIO(csv_text), index_col=0)
    else:
        file = await update.message.document.get_file()
        path = f"{file.file_unique_id}_target.csv"
        await file.download_to_drive(path)
        context.user_data['target_df'] = pd.read_csv(path, index_col=0)
        os.remove(path)

    text_result, plot_files = run_nnls(context.user_data['target_df'], ancient_df, save_plot=True)
    await update.message.reply_text(text_result[:4000])
    for plot_file in plot_files:
        with open(plot_file,'rb') as f:
            await update.message.reply_document(f)
        os.remove(plot_file)
    return ConversationHandler.END

# ---------------- /closest ----------------
async def closest_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Closest population analysis (ancient + modern).\nReply with 'paste' to paste CSV data or 'upload' to upload a file."
    )
    return CLOSE_CHOICE

async def closest_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.lower()
    context.user_data['closest_choice'] = choice
    if choice == 'paste':
        await update.message.reply_text("Paste your SAMPLE CSV data:")
        return CLOSE_SAMPLE
    elif choice == 'upload':
        await update.message.reply_text("Upload your SAMPLE CSV file:")
        return CLOSE_SAMPLE
    else:
        await update.message.reply_text("Please reply with 'paste' or 'upload'.")
        return CLOSE_CHOICE

async def closest_sample(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = context.user_data['closest_choice']
    if choice == 'paste':
        csv_text = update.message.text
        context.user_data['sample_df'] = pd.read_csv(io.StringIO(csv_text), index_col=0)
    else:
        file = await update.message.document.get_file()
        path = f"{file.file_unique_id}_sample.csv"
        await file.download_to_drive(path)
        context.user_data['sample_df'] = pd.read_csv(path, index_col=0)
        os.remove(path)

    text_result, plot_files = run_closest(context.user_data['sample_df'], both_df, save_plot=True)
    await update.message.reply_text(text_result[:4000])
    for plot_file in plot_files:
        with open(plot_file,'rb') as f:
            await update.message.reply_document(f)
        os.remove(plot_file)
    return ConversationHandler.END

# ---------------- /pca ----------------
async def pca_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "PCA visualization (modern populations only).\nReply with 'paste' to paste CSV data or 'upload' to upload a file."
    )
    return PCA_CHOICE

async def pca_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.lower()
    context.user_data['pca_choice'] = choice
    if choice == 'paste':
        await update.message.reply_text("Paste your SAMPLE CSV data:")
        return PCA_SAMPLE
    elif choice == 'upload':
        await update.message.reply_text("Upload your SAMPLE CSV file:")
        return PCA_SAMPLE
    else:
        await update.message.reply_text("Please reply with 'paste' or 'upload'.")
        return PCA_CHOICE

async def pca_sample(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = context.user_data['pca_choice']
    if choice == 'paste':
        csv_text = update.message.text
        context.user_data['sample_df'] = pd.read_csv(io.StringIO(csv_text), index_col=0)
    else:
        file = await update.message.document.get_file()
        path = f"{file.file_unique_id}_sample.csv"
        await file.download_to_drive(path)
        context.user_data['sample_df'] = pd.read_csv(path, index_col=0)
        os.remove(path)

    plot_file = run_pca(context.user_data['sample_df'], modern_df, save_plot=True)
    with open(plot_file,'rb') as f:
        await update.message.reply_document(f)
    os.remove(plot_file)
    return ConversationHandler.END

# ---------------- Main ----------------
def main():
    app = Application.builder().token(TOKEN).build()

    # Handlers
    nnls_suggest_conv = ConversationHandler(
        entry_points=[CommandHandler('nnls_suggest', nnls_suggest_start)],
        states={
            NNLS_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, nnls_suggest_input)],
            NNLS_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, nnls_suggest_select)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    nnls_conv = ConversationHandler(
        entry_points=[CommandHandler('nnls', nnls_start)],
        states={
            NNLS_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, nnls_choice)],
            NNLS_TARGET: [MessageHandler(filters.TEXT | filters.Document.ALL, nnls_target)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    closest_conv = ConversationHandler(
        entry_points=[CommandHandler('closest', closest_start)],
        states={
            CLOSE_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, closest_choice)],
            CLOSE_SAMPLE: [MessageHandler(filters.TEXT | filters.Document.ALL, closest_sample)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    pca_conv = ConversationHandler(
        entry_points=[CommandHandler('pca', pca_start)],
        states={
            PCA_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, pca_choice)],
            PCA_SAMPLE: [MessageHandler(filters.TEXT | filters.Document.ALL, pca_sample)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Add handlers
    app.add_handler(nnls_suggest_conv)
    app.add_handler(nnls_conv)
    app.add_handler(closest_conv)
    app.add_handler(pca_conv)
    app.add_handler(CommandHandler('cancel', cancel))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
