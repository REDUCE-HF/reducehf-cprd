import os
import sys
import warnings
warnings.filterwarnings('ignore')
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, AgglomerativeClustering, OPTICS
from sklearn_extra.cluster import KMedoids
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import pairwise_distances
from sklearn.metrics import roc_auc_score, silhouette_score, calinski_harabasz_score
from sdc_helpers import apply_disclosure_control
from config import (
    RAW_PATH, SCALED_PATH,
    MEMBERSHIP_DATE_COLS, AGE_BINS, AGE_LABELS, HOUSEHOLD_BINS, HOUSEHOLD_LABELS,
    CATEGORICAL_COLS, DATE_BASED_CONDITIONS, OBESITY_DATE_COLS, OBESITY_BMI_THRESHOLD,
    LTC_COLS, UNDERSERVED_COLS, CONDITION_TIME_WINDOW_DAYS, DIABETES_UNLIKELY_VALUE,
    DIAGNOSIS_PRIMARY_COL, DIAGNOSIS_HOSPITAL_COLS, umap_path
)


sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)


# ============================================
# Common helper functions for clustering scripts
# ============================================

def load_data(raw_path=RAW_PATH, scaled_path=SCALED_PATH):
    """Load raw and scaled datasets and return both DataFrames and feature arrays."""
    
    raw_df = pd.read_csv(raw_path)
    patient_ids = raw_df["patient_id"].values

    scaled_df = pd.read_csv(scaled_path)
    
    X_raw = raw_df.drop(columns=["patient_id"]).values.astype(object) 
    X_scaled = scaled_df.drop(columns=["patient_id"]).values
    
    # Return all four expected variables
    return X_raw, X_scaled, patient_ids

def load_feature_names(raw_path=RAW_PATH):
    """
    Load the list of feature names (column names) from the raw data file.

    """
    raw_df = pd.read_csv(raw_path)
    id_col = "patient_id"
    # Return column names, excluding the patient ID
    return raw_df.drop(columns=[id_col], errors='ignore').columns.tolist()



def run_pca(X_scaled, var_threshold=0.8):
    """Run PCA to reduce dimensions until target variance explained.
    
    Returns:
        X_pca: Transformed data in reduced PCA space
        var_explained: Total variance explained
    """
    pca = PCA(n_components=var_threshold, random_state=42)
    X_pca = pca.fit_transform(X_scaled)
    var_explained = pca.explained_variance_ratio_.sum()
    return X_pca, var_explained






# ============================================
# Clustering algorithm wrapper functions
# ============================================

def run_kmedoids_gower(D, k):
    """
    Run k-medoids clustering on precomputed Gower distance matrix.
    
    Args:
        D: Precomputed distance matrix (Gower)
        k: Number of clusters
        
    Returns:
        Cluster labels
    """
    model = KMedoids(n_clusters=k, metric="precomputed", init="k-medoids++", random_state=42)
    return model.fit_predict(D)


def run_agglomerative_precomputed(D, k):
    """
    Run agglomerative clustering on precomputed distance matrix.
    
    Args:
        D: Precomputed distance matrix (Gower)
        k: Number of clusters
        
    Returns:
        Cluster labels
    """
    model = AgglomerativeClustering(n_clusters=k, metric="precomputed", linkage="average")
    return model.fit_predict(D)


def run_kmeans(X, k):
    """
    Run k-means clustering on feature matrix.
    
    Args:
        X: Feature matrix (e.g., PCA-transformed data)
        k: Number of clusters
        
    Returns:
        Cluster labels
    """
    return KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(X)


def run_agglomerative_euclidean(X, k):
    """
    Run agglomerative clustering with Euclidean distance.
    
    Args:
        X: Feature matrix (e.g., PCA-transformed data)
        k: Number of clusters
        
    Returns:
        Cluster labels
    """
    return AgglomerativeClustering(n_clusters=k, metric="euclidean", linkage="average").fit_predict(X)


def run_optics(X):
    """
    Run OPTICS clustering (does not require fixed k).
    
    Args:
        X: Feature matrix (e.g., PCA-transformed data)
        
    Returns:
        Cluster labels (-1 for noise points)
    """
    
    optics = OPTICS(min_samples=10, xi=0.05, metric="euclidean").fit(X)
    return optics.labels_


