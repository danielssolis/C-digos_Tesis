import pandas as pd


INPUT_FILE = "data/dataset_real_clean.csv"   # ← ESTE ES CON COMAS
OUTPUT_FILE = "data/dataset_banio.csv"

INPUT_SEP = ","   # ← origen
OUTPUT_SEP = ";"  # ← destino


def main():
    # Leer dataset original (con coma)
    df = pd.read_csv(INPUT_FILE, sep=INPUT_SEP)

    # Limpiar nombres de columnas
    df.columns = [str(col).strip().replace("\ufeff", "") for col in df.columns]

    print("Columnas detectadas:")
    print(df.columns.tolist())

    if "timestamp" not in df.columns:
        raise ValueError("No se encontró la columna 'timestamp'.")

    # Filtrar columnas del baño
    columnas_banio = [col for col in df.columns if "banio" in col.lower()]

    if not columnas_banio:
        raise ValueError("No se encontraron columnas del baño.")

    columnas_finales = ["timestamp"] + columnas_banio

    df_banio = df[columnas_finales].copy()

    # Guardar con ;
    df_banio.to_csv(OUTPUT_FILE, index=False, sep=OUTPUT_SEP)

    print("\n✅ Dataset baño creado correctamente")
    print("Archivo:", OUTPUT_FILE)
    print("Filas:", len(df_banio))
    print("Columnas:", len(df_banio.columns))


if __name__ == "__main__":
    main()