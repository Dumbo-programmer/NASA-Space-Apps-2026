"""
Ignis mu / AgniShikha - model selection engine (v2)
Data Science Lead: Prachya Biswas

Why this exists
---------------
v1 picked the model with the best cross-validation score and then reported that SAME score.
That is optimistic: the score that chose the winner is also the score we show (selection bias),
and every model ran with one hand-picked setting (no tuning).

v2 does model selection properly:

  1. Many model families (linear -> kernel -> trees -> boosting), each with a hyper-parameter grid.
  2. NESTED, GROUPED cross-validation
        outer loop : holds out whole ISS test series / sessions -> honest score of the WHOLE procedure
        inner loop : inside the outer-training part only, tunes every family and picks one
     So the reported score never saw the data it is scored on, not even during selection.
  3. Selection rule = "one-standard-error rule": among families whose inner score is within
     1 SE of the best, take the SIMPLEST one (fewer ways to over-fit on small NASA datasets).
  4. Selection criterion uses PROPER scoring rules (log-loss for probabilities, MAE for values),
     so a classifier with good ranking but bad probabilities cannot win.
  5. Repeated outer CV (different group shuffles) + group bootstrap 95% CI for every metric.
  6. Prediction bands come from the nested residuals (what the procedure really gets wrong).
"""
import warnings
import numpy as np, pandas as pd
from sklearn.base import clone
from sklearn.model_selection import GridSearchCV, GroupKFold, LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.compose import TransformedTargetRegressor
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.neighbors import KNeighborsRegressor, KNeighborsClassifier
from sklearn.svm import SVR, SVC
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, RBF, WhiteKernel
from sklearn.ensemble import (RandomForestRegressor, ExtraTreesRegressor, GradientBoostingRegressor,
                              RandomForestClassifier, ExtraTreesClassifier, GradientBoostingClassifier)
from sklearn.metrics import make_scorer
from sklearn.metrics import (mean_absolute_error, r2_score, mean_squared_error, roc_auc_score,
                             brier_score_loss, log_loss, balanced_accuracy_score)
warnings.filterwarnings("ignore")
RS = 42
# log-loss that still works when a small inner fold holds only one class (labels fixed to 0/1)
LOGLOSS = make_scorer(log_loss, greater_is_better=False, response_method="predict_proba", labels=[0, 1])


# ------------------------------------------------------------------ candidate families
def regression_families(n_features, allow_log=False):
    """name -> (complexity rank, estimator, grid). Lower rank = simpler model.
    allow_log=True adds 'fit on log(target)' as a tuned option for every family (scores stay on the original scale)."""
    fams = _base_regression_families(n_features)
    out = {}
    for name, (rank, est, grid) in fams.items():
        wrapped = TransformedTargetRegressor(regressor=est, check_inverse=False)
        g = {"regressor__" + k: v for k, v in grid.items()}
        opts = [{"func": [None], "inverse_func": [None]}]
        if allow_log:
            opts.append({"func": [np.log], "inverse_func": [np.exp]})
        out[name] = (rank, wrapped, [dict(g, **o) for o in opts])
    return out


def _base_regression_families(n_features):
    ls = np.ones(n_features)
    ttr = lambda est: TransformedTargetRegressor(regressor=est, transformer=StandardScaler())
    return {
        "Ridge (linear)": (1, Pipeline([("sc", StandardScaler()), ("m", Ridge())]),
                           {"m__alpha": np.logspace(-3, 3, 7)}),
        "Ridge + pairwise interactions": (2, Pipeline([("sc", StandardScaler()), ("pf", PolynomialFeatures(2, interaction_only=True, include_bias=False)),
                                                      ("sc2", StandardScaler()), ("m", Ridge())]),
                                          {"m__alpha": np.logspace(-2, 3, 6)}),
        "k-nearest neighbours": (3, Pipeline([("sc", StandardScaler()), ("m", KNeighborsRegressor())]),
                                 {"m__n_neighbors": [3, 5, 8, 12], "m__weights": ["uniform", "distance"]}),
        "Support vector regression (RBF)": (4, ttr(Pipeline([("sc", StandardScaler()), ("m", SVR())])),
                                            {"regressor__m__C": [1, 3, 10, 30], "regressor__m__gamma": ["scale", 0.3],
                                             "regressor__m__epsilon": [0.05, 0.2]}),
        "Gaussian process (ARD)": (4, Pipeline([("sc", StandardScaler()), ("m", GaussianProcessRegressor(
                                       kernel=ConstantKernel(1.0) * RBF(length_scale=ls, length_scale_bounds=(1e-2, 1e3))
                                       + WhiteKernel(0.1, (1e-5, 1e1)), normalize_y=True, n_restarts_optimizer=2, random_state=RS))]),
                                   {}),
        "Random forest": (5, RandomForestRegressor(200, random_state=RS, n_jobs=1),
                          {"min_samples_leaf": [1, 3, 5], "max_features": [0.5, 1.0]}),
        "Extra trees": (5, ExtraTreesRegressor(200, random_state=RS, n_jobs=1),
                        {"min_samples_leaf": [1, 3, 5], "max_features": [0.5, 1.0]}),
        "Gradient boosting": (6, GradientBoostingRegressor(subsample=0.8, random_state=RS),
                              {"n_estimators": [100, 300], "learning_rate": [0.03, 0.1], "max_depth": [2, 3]}),
    }


def classification_families(n_features):
    return {
        "Logistic regression": (1, Pipeline([("sc", StandardScaler()), ("m", LogisticRegression(max_iter=5000))]),
                                {"m__C": np.logspace(-2, 2, 7)}),
        "Logistic + pairwise interactions": (2, Pipeline([("sc", StandardScaler()), ("pf", PolynomialFeatures(2, interaction_only=True, include_bias=False)),
                                                         ("sc2", StandardScaler()), ("m", LogisticRegression(max_iter=5000))]),
                                             {"m__C": np.logspace(-3, 1, 6)}),
        "k-nearest neighbours": (3, Pipeline([("sc", StandardScaler()), ("m", KNeighborsClassifier())]),
                                 {"m__n_neighbors": [8, 15, 25], "m__weights": ["uniform", "distance"]}),
        "Support vector machine (RBF)": (4, Pipeline([("sc", StandardScaler()), ("m", SVC(probability=True, random_state=RS))]),
                                         {"m__C": [0.3, 1, 3, 10], "m__gamma": ["scale", 0.1]}),
        "Random forest": (5, RandomForestClassifier(200, random_state=RS, n_jobs=1),
                          {"min_samples_leaf": [1, 3, 8], "max_features": [0.5, 1.0]}),
        "Extra trees": (5, ExtraTreesClassifier(200, random_state=RS, n_jobs=1),
                        {"min_samples_leaf": [1, 3, 8], "max_features": [0.5, 1.0]}),
        "Gradient boosting": (6, GradientBoostingClassifier(subsample=0.8, random_state=RS),
                              {"n_estimators": [100, 300], "learning_rate": [0.03, 0.1], "max_depth": [1, 2]}),
    }


# ------------------------------------------------------------------ leakage guard
class LeakageError(AssertionError):
    pass


def assert_group_disjoint(g, tr, te, where=""):
    """Fail loudly if any ISS test / session / run appears on both sides of a split."""
    shared = set(np.asarray(g)[tr]) & set(np.asarray(g)[te])
    if shared:
        raise LeakageError(f"group leakage {where}: {sorted(shared)[:5]} in both train and test")
    if len(set(tr) & set(te)):
        raise LeakageError(f"row leakage {where}: the same row is in train and test")


def checked_splits(cv, X, y, g, where=""):
    """Materialise a splitter's folds and check every one for group leakage."""
    folds = list(cv.split(X, y, g))
    for k, (tr, te) in enumerate(folds):
        assert_group_disjoint(g, tr, te, f"{where} fold {k}")
    return folds


# ------------------------------------------------------------------ CV splitters
def make_cv(kind, n_groups, seed=0):
    if kind == "logo":
        return LeaveOneGroupOut()
    return GroupKFold(n_splits=min(5, n_groups), shuffle=True, random_state=seed)


# ------------------------------------------------------------------ inner selection (tune all, pick one)
def select(X, y, g, families, scoring, inner_splits=5, seed=0, n_jobs=2):
    """Tune every family with grouped CV on (X, y), then apply a PAIRED one-standard-error rule:
    a family is 'as good as the best' if its fold-by-fold deficit to the best is within one SE of that deficit;
    among those, the simplest family wins. Few groups (<=12) -> inner leave-one-group-out (lower-variance choice)."""
    ng = len(np.unique(g))
    if ng <= 12:
        inner = checked_splits(LeaveOneGroupOut(), X, y, g, "inner")
    else:                                   # 2 x repeated grouped 5-fold -> steadier choice on small data
        inner = [sp for r in range(2) for sp in checked_splits(GroupKFold(n_splits=min(inner_splits, ng), shuffle=True,
                 random_state=seed + 1000 + r), X, y, g, "inner")]
    res = {}
    for name, (rank, est, grid) in families.items():
        gs = GridSearchCV(clone(est), grid or {}, scoring=scoring, cv=inner, n_jobs=n_jobs, refit=True, error_score=np.nan)
        gs.fit(X, y, groups=g)
        i = gs.best_index_
        folds = np.array([gs.cv_results_[k][i] for k in sorted(gs.cv_results_) if k.startswith("split") and k.endswith("_test_score")])
        res[name] = {"rank": rank, "score": gs.best_score_, "folds": folds, "params": gs.best_params_, "est": gs.best_estimator_}
    best = max(res, key=lambda n: res[n]["score"] if np.isfinite(res[n]["score"]) else -np.inf)
    ok = [best]
    for n, r in res.items():
        diff = res[best]["folds"] - r["folds"]                       # >= 0 on average
        diff = diff[np.isfinite(diff)]
        se = diff.std(ddof=1) / np.sqrt(len(diff)) if len(diff) > 1 else 0.0
        r["se"] = float(se)
        if n != best and np.isfinite(r["score"]) and len(diff) and diff.mean() <= se:
            ok.append(n)
    one_se = sorted(ok, key=lambda n: (res[n]["rank"], -res[n]["score"]))[0]
    ranking = sorted([n for n in res if np.isfinite(res[n]["score"])], key=lambda n: -res[n]["score"])
    members = {"best inner score": [best], "1-SE rule (simplest near-best)": [one_se], "top-3 average": ranking[:3]}
    return {"chosen": one_se, "best_raw": best, "ranking": ranking, "members": members, "table": res}


PROCEDURES = ["best inner score", "1-SE rule (simplest near-best)", "top-3 average"]


class AveragedModel:
    """Equal-weight average of several fitted models (probabilities for classifiers)."""
    def __init__(self, members, names, task):
        self.members, self.names, self.task = members, names, task
    def predict(self, X):
        if self.task == "classification":
            return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)
        return np.mean([m.predict(X) for m in self.members], axis=0)
    def predict_proba(self, X):
        p = np.mean([m.predict_proba(X)[:, 1] for m in self.members], axis=0)
        return np.column_stack([1 - p, p])


# ------------------------------------------------------------------ metrics
def reg_metrics(y, p):
    return {"MAE": mean_absolute_error(y, p), "RMSE": mean_squared_error(y, p) ** 0.5, "R2": r2_score(y, p),
            "MAPE_pct": 100 * float(np.mean(np.abs(p - y) / np.abs(y)))}


def clf_metrics(y, p, thr):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return {"ROC_AUC": roc_auc_score(y, p), "Brier": brier_score_loss(y, p), "log_loss": log_loss(y, p),
            "balanced_accuracy": balanced_accuracy_score(y, (p >= thr).astype(int))}


