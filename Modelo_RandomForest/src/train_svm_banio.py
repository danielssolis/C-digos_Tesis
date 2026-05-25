import pandas as pd
import joblib

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.svm import SVC
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import LabelEncoder, StandardScaler


INPUT_FILE = "data/dataset_banio_windows_labeled.csv"
MODEL_FILE = "models/svm_banio.joblib"
ENCODER_FILE = "models/le_banio_svm.joblib"

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

    if "uso_inodoro_completado" in df.columns:
        df["uso_inodoro_completado"] = pd.to_numeric(
            df["uso_inodoro_completado"], errors="coerce"
        ).fillna(0)

    for col in df.columns:
        if col not in ["timestamp", "activity"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    distance_cols = [c for c in df.columns if "distance" in c.lower()]
    for col in distance_cols:
        df.loc[df[col] > 400, col] = pd.NA
        df.loc[df[col] < 0, col] = pd.NA

    empty_cols = df.columns[df.isna().all()].tolist()
    if empty_cols:
        print("\n===== COLUMNAS ELIMINADAS =====")
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

    print("\n===== DISTRIBUCIÓN DE CLASES =====")
    print(df["activity"].value_counts())

    # =========================
    # X e y
    # =========================
    X = df.drop(
        columns=["activity", "timestamp", "uso_inodoro_completado"],
        errors="ignore"
    ).copy()

    y = df["activity"].astype(str)

    X = X.apply(pd.to_numeric, errors="coerce")

    empty_cols = X.columns[X.isna().all()].tolist()
    if empty_cols:
        print("\n===== COLUMNAS ELIMINADAS EN X =====")
        for col in empty_cols:
            print(col)
        X = X.drop(columns=empty_cols)

    # =========================
    # Encoder
    # =========================
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    print("\n===== CLASES CODIFICADAS =====")
    print(list(le.classes_))

    # =========================
    # Split temporal
    # =========================
    split_idx = int(len(df) * 0.8)

    X_train = X.iloc[:split_idx]
    X_test = X.iloc[split_idx:]

    y_train = y_encoded[:split_idx]
    y_test = y_encoded[split_idx:]

    print("\n===== TAMAÑO TRAIN / TEST =====")
    print("Train:", len(X_train))
    print("Test :", len(X_test))

    # =========================
    # 🔥 MODELO SVM (BIEN AJUSTADO)
    # =========================
    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),

        ("svm", SVC(
            kernel="rbf",

            # 🔥 clave para mejorar rendimiento
            C=5,
            gamma=0.005,

            class_weight={0:2, 1:2, 2:2, 3:2},
            probability=True,
            random_state=42
        ))
    ])

    # =========================
    # Entrenamiento
    # =========================
    model.fit(X_train, y_train)

    # =========================
    # Evaluación
    # =========================
    y_pred = model.predict(X_test)

    print("\n===== RESULTADOS SVM BAÑO =====\n")
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

    # =========================
    # Guardar
    # =========================
    joblib.dump(model, MODEL_FILE)
    joblib.dump(le, ENCODER_FILE)

    print("\n✅ Modelo SVM guardado en:", MODEL_FILE)
    print("✅ Codificador guardado en:", ENCODER_FILE)


if __name__ == "__main__":
    main()