# -------------------
# Prediction Strength (PS) Calculation
# -------------------
def split_indices(n_samples, rng):
    """Return two shuffled index arrays of equal size."""
    idx = rng.permutation(n_samples)
    mid = len(idx) // 2
    return idx[:mid], idx[mid:]

def compute_representatives(X, labels, precomputed): 
    """ medoids if precomputed or centroids otherwise."""
    if precomputed: #X is a distance matrix 
        medoids = []
        for c in np.unique(labels):
            members = np.where(labels == c)[0]
            cluster_dist = X[np.ix_(members, members)]
            medoids.append(members[np.argmin(cluster_dist.sum(axis=1))])
        return np.array(medoids)          
    else: # X is the data (feature matrix)
        centroids = []
        for c in np.unique(labels):
            cluster_points = X[labels == c]
            centroid = cluster_points.mean(axis=0)
            centroids.append(centroid)
        return np.vstack(centroids)
    
def assign_to_nearest(X_full, idx_half2, medoid_global_idx, X_half2, representatives, precomputed):
    """Return nearest-representative index for each test point."""
    if precomputed:
        distances = X_full[np.ix_(idx_half2, medoid_global_idx)]
        return np.argmin(distances, axis=1)
    else:
        return np.argmin(pairwise_distances(X_half2, representatives, metric="euclidean"), axis=1)


def ps_for_split(labels_half2, nearest):
    """Compute min co-membership fraction across clusters for one split."""
    ps_k = []
    for c in np.unique(labels_half2):
        idx_c = np.where(labels_half2 == c)[0]
        if len(idx_c) < 2:
            continue
        pairs = [(i, j) for i in idx_c for j in idx_c if i < j] #unique pair of points in cluster 
        same = sum(nearest[i] == nearest[j] for i, j in pairs) #count pairs that are assigned to the same centroid/medoid in the other half
        ps_k.append(same / len(pairs))
    return min(ps_k) 


def compute_prediction_strength(X, cluster_fn, k, precomputed=False, n_splits=5, random_state=42):
    rng = np.random.default_rng(random_state)
    ps_values = []

    for split_i in range(n_splits):
        idx_half1, idx_half2 = split_indices(X.shape[0], rng)

        if precomputed:
            D_half1 = X[np.ix_(idx_half1, idx_half1)]
            D_half2 = X[np.ix_(idx_half2, idx_half2)]
            labels_half1 = cluster_fn(D_half1, k)
            labels_half2 = cluster_fn(D_half2, k)
            medoid_local_idx = compute_representatives(D_half1, labels_half1, precomputed=True)# positions within D_half1
            medoid_global_idx = idx_half1[medoid_local_idx]#full data space
            nearest = assign_to_nearest(X, idx_half2, medoid_global_idx, None, None, precomputed=True)
        else:
            X_half1, X_half2 = X[idx_half1], X[idx_half2]
            labels_half1 = cluster_fn(X_half1, k)
            labels_half2 = cluster_fn(X_half2, k)
            representatives = compute_representatives(X_half1, labels_half1, precomputed=False)
            nearest = assign_to_nearest(None, None, None, X_half2, representatives, precomputed=False)

        ps = ps_for_split(labels_half2, nearest)
        
        ps_values.append(ps)

    return np.mean(ps_values), np.std(ps_values) / np.sqrt(n_splits)

# -------------------
# synthetic data
# -------------------
def parse_args():
    parser = argparse.ArgumentParser(description="Generate synthetic clustering data.")
    parser.add_argument(
        "--synthetic-output-dir",
        help="Write synthetic outputs here instead of the default in config.",
    )
    return parser.parse_args()



def get_best_config(validation_results_path):
    """
    Load validation results and return the best configuration name.
    """
    if not os.path.exists(validation_results_path):
        raise FileNotFoundError(f"Validation results not found: {validation_results_path}")
    
    val_df = pd.read_csv(validation_results_path)
    # add ranks rather than adding scores because scales are very differnt
    val_df["rank"] = (val_df["silhouette"].rank(ascending=False) + 
                      val_df["calinski_harabasz"].rank(ascending=False))
    
    best_config = val_df.sort_values("rank").iloc[0]["config"]
    
    return best_config


