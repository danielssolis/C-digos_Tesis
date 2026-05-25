import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC   # 🔥 IMPORTANTE


INPUT_FILE = "data/dataset_sala_windows_labeled.csv"
MODEL_FILE = "models/svm_sala.joblib"   # 🔥 nombre actualizado
ENCODER_FILE = "models/le_sala_svm.joblib"


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    if "timestamp" not in df.columns:
        raise ValueError("El dataset debe contener la columna 'timestamp'.")

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["timestamp_colombia"] = df["timestamp"].dt.tz_convert("America/Bogota")
    df["hora_colombia"] = df["timestamp_colombia"].dt.hour
    df["es_noche"] = df["hora_colombia"].apply(lambda x: 1 if x >= 19 or x <= 7 else 0)

    return df


def main():
    df = pd.read_csv(INPUT_FILE, sep=";", decimal=".")
    df.columns = [str(col).strip().replace("\ufeff", "") for col in df.columns]

    print("===== COLUMNAS DETECTADAS =====")
    print(df.columns.tolist())

    if "activity" not in df.columns:
        raise ValueError("El dataset debe contener la columna 'activity'.")

    df = add_time_features(df)

    df["activity"] = df["activity"].astype(str).str.strip().str.lower()

    invalid_labels = {"", "nan", "none", "null"}
    df = df[~df["activity"].isin(invalid_labels)].copy()

    valid_classes = {"ver_tv", "uso_sofa_sala", "descanso_sala", "sin_act_sala"}
    df = df[df["activity"].isin(valid_classes)].copy()

    print("\n===== DISTRIBUCIÓN DE CLASES =====")
    print(df["activity"].value_counts())

    # =========================
    # X e y
    # =========================
    X = df.drop(
        columns=["activity", "timestamp", "timestamp_colombia"],
        errors="ignore"
    ).copy()

    X = X.apply(pd.to_numeric, errors="coerce")

    empty_cols = X.columns[X.isna().all()].tolist()
    if empty_cols:
        print("\n===== COLUMNAS ELIMINADAS =====")
        for col in empty_cols:
            print(col)
        X = X.drop(columns=empty_cols)

    y = df["activity"].astype(str)

    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    print("\n===== CLASES CODIFICADAS =====")
    print(list(le.classes_))

    # =========================
    # SPLIT
    # =========================
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y_encoded,
        test_size=0.2,
        random_state=42,
        stratify=y_encoded
    )

    # =========================
    # 🔥 SVM OPTIMIZADO (MISMO DEL BAÑO)
    # =========================
    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),

        ("svm", SVC(
            kernel="rbf",
            C=5,
            gamma=0.005,

            # 🔥 clave: mismo enfoque que te funcionó
            class_weight={0:2, 1:2, 2:2, 3:2},

            probability=True,
            random_state=42
        ))
    ])

    # =========================
    # ENTRENAMIENTO
    # =========================
    model.fit(X_train, y_train)

    # =========================
    # EVALUACIÓN
    # =========================
    y_pred = model.predict(X_test)

    print("\n===== RESULTADOS SVM SALA =====\n")
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
    # GUARDAR
    # =========================
    joblib.dump(model, MODEL_FILE)
    joblib.dump(le, ENCODER_FILE)

    print("\n✅ Modelo SVM guardado en:", MODEL_FILE)
    print("✅ Codificador guardado en:", ENCODER_FILE)


if __name__ == "__main__":
    main()