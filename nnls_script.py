# nnls_script.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import nnls

TARGET_SOURCES = {
    "Turkey_N", "Russia_Samara_EBA_Yamnaya", "Iran_Wezmeh_N.SG", "Israel_Natufian",
    "China_AmurRiver_N", "Georgia_Kotias.SG", "Russia_Karelia_HG", "Russia_Baikal_EN",
    "Morocco_Iberomaurusian"
}

def run_nnls(target_path, ancient_path, save_plot=False):
    target_data = pd.read_csv(target_path, index_col=0)
    ancient_data = pd.read_csv(ancient_path, index_col=0)
    ancient_data['Population'] = ancient_data.index.to_series().apply(lambda x: x.split(':')[0])
    ancient_data = ancient_data[ancient_data['Population'].isin(TARGET_SOURCES)].copy()
    numeric_columns = ancient_data.select_dtypes(include=[np.number]).columns
    ancient_numeric = ancient_data[numeric_columns]
    ancient_averaged = ancient_data.groupby(ancient_data['Population']).mean()
    populations = list(ancient_averaged.index)
    sources_matrix = ancient_averaged.values

    results_texts = []
    plot_files = []

    for sample_name, pcs in target_data.iterrows():
        coeffs, _ = nnls(sources_matrix.T, pcs.values)
        coeffs /= coeffs.sum()

        result_text = f"{sample_name}:\n"
        for pop, coef in zip(populations, coeffs):
            result_text += f"  {pop:20} -> {coef:.2%}\n"
        results_texts.append(result_text)

        # Plot
        plt.figure(figsize=(6,6))
        non_zero = coeffs > 1e-4
        filtered_coeffs = coeffs[non_zero]
        filtered_pops = np.array(populations)[non_zero]
        colors = plt.cm.Paired(np.linspace(0,1,len(filtered_pops)))
        plt.pie(filtered_coeffs, labels=None, autopct='%1.1f%%', startangle=140, colors=colors)
        plt.axis('equal')
        plt.title(f"Ancestry of {sample_name}")
        if save_plot:
            plot_file = f"{sample_name}_nnls.png"
            plt.savefig(plot_file)
            plot_files.append(plot_file)
        plt.close()

    return "\n".join(results_texts), plot_files
