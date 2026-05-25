import pandas as pd


CSV_FILE = "data/dataset_sala_windows.csv"
XLSX_FILE = "data/dataset_sala_windows_label.xlsx"
OUTPUT_FILE = "data/dataset_sala_windows_labeled.csv"

CSV_SEP = ";"


def main():
    # Leer archivos
    df_csv = pd.read_csv(CSV_FILE, sep=CSV_SEP, decimal=".")
    df_xlsx = pd.read_excel(XLSX_FILE, sheet_name="Etiquetado")

    # Limpiar nombres de columnas
    df_csv.columns = [str(c).strip().replace("\ufeff", "") for c in df_csv.columns]
    df_xlsx.columns = [str(c).strip().replace("\ufeff", "") for c in df_xlsx.columns]

    # Validar tamaños
    if len(df_csv) != len(df_xlsx):
        raise ValueError(
            f"La cantidad de filas no coincide. CSV={len(df_csv)} | XLSX={len(df_xlsx)}"
        )

    # Validar columna de etiquetas
    if "activity" not in df_xlsx.columns:
        raise ValueError("No se encontró la columna 'activity' en el Excel.")

    # Copiar etiquetas
    df_csv["activity"] = df_xlsx["activity"]

    # Limpiar texto
    df_csv["activity"] = df_csv["activity"].astype(str).str.strip().str.lower()

    # Guardar CSV final para entrenamiento
    df_csv.to_csv(
        OUTPUT_FILE,
        index=False,
        sep=CSV_SEP,
        decimal=".",
        float_format="%.6f"
    )

    print("✅ Etiquetas copiadas correctamente")
    print("Archivo final:", OUTPUT_FILE)
    print("\nConteo de activity:")
    print(df_csv["activity"].value_counts(dropna=False))


if __name__ == "__main__":
    main()