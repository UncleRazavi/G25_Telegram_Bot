# pca_script.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
import seaborn as sns

def run_pca(sample_path, reference_path, save_plot=True):
    # Load data
    sample_df = pd.read_csv(sample_path, index_col=0)
    ref_df = pd.read_csv(reference_path, index_col=0)

    # Combine data for PCA
    combined_df = pd.concat([ref_df, sample_df])
    pca = PCA(n_components=2)
    pca_coords = pca.fit_transform(combined_df.values)

    # Prepare DataFrame for plotting
    pca_df = pd.DataFrame(pca_coords, columns=['PC1', 'PC2'], index=combined_df.index)
    pca_df['Type'] = ['Reference'] * len(ref_df) + ['Sample'] * len(sample_df)

    plt.figure(figsize=(8,6))
    sns.scatterplot(data=pca_df, x='PC1', y='PC2', hue='Type', style='Type', s=100, palette=['blue','red'])

    # Annotate reference populations
    for i, row in pca_df.iterrows():
        if row['Type'] == 'Reference':
            plt.text(row['PC1']+0.01, row['PC2']+0.01, i, fontsize=8)

    plt.title('PCA of Sample vs Reference Populations')
    plt.tight_layout()

    plot_file = "pca_plot.png"
    if save_plot:
        plt.savefig(plot_file)
        plt.close()
        return plot_file
    else:
        plt.show()
        return None