def variance_of_means(labels, X):
    """Calculate variance of cluster means for each feature."""
    df = X.assign(cluster=labels)
    df = df[df["cluster"] != -1]
    return df.groupby("cluster").mean(numeric_only=True).var()

def get_diagnosis_location(df):
    """
    Determine diagnosis location (community vs emergency) based on earliest diagnosis date.
    
    """
    all_diag_cols = [DIAGNOSIS_PRIMARY_COL, *DIAGNOSIS_HOSPITAL_COLS]
    diag_dates = df[all_diag_cols].apply(pd.to_datetime, errors="coerce")

    primary_date = diag_dates[DIAGNOSIS_PRIMARY_COL]
    earliest_overall = diag_dates.min(axis=1)

    diagnosis_community = primary_date.eq(earliest_overall).astype(int)
    diagnosis_emergency = (1- diagnosis_community).astype(int)

    return diagnosis_community, diagnosis_emergency

def build_membership_features(df):
    """Build membership features for cluster characterization."""
    out = pd.DataFrame({"patient_id": df["patient_id"]},index=df.index)

    # Convert all date columns to datetime
    dates_df = {col: pd.to_datetime(df[col], errors="coerce") 
             for col in MEMBERSHIP_DATE_COLS }
    
    # Diagnosis location
    out["diagnosis_community"], out["diagnosis_emergency"] = get_diagnosis_location(df)
    
    # Age bands
    age = np.floor((dates_df["patient_index_date"] - dates_df["birth_date"]).dt.days / 365.25)
    out["age_band"] = pd.cut(age, bins=AGE_BINS, labels=AGE_LABELS, right=False).astype("object")
    
    # Categorical variables - Household size
    hs_numeric = pd.to_numeric(df["household_size"], errors="coerce")
    out["cat_household_size"] = pd.cut(
        hs_numeric,
        bins=HOUSEHOLD_BINS,
        labels=HOUSEHOLD_LABELS,
        right=True,
        include_lowest=True
    ).astype("object")

    out.loc[hs_numeric.isna() | (hs_numeric <= 0), "cat_household_size"] = "unknown"

    for col in CATEGORICAL_COLS:
        if col=="cat_household_size":
            continue
        out[col] = df[col].astype("object")
    
    # Create pre_existing and new conditions based on time window before hf diagnosis
    hf_diagnosis_date = dates_df["hf_diagnosis_date"]
    time_window = pd.Timedelta(days=CONDITION_TIME_WINDOW_DAYS)
    
    for condition, cols in DATE_BASED_CONDITIONS.items():
        condition_dates = pd.DataFrame({c: dates_df.get(c) for c in cols })
        first_date = condition_dates.min(axis=1)
        out[f"{condition}_preexisting"] = (first_date < (hf_diagnosis_date - time_window)).fillna(False).astype(int)
        out[f"{condition}_new"] = ((first_date >= (hf_diagnosis_date - time_window)) & (first_date <= hf_diagnosis_date)).fillna(False).astype(int)
    
    # Obesity: combine date-based and BMI-based
    obesity_dates = pd.DataFrame({c: dates_df.get(c) for c in OBESITY_DATE_COLS })
    obesity_from_dates = obesity_dates.notna().any(axis=1).astype(int) 
    obesity_bmi = (pd.to_numeric(df["bmi_value"], errors="coerce") >= OBESITY_BMI_THRESHOLD).fillna(False).astype(int)
    out["obesity"] = ((obesity_from_dates == 1) | (obesity_bmi == 1)).astype(int)
    
    # Diabetes
    out["has_diabetes"] = (df["cat_diabetes"] != DIABETES_UNLIKELY_VALUE).astype(int)
    
    # Multi-morbidity
    out["mltc_count"] = out[LTC_COLS].sum(axis=1)
    out["has_mltc"] = (out["mltc_count"] >= 2).astype(int)
    
    # Under-served groups
    for col in UNDERSERVED_COLS:
        out[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    
    return out


def evaluate_clustering(config, X, labels, metric="euclidean"):
    n_clusters = len(np.unique(labels))
    if n_clusters < 2:
        print(f"Warning: {config}: only one cluster — skipping.")
        return {"config": config, "silhouette": np.nan, "calinski_harabasz": np.nan}
    sil = silhouette_score(X, labels, metric=metric)
    ch = calinski_harabasz_score(X, labels)  
    print(f"{config}: silhouette={sil:.3f}, calinski_harabasz={ch:.1f}")
    return {"config": config, "silhouette": sil, "calinski_harabasz": ch}


def make_ovr_labels(labels, cluster_id):
    """Binary labels: 1 = in cluster, 0 = outside."""
    return (labels == cluster_id).astype(int)

def fit_decision_tree_cv(X, y, param_grid, random_state=42):
    """GridSearchCV for a decision tree using ROC AUC."""
    model = DecisionTreeClassifier(random_state=random_state)

    grid = GridSearchCV(
        estimator=model,
        param_grid=param_grid,
        scoring="roc_auc",
        cv=5,
        n_jobs=-1,#
        return_train_score=True
    )
    grid.fit(X, y)
    return grid

def evaluate_best_model(model, X, y):
    """Compute training AUC for the best estimator."""
    y_pred = model.predict_proba(X)[:, 1]
    return roc_auc_score(y, y_pred)

def summarise_cluster_features(X, y, model, cluster_id):
    """Combine Gini importance with mean differences."""
    gini = pd.Series(model.feature_importances_, index=X.columns)

    mean_in  = X[y == 1].mean(axis=0)
    mean_out = X[y == 0].mean(axis=0)

    df = pd.DataFrame({
        "cluster": cluster_id,
        "feature": X.columns,
        "gini_importance": gini.values,
        "mean_in_cluster": mean_in.values,
        "mean_outside_cluster": mean_out.values,
    })

    df["mean_difference"] = df["mean_in_cluster"] - df["mean_outside_cluster"]
    df["distinguishing_feature"] = np.where(
        df["mean_difference"] > 0, "presence",
        np.where(df["mean_difference"] < 0, "absence", "equal")
    )
    return df

def train_ovr(X, labels, output_dir, random_state=42):
    """Train OvR decision trees and return interpretability table."""

    clusters = sorted(labels.unique())
    param_grid = {
        "max_depth": [5, 10, 50, 100],
        "min_samples_leaf": [5, 10, 50],
    }

    all_results = []

    for k in clusters:
        if k == -1:
            continue  # Skip noise cluster
        y = make_ovr_labels(labels, k)
        print(f"{labels.value_counts()[k]} samples in cluster {k}")
        grid = fit_decision_tree_cv(X, y, param_grid, random_state)
        best_model = grid.best_estimator_

        train_auc = evaluate_best_model(best_model, X, y)

        print(
            f"Cluster {k}: "
            f"Best params={grid.best_params_}, "
            f"CV AUC={grid.best_score_:.3f}, "
            f"Train AUC={train_auc:.3f}"
        )

        summary = summarise_cluster_features(X, y, best_model, k)
        all_results.append(summary)

    return (
        pd.concat(all_results, ignore_index=True)
          .sort_values(["cluster", "gini_importance"], ascending=[True, False])
    )


# ============================================
# Visualisation helpers
# ============================================

def plot_clusters_umap(umap_values, labels, config_name):
    """Plot UMAP embedding coloured by cluster labels and save to disk."""
    df = pd.DataFrame(umap_values, columns=["UMAP1", "UMAP2"])
    df["cluster_id"] = labels
    counts = df["cluster_id"].value_counts()

    names = df["cluster_id"].replace(-1, "Noise").astype(str)
    sizes = df["cluster_id"].map(counts).astype(str)
    df["cluster"] = names + " (" + sizes + ")"

    n_clusters = len(counts) - (1 if -1 in counts else 0)

    plt.figure(figsize=(10, 7))
    sns.scatterplot(
        data=df.sort_values("cluster_id"),
        x="UMAP1", y="UMAP2",
        hue="cluster", palette="tab20", s=50, alpha=0.8
    )
    plt.title(f"UMAP: {config_name} | {n_clusters} Clusters")
    plt.legend(title="Cluster (Size)", bbox_to_anchor=(1.05, 1), loc="upper left")

    save_path = umap_path(config_name)
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.show()
    plt.close()
    print(f"  Saved {save_path}")

