import pandas as pd
import joblib

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import LabelEncoder


INPUT_FILE = "data/dataset_habitacion_windows_labeled.csv"

MODEL_FILE = "models/rf_habitacion.joblib"
ENCODER_FILE = "models/le_habitacion.joblib"

CSV_SEP = ";"


def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]

    if "activity" not in df.columns:
        raise ValueError("No se encontró la columna 'activity'.")

    df["activity"] = df["activity"].astype(str).str.strip().str.lower()

    invalid_labels = {"", "nan", "none", "null"}
    df = df[~df["activity"].isin(invalid_labels)].copy()

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

    for col in df.columns:
        if col not in ["timestamp", "activity"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    distance_cols = [c for c in df.columns if "distance" in c.lower()]
    for col in distance_cols:
        df.loc[df[col] > 400, col] = pd.NA
        df.loc[df[col] < 0, col] = pd.NA

    empty_cols = df.columns[df.isna().all()].tolist()
    if empty_cols:
        print("\n===== COLUMNAS ELIMINADAS POR ESTAR VACÍAS =====")
        for col in empty_cols:
            print(col)
        df = df.drop(columns=empty_cols)

    if "timestamp" in df.columns:
        df = df.sort_values("timestamp").reset_index(drop=True)

    return df


def main():
    df = pd.read_csv(INPUT_FILE, sep=CSV_SEP, decimal=".")
    df = clean_dataset(df)

    print("===== COLUMNAS DETECTADAS =====")
    print(df.columns.tolist())

    if len(df) == 0:
        raise ValueError("No quedaron filas válidas en el dataset.")

    print("\n===== DISTRIBUCIÓN DE CLASES =====")
    print(df["activity"].value_counts())

    X = df.drop(
        columns=[
            "activity",
            "timestamp",
        ],
        errors="ignore"
    ).copy()

    y = df["activity"].astype(str)

    X = X.apply(pd.to_numeric, errors="coerce")

    empty_cols = X.columns[X.isna().all()].tolist()
    if empty_cols:
        print("\n===== COLUMNAS ELIMINADAS EN X POR ESTAR VACÍAS =====")
        for col in empty_cols:
            print(col)
        X = X.drop(columns=empty_cols)

    if X.shape[1] == 0:
        raise ValueError("No quedaron variables de entrada válidas.")

    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    print("\n===== CLASES CODIFICADAS =====")
    print(list(le.classes_))

    split_idx = int(len(df) * 0.8)

    X_train = X.iloc[:split_idx].copy()
    X_test = X.iloc[split_idx:].copy()

    y_train = y_encoded[:split_idx]
    y_test = y_encoded[split_idx:]

    print("\n===== TAMAÑO TRAIN / TEST =====")
    print("Train:", len(X_train))
    print("Test :", len(X_test))

    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("rf", RandomForestClassifier(
            n_estimators=300,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
            class_weight="balanced"
        ))
    ])

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    print("\n===== RESULTADOS RANDOM FOREST HABITACIÓN =====\n")
    print("Accuracy:", accuracy_score(y_test, y_pred))

    print("\nClassification Report:\n")
    print(classification_report(
        y_test,
        y_pred,
        target_names=le.classes_,
        zero_division=0
    ))

    print("Confusion Matrix:\n")
    print(confusion_matrix(y_test, y_pred))

    rf = model.named_steps["rf"]

    feature_importance = pd.DataFrame({
        "feature": X.columns,
        "importance": rf.feature_importances_
    }).sort_values(by="importance", ascending=False)

    print("\n===== TOP 20 VARIABLES MÁS IMPORTANTES =====\n")
    print(feature_importance.head(20).to_string(index=False))

    joblib.dump(model, MODEL_FILE)
    joblib.dump(le, ENCODER_FILE)

    print("\n✅ Modelo guardado en:", MODEL_FILE)
    print("✅ Codificador guardado en:", ENCODER_FILE)


if __name__ == "__main__":
    main()