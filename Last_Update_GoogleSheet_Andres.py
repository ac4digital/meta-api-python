import os
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# =============================
# 🔐 AUTENTICACIÓN GOOGLE SHEETS
# =============================
SERVICE_ACCOUNT_FILE = 'facebookcampaignsdr-andres.json'
SPREADSHEET_ID = '1Lob1WrtVsb0alLpVHV612nEg71y6ETqCLv3Bc8OtqjU'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(credentials)

# =============================
# 📄 ABRIR HOJA
# =============================
sheet = client.open_by_key(SPREADSHEET_ID)
worksheet = sheet.worksheet("October")

# =============================
# 📥 LEER HOJA EXISTENTE
# =============================
existing_data = worksheet.get_all_values()[1:]  # Salta A1 (fecha)
if existing_data:
    headers = existing_data[0]
    rows = existing_data[1:]
    df_sheet = pd.DataFrame(rows, columns=headers)
else:
    df_sheet = pd.DataFrame(columns=["Campaign ID", "Campaign Name", "Spend", "Leads", "CPL", "Status"])

# =============================
# 📥 LEER CSV NUEVO
# =============================
df_csv = pd.read_csv("Campaign_Insights_Andres.csv", keep_default_na=False)

# =============================
# 🧹 LIMPIEZA Y NORMALIZACIÓN
# =============================
# Limpiar nombres de columnas
df_sheet.columns = df_sheet.columns.str.strip().str.lower()
df_csv.columns = df_csv.columns.str.strip().str.lower()

# Asegurar existencia de campaign id
if 'campaign id' not in df_sheet.columns:
    df_sheet['campaign id'] = ''

# Limpiar datos y asegurar que sean texto
for df in [df_sheet, df_csv]:
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    df.replace([np.nan, 'nan', 'None'], '', inplace=True)
    df.fillna('', inplace=True)

# =============================
# 🔗 MERGE POR CAMPAIGN ID
# =============================
df_merged = pd.merge(df_sheet, df_csv, on='campaign id', how='outer', suffixes=('', '_new'))

#==================================
# ✅ ORDENAR POR NOMBRE DE CAMPAÑA
#==================================
if 'campaign name' in df_merged.columns:
    df_merged.sort_values(by='campaign name', ascending=True, inplace=True, key=lambda col: col.str.lower())
    df_merged.reset_index(drop=True, inplace=True)


# =============================
# 🔄 ACTUALIZAR COLUMNAS ESPECÍFICAS
# =============================
columnas_actualizar = ['spend', 'leads', 'cpl', 'status']

for col in columnas_actualizar:
    new_col = f"{col}_new"
    if new_col in df_merged.columns:
        df_merged[col] = np.where(df_merged[new_col] != '', df_merged[new_col], df_merged[col])
        df_merged.drop(columns=[new_col], inplace=True)

# =============================
# 📑 REORDENAR COLUMNAS COMO LA HOJA ORIGINAL
# =============================
column_order = df_sheet.columns.tolist()
df_merged = df_merged.reindex(columns=column_order)

# =============================
# 🧽 LIMPIEZA FINAL
# =============================
df_merged.fillna('', inplace=True)
df_merged.replace(['nan', 'None'], '', inplace=True)

# =============================
# 📅 ACTUALIZAR FECHA EN A1
# =============================
fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
worksheet.update_acell('A1', f"Last updated: {fecha_actual}")

# =============================
# ☁️ SUBIR A GOOGLE SHEET (SOLO VALORES)
# =============================
worksheet.update(
    values=[df_merged.columns.tolist()] + df_merged.values.tolist(),
    range_name='A2'
)

print("✅ Google Sheet actualizado correctamente.")
print("📅 Fecha:", fecha_actual)
print("📊 Total filas:", len(df_merged))
