#!/usr/bin/env python3
"""
G25 Ancestry Telegram Bot (Enhanced Version)
"""

import os
import io
import sys
import logging
import numpy as np
import pandas as pd
import difflib
from pathlib import Path
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)

from nnls_script import run_nnls
from closest_script import run_closest
from pca_script import run_pca

# ============================================================
# CONFIG
# ============================================================

load_dotenv()

CONFIG = {
    "BOT_TOKEN": os.getenv("BOT_TOKEN"),
    "ANCIENT_REF_PATH": os.getenv("ANCIENT_REF_PATH"),
    "MODERN_REF_PATH": os.getenv("MODERN_REF_PATH"),
    "TEMP_DIR": Path(os.getenv("TEMP_DIR", "./temp")),
    "LOG_DIR": Path("./logs")
}

if not CONFIG["BOT_TOKEN"]:
    raise RuntimeError("BOT_TOKEN is missing")

CONFIG["TEMP_DIR"].mkdir(parents=True, exist_ok=True)
CONFIG["LOG_DIR"].mkdir(parents=True, exist_ok=True)

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(CONFIG["LOG_DIR"] / "bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("G25-BOT")

# ============================================================
# DATA LOADING
# ============================================================

def load_data():
    ancient = pd.read_csv(CONFIG["ANCIENT_REF_PATH"], index_col=0)
    modern = pd.read_csv(CONFIG["MODERN_REF_PATH"], index_col=0)

    ancient["Population"] = ancient.index.astype(str).str.split(":").str[0]

    ancient_avg = ancient.groupby("Population").mean()

    return ancient, ancient_avg, modern


ancient_df, ancient_avg, modern_df = load_data()
ANCIENT_POPS = sorted(ancient_avg.index.tolist())

# ============================================================
# HELPERS
# ============================================================

def suggest(name, pool, n=5):
    return difflib.get_close_matches(name, pool, n=n, cutoff=0.3)


def parse_csv(update):
    """Handles both paste + file upload safely"""
    if update.message.document:
        file = update.message.document.get_file()
        path = CONFIG["TEMP_DIR"] / f"{file.file_unique_id}.csv"
        file.download_to_drive(str(path))
        df = pd.read_csv(path, index_col=0)
        path.unlink(missing_ok=True)
    else:
        df = pd.read_csv(io.StringIO(update.message.text), index_col=0)

    return df


def add_history(context, entry):
    context.user_data.setdefault("history", []).append(entry)

# ============================================================
# START / HELP
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "G25 Ancestry Bot Ready.\n\n"
        "/nnls\n/closest\n/pca\n/search\n/compare\n/history"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "NNLS, PCA, closest population analysis using G25 datasets."
    )

# ============================================================
# NNLS (SIMPLIFIED CORE)
# ============================================================

async def nnls_start(update: Update, context):
    await update.message.reply_text("Paste or upload CSV:")
    return 0


async def nnls_process(update: Update, context):
    try:
        df = parse_csv(update)

        result_text, plots = run_nnls(df, ancient_df, save_plot=True)

        await update.message.reply_text(result_text[:4000])

        for p in plots:
            with open(p, "rb") as f:
                await update.message.reply_document(f)
            os.remove(p)

        add_history(context, {"type": "nnls", "n": len(df)})

    except Exception as e:
        logger.exception(e)
        await update.message.reply_text("NNLS failed.")

    return ConversationHandler.END

# ============================================================
# PCA
# ============================================================

async def pca_start(update, context):
    await update.message.reply_text("Paste or upload CSV:")
    return 0


async def pca_process(update, context):
    try:
        df = parse_csv(update)

        plot = run_pca(df, modern_df, save_plot=True)

        with open(plot, "rb") as f:
            await update.message.reply_document(f)

        os.remove(plot)

        add_history(context, {"type": "pca", "n": len(df)})

    except Exception as e:
        logger.exception(e)
        await update.message.reply_text("PCA failed.")

    return ConversationHandler.END

