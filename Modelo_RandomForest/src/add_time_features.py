import pandas as pd

INPUT_FILE = "data/dataset_habitacion_windows_colombia.csv"
OUTPUT_FILE = "data/dataset_habitacion_windows_colombia_v2.csv"


def main():
    df = pd.read_csv(INPUT_FILE, sep=";", decimal=",")

    df.columns = [str(col).strip().replace("\ufeff", "") for col in df.columns]

    if "timestamp_colombia" not in df.columns:
        raise ValueError(
            f"No se encontró la columna 'timestamp_colombia'. "
            f"Columnas detectadas: {df.columns.tolist()}"
        )

    df["timestamp_colombia"] = pd.to_datetime(df["timestamp_colombia"])

    df["hora_colombia"] = df["timestamp_colombia"].dt.hour
    df["es_noche"] = df["hora_colombia"].apply(lambda x: 1 if x >= 19 or x <= 7 else 0)

    df.to_csv(OUTPUT_FILE, index=False, sep=";", decimal=",")

    print("✅ Columnas agregadas correctamente")
    print("Archivo:", OUTPUT_FILE)
    print("\nPrimeras filas:")
    cols = ["timestamp_colombia", "hora_colombia", "es_noche"]
    print(df[cols].head().to_string())


if __name__ == "__main__":
    main()