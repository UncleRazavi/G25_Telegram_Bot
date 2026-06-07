import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


def run_pca_clean(
    sample_df,
    reference_df,
    label_top_n=15,
    save_plot=True,
    plot_file="pca_clean.png"
):

    # -----------------------------
    # Combine
    # -----------------------------
    combined = pd.concat([reference_df, sample_df])
    combined = combined.fillna(combined.mean(numeric_only=True))

    # -----------------------------
    # Standardize + PCA
    # -----------------------------
    X = StandardScaler().fit_transform(combined.values)

    pca = PCA(n_components=2)
    coords = pca.fit_transform(X)

    pca_df = pd.DataFrame(coords, columns=["PC1", "PC2"], index=combined.index)

    pca_df["Type"] = ["Reference"] * len(reference_df) + ["Sample"] * len(sample_df)

    # -----------------------------
    # Split
    # -----------------------------
    ref = pca_df[pca_df["Type"] == "Reference"].copy()
    samp = pca_df[pca_df["Type"] == "Sample"].copy()

    # -----------------------------
    # Find closest refs to sample
    # -----------------------------
    if len(samp) > 0:
        sx, sy = samp.iloc[0][["PC1", "PC2"]]

        ref["dist"] = np.sqrt((ref["PC1"] - sx)**2 + (ref["PC2"] - sy)**2)
        closest = ref.nsmallest(label_top_n, "dist")
    else:
        closest = ref.iloc[:0]

    # -----------------------------
    # Plot
    # -----------------------------
    plt.figure(figsize=(11, 8))

    # References (light, no labels)
    plt.scatter(
        ref["PC1"], ref["PC2"],
        s=25,
        alpha=0.25,
        c="steelblue",
        label="Reference"
    )

    # Highlight closest refs
    plt.scatter(
        closest["PC1"], closest["PC2"],
        s=80,
        alpha=0.9,
        c="darkblue",
        label="Closest references"
    )

    # Sample (highlighted star)
    plt.scatter(
        samp["PC1"], samp["PC2"],
        s=200,
        c="red",
        marker="*",
        edgecolor="black",
        label="Sample"
    )

    # -----------------------------
    # ONLY label closest refs
    # -----------------------------
    for idx, row in closest.iterrows():
        plt.text(
            row["PC1"],
            row["PC2"],
            idx,
            fontsize=9
        )

    # -----------------------------
    # Variance labels
    # -----------------------------
    evr = pca.explained_variance_ratio_ * 100

    plt.xlabel(f"PC1 ({evr[0]:.2f}%)")
    plt.ylabel(f"PC2 ({evr[1]:.2f}%)")

    plt.title("PCA: Sample vs Reference Populations")
    plt.grid(alpha=0.2)
    plt.legend()

    plt.tight_layout()

    # -----------------------------
    # Save
    # -----------------------------
    if save_plot:
        plt.savefig(plot_file, dpi=300, bbox_inches="tight")
        plt.close()
        return plot_file

    plt.show()
    return pca_df
