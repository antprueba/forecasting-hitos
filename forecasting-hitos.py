import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Predicción de Hitos", layout="wide")

# --- ENCABEZADO ---
st.title("📊 Forecasting hitos 📊")

# --- GUÍA VISUAL PARA EL USUARIO ---
with st.expander("📢 IMPORTANTE: Formato del archivo Excel", expanded=True):
    st.markdown("""
    Para que el sistema funcione correctamente, **cada fila debe ser un hito**. 
    Si un proyecto tiene varios hitos, debes repetir el nombre del proyecto y el total en cada fila, como se muestra aquí:
    """)
    
    # Creación del ejemplo visual exacto
    data_ejemplo = {
        "Proyecto": ["Proyecto A", "Proyecto A", "Proyecto A", "Proyecto B"],
        "Total Proyecto": [150000, 150000, 150000, 80000],
        "Hito": ["Diseño Inicial", "Desarrollo", "Entrega Final", "Fase Única"],
        "% del Proyecto": [20, 50, 30, 100],
        "Fecha Inicio": ["2025-01-01", "2025-02-01", "2025-05-15", "2025-03-01"],
        "Fecha Fin": ["2025-01-31", "2025-05-14", "2025-06-30", "2025-04-30"]
    }
    df_ejemplo = pd.DataFrame(data_ejemplo)
    
    # Mostramos la tabla de ejemplo
    st.table(df_ejemplo)
    

st.divider()

# --- CARGA DE ARCHIVO ---
archivo_subido = st.file_uploader("Sube tu archivo Excel aquí", type=["xlsx"])

if archivo_subido is not None:
    try:
        df = pd.read_excel(archivo_subido)
        
        # Validar columnas necesarias
        cols_req = ["Proyecto", "Total Proyecto", "Hito", "% del Proyecto", "Fecha Inicio", "Fecha Fin"]
        if not all(c in df.columns for c in cols_req):
            st.error(f"Faltan columnas. Asegúrate de tener: {', '.join(cols_req)}")
        else:
            # --- PROCESAMIENTO ---
            df['Fecha Inicio'] = pd.to_datetime(df['Fecha Inicio'])
            df['Fecha Fin'] = pd.to_datetime(df['Fecha Fin'])
            
            # Ajuste de escala de porcentaje
            escala = 100 if df['% del Proyecto'].max() > 1 else 1
            
            # --- PANEL DE AUDITORÍA ---
            st.subheader("🔍 Verificación de Proyectos (Suma de Hitos)")
            audit = df.groupby('Proyecto')['% del Proyecto'].sum().reset_index()
            if escala == 1: audit['% del Proyecto'] *= 100
            
            num_proyectos = len(audit)
            cols_audit = st.columns(min(num_proyectos, 4))
            for i, (idx, row) in enumerate(audit.iterrows()):
                with cols_audit[i % 4]:
                    val = round(row['% del Proyecto'], 2)
                    if 99.9 <= val <= 100.1:
                        st.success(f"**{row['Proyecto']}**\n\n{val}% ✅")
                    else:
                        st.error(f"**{row['Proyecto']}**\n\n{val}% 🚨")

            # --- CÁLCULO DE DISTRIBUCIÓN ---
            df['Monto Real'] = df['Total Proyecto'].astype(float) * (df['% del Proyecto'].astype(float) / escala)
            df['Días'] = (df['Fecha Fin'] - df['Fecha Inicio']).dt.days + 1
            df['Diario'] = df['Monto Real'] / df['Días']

            f_min = df['Fecha Inicio'].min().replace(day=1)
            f_max = df['Fecha Fin'].max().replace(day=1)
            meses = pd.date_range(start=f_min, end=f_max, freq='MS').strftime('%Y-%m').tolist()

            resumen = []
            for _, row in df.iterrows():
                d_row = {'Proyecto': row['Proyecto'], 'Hito': row['Hito'], 'Monto Hito': round(row['Monto Real'], 2)}
                r_dias = pd.date_range(start=row['Fecha Inicio'], end=row['Fecha Fin'], freq='D')
                for m in meses:
                    d_mes = sum(1 for d in r_dias if d.strftime('%Y-%m') == m)
                    d_row[m] = round(d_mes * row['Diario'], 2)
                resumen.append(d_row)

            df_final = pd.DataFrame(resumen)
            
            # Fila de Totales
            f_tot = {c: '' for c in df_final.columns}
            f_tot['Proyecto'] = 'TOTAL MENSUAL'
            for c in ['Monto Hito'] + meses: f_tot[c] = df_final[c].sum()
            df_final = pd.concat([df_final, pd.DataFrame([f_tot])], ignore_index=True)

            # --- VISUALIZACIÓN Y DESCARGA ---
            st.subheader("📅 Proyección Mensual")
            st.dataframe(df_final.style.format(subset=['Monto Hito'] + meses, precision=2), use_container_width=True)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, index=False, sheet_name='Proyeccion')
                wb = writer.book
                fmt = wb.add_format({'num_format': '#,##0.00'})
                ws = writer.sheets['Proyeccion']
                ws.set_column(2, len(df_final.columns), 15, fmt)
            
            st.download_button("📥 Descargar Reporte Calculado", buffer.getvalue(), "reporte_proyeccion.xlsx")

    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")