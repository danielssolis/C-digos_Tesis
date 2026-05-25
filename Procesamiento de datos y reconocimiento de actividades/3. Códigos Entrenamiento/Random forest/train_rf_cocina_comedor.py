import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import LabelEncoder


INPUT_FILE = "data/dataset_cocina_comedor_windows_labeled.csv"

MODEL_FILE = "models/rf_cocina_comedor.joblib"
ENCODER_FILE = "models/le_cocina_comedor.joblib"


def main():
    df = pd.read_csv(INPUT_FILE, sep=";", decimal=".")
    df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]

    print("===== COLUMNAS DETECTADAS =====")
    print(df.columns.tolist())

    if "activity" not in df.columns:
        raise ValueError("El dataset debe contener la columna 'activity'.")

    df["activity"] = df["activity"].astype(str).str.strip().str.lower()

    invalid = {"", "nan", "none", "null"}
    df = df[~df["activity"].isin(invalid)].copy()

    valid_classes = {
        "sin_act_cocina_comedor",
        "uso_lavaplatos",
        "cocinando",
        "consumo_alimentos",
    }

    df = df[df["activity"].isin(valid_classes)].copy()

    if len(df) == 0:
        raise ValueError("No quedaron filas válidas para entrenar.")

    print("\n===== DISTRIBUCIÓN DE CLASES =====")
    print(df["activity"].value_counts())

    X = df.drop(
        columns=[
            "activity",
            "timestamp",
            "timestamp_colombia",
        ],
        errors="ignore"
    ).copy()

    X = X.apply(pd.to_numeric, errors="coerce")

    empty_cols = X.columns[X.isna().all()].tolist()
    if empty_cols:
        print("\n===== COLUMNAS ELIMINADAS POR ESTAR VACÍAS =====")
        print(empty_cols)
        X = X.drop(columns=empty_cols)

    y = df["activity"].astype(str)

    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    print("\n===== CLASES CODIFICADAS =====")
    print(list(le.classes_))

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y_encoded,
        test_size=0.2,
        random_state=42,
        stratify=y_encoded
    )

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

    print("\n===== RESULTADOS RANDOM FOREST COCINA/COMEDOR =====\n")
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

    importances = pd.DataFrame({
        "feature": X.columns,
        "importance": rf.feature_importances_
    }).sort_values(by="importance", ascending=False)

    print("\n===== TOP 20 VARIABLES MÁS IMPORTANTES =====\n")
    print(importances.head(20).to_string(index=False))

    joblib.dump(model, MODEL_FILE)
    joblib.dump(le, ENCODER_FILE)

    print("\n✅ Modelo guardado en:", MODEL_FILE)
    print("✅ Codificador guardado en:", ENCODER_FILE)


if __name__ == "__main__":
    main()