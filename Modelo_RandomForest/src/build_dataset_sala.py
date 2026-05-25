# src/build_dataset_sala.py
import pandas as pd

INPUT_FILE = "data/dataset_real_clean2.csv"   # archivo original general
OUTPUT_FILE = "data/dataset_sala2.csv"

INPUT_SEP = ","
OUTPUT_SEP = ";"


def main():
    df = pd.read_csv(INPUT_FILE, sep=INPUT_SEP)
    df.columns = [str(col).strip().replace("\ufeff", "") for col in df.columns]

    print("Columnas detectadas en dataset principal:")
    print(df.columns.tolist())

    if "timestamp" not in df.columns:
        raise ValueError("No se encontró la columna 'timestamp'.")

    columnas_sala = [col for col in df.columns if "sala" in col.lower()]

    if len(columnas_sala) == 0:
        raise ValueError("No se encontraron columnas relacionadas con 'sala'.")

    columnas_finales = ["timestamp"] + columnas_sala
    df_sala = df[columnas_finales].copy()

    df_sala.to_csv(OUTPUT_FILE, index=False, sep=OUTPUT_SEP)

    print("\n✅ Dataset sala creado correctamente")
    print("Archivo:", OUTPUT_FILE)
    print("Filas:", len(df_sala))
    print("Columnas:", len(df_sala.columns))
    print("\nColumnas de sala:")
    print(df_sala.columns.tolist())
    print("\nPrimeras filas:")
    print(df_sala.head().to_string())


if __name__ == "__main__":
    main()