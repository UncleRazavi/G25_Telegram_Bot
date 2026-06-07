# pca_script.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


def run_pca(
    sample_path,
    reference_path,
    save_plot=True,
    plot_file="pca_plot.png",
    n_labels=20
):

    # -----------------------------
    # Load data
    # -----------------------------
    if isinstance(sample_path, pd.DataFrame):
        sample_df = sample_path.copy()
    else:
        sample_df = pd.read_csv(sample_path, index_col=0)

    if isinstance(reference_path, pd.DataFrame):
        ref_df = reference_path.copy()
    else:
        ref_df = pd.read_csv(reference_path, index_col=0)

    # -----------------------------
    # Combine datasets
    # -----------------------------
    combined_df = pd.concat([ref_df, sample_df])

    # Fill missing values if any
    combined_df = combined_df.fillna(combined_df.mean())

    # -----------------------------
    # Standardize
    # -----------------------------
    scaler = StandardScaler()
    X = scaler.fit_transform(combined_df.values)

    # -----------------------------
    # PCA
    # -----------------------------
    pca = PCA(n_components=2)
    coords = pca.fit_transform(X)

    pca_df = pd.DataFrame(
        coords,
        columns=["PC1", "PC2"],
        index=combined_df.index
    )

    pca_df["Type"] = (
        ["Reference"] * len(ref_df)
        + ["Sample"] * len(sample_df)
    )

    # -----------------------------
    # Plot
    # -----------------------------
    plt.figure(figsize=(12, 8))

    ref_mask = pca_df["Type"] == "Reference"
    sample_mask = pca_df["Type"] == "Sample"

    # References
    plt.scatter(
        pca_df.loc[ref_mask, "PC1"],
        pca_df.loc[ref_mask, "PC2"],
        c="steelblue",
        alpha=0.6,
        s=40,
        label="Reference"
    )

    # Samples
    plt.scatter(
        pca_df.loc[sample_mask, "PC1"],
        pca_df.loc[sample_mask, "PC2"],
        c="red",
        s=180,
        marker="*",
        edgecolors="black",
        label="Sample"
    )

    # -----------------------------
    # Label samples
    # -----------------------------
    for idx in pca_df[sample_mask].index:
        plt.annotate(
            idx,
            (
                pca_df.loc[idx, "PC1"],
                pca_df.loc[idx, "PC2"]
            ),
            fontsize=11,
            fontweight="bold"
        )

    # -----------------------------
    # Label closest references
    # -----------------------------
    for sample_name in pca_df[sample_mask].index:

        sample_x = pca_df.loc[sample_name, "PC1"]
        sample_y = pca_df.loc[sample_name, "PC2"]

        refs = pca_df[ref_mask].copy()

        refs["Distance"] = np.sqrt(
            (refs["PC1"] - sample_x) ** 2 +
            (refs["PC2"] - sample_y) ** 2
        )

        closest = refs.nsmallest(n_labels, "Distance")

        for idx, row in closest.iterrows():
            plt.annotate(
                idx,
                (row["PC1"], row["PC2"]),
                fontsize=8,
                alpha=0.8
            )

        print(f"\nClosest populations to {sample_name}:")
        print("-" * 50)

        for idx, row in closest.iterrows():
            print(f"{idx:<30} {row['Distance']:.4f}")

    # -----------------------------
    # Labels
    # -----------------------------
    var1 = pca.explained_variance_ratio_[0] * 100
    var2 = pca.explained_variance_ratio_[1] * 100

    plt.xlabel(f"PC1 ({var1:.2f}% variance)")
    plt.ylabel(f"PC2 ({var2:.2f}% variance)")

    plt.title("PCA: Sample vs Reference Populations")
    plt.legend()
    plt.grid(alpha=0.3)

    plt.tight_layout()

    # -----------------------------
    # Save / Show
    # -----------------------------
    if save_plot:
        plt.savefig(
            plot_file,
            dpi=300,
            bbox_inches="tight"
        )
        plt.close()
        return plot_file

    plt.show()
    return pca_df
