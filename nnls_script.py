import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import nnls

TARGET_SOURCES = {
    "Turkey_N", "Russia_Samara_EBA_Yamnaya", "Iran_Wezmeh_N.SG",
    "Israel_Natufian", "China_AmurRiver_N", "Georgia_Kotias.SG",
    "Russia_Karelia_HG", "Russia_Baikal_EN", "Morocco_Iberomaurusian"
}


def run_nnls(target_path, ancient_path, save_plot=False, eps=1e-6):
    """
    NNLS ancestry decomposition using ancient reference populations.
    """

    # -----------------------------
    # Load data
    # -----------------------------
    if isinstance(target_path, pd.DataFrame):
        target_data = target_path.copy()
    else:
        target_data = pd.read_csv(target_path, index_col=0)

    if isinstance(ancient_path, pd.DataFrame):
        ancient_data = ancient_path.copy()
    else:
        ancient_data = pd.read_csv(ancient_path, index_col=0)

    # -----------------------------
    # Extract population names
    # -----------------------------
    ancient_data["Population"] = ancient_data.index.astype(str).str.split(":").str[0]

    ancient_data = ancient_data[
        ancient_data["Population"].isin(TARGET_SOURCES)
    ].copy()

    # -----------------------------
    # Numeric matrix
    # -----------------------------
    numeric_cols = ancient_data.select_dtypes(include=[np.number]).columns

    ancient_numeric = ancient_data[numeric_cols]

    # Average per population (important for stability)
    ancient_avg = ancient_data.groupby("Population")[numeric_cols].mean()

    populations = ancient_avg.index.tolist()
    sources_matrix = ancient_avg.values

    results = {}
    plot_files = []

    # -----------------------------
    # NNLS per sample
    # -----------------------------
    for sample_name, row in target_data.iterrows():

        sample_vec = row.values.astype(float)

        coeffs, _ = nnls(sources_matrix.T, sample_vec)

        # -------------------------
        # Safe normalization
        # -------------------------
        total = coeffs.sum()
        if total > eps:
            coeffs = coeffs / total

        # Sort results (important for interpretation)
        sorted_idx = np.argsort(coeffs)[::-1]
        coeffs_sorted = coeffs[sorted_idx]
        pops_sorted = np.array(populations)[sorted_idx]

        # Store structured result
        results[sample_name] = {
            pop: float(coef)
            for pop, coef in zip(pops_sorted, coeffs_sorted)
            if coef > 1e-4
        }

        # -------------------------
        # Text output
        # -------------------------
        print(f"\n{sample_name}")
        print("-" * 40)

        for pop, coef in zip(pops_sorted, coeffs_sorted):
            if coef > 1e-4:
                print(f"{pop:<25} {coef:6.2%}")

        # -------------------------
        # Plot
        # -------------------------
        plt.figure(figsize=(6, 6))

        mask = coeffs_sorted > 1e-4

        plt.pie(
            coeffs_sorted[mask],
            labels=pops_sorted[mask],
            autopct="%1.1f%%",
            startangle=140,
            textprops={"fontsize": 8}
        )

        plt.title(f"NNLS ancestry: {sample_name}")
        plt.axis("equal")

        if save_plot:
            file_name = f"{sample_name}_nnls.png"
            plt.savefig(file_name, dpi=300, bbox_inches="tight")
            plot_files.append(file_name)

        plt.close()

    return results, plot_files