def group_bootstrap_ci(y, p, g, fn, n=1000, seed=RS):
    """95% CI of a metric, resampling whole groups (tests/sessions) with replacement."""
    rng = np.random.default_rng(seed); ug = np.unique(g); idx = {u: np.where(g == u)[0] for u in ug}; vals = []
    for _ in range(n):
        take = np.concatenate([idx[u] for u in rng.choice(ug, len(ug), replace=True)])
        try:
            vals.append(fn(y[take], p[take]))
        except ValueError:
            pass
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]


# ------------------------------------------------------------------ nested CV
def nested_cv(X, y, g, task, outer="kfold", repeats=3, transform=None, verbose=True):
    """
    task: "regression" | "classification".  transform: "log" -> fit on log(y) always;
    "tune" -> log vs raw target is a tuned hyper-parameter;  None -> raw target.
    Returns honest outer-fold predictions for every family and for every selection PROCEDURE.
    """
    X = X.reset_index(drop=True); y = np.asarray(y); g = np.asarray(g)
    fams = regression_families(X.shape[1], allow_log=(transform == "tune")) if task == "regression" else classification_families(X.shape[1])
    scoring = "neg_mean_absolute_error" if task == "regression" else LOGLOSS
    yfit = np.log(y) if transform == "log" else y
    inv = (lambda v: np.exp(v)) if transform == "log" else (lambda v: v)
    reps = 1 if outer == "logo" else repeats
    raw = {n: np.zeros((reps, len(y))) for n in fams}               # predictions in fitting space
    proc_raw = {p: np.zeros((reps, len(y))) for p in PROCEDURES}
    picks = {p: [] for p in PROCEDURES}
    for r in range(reps):
        cv = make_cv(outer, len(np.unique(g)), seed=r)
        for fold, (tr, te) in enumerate(checked_splits(cv, X, y, g, f"outer repeat {r}")):
            sel = select(X.iloc[tr], yfit[tr], g[tr], fams, scoring, seed=100 * r + fold)
            for n, info in sel["table"].items():
                est = info["est"]
                raw[n][r, te] = est.predict_proba(X.iloc[te])[:, 1] if task == "classification" else est.predict(X.iloc[te])
            for p in PROCEDURES:
                proc_raw[p][r, te] = np.mean([raw[n][r, te] for n in sel["members"][p]], axis=0)
                picks[p].append(" + ".join(sel["members"][p]))
            if verbose:
                print(f"  repeat {r+1} fold {fold+1}: best={sel['best_raw']} | 1-SE={sel['chosen']} | top3={sel['members']['top-3 average']}", flush=True)
    fam_pred = {n: (v if task == "classification" else inv(v)) for n, v in raw.items()}
    proc_pred = {p: (v if task == "classification" else inv(v)) for p, v in proc_raw.items()}
    return {"families": fams, "fam_pred": fam_pred, "proc_pred": proc_pred, "picks": picks, "reps": reps}


def summarise(res, y, g, task, thr_fn=None):
    """Honest comparison table: every family (tuned in the inner loop) and every selection procedure, scored on outer folds."""
    y = np.asarray(y); rows = []
    preds = {f"[procedure] {p}": P for p, P in res["proc_pred"].items()}
    preds.update(res["fam_pred"])
    for n, P in preds.items():
        ms = [reg_metrics(y, P[r]) if task == "regression" else clf_metrics(y, P[r], thr_fn(P[r])) for r in range(P.shape[0])]
        m = pd.DataFrame(ms); row = {"model": n}
        for c in m.columns:
            row[c] = m[c].mean()
            if P.shape[0] > 1:
                row[c + "_sd_over_repeats"] = m[c].std(ddof=0)
        rows.append(row)
    t = pd.DataFrame(rows)
    single = pd.Series(res["picks"]["best inner score"]).value_counts(normalize=True)
    t["picked_as_best_in_pct_of_outer_folds"] = t.model.map(lambda n: round(100 * single.get(n, 0), 1) if not n.startswith("[") else np.nan)
    return t
