import pandas as pd

INPUT_FILE = "data/dataset_habitacion_windows_final.csv"
OUTPUT_FILE = "data/dataset_habitacion_windows_3clases.csv"


def main():
    df = pd.read_csv(INPUT_FILE, sep=";", decimal=".")
    df.columns = [str(c).strip().replace("\ufeff", "") for c in df.columns]

    if "activity" not in df.columns:
        raise ValueError("No se encontró la columna 'activity'.")

    df["activity"] = df["activity"].astype(str).str.strip().str.lower()

    # Unificar dormir y siesta
    df["activity_3clases"] = df["activity"].replace({
        "dormir": "descanso_cama",
        "siesta": "descanso_cama",
        "ver_tv": "ver_tv",
        "sin_act_hab": "sin_act_hab",
    })

    # Limpiar inválidos
    invalid = {"", "nan", "none", "null"}
    df = df[~df["activity_3clases"].isin(invalid)].copy()

    df.to_csv(OUTPUT_FILE, index=False, sep=";", decimal=".")

    print("✅ Dataset de 3 clases generado")
    print("Archivo:", OUTPUT_FILE)
    print("\nDistribución:")
    print(df["activity_3clases"].value_counts())


if __name__ == "__main__":
    main()