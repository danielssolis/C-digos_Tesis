import pandas as pd


CSV_FILE = "data/dataset_banio_windows.csv"
XLSX_FILE = "data/dataset_banio_windows_label.xlsx"
OUTPUT_FILE = "data/dataset_banio_windows_labeled.csv"

CSV_SEP = ";"


def main():
    df_csv = pd.read_csv(CSV_FILE, sep=CSV_SEP, decimal=".")
    df_xlsx = pd.read_excel(XLSX_FILE, sheet_name="Etiquetado")

    df_csv.columns = [str(c).strip().replace("\ufeff", "") for c in df_csv.columns]
    df_xlsx.columns = [str(c).strip().replace("\ufeff", "") for c in df_xlsx.columns]

    if len(df_csv) != len(df_xlsx):
        raise ValueError(
            f"La cantidad de filas no coincide. CSV={len(df_csv)} | XLSX={len(df_xlsx)}"
        )

    required_cols = ["activity", "uso_inodoro_completado"]
    for col in required_cols:
        if col not in df_xlsx.columns:
            raise ValueError(f"No se encontró la columna '{col}' en el Excel.")

    df_csv["activity"] = df_xlsx["activity"]
    df_csv["uso_inodoro_completado"] = pd.to_numeric(
        df_xlsx["uso_inodoro_completado"], errors="coerce"
    )

    df_csv["activity"] = df_csv["activity"].astype(str).str.strip().str.lower()

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
    print("\nConteo de uso_inodoro_completado:")
    print(df_csv["uso_inodoro_completado"].value_counts(dropna=False))


if __name__ == "__main__":
    main()