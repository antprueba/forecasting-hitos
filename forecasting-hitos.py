import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Forecasting Hitos", layout="wide")

# --- ENCABEZADO ---
st.title("📊 Forecasting hitos 📊")

# --- GUÍA VISUAL ---
with st.expander("📢 IMPORTANTE: Formato del archivo Excel", expanded=True):
    st.markdown("""
    ### Guía de Normalización de Unidades
    **Evita mezclar formatos en un mismo proyecto para mayor precisión.**
    """)
    
    data_ejemplo = {
        "Proyecto": ["Proyecto A", "Proyecto A", "Proyecto B", "Proyecto C"],
        "Total Proyecto": [150000, 150000, 80000, 200000],
        "Hito": ["Hito 1", "Hito 2", "Fase Única", "Inicio"],
        "% del Proyecto": [20, 80, 1.0, 0.5],
        "Nota": ["Se toma como 20%", "Se toma como 80%", "Se toma como 100%", "Se toma como 50%"]
    }
    st.table(pd.DataFrame(data_ejemplo))

st.divider()

# --- CARGA DE ARCHIVO ---
archivo_subido = st.file_uploader("Sube tu archivo Excel aquí", type=["xlsx"])

if archivo_subido is not None:
    try:
        df = pd.read_excel(archivo_subido)
        
        cols_req = ["Proyecto", "Total Proyecto", "Hito", "% del Proyecto", "Fecha Inicio", "Fecha Fin"]
        if not all(c in df.columns for c in cols_req):
            st.error(f"Faltan columnas. Asegúrate de tener: {', '.join(cols_req)}")
        else:
            # --- MÓDULO DE NORMALIZACIÓN ---
            def normalizar_porcentaje(valor):
                try:
                    val = float(valor)
                    # Si el valor es mayor a 1, asumimos que es escala 1-100 (ej. 20 -> 0.2)
                    # Si es menor o igual a 1, asumimos que ya es decimal (ej. 0.2 -> 0.2)
                    # Nota: El único caso ambiguo es un hito de exactamente 1%. 
                    # Se trata como 100% (1.0). Si es 1%, debe escribirse como 0.01.
                    if val > 1:
                        return val / 100
                    return val
                except:
                    return 0.0

            # Aplicamos normalización a una columna interna de trabajo
            df['Pct_Normalizado'] = df['% del Proyecto'].apply(normalizar_porcentaje)
            
            # --- PROCESAMIENTO DE FECHAS ---
            df['Fecha Inicio'] = pd.to_datetime(df['Fecha Inicio'])
            df['Fecha Fin'] = pd.to_datetime(df['Fecha Fin'])
            
            # --- PANEL DE AUDITORÍA (CORREGIDO) ---
            st.subheader("🔍 Verificación de Proyectos (Suma de Hitos)")
            # Sumamos los valores ya normalizados (escala 0-1)
            audit = df.groupby('Proyecto')['Pct_Normalizado'].sum().reset_index()
            
            num_proyectos = len(audit)
            cols_audit = st.columns(min(num_proyectos, 4))
            
            for i, (idx, row) in enumerate(audit.iterrows()):
                with cols_audit[i % 4]:
                    # Convertimos a base 100 solo para mostrar al usuario
                    porcentaje_total = round(row['Pct_Normalizado'] * 100, 2)
                    
                    if 99.0 <= porcentaje_total <= 101.0:
                        st.success(f"**{row['Proyecto']}**\n\n{porcentaje_total}% ✅")
                    else:
                        st.error(f"**{row['Proyecto']}**\n\n{porcentaje_total}% 🚨")

            # --- CÁLCULO DE DISTRIBUCIÓN ---
            # Usamos siempre Pct_Normalizado para el cálculo de dinero
            df['Monto Real'] = df['Total Proyecto'].astype(float) * df['Pct_Normalizado']
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
            for c in ['Monto Hito'] + meses: 
                f_tot[c] = df_final[c].sum()
            df_final = pd.concat([df_final, pd.DataFrame([f_tot])], ignore_index=True)

            # --- VISUALIZACIÓN ---
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
