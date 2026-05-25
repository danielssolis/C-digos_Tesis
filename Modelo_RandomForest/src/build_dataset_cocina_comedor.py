import pandas as pd


INPUT_FILE = "data/dataset_real_clean2.csv"
OUTPUT_FILE = "data/dataset_cocina_comedor2.csv"

INPUT_SEP = ","
OUTPUT_SEP = ";"


def main():
    df = pd.read_csv(INPUT_FILE, sep=INPUT_SEP)
    df.columns = [str(col).strip().replace("\ufeff", "") for col in df.columns]

    print("Columnas detectadas en dataset principal:")
    print(df.columns.tolist())

    if "timestamp" not in df.columns:
        raise ValueError("No se encontró la columna 'timestamp'.")

    columnas_cc = [
        col for col in df.columns
        if ("cocina" in col.lower()) or ("comedor" in col.lower())
    ]

    if len(columnas_cc) == 0:
        raise ValueError("No se encontraron columnas relacionadas con cocina/comedor.")

    columnas_finales = ["timestamp"] + columnas_cc
    df_cc = df[columnas_finales].copy()

    df_cc.to_csv(OUTPUT_FILE, index=False, sep=OUTPUT_SEP)

    print("\n✅ Dataset cocina/comedor creado correctamente")
    print("Archivo:", OUTPUT_FILE)
    print("Filas:", len(df_cc))
    print("Columnas:", len(df_cc.columns))
    print("\nColumnas seleccionadas:")
    print(df_cc.columns.tolist())
    print("\nPrimeras filas:")
    print(df_cc.head().to_string())


if __name__ == "__main__":
    main()