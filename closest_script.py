import difflib
import numpy as np
import pandas as pd


# ============================================================
# CLEAN POPULATION EXTRACTION
# ============================================================

def get_ancient_populations(ancient_df: pd.DataFrame):
    """
    Extract clean ancient population names.
    """
    if "Population" not in ancient_df.columns:
        ancient_df["Population"] = ancient_df.index.astype(str).str.split(":").str[0]

    return sorted(ancient_df["Population"].dropna().unique().tolist())


def get_modern_populations(modern_df: pd.DataFrame):
    """
    Extract clean modern population names.
    Fixes issues like 'Serbian:729' -> 'Serbian'
    """
    return sorted(
        modern_df.index.astype(str)
        .str.split(":")
        .str[0]
        .unique()
        .tolist()
    )


# ============================================================
# POPULATION SEARCH (FIXED + STRICT)
# ============================================================

def search_population(user_input: str, ancient_df, modern_df, max_results=8):
    """
    Clean, strict population search for ancestry datasets.
    """

    ancient_pops = get_ancient_populations(ancient_df)
    modern_pops = get_modern_populations(modern_df)

    # stronger cutoff (fixes garbage matches like Serbia/Spain spam)
    ancient_matches = difflib.get_close_matches(
        user_input,
        ancient_pops,
        n=max_results,
        cutoff=0.55
    )

    modern_matches = difflib.get_close_matches(
        user_input,
        modern_pops,
        n=max_results,
        cutoff=0.60
    )

    return {
        "ancient": ancient_matches,
        "modern": modern_matches,
        "all": ancient_matches + modern_matches
    }


# ============================================================
# CLEAN POPULATION AVERAGING
# ============================================================

def get_population_average(pop_name: str, ancient_df, modern_df):
    """
    Returns clean averaged PCA vector for a population.
    """

    # -------------------------
    # Ancient
    # -------------------------
    if pop_name in get_ancient_populations(ancient_df):

        df = ancient_df.copy()

        if "Population" not in df.columns:
            df["Population"] = df.index.astype(str).str.split(":").str[0]

        group = df[df["Population"] == pop_name].drop(columns=["Population"], errors="ignore")

        if len(group) == 0:
            return None, None

        avg = group.mean()

        return pd.DataFrame([avg], index=[pop_name]), {
            "type": "ancient",
            "n": len(group)
        }

    # -------------------------
    # Modern
    # -------------------------
    modern_group = modern_df.loc[
        modern_df.index.astype(str).str.split(":").str[0] == pop_name
    ]

    if len(modern_group) == 0:
        return None, None

    avg = modern_group.mean()

    return pd.DataFrame([avg], index=[pop_name]), {
        "type": "modern",
        "n": len(modern_group)
    }
