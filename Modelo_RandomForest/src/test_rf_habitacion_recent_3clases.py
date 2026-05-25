import pandas as pd
import joblib

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

INPUT_FILE = "data/dataset_habitacion_recent_windows_colombia.csv"
MODEL_FILE = "models/rf_habitacion_recent_3clases.joblib"
ENCODER_FILE = "models/le_habitacion_recent_3clases.joblib"


def apply_final_rule(pred_3class: str, es_noche: int) -> str:
    if pred_3class == "descanso_cama":
        return "dormir" if int(es_noche) == 1 else "siesta"
    return pred_3class


def build_y_true_final(activity: str, es_noche: int) -> str:
    activity = str(activity).strip().lower()
    if activity == "descanso_cama":
        return "dormir" if int(es_noche) == 1 else "siesta"
    return activity


def main():
    df = pd.read_csv(INPUT_FILE, sep=";", decimal=".")
    df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]

    if "activity" not in df.columns:
        raise ValueError("No se encontró la columna 'activity'.")
    if "es_noche" not in df.columns:
        raise ValueError("No se encontró la columna 'es_noche'.")

    df["activity"] = df["activity"].astype(str).str.strip().str.lower()

    invalid_labels = {"", "nan", "none", "null"}
    df = df[~df["activity"].isin(invalid_labels)].copy()

    valid_classes = {"descanso_cama", "sin_act_hab", "ver_tv"}
    df = df[df["activity"].isin(valid_classes)].copy()

    print("===== DISTRIBUCIÓN DE CLASES REALES =====")
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

    model = joblib.load(MODEL_FILE)
    le = joblib.load(ENCODER_FILE)

    expected_features = list(model.named_steps["imputer"].feature_names_in_)

    # Alinear columnas al modelo
    for col in expected_features:
        if col not in X.columns:
            X[col] = pd.NA

    X = X[expected_features].copy()
    X = X.apply(pd.to_numeric, errors="coerce")

    y_pred_encoded = model.predict(X)
    y_pred_3class = le.inverse_transform(y_pred_encoded)

    y_pred_final = [
        apply_final_rule(pred, es_noche)
        for pred, es_noche in zip(y_pred_3class, df["es_noche"])
    ]

    y_true_final = [
        build_y_true_final(act, es_noche)
        for act, es_noche in zip(df["activity"], df["es_noche"])
    ]

    labels_final = ["dormir", "siesta", "sin_act_hab", "ver_tv"]

    print("\n===== RESULTADOS FINALES (MODELO + REGLA) =====\n")
    print("Accuracy:", accuracy_score(y_true_final, y_pred_final))
    print("\nClassification Report:\n")
    print(classification_report(y_true_final, y_pred_final, labels=labels_final, zero_division=0))
    print("Confusion Matrix:\n")
    print(confusion_matrix(y_true_final, y_pred_final, labels=labels_final))

    print("\n===== ORDEN DE CLASES =====")
    print(labels_final)


if __name__ == "__main__":
    main()