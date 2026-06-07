#!/usr/bin/env python3
"""
G25 Ancestry Telegram Bot
Performs ancestry analysis using G25 datasets via Telegram
"""

import os
import io
import sys
import logging
from pathlib import Path
from typing import Tuple, List
import pandas as pd
import difflib
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)

# Import analysis scripts
from nnls_script import run_nnls
from closest_script import run_closest
from pca_script import run_pca

# ============================================================================
# CONFIGURATION & LOGGING
# ============================================================================

# Load environment variables
load_dotenv()

# Configure logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log') if os.path.exists('logs') or os.makedirs('logs', exist_ok=True) else logging.NullHandler(),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    'BOT_TOKEN': os.environ.get("BOT_TOKEN"),
    'ANCIENT_REF_PATH': os.environ.get("ANCIENT_REF_PATH", "/Data/Global25_PCA_scaled (Ancient Individuals).csv"),
    'MODERN_REF_PATH': os.environ.get("MODERN_REF_PATH", "/Data/Global25_PCA_modern_scaled.csv"),
    'TEMP_DIR': os.environ.get("TEMP_DIR", "./temp"),
}

# Validate configuration
if not CONFIG['BOT_TOKEN']:
    logger.error("BOT_TOKEN environment variable is not set")
    sys.exit(1)

# Create temp and logs directories
Path(CONFIG['TEMP_DIR']).mkdir(parents=True, exist_ok=True)
Path('logs').mkdir(parents=True, exist_ok=True)

logger.info("Configuration loaded successfully")
logger.info(f"Ancient reference path: {CONFIG['ANCIENT_REF_PATH']}")
logger.info(f"Modern reference path: {CONFIG['MODERN_REF_PATH']}")

# ============================================================================
# DATA LOADING & VALIDATION
# ============================================================================

def load_reference_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, List[str]]:
    """Load and validate reference datasets"""
    try:
        logger.info("Loading reference datasets...")
        
        ancient_df = pd.read_csv(CONFIG['ANCIENT_REF_PATH'], index_col=0)
        modern_df = pd.read_csv(CONFIG['MODERN_REF_PATH'], index_col=0)
        
        logger.info(f"Loaded {len(ancient_df)} ancient samples and {len(modern_df)} modern samples")
        
        # Process ancient data
        ancient_df['Population'] = ancient_df.index.to_series().apply(lambda x: x.split(':')[0])
        ancient_averages = ancient_df.groupby('Population').mean()
        ancient_populations = list(ancient_averages.index)
        
        # Combine for closest finder
        both_df = pd.concat([ancient_df.drop(columns=['Population'], errors='ignore'), modern_df])
        both_df = both_df[~both_df.index.duplicated(keep='first')]
        
        logger.info(f"Identified {len(ancient_populations)} ancient populations")
        logger.info("Reference data loaded successfully")
        
        return ancient_df, ancient_averages, both_df, ancient_populations
        
    except FileNotFoundError as e:
        logger.error(f"Reference file not found: {e}")
        logger.error("Make sure Data files are mounted correctly in Docker")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error loading reference data: {e}")
        sys.exit(1)

# Load data at startup
try:
    ancient_df, ancient_averages, both_df, ANCIENT_POPULATIONS = load_reference_data()
    modern_df = pd.read_csv(CONFIG['MODERN_REF_PATH'], index_col=0)
except Exception as e:
    logger.error(f"Failed to load reference data: {e}")
    sys.exit(1)

# ============================================================================
# CONVERSATION STATES
# ============================================================================

NNLS_INPUT, NNLS_SELECT = range(2)
NNLS_CHOICE, NNLS_TARGET = range(2, 4)
CLOSE_CHOICE, CLOSE_SAMPLE = range(4, 6)
PCA_CHOICE, PCA_SAMPLE = range(6, 8)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def suggest_populations(user_input: str, populations: List[str], n: int = 5) -> List[str]:
    """Suggest population names based on user input"""
    return difflib.get_close_matches(user_input, populations, n=n, cutoff=0.3)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current operation"""
    await update.message.reply_text("Operation cancelled.")
    logger.info(f"Operation cancelled by user {update.effective_user.id}")
    return ConversationHandler.END

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the /start command is issued"""
    welcome_message = """
Welcome to the G25 Ancestry Analysis Bot! 🧬

Available commands:
/nnls - NNLS ancestry decomposition (ancient populations)
/closest - Find closest populations (ancient + modern)
/pca - PCA visualization (modern populations)
/nnls_suggest - Search ancient populations by name
/help - Show detailed help
/cancel - Cancel current operation
"""
    await update.message.reply_text(welcome_message)
    logger.info(f"User {update.effective_user.id} started the bot")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send detailed help information"""
    help_text = """
📊 **NNLS Analysis** (/nnls)
Decomposes your sample ancestry using ancient populations
Input: CSV with PCA coordinates
Output: Text results + Pie chart

🔍 **Closest Finder** (/closest)
Finds populations most similar to your sample
Input: CSV with PCA coordinates
Output: Text results + Bar chart

📈 **PCA Visualization** (/pca)
Projects your sample onto modern population PCA space
Input: CSV with PCA coordinates
Output: Scatter plot

🏛️ **Population Search** (/nnls_suggest)
Search for ancient populations by name
Provides suggestions for similar names

📝 **Data Format**:
CSV files should have populations/samples as rows and PCA components as columns
Example:
```
Sample,PC1,PC2,PC3,...
Sample1,0.1,0.2,0.3,...
Sample2,-0.1,0.3,0.1,...
```
"""
    await update.message.reply_text(help_text)
    logger.info(f"User {update.effective_user.id} requested help")

# ============================================================================
# NNLS_SUGGEST CONVERSATION
# ============================================================================

async def nnls_suggest_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start NNLS suggest conversation"""
    await update.message.reply_text(
        "Type the population name you want to analyze (e.g., 'Turkey_N'):"
    )
    logger.info(f"User {update.effective_user.id} started NNLS suggest")
    return NNLS_INPUT

async def nnls_suggest_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process population search input"""
    user_input = update.message.text
    suggestions = suggest_populations(user_input, ANCIENT_POPULATIONS, n=5)
    
    if not suggestions:
        await update.message.reply_text(
            "No close matches found. Please try again or see /help for population list."
        )
        logger.warning(f"No population matches for: {user_input}")
        return NNLS_INPUT

    context.user_data['suggestions'] = suggestions
    text = "Did you mean one of these?\n"
    for i, pop in enumerate(suggestions, 1):
        text += f"{i}. {pop}\n"
    text += "\nReply with the number."
    await update.message.reply_text(text)
    return NNLS_SELECT

async def nnls_suggest_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process population selection"""
    try:
        choice = int(update.message.text) - 1
        suggestions = context.user_data['suggestions']
        if choice < 0 or choice >= len(suggestions):
            raise ValueError("Invalid choice")
        selected_pop = suggestions[choice]
    except (ValueError, IndexError):
        await update.message.reply_text("Invalid selection. Reply with the number.")
        return NNLS_SELECT

    try:
        target_df = ancient_averages.loc[[selected_pop]]
        await update.message.reply_text("⏳ Running NNLS analysis...")

        text_result, plot_files = run_nnls(target_df, ancient_df, save_plot=True)
        
        # Send results
        await update.message.reply_text(text_result[:4000])
        
        for plot_file in plot_files:
            if os.path.exists(plot_file):
                with open(plot_file, 'rb') as f:
                    await update.message.reply_document(f)
                os.remove(plot_file)
        
        logger.info(f"NNLS analysis completed for {selected_pop}")
    except Exception as e:
        logger.error(f"Error in NNLS analysis: {e}")
        await update.message.reply_text(f"❌ Error during analysis: {str(e)}")
    
    return ConversationHandler.END

# ============================================================================
# NNLS CONVERSATION
# ============================================================================

async def nnls_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start NNLS conversation"""
    await update.message.reply_text(
        "NNLS ancestry analysis (ancient populations).\n"
        "Reply with 'paste' to paste CSV data or 'upload' to upload a file."
    )
    logger.info(f"User {update.effective_user.id} started NNLS")
    return NNLS_CHOICE

async def nnls_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get NNLS input method choice"""
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

