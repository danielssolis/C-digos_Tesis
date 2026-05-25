import pandas as pd


INPUT_FILE = "data/dataset_banio.csv"   # este ya viene con ;
OUTPUT_FILE = "data/dataset_banio_windows.csv"

INPUT_SEP = ";"
OUTPUT_SEP = ";"
WINDOW_SIZE = "30s"


def main():
    # Leer dataset del baño
    df = pd.read_csv(INPUT_FILE, sep=INPUT_SEP, decimal=".")

    # Limpiar nombres de columnas
    df.columns = [str(col).strip().replace("\ufeff", "") for col in df.columns]

    print("Columnas detectadas:")
    print(df.columns.tolist())

    if "timestamp" not in df.columns:
        raise ValueError("No se encontró la columna 'timestamp'.")

    # Convertir timestamp
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    # Forzar todas las demás columnas a numéricas
    columnas_datos = [col for col in df.columns if col != "timestamp"]
    for col in columnas_datos:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Opcional: revisar cuántos NaN se generaron
    print("\nValores NaN por columna después de convertir a numérico:")
    print(df[columnas_datos].isna().sum())

    # Ordenar y usar timestamp como índice
    df = df.sort_values("timestamp").set_index("timestamp")

    # Mantener último valor conocido
    df = df.ffill()

    # Definir agregaciones
    agg_dict = {}

    for col in df.columns:
        c = col.lower()

        if any(x in c for x in ["temperature", "humidity", "distance"]):
            agg_dict[col] = ["mean", "min", "max", "std"]

        elif any(x in c for x in ["movement", "flow_state"]):
            agg_dict[col] = ["mean", "sum", "max"]

        else:
            agg_dict[col] = ["mean", "max"]

    # Construir ventanas
    df_windows = df.resample(WINDOW_SIZE).agg(agg_dict)

    # Aplanar nombres de columnas
    df_windows.columns = [f"{col}_{stat}" for col, stat in df_windows.columns]

    # Eliminar ventanas vacías y rellenar NaN
    df_windows = df_windows.dropna(how="all").fillna(0).reset_index()

    # Redondear columnas numéricas para evitar números larguísimos
    columnas_numericas = df_windows.select_dtypes(include=["number"]).columns
    df_windows[columnas_numericas] = df_windows[columnas_numericas].round(6)

    # Guardar CSV
    df_windows.to_csv(
        OUTPUT_FILE,
        index=False,
        sep=OUTPUT_SEP,
        decimal=".",         # mantener punto decimal
        float_format="%.6f"  # controlar longitud
    )

    print("\n✅ Dataset ventanas baño creado correctamente")
    print("Archivo:", OUTPUT_FILE)
    print("Filas:", len(df_windows))
    print("Columnas:", len(df_windows.columns))
    print("\nPrimeras filas:")
    print(df_windows.head().to_string())


if __name__ == "__main__":
    main()