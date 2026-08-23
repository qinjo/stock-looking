import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, roc_auc_score


def _train_model(X_train, y_train):
    model = LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        num_leaves=15,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=-1,
    )
    model.fit(X_train, y_train)
    return model


def walk_forward_eval(df, feature_cols, label_col, min_train=500, step=60):
    df = df.dropna(subset=feature_cols + [label_col]).reset_index(drop=True)
    if len(df) <= min_train:
        raise ValueError("not enough data after dropping NaNs")

    y_true_all = []
    y_pred_all = []
    y_prob_all = []
    start = min_train
    while start < len(df):
        train = df.iloc[:start]
        test = df.iloc[start : start + step]
        if test.empty:
            break
        model = _train_model(train[feature_cols], train[label_col])
        y_pred_all.append(model.predict(test[feature_cols]))
        y_prob_all.append(model.predict_proba(test[feature_cols])[:, 1])
        y_true_all.append(test[label_col].values)
        start += step

    y_true = np.concatenate(y_true_all)
    y_pred = np.concatenate(y_pred_all)
    y_prob = np.concatenate(y_prob_all)
    return y_true, y_pred, y_prob


def evaluate(y_true, y_pred, y_prob):
    acc = accuracy_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    auc = roc_auc_score(y_true, y_prob) if len(np.unique(y_true)) > 1 else np.nan
    up_rate = float(y_true.mean())
    win_rate = tp / (tp + fp) if (tp + fp) else np.nan
    return {
        "n": int(len(y_true)),
        "up_rate": up_rate,
        "accuracy": acc,
        "auc": auc,
        "win_rate": win_rate,
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }
