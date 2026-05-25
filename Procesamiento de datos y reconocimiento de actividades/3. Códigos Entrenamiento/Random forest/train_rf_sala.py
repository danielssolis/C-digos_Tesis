import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import LabelEncoder


INPUT_FILE = "data/dataset_sala_windows_labeled.csv"
MODEL_FILE = "models/rf_sala.joblib"
ENCODER_FILE = "models/le_sala.joblib"


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega timestamp_colombia, hora_colombia y es_noche si no existen.
    """
    if "timestamp" not in df.columns:
        raise ValueError("El dataset debe contener la columna 'timestamp'.")

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["timestamp_colombia"] = df["timestamp"].dt.tz_convert("America/Bogota")
    df["hora_colombia"] = df["timestamp_colombia"].dt.hour
    df["es_noche"] = df["hora_colombia"].apply(lambda x: 1 if x >= 19 or x <= 7 else 0)

    return df


def main():
    # =========================
    # 1. Cargar dataset
    # =========================
    df = pd.read_csv(INPUT_FILE, sep=";", decimal=".")
    df.columns = [str(col).strip().replace("\ufeff", "") for col in df.columns]

    print("===== COLUMNAS DETECTADAS =====")
    print(df.columns.tolist())

    if "activity" not in df.columns:
        raise ValueError("El dataset debe contener la columna 'activity'.")

    # =========================
    # 2. Agregar variables de tiempo
    # =========================
    df = add_time_features(df)

    # =========================
    # 3. Limpiar etiquetas
    # =========================
    df["activity"] = df["activity"].astype(str).str.strip().str.lower()

    invalid_labels = {"", "nan", "none", "null"}
    df = df[~df["activity"].isin(invalid_labels)].copy()

    # Actividades esperadas en sala
    valid_classes = {"ver_tv", "uso_sofa_sala", "descanso_sala", "sin_act_sala"}
    df = df[df["activity"].isin(valid_classes)].copy()

    if len(df) == 0:
        raise ValueError("No quedaron filas válidas después de limpiar 'activity'.")

    print("\n===== DISTRIBUCIÓN DE CLASES =====")
    print(df["activity"].value_counts())

    # =========================
    # 4. Separar X e y
    # =========================
    X = df.drop(
        columns=[
            "activity",
            "timestamp",
            "timestamp_colombia",
        ],
        errors="ignore"
    ).copy()

    X = X.apply(pd.to_numeric, errors="coerce")

    # Eliminar columnas totalmente vacías
    empty_cols = X.columns[X.isna().all()].tolist()
    if empty_cols:
        print("\n===== COLUMNAS ELIMINADAS POR ESTAR VACÍAS =====")
        for col in empty_cols:
            print(col)
        X = X.drop(columns=empty_cols)

    if X.shape[1] == 0:
        raise ValueError("No quedaron variables válidas para entrenar.")

    y = df["activity"].astype(str)

    # =========================
    # 5. Codificar etiquetas
    # =========================
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    print("\n===== CLASES CODIFICADAS =====")
    print(list(le.classes_))

    # =========================
    # 6. Dividir train/test
    # =========================
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y_encoded,
        test_size=0.2,
        random_state=42,
        stratify=y_encoded
    )

    # =========================
    # 7. Modelo
    # =========================
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

    # =========================
    # 8. Entrenamiento
    # =========================
    model.fit(X_train, y_train)

    # =========================
    # 9. Evaluación
    # =========================
    y_pred = model.predict(X_test)

    print("\n===== RESULTADOS RANDOM FOREST SALA =====\n")
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print("\nClassification Report:\n")
    print(classification_report(y_test, y_pred, target_names=le.classes_, zero_division=0))
    print("Confusion Matrix:\n")
    print(confusion_matrix(y_test, y_pred))

    # =========================
    # 10. Importancia de variables
    # =========================
    rf = model.named_steps["rf"]
    feature_importance = pd.DataFrame({
        "feature": X.columns,
        "importance": rf.feature_importances_
    }).sort_values(by="importance", ascending=False)

    print("\n===== TOP 20 VARIABLES MÁS IMPORTANTES =====\n")
    print(feature_importance.head(20).to_string(index=False))

    # =========================
    # 11. Guardar
    # =========================
    joblib.dump(model, MODEL_FILE)
    joblib.dump(le, ENCODER_FILE)

    print("\n✅ Modelo guardado en:", MODEL_FILE)
    print("✅ Codificador guardado en:", ENCODER_FILE)


if __name__ == "__main__":
    main()