# closest_script.py
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def run_closest(sample_path, reference_path, top_n=5, save_plot=False):
    sample_df = pd.read_csv(sample_path, index_col=0)
    ref_df = pd.read_csv(reference_path, index_col=0)

    results_texts = []
    plot_files = []

    for sample_name, sample_coords in sample_df.iterrows():
        distances = {ref_name: np.linalg.norm(sample_coords - ref_coords) 
                     for ref_name, ref_coords in ref_df.iterrows()}
        sorted_dist = sorted(distances.items(), key=lambda x: x[1])
        top_matches = sorted_dist[:top_n]

        result_text = f"Top {top_n} closest populations to {sample_name}:\n"
        for name, dist in top_matches:
            result_text += f"{name}: {dist:.4f}\n"
        results_texts.append(result_text)

        if save_plot:
            labels = [x[0] for x in top_matches]
            values = [x[1] for x in top_matches]
            plt.figure()
            plt.barh(labels[::-1], values[::-1])
            plt.title(f"Top {top_n} Closest Populations to {sample_name}")
            plt.xlabel("Euclidean Distance")
            plot_file = f"{sample_name}_closest.png"
            plt.tight_layout()
            plt.savefig(plot_file)
            plot_files.append(plot_file)
            plt.close()

    return "\n".join(results_texts), plot_files