# ============================================================
# CLOSEST
# ============================================================

async def closest_start(update, context):
    await update.message.reply_text("Paste or upload CSV:")
    return 0


async def closest_process(update, context):
    try:
        df = parse_csv(update)

        text, plots = run_closest(df, modern_df, save_plot=True)

        await update.message.reply_text(text[:4000])

        for p in plots:
            with open(p, "rb") as f:
                await update.message.reply_document(f)
            os.remove(p)

        add_history(context, {"type": "closest", "n": len(df)})

    except Exception as e:
        logger.exception(e)
        await update.message.reply_text("Closest analysis failed.")

    return ConversationHandler.END

# ============================================================
# HISTORY
# ============================================================

async def history(update, context):
    hist = context.user_data.get("history", [])

    if not hist:
        await update.message.reply_text("No history yet.")
        return

    msg = "History:\n\n"
    for h in hist[-10:]:
        msg += f"{h}\n"

    await update.message.reply_text(msg)

# ============================================================
# MAIN
# ============================================================

def main():
    app = Application.builder().token(CONFIG["BOT_TOKEN"]).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("history", history))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("nnls", nnls_start)],
        states={0: [MessageHandler(filters.ALL, nnls_process)]},
        fallbacks=[]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("pca", pca_start)],
        states={0: [MessageHandler(filters.ALL, pca_process)]},
        fallbacks=[]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("closest", closest_start)],
        states={0: [MessageHandler(filters.ALL, closest_process)]},
        fallbacks=[]
    ))

    logger.info("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()#!/usr/bin/env python3
"""
G25 Ancestry Telegram Bot
Performs ancestry analysis using G25 datasets via Telegram
"""

import os
import io
import sys
import logging
import numpy as np
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
COMPARE_POP1, COMPARE_POP2 = range(8, 10)
SEARCH_INPUT, SEARCH_SELECT = range(10, 12)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def suggest_populations(user_input: str, populations: List[str], n: int = 5) -> List[str]:
    """Suggest population names based on user input"""
    return difflib.get_close_matches(user_input, populations, n=n, cutoff=0.3)

# ============================================================================
# POPULATION SEARCH & AVERAGING FUNCTIONS
# ============================================================================

def get_all_populations() -> Tuple[List[str], List[str]]:
    """Get lists of all ancient and modern populations"""
    # Ancient populations - extracted from index
    ancient_pops = list(set([name.split(':')[0] for name in ancient_df.index]))
    ancient_pops.sort()
    
    # Modern populations - all index values
    modern_pops = list(modern_df.index)
    modern_pops.sort()
    
    return ancient_pops, modern_pops

def search_population(user_input: str) -> dict:
    """
    Search for a population in both ancient and modern datasets.
    Returns a dictionary with search results from both datasets.
    """
    ancient_pops, modern_pops = get_all_populations()
    
    # Search in ancient populations
    ancient_matches = difflib.get_close_matches(user_input, ancient_pops, n=10, cutoff=0.3)
    
    # Search in modern populations
    modern_matches = difflib.get_close_matches(user_input, modern_pops, n=10, cutoff=0.3)
    
    return {
        'ancient': ancient_matches,
        'modern': modern_matches
    }

def get_population_average(population_name: str, dataset_type: str = 'ancient') -> Tuple[pd.DataFrame, dict]:
    """
    Calculate average PCA coordinates for a population.
    
    Args:
        population_name: Name of the population
        dataset_type: 'ancient' or 'modern'
    
    Returns:
        Tuple of (average_df, stats_dict)
    """
    if dataset_type == 'ancient':
        # Get all samples for this population
        pop_samples = ancient_df[ancient_df['Population'] == population_name].drop(columns=['Population'])
        if len(pop_samples) == 0:
            return None, None
        
        average = pop_samples.mean()
        stats = {
            'population': population_name,
            'dataset': 'Ancient',
            'sample_count': len(pop_samples),
            'pc_components': len(average)
        }
    else:  # modern
        # For modern populations, the population name is the index
        pop_samples = modern_df.loc[modern_df.index == population_name]
        if len(pop_samples) == 0:
            return None, None
        
        average = pop_samples.iloc[0]
        stats = {
            'population': population_name,
            'dataset': 'Modern',
            'sample_count': 1,
            'pc_components': len(average)
        }
    
    return pd.DataFrame([average], index=[population_name]), stats

def format_population_data(population_name: str, avg_df: pd.DataFrame, stats: dict) -> str:
    """Format population average data for display"""
    result = f"{'=' * 60}\n"
    result += f"POPULATION: {population_name} ({stats['dataset']})\n"
    result += f"{'=' * 60}\n"
    result += f"Samples: {stats['sample_count']}\n"
    result += f"PCA Components: {stats['pc_components']}\n"
    result += f"\nPCA COORDINATES:\n"
    result += "-" * 60 + "\n"
    
    # Display each PC component
    for i, col in enumerate(avg_df.columns, 1):
        value = avg_df.iloc[0, i-1]
        result += f"PC{i:2d}: {value:10.6f}\n"
    
    return result

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the current operation"""
    await update.message.reply_text("Operation cancelled.")
    logger.info(f"Operation cancelled by user {update.effective_user.id}")
    return ConversationHandler.END

# ============================================================================
# SEARCH POPULATION CONVERSATION
# ============================================================================

async def search_population_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start population search conversation"""
    await update.message.reply_text(
        "🔍 Search for ancient or modern population\n\n"
        "Type the population name you want to search (e.g., 'persian', 'albania', etc.):"
    )
    logger.info(f"User {update.effective_user.id} started population search")
    return SEARCH_INPUT

async def search_population_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process population search input"""
    user_input = update.message.text.strip()
    
    if not user_input:
        await update.message.reply_text("Please enter a population name:")
        return SEARCH_INPUT
    
    # Search for population
    results = search_population(user_input)
    all_matches = results['ancient'] + results['modern']
    
    if not all_matches:
        await update.message.reply_text(
            f"❌ No populations found matching '{user_input}'.\n\n"
            "Try with a different spelling or /cancel to exit."
        )
        logger.warning(f"No population matches for: {user_input}")
        return SEARCH_INPUT
    
    # Store results and show suggestions
    context.user_data['search_results'] = {
        'ancient': results['ancient'],
        'modern': results['modern'],
        'all': all_matches
    }
    
    text = f"✅ Found {len(all_matches)} population(s) matching '{user_input}':\n\n"
    
    if results['ancient']:
        text += "📜 ANCIENT POPULATIONS:\n"
        for i, pop in enumerate(results['ancient'], 1):
            text += f"{i}. {pop}\n"
    
    if results['modern']:
        start_idx = len(results['ancient']) + 1
        text += "\n🌍 MODERN POPULATIONS:\n"
        for i, pop in enumerate(results['modern'], 1):
            text += f"{start_idx + i - 1}. {pop}\n"
    
    text += "\nReply with the number to get detailed information:"
    await update.message.reply_text(text)
    return SEARCH_SELECT

async def search_population_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process population selection and display data"""
    try:
        choice = int(update.message.text) - 1
        all_matches = context.user_data['search_results']['all']
        
        if choice < 0 or choice >= len(all_matches):
            await update.message.reply_text(
                "Invalid selection. Please reply with a valid number:"
            )
            return SEARCH_SELECT
        
        selected_pop = all_matches[choice]
        
        # Determine which dataset the population is from
        results = context.user_data['search_results']
        if selected_pop in results['ancient']:
            avg_df, stats = get_population_average(selected_pop, 'ancient')
            dataset_type = 'ancient'
        else:
            avg_df, stats = get_population_average(selected_pop, 'modern')
            dataset_type = 'modern'
        
        if avg_df is None:
            await update.message.reply_text(f"Error: Could not retrieve data for {selected_pop}")
            return ConversationHandler.END
        
        # Format and send the data
        formatted_data = format_population_data(selected_pop, avg_df, stats)
        await update.message.reply_text(formatted_data)
        
        # Check if population exists in both datasets
        ancient_pops, modern_pops = get_all_populations()
        in_ancient = selected_pop in ancient_pops
        in_modern = selected_pop in modern_pops
        
        if in_ancient and in_modern:
            # Get data from other dataset
            other_type = 'modern' if dataset_type == 'ancient' else 'ancient'
            other_avg_df, other_stats = get_population_average(selected_pop, other_type)
            if other_avg_df is not None:
                other_data = format_population_data(selected_pop, other_avg_df, other_stats)
                await update.message.reply_text(f"\n⚠️ ALSO FOUND IN {other_type.upper()} DATA:\n\n{other_data}")
        
        # Store in history
        if 'user_history' not in context.user_data:
            context.user_data['user_history'] = []
        context.user_data['user_history'].append({
            'type': 'search',
            'population': selected_pop,
            'dataset': dataset_type,
            'timestamp': pd.Timestamp.now()
        })
        
        logger.info(f"Population search completed for {selected_pop}")
        
    except (ValueError, IndexError):
        await update.message.reply_text(
            "Invalid input. Please reply with the number of your choice:"
        )
        return SEARCH_SELECT
    except Exception as e:
        logger.error(f"Error in search_population_select: {e}")
        await update.message.reply_text(f"Error processing selection: {str(e)}")
    
    return ConversationHandler.END

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the /start command is issued"""
    welcome_message = """
Welcome to the G25 Ancestry Analysis Bot!

Available Analysis Commands:
/nnls - NNLS ancestry decomposition (ancient populations)
/closest - Find closest populations (ancient + modern)
/pca - PCA visualization (modern populations)
/search - Search for population data and averages
/nnls_suggest - Search ancient populations by name
/compare - Compare two populations
/population_stats - Show population statistics
/history - View your analysis history

Other Commands:
/help - Show detailed help
/cancel - Cancel current operation

Type /help to learn more about each feature.
"""
    await update.message.reply_text(welcome_message)
    logger.info(f"User {update.effective_user.id} started the bot")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send detailed help information"""
    help_text = """
ANALYSIS TOOLS

NNLS Analysis (/nnls)
Decomposes your sample ancestry using ancient populations
Input: CSV with PCA coordinates
Output: Text results + Pie chart

Closest Finder (/closest)
Finds populations most similar to your sample
Input: CSV with PCA coordinates
Output: Text results + Bar chart

PCA Visualization (/pca)
Projects your sample onto modern population PCA space
Input: CSV with PCA coordinates
Output: Scatter plot

Population Search (/search) ⭐ NEW
Search for ancient and modern populations by name
Get averaged PCA coordinates for any population
Shows data from both ancient and modern datasets
Example: /search → "persian" → select population

Population Suggestion (/nnls_suggest)
Search for ancient populations by name
Provides suggestions for similar names

Compare Populations (/compare)
Compare genetic distance between two populations
Shows detailed statistics and visualization

Population Statistics (/population_stats)
View summary statistics of available populations
Useful for understanding dataset composition

Analysis History (/history)
View your last 10 recent analyses
Helpful for tracking your research

DATA FORMAT:
CSV files should have populations/samples as rows and PCA components as columns
Example:
```
Sample,PC1,PC2,PC3,...
Sample1,0.1,0.2,0.3,...
Sample2,-0.1,0.3,0.1,...
```

TIPS:
- Use 'paste' to send CSV data directly
- Use 'upload' to send a CSV file
- /cancel stops the current operation
- Your analyses are saved for history
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
        await update.message.reply_text("Running NNLS analysis...")

        text_result, plot_files = run_nnls(target_df, ancient_df, save_plot=True)
        
        # Send results
        await update.message.reply_text(text_result[:4000])
        
        for plot_file in plot_files:
            if os.path.exists(plot_file):
                with open(plot_file, 'rb') as f:
                    await update.message.reply_document(f)
                os.remove(plot_file)
        
        # Store in history
        if 'user_history' not in context.user_data:
            context.user_data['user_history'] = []
        context.user_data['user_history'].append({
            'type': 'nnls',
            'population': selected_pop,
            'timestamp': pd.Timestamp.now()
        })
        
        logger.info(f"NNLS analysis completed for {selected_pop}")
    except Exception as e:
        logger.error(f"Error in NNLS analysis: {e}")
        await update.message.reply_text(f"Error during analysis: {str(e)}")
    
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

        await update.message.reply_text("Running NNLS analysis...")
        text_result, plot_files = run_nnls(context.user_data['target_df'], ancient_df, save_plot=True)
        
        await update.message.reply_text(text_result[:4000])
        for plot_file in plot_files:
            if os.path.exists(plot_file):
                with open(plot_file, 'rb') as f:
                    await update.message.reply_document(f)
                os.remove(plot_file)
        
        # Store in history
        if 'user_history' not in context.user_data:
            context.user_data['user_history'] = []
        context.user_data['user_history'].append({
            'type': 'nnls',
            'samples': len(context.user_data['target_df']),
            'timestamp': pd.Timestamp.now()
        })
        
        logger.info(f"NNLS analysis completed for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in NNLS target processing: {e}")
        await update.message.reply_text(f"Error processing data: {str(e)}")
    
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

        await update.message.reply_text("Finding closest populations...")
        text_result, plot_files = run_closest(context.user_data['sample_df'], both_df, save_plot=True)
        
        await update.message.reply_text(text_result[:4000])
        for plot_file in plot_files:
            if os.path.exists(plot_file):
                with open(plot_file, 'rb') as f:
                    await update.message.reply_document(f)
                os.remove(plot_file)
        
        # Store in history
        if 'user_history' not in context.user_data:
            context.user_data['user_history'] = []
        context.user_data['user_history'].append({
            'type': 'closest',
            'samples': len(context.user_data['sample_df']),
            'timestamp': pd.Timestamp.now()
        })
        
        logger.info(f"Closest finder analysis completed for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in closest sample processing: {e}")
        await update.message.reply_text(f"Error processing data: {str(e)}")
    
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

        await update.message.reply_text("Generating PCA visualization...")
        plot_file = run_pca(context.user_data['sample_df'], modern_df, save_plot=True)
        
        if plot_file and os.path.exists(plot_file):
            with open(plot_file, 'rb') as f:
                await update.message.reply_document(f)
            os.remove(plot_file)
        
        # Store in history
        if 'user_history' not in context.user_data:
            context.user_data['user_history'] = []
        context.user_data['user_history'].append({
            'type': 'pca',
            'samples': len(context.user_data['sample_df']),
            'timestamp': pd.Timestamp.now()
        })
        
        logger.info(f"PCA visualization completed for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in PCA sample processing: {e}")
        await update.message.reply_text(f"Error processing data: {str(e)}")
    
    return ConversationHandler.END

# ============================================================================
# POPULATION STATISTICS & COMPARISON
# ============================================================================

async def population_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show statistics about available populations"""
    try:
        stats_text = "POPULATION STATISTICS\n"
        stats_text += "=" * 50 + "\n\n"
        
        stats_text += f"ANCIENT POPULATIONS\n"
        stats_text += "-" * 30 + "\n"
        stats_text += f"Total populations: {len(ANCIENT_POPULATIONS)}\n"
        stats_text += f"Total ancient samples: {len(ancient_df)}\n"
        stats_text += f"PCA components: {len(ancient_df.columns) - 1 if 'Population' in ancient_df.columns else len(ancient_df.columns)}\n\n"
        
        # Show sample of populations
        stats_text += "Sample populations:\n"
        for pop in sorted(ANCIENT_POPULATIONS)[:10]:
            pop_count = len(ancient_df[ancient_df['Population'] == pop]) if 'Population' in ancient_df.columns else 1
            stats_text += f"  - {pop}: {pop_count} samples\n"
        
        if len(ANCIENT_POPULATIONS) > 10:
            stats_text += f"  ... and {len(ANCIENT_POPULATIONS) - 10} more\n\n"
        
        stats_text += f"\nMODERN POPULATIONS\n"
        stats_text += "-" * 30 + "\n"
        stats_text += f"Total modern samples: {len(modern_df)}\n"
        stats_text += f"PCA components: {len(modern_df.columns)}\n"
        
        await update.message.reply_text(stats_text)
        logger.info(f"User {update.effective_user.id} requested population statistics")
    except Exception as e:
        logger.error(f"Error in population_stats: {e}")
        await update.message.reply_text(f"Error retrieving statistics: {str(e)}")

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's analysis history"""
    try:
        if 'user_history' not in context.user_data or not context.user_data['user_history']:
            await update.message.reply_text("No analysis history yet. Start by running an analysis!")
            return
        
        history_list = context.user_data['user_history'][-10:]  # Last 10
        history_text = "YOUR ANALYSIS HISTORY (Last 10)\n"
        history_text += "=" * 50 + "\n\n"
        
        for i, entry in enumerate(reversed(history_list), 1):
            history_text += f"{i}. {entry['type'].upper()}\n"
            if 'population' in entry:
                history_text += f"   Population: {entry['population']}\n"
            if 'samples' in entry:
                history_text += f"   Samples: {entry['samples']}\n"
            history_text += f"   Time: {entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        await update.message.reply_text(history_text)
        logger.info(f"User {update.effective_user.id} viewed analysis history")
    except Exception as e:
        logger.error(f"Error in history: {e}")
        await update.message.reply_text(f"Error retrieving history: {str(e)}")

async def compare_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start population comparison"""
    await update.message.reply_text(
        "Compare two ancient populations.\n"
        "Enter the first population name (or /cancel to exit):"
    )
    logger.info(f"User {update.effective_user.id} started population comparison")
    return COMPARE_POP1

async def compare_pop1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get first population for comparison"""
    user_input = update.message.text
    suggestions = suggest_populations(user_input, ANCIENT_POPULATIONS, n=5)
    
    if not suggestions:
        await update.message.reply_text("No matches found. Try again with different spelling:")
        return COMPARE_POP1
    
    if len(suggestions) == 1:
        context.user_data['compare_pop1'] = suggestions[0]
        await update.message.reply_text(
            f"Selected: {suggestions[0]}\n\n"
            "Now enter the second population name:"
        )
        return COMPARE_POP2
    else:
        context.user_data['compare_suggestions'] = suggestions
        text = "Multiple matches found:\n"
        for i, pop in enumerate(suggestions, 1):
            text += f"{i}. {pop}\n"
        text += "\nReply with the number:"
        await update.message.reply_text(text)
        context.user_data['compare_stage'] = 'pop1_select'
        return COMPARE_POP1

async def compare_pop_select(update: Update, context: ContextTypes.DEFAULT_TYPE, stage: str) -> int:
    """Handle population selection"""
    try:
        choice = int(update.message.text) - 1
        suggestions = context.user_data.get('compare_suggestions', [])
        if choice < 0 or choice >= len(suggestions):
            raise ValueError("Invalid choice")
        selected = suggestions[choice]
        
        if stage == 'pop1_select':
            context.user_data['compare_pop1'] = selected
            await update.message.reply_text(
                f"Selected: {selected}\n\n"
                "Now enter the second population name:"
            )
            return COMPARE_POP2
        else:  # pop2_select
            context.user_data['compare_pop2'] = selected
            # Perform comparison
            return await perform_comparison(update, context)
    except (ValueError, IndexError):
        await update.message.reply_text("Invalid selection. Reply with the number:")
        return COMPARE_POP1 if stage == 'pop1_select' else COMPARE_POP2

async def compare_pop2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get second population for comparison"""
    user_input = update.message.text
    suggestions = suggest_populations(user_input, ANCIENT_POPULATIONS, n=5)
    
    if not suggestions:
        await update.message.reply_text("No matches found. Try again:")
        return COMPARE_POP2
    
    if len(suggestions) == 1:
        context.user_data['compare_pop2'] = suggestions[0]
        return await perform_comparison(update, context)
    else:
        context.user_data['compare_suggestions'] = suggestions
        context.user_data['compare_stage'] = 'pop2_select'
        text = "Multiple matches found:\n"
        for i, pop in enumerate(suggestions, 1):
            text += f"{i}. {pop}\n"
        text += "\nReply with the number:"
        await update.message.reply_text(text)
        return COMPARE_POP2

async def perform_comparison(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Perform and display population comparison"""
    try:
        pop1 = context.user_data.get('compare_pop1')
        pop2 = context.user_data.get('compare_pop2')
        
        if not pop1 or not pop2:
            await update.message.reply_text("Error: populations not selected properly")
            return ConversationHandler.END
        
        await update.message.reply_text("Comparing populations...")
        
        # Get population averages
        pop1_data = ancient_averages.loc[[pop1]]
        pop2_data = ancient_averages.loc[[pop2]]
        
        # Calculate Euclidean distance
        distance = np.sqrt(((pop1_data.values - pop2_data.values) ** 2).sum())
        
        # Create comparison report
        report = f"POPULATION COMPARISON\n"
        report += "=" * 50 + "\n"
        report += f"Population 1: {pop1}\n"
        report += f"Population 2: {pop2}\n"
        report += f"Genetic Distance: {distance:.4f}\n"
        report += f"Similarity: {'High' if distance < 0.1 else 'Moderate' if distance < 0.5 else 'Low'}\n"
        
        await update.message.reply_text(report)
        
        # Store in history
        if 'user_history' not in context.user_data:
            context.user_data['user_history'] = []
        context.user_data['user_history'].append({
            'type': 'compare',
            'pop1': pop1,
            'pop2': pop2,
            'distance': distance,
            'timestamp': pd.Timestamp.now()
        })
        
        logger.info(f"Comparison completed for {pop1} vs {pop2}")
    except Exception as e:
        logger.error(f"Error in population comparison: {e}")
        await update.message.reply_text(f"Error during comparison: {str(e)}")
    
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

    compare_conv = ConversationHandler(
        entry_points=[CommandHandler('compare', compare_start)],
        states={
            COMPARE_POP1: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, compare_pop1),
                MessageHandler(filters.Regex(r'^\d+$'), 
                    lambda u, c: compare_pop_select(u, c, 'pop1_select'))
            ],
            COMPARE_POP2: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, compare_pop2),
                MessageHandler(filters.Regex(r'^\d+$'),
                    lambda u, c: compare_pop_select(u, c, 'pop2_select'))
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    search_conv = ConversationHandler(
        entry_points=[CommandHandler('search', search_population_start)],
        states={
            SEARCH_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_population_input)],
            SEARCH_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_population_select)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Add command handlers
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('population_stats', population_stats))
    app.add_handler(CommandHandler('history', history))
    
    # Add conversation handlers
    app.add_handler(nnls_suggest_conv)
    app.add_handler(nnls_conv)
    app.add_handler(closest_conv)
    app.add_handler(pca_conv)
    app.add_handler(compare_conv)
    app.add_handler(search_conv)
    app.add_handler(CommandHandler('cancel', cancel))

    logger.info("Bot handlers registered successfully")
    logger.info("Bot started. Polling for messages...")
    
    app.run_polling()

if __name__ == "__main__":
    main()
