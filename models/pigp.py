"""
Ignis mu / AgniShikha - Physics-Informed Gaussian Process (PI-GP)
Data Science Lead: Prachya Biswas

    y (physics space) = m(x)  +  f(x)  +  b_test  +  e
      m(x)   physics law: ridge regression on physics terms (a power law when the target is log-transformed)
      f(x)   Gaussian-process correction: learns where reality departs from the law, with its own uncertainty
      b_test test-to-test offset (hardware / session): its variance tau^2 is estimated from training groups
      e      measurement noise: WhiteKernel, started from the replicate-noise prior of preprocessing v3

Why this shape fits the objective (fire-risk envelope + where to test next):
  * far from NASA data f(x) -> 0, so the model falls back to the physics law by itself (no hand-made switch)
  * the predictive standard deviation grows where data is missing -> trustworthy bands + next-experiment pick
  * very few parameters to learn from 52-256 rows; kernel settings come from the marginal likelihood
"""
import numpy as np, pandas as pd
from scipy.stats import norm
from sklearn.base import BaseEstimator, RegressorMixin, ClassifierMixin
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.gaussian_process import GaussianProcessRegressor, GaussianProcessClassifier
from sklearn.gaussian_process.kernels import ConstantKernel, RBF, WhiteKernel


class PhysicsGPRegressor(BaseEstimator, RegressorMixin):
    """Hierarchical PI-GP. Kernel on [physics inputs, test id]:
         smooth physics correction  C1 * RBF(physics inputs; length >= 0.5 sd, so corrections stay smooth)
       + test offset                C2 * [same ISS test]   (learned by marginal likelihood = between-test variance)
       + measurement noise          White
    For a test never seen before the offset term contributes no mean but adds C2 to the variance."""
    NEW = -100.0          # code for a test never seen in training (codes are 10 apart: far for the test kernel, near-zero for the physics kernel)

    def __init__(self, mean_cols=None, gp_cols=None, log_target=False, alpha=1e-2, noise=None, correction="auto", random_state=0):
        self.mean_cols, self.gp_cols, self.log_target, self.alpha, self.noise, self.correction, self.random_state = mean_cols, gp_cols, log_target, alpha, noise, correction, random_state

    def _t(self, y):
        return np.log(y) if self.log_target else np.asarray(y, float)

    def _Z(self, X, groups=None):
        Z = self.sg_.transform(pd.DataFrame(X)[self.gp_cols])
        if groups is None:
            code = np.full(len(Z), self.NEW)
        else:
            code = np.array([self.gmap_.get(gg, self.NEW) for gg in groups], float)
        return np.column_stack([Z, code])

    def fit(self, X, y, groups=None):
        X = pd.DataFrame(X); groups = np.arange(len(X)) if groups is None else np.asarray(groups)
        self.use_correction_ = self.correction if isinstance(self.correction, bool) else self._choose(X, y, groups)
        return self._fit(X, y, groups)

    def _choose(self, X, y, groups):
        """Is a smooth GP correction on top of the physics law supported by the data? Decided by grouped inner CV
        on the TRAINING rows only (leave-one-test-out when there are few tests). The criterion is the objective's own:
        negative log predictive density (NLPD), which rewards accurate predictions AND honest uncertainty, and
        punishes a confident wrong answer."""
        from sklearn.model_selection import LeaveOneGroupOut, GroupKFold
        ug = np.unique(groups)
        if len(ug) < 4:
            return False
        cv = LeaveOneGroupOut() if len(ug) <= 12 else GroupKFold(5, shuffle=True, random_state=self.random_state)
        err = {True: [], False: []}; zs = {True: [], False: []}
        for tr, te in cv.split(X, y, groups):
            for flag in (True, False):
                m = PhysicsGPRegressor(self.mean_cols, self.gp_cols, self.log_target, self.alpha, self.noise, flag, self.random_state)
                m._fit(X.iloc[tr], np.asarray(y)[tr], groups[tr])
                mu, sd = m.predict_t(X.iloc[te]); yt = self._t(np.asarray(y)[te])
                err[flag].append(float(np.mean(0.5 * np.log(2 * np.pi * sd ** 2) + (yt - mu) ** 2 / (2 * sd ** 2))))
                zs[flag].extend(np.abs(yt - mu) / sd)
        self.inner_nlpd_ = {"with_correction": float(np.mean(err[True])), "physics_law_only": float(np.mean(err[False]))}
        flag = bool(np.mean(err[True]) < np.mean(err[False]))
        # interval calibration (split-conformal style, training rows only): stretch or shrink sd so that 90 % of
        # held-out inner-CV rows fall inside the band
        self.scale_ = float(np.quantile(zs[flag], 0.9) / norm.ppf(0.95))
        return flag

    def _fit(self, X, y, groups):
        X = pd.DataFrame(X); yt = self._t(y)
        self.sm_ = StandardScaler().fit(X[self.mean_cols]); self.mean_ = Ridge(alpha=self.alpha).fit(self.sm_.transform(X[self.mean_cols]), yt)
        Xm = self.sm_.transform(X[self.mean_cols]); r = yt - self.mean_.predict(Xm)
        # uncertainty of the physics-law coefficients (Bayesian linear model): grows as inputs leave the data cloud
        A = np.c_[np.ones(len(Xm)), Xm]; self.Ainv_ = np.linalg.inv(A.T @ A + self.alpha * np.eye(A.shape[1]))
        self.sg_ = StandardScaler().fit(X[self.gp_cols])
        self.gmap_ = {gg: 10.0 * i for i, gg in enumerate(pd.unique(groups))}
        Z = self._Z(X, groups); d = Z.shape[1] - 1
        rs2 = max(float(np.var(r)), 1e-12)
        n0 = min(max((self.noise or 0.1 * rs2) / rs2, 1e-4), 0.9)              # replicate-noise prior, normalised units
        big = [1e5, 1e5 + 1]
        phys = RBF(np.r_[np.ones(d), 1e5], np.array([[0.5, 100.0]] * d + [big]))
        test = RBF(np.r_[np.full(d, 1e5), 1.0], np.array([big] * d + [[1.0, 1.0 + 1e-6]]))
        k = ConstantKernel(0.2, (1e-4, 1e1)) * test + WhiteKernel(n0, (1e-4, 1.0))
        if getattr(self, "use_correction_", self.correction is True):
            k = ConstantKernel(0.5, (1e-3, 1e1)) * phys + k
        self.gp_ = GaussianProcessRegressor(k, normalize_y=True, n_restarts_optimizer=3, random_state=self.random_state).fit(Z, r)
        self.s2_ = float(np.var(r - self.gp_.predict(Z)))                       # residual variance for the coefficient term
        return self

    def predict_t(self, X, groups=None):
        """mean and sd in the transformed (physics) space; unseen tests get the between-test variance"""
        X = pd.DataFrame(X)
        m = self.mean_.predict(self.sm_.transform(X[self.mean_cols]))
        mu, sd = self.gp_.predict(self._Z(X, groups), return_std=True)
        A = np.c_[np.ones(len(X)), self.sm_.transform(X[self.mean_cols])]
        var_law = self.s2_ * np.einsum("ij,jk,ik->i", A, self.Ainv_, A)          # law-coefficient uncertainty
        return m + mu, np.sqrt(sd ** 2 + var_law) * getattr(self, "scale_", 1.0)

    def predict(self, X):
        mu, _ = self.predict_t(X)
        return np.exp(mu) if self.log_target else mu                            # median on the original scale

    def predict_interval(self, X, level=0.9):
        mu, sd = self.predict_t(X); z = norm.ppf(0.5 + level / 2)
        lo, hi = mu - z * sd, mu + z * sd
        return (np.exp(lo), np.exp(hi)) if self.log_target else (lo, hi)

    def physics_only(self, X):
        X = pd.DataFrame(X); m = self.mean_.predict(self.sm_.transform(X[self.mean_cols]))
        return np.exp(m) if self.log_target else m


class PhysicsGPClassifier(BaseEstimator, ClassifierMixin):
    """GP classifier on the physics features (O2 partial pressure, log pressure, diluents, size, fuel)."""
    def __init__(self, gp_cols=None, random_state=0):
        self.gp_cols, self.random_state = gp_cols, random_state

    def fit(self, X, y, groups=None):
        X = pd.DataFrame(X); self.sc_ = StandardScaler().fit(X[self.gp_cols]); Z = self.sc_.transform(X[self.gp_cols])
        k = ConstantKernel(1.0, (1e-2, 1e2)) * RBF(np.ones(Z.shape[1]), (5e-2, 1e2))
        self.gp_ = GaussianProcessClassifier(k, n_restarts_optimizer=2, random_state=self.random_state).fit(Z, y)
        self.classes_ = self.gp_.classes_
        return self

    def predict_proba(self, X):
        return self.gp_.predict_proba(self.sc_.transform(pd.DataFrame(X)[self.gp_cols]))

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)
