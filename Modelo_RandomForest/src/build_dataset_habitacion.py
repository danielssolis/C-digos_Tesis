import pandas as pd


def main():
    df = pd.read_csv("data/dataset_real_clean.csv")

    # Filtrar columnas de habitación
    columnas_habitacion = [col for col in df.columns if "habitacion" in col]

    columnas_finales = ["timestamp"] + columnas_habitacion

    df_hab = df[columnas_finales]

    df_hab.to_csv("data/dataset_habitacion.csv", index=False)

    print("✅ Dataset habitación creado")
    print("Columnas:", len(df_hab.columns))
    print(df_hab.head())


if __name__ == "__main__":
    main()