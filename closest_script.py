import difflib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


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


def run_closest(sample_df, ancient_df, modern_df, top_n=15, save_plot=False):
    """
    Find the closest ancient and modern reference populations for each sample.
    """
    ref_frames = []

    ancient_copy = ancient_df.copy()
    if "Population" not in ancient_copy.columns:
        ancient_copy["Population"] = ancient_copy.index.astype(str).str.split(":").str[0]
    ancient_avg = ancient_copy.groupby("Population").mean(numeric_only=True)
    ancient_avg.index = "Ancient: " + ancient_avg.index.astype(str)
    ref_frames.append(ancient_avg)

    modern_copy = modern_df.copy()
    modern_copy["Population"] = modern_copy.index.astype(str).str.split(":").str[0]
    modern_avg = modern_copy.groupby("Population").mean(numeric_only=True)
    modern_avg.index = "Modern: " + modern_avg.index.astype(str)
    ref_frames.append(modern_avg)

    references = pd.concat(ref_frames)
    common_cols = references.columns.intersection(sample_df.columns)
    if len(common_cols) == 0:
        raise ValueError("No matching PCA columns were found between sample and reference data.")

    references = references[common_cols].astype(float)
    samples = sample_df[common_cols].astype(float)

    lines = ["Closest population matches", ""]
    plot_files = []

    for sample_name, sample_row in samples.iterrows():
        distances = np.linalg.norm(references.values - sample_row.values, axis=1)
        ranking = pd.Series(distances, index=references.index).sort_values().head(top_n)

        lines.append(str(sample_name))
        lines.append("-" * min(36, max(12, len(str(sample_name)))))
        for rank, (population, distance) in enumerate(ranking.items(), 1):
            lines.append(f"{rank:>2}. {population:<36} {distance:.6f}")
        lines.append("")

        if save_plot:
            safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(sample_name))
            plot_file = f"{safe_name}_closest.png"
            plt.figure(figsize=(9, 6))
            ranking.sort_values().plot(kind="barh", color="#3f7cac")
            plt.xlabel("Euclidean distance")
            plt.title(f"Closest references: {sample_name}")
            plt.tight_layout()
            plt.savefig(plot_file, dpi=250, bbox_inches="tight")
            plt.close()
            plot_files.append(plot_file)

    return "\n".join(lines).strip(), plot_files