async def nnls_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process NNLS target data"""
    try:
        choice = context.user_data['nnls_choice']
        if choice == 'paste':
            csv_text = update.message.text
            context.user_data['target_df'] = pd.read_csv(io.StringIO(csv_text), index_col=0)
        else:
            file = await update.message.document.get_file()
            path = os.path.join(CONFIG['TEMP_DIR'], f"{file.file_unique_id}_target.csv")
            await file.download_to_drive(path)
            context.user_data['target_df'] = pd.read_csv(path, index_col=0)
            os.remove(path)

        await update.message.reply_text("⏳ Running NNLS analysis...")
        text_result, plot_files = run_nnls(context.user_data['target_df'], ancient_df, save_plot=True)
        
        await update.message.reply_text(text_result[:4000])
        for plot_file in plot_files:
            if os.path.exists(plot_file):
                with open(plot_file, 'rb') as f:
                    await update.message.reply_document(f)
                os.remove(plot_file)
        
        logger.info(f"NNLS analysis completed for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in NNLS target processing: {e}")
        await update.message.reply_text(f"❌ Error processing data: {str(e)}")
    
    return ConversationHandler.END

# ============================================================================
# CLOSEST CONVERSATION
# ============================================================================

async def closest_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start closest finder conversation"""
    await update.message.reply_text(
        "Closest population analysis (ancient + modern).\n"
        "Reply with 'paste' to paste CSV data or 'upload' to upload a file."
    )
    logger.info(f"User {update.effective_user.id} started closest finder")
    return CLOSE_CHOICE

async def closest_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get closest input method choice"""
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

async def closest_sample(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process closest finder data"""
    try:
        choice = context.user_data['closest_choice']
        if choice == 'paste':
            csv_text = update.message.text
            context.user_data['sample_df'] = pd.read_csv(io.StringIO(csv_text), index_col=0)
        else:
            file = await update.message.document.get_file()
            path = os.path.join(CONFIG['TEMP_DIR'], f"{file.file_unique_id}_sample.csv")
            await file.download_to_drive(path)
            context.user_data['sample_df'] = pd.read_csv(path, index_col=0)
            os.remove(path)

        await update.message.reply_text("⏳ Finding closest populations...")
        text_result, plot_files = run_closest(context.user_data['sample_df'], both_df, save_plot=True)
        
        await update.message.reply_text(text_result[:4000])
        for plot_file in plot_files:
            if os.path.exists(plot_file):
                with open(plot_file, 'rb') as f:
                    await update.message.reply_document(f)
                os.remove(plot_file)
        
        logger.info(f"Closest finder analysis completed for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in closest sample processing: {e}")
        await update.message.reply_text(f"❌ Error processing data: {str(e)}")
    
    return ConversationHandler.END

# ============================================================================
# PCA CONVERSATION
# ============================================================================

async def pca_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start PCA conversation"""
    await update.message.reply_text(
        "PCA visualization (modern populations only).\n"
        "Reply with 'paste' to paste CSV data or 'upload' to upload a file."
    )
    logger.info(f"User {update.effective_user.id} started PCA")
    return PCA_CHOICE

async def pca_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get PCA input method choice"""
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

async def pca_sample(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process PCA data"""
    try:
        choice = context.user_data['pca_choice']
        if choice == 'paste':
            csv_text = update.message.text
            context.user_data['sample_df'] = pd.read_csv(io.StringIO(csv_text), index_col=0)
        else:
            file = await update.message.document.get_file()
            path = os.path.join(CONFIG['TEMP_DIR'], f"{file.file_unique_id}_sample.csv")
            await file.download_to_drive(path)
            context.user_data['sample_df'] = pd.read_csv(path, index_col=0)
            os.remove(path)

        await update.message.reply_text("⏳ Generating PCA visualization...")
        plot_file = run_pca(context.user_data['sample_df'], modern_df, save_plot=True)
        
        if plot_file and os.path.exists(plot_file):
            with open(plot_file, 'rb') as f:
                await update.message.reply_document(f)
            os.remove(plot_file)
        
        logger.info(f"PCA visualization completed for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in PCA sample processing: {e}")
        await update.message.reply_text(f"❌ Error processing data: {str(e)}")
    
    return ConversationHandler.END

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Start the bot"""
    logger.info("Starting G25 Ancestry Telegram Bot")
    
    app = Application.builder().token(CONFIG['BOT_TOKEN']).build()

    # Conversation handlers
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

    # Add command handlers
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_command))
    
    # Add conversation handlers
    app.add_handler(nnls_suggest_conv)
    app.add_handler(nnls_conv)
    app.add_handler(closest_conv)
    app.add_handler(pca_conv)
    app.add_handler(CommandHandler('cancel', cancel))

    logger.info("Bot handlers registered successfully")
    logger.info("Bot started. Polling for messages...")
    
    app.run_polling()

if __name__ == "__main__":
    main()
