import pandas as pd


INPUT_FILE = "data/dataset_habitacion_windows.csv"
OUTPUT_FILE = "data/dataset_habitacion_windows_colombia.csv"


def main():
    # Leer CSV con separador correcto: coma
    df = pd.read_csv(INPUT_FILE, sep=";")

    # Limpiar nombres de columnas
    df.columns = [str(col).strip().replace("\ufeff", "") for col in df.columns]

    if "timestamp" not in df.columns:
        raise ValueError(f"No se encontró la columna 'timestamp'. Columnas detectadas: {df.columns.tolist()}")

    # Convertir timestamp a datetime UTC
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    # Crear columna en hora Colombia
    df["timestamp_colombia"] = df["timestamp"].dt.tz_convert("America/Bogota")

    # Guardar la copia
    df.to_csv(OUTPUT_FILE, index=False)

    print("✅ Archivo convertido correctamente")
    print("Archivo:", OUTPUT_FILE)
    print("\nPrimeras filas:")
    print(df[["timestamp", "timestamp_colombia"]].head().to_string())


if __name__ == "__main__":
    main()