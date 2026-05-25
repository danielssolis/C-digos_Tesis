import pandas as pd


def main():
    # Cargar dataset real exportado desde InfluxDB
    df = pd.read_csv("data/dataset_real2.csv")

    # Convertir timestamp a fecha
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    # Ordenar por tiempo
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Rellenar valores faltantes con el último valor conocido
    df = df.ffill()

    # Lo que siga vacío, llenarlo con 0
    df = df.fillna(0)

    # Guardar dataset limpio
    df.to_csv("data/dataset_real_clean2.csv", index=False)

    print("✅ Dataset limpio guardado en data/dataset_real_clean2.csv")
    print("Filas:", len(df))
    print("Columnas:", len(df.columns))
    print("\nPrimeras 5 filas:")
    print(df.head().to_string())


if __name__ == "__main__":
    main()