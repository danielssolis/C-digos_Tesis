import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter


INPUT_FILE = "data/dataset_sala2.csv"
OUTPUT_CSV = "data/dataset_sala_windows2.csv"
OUTPUT_XLSX = "data/dataset_sala_windows_label2.xlsx"

INPUT_SEP = ";"
OUTPUT_SEP = ";"
WINDOW_SIZE = "30s"


def auto_adjust_columns(ws, max_width=24):
    for col_cells in ws.columns:
        col_letter = get_column_letter(col_cells[0].column)
        max_length = 0

        for cell in col_cells:
            try:
                value = "" if cell.value is None else str(cell.value)
                max_length = max(max_length, len(value))
            except Exception:
                pass

        ws.column_dimensions[col_letter].width = min(max_length + 2, max_width)


def prepare_excel_for_labeling(xlsx_path: str):
    wb = load_workbook(xlsx_path)
    ws = wb["Etiquetado"]

    ws.freeze_panes = "C2"
    ws.auto_filter.ref = ws.dimensions

    header_fill = PatternFill(fill_type="solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    header_map = {cell.value: cell.column for cell in ws[1]}
    activity_col = header_map.get("activity")

    label_fill = PatternFill(fill_type="solid", fgColor="FFF2CC")

    if activity_col:
        letter = get_column_letter(activity_col)
        for row in range(1, ws.max_row + 1):
            ws[f"{letter}{row}"].fill = label_fill

    if "Listas" in wb.sheetnames:
        del wb["Listas"]

    ws_list = wb.create_sheet("Listas")
    ws_list["A1"] = "sin_act_sala"
    ws_list["A2"] = "ver_tv"
    ws_list["A3"] = "descanso_sala"
    ws_list.sheet_state = "hidden"

    if activity_col:
        letter = get_column_letter(activity_col)
        dv_activity = DataValidation(
            type="list",
            formula1="=Listas!$A$1:$A$3",
            allow_blank=True
        )
        ws.add_data_validation(dv_activity)
        dv_activity.add(f"{letter}2:{letter}{ws.max_row}")

    auto_adjust_columns(ws)
    wb.save(xlsx_path)


def main():
    df = pd.read_csv(INPUT_FILE, sep=INPUT_SEP, decimal=".")
    df.columns = [str(col).strip().replace("\ufeff", "") for col in df.columns]

    print("Columnas detectadas:")
    print(df.columns.tolist())

    if "timestamp" not in df.columns:
        raise ValueError("No se encontró la columna 'timestamp'.")

    # Timestamp
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    # Convertir columnas numéricas
    columnas_datos = [col for col in df.columns if col != "timestamp"]
    for col in columnas_datos:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Limpieza básica de distancias inválidas:
    # 0 y >400 se consideran sin lectura
    for col in df.columns:
        if "distance" in col.lower():
            df[col] = df[col].mask(df[col] <= 0)
            df[col] = df[col].mask(df[col] > 400)

    # Ordenar e indexar
    df = df.sort_values("timestamp").set_index("timestamp")

    # ==========================================
    # ffill selectivo:
    # NO aplicar a distance ni movement
    # ==========================================
    for col in df.columns:
        c = col.lower()

        if "distance" in c or "movement" in c:
            continue

        df[col] = df[col].ffill()

    # =========================
    # Agregaciones pensadas para SALA
    # =========================
    agg_dict = {}

    for col in df.columns:
        c = col.lower()

        # Señales continuas fisiológicas o ambientales
        if any(x in c for x in ["heartbeat", "respiration", "temperature", "humidity"]):
            agg_dict[col] = ["mean", "min", "max", "std"]

        # Distancias: usar LAST porque interesa el estado final de la ventana
        # y también MIN/MAX para revisar rangos reales
        elif "distance" in c:
            agg_dict[col] = ["last", "min", "max"]

        # Corriente: usar LAST y MAX
        elif "current" in c:
            agg_dict[col] = ["last", "max"]

        # Estados discretos: LAST
        elif any(x in c for x in ["presence", "in_bed", "sleep_state"]):
            agg_dict[col] = ["last"]

        # Movimiento: LAST y SUM
        elif "movement" in c:
            agg_dict[col] = ["last", "sum", "max"]

        # Eventos acumulativos
        elif any(x in c for x in ["turnover", "body_move", "apnea"]):
            agg_dict[col] = ["sum", "max"]

        # Fallback
        else:
            agg_dict[col] = ["last"]

    df_windows = df.resample(WINDOW_SIZE).agg(agg_dict)

    # Aplanar nombres de columnas
    df_windows.columns = [f"{col}_{stat}" for col, stat in df_windows.columns]

    # No borrar ventanas que sí existen en tiempo; solo limpiar completamente vacías
    df_windows = df_windows.dropna(how="all")

    # Rellenar NaN después del resample
    df_windows = df_windows.fillna(0).reset_index()

    # Redondear numéricas
    columnas_numericas = df_windows.select_dtypes(include=["number"]).columns
    df_windows[columnas_numericas] = df_windows[columnas_numericas].round(6)

    # Columna para etiquetar
    if "activity" not in df_windows.columns:
        df_windows["activity"] = ""

    # Reordenar columnas
    cols = df_windows.columns.tolist()
    cols_reordered = []

    for c in ["timestamp", "activity"]:
        if c in cols:
            cols_reordered.append(c)

    for c in cols:
        if c not in cols_reordered:
            cols_reordered.append(c)

    df_windows = df_windows[cols_reordered].copy()

    # Guardar CSV técnico
    df_windows.to_csv(
        OUTPUT_CSV,
        index=False,
        sep=OUTPUT_SEP,
        decimal=".",
        float_format="%.6f"
    )

    # Excel para etiquetado (sin timezone)
    df_excel = df_windows.copy()
    if "timestamp" in df_excel.columns:
        df_excel["timestamp"] = pd.to_datetime(
            df_excel["timestamp"], utc=True
        ).dt.tz_localize(None)

    with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as writer:
        df_excel.to_excel(writer, index=False, sheet_name="Etiquetado")

    prepare_excel_for_labeling(OUTPUT_XLSX)

    print("\n✅ Dataset ventanas sala creado correctamente")
    print("CSV técnico:", OUTPUT_CSV)
    print("Excel etiquetado:", OUTPUT_XLSX)
    print("Filas:", len(df_windows))
    print("Columnas:", len(df_windows.columns))
    print("\nPrimeras filas:")
    print(df_windows.head().to_string())


if __name__ == "__main__":
    main()