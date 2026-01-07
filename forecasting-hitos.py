import streamlit as st
import pandas as pd
import io
import base64

st.set_page_config(page_title="Forecasting Hitos", layout="wide")

# --- ENCABEZADO ---
st.title("📊 Forecasting hitos 📊")

# --- GUÍA VISUAL PARA EL USUARIO ---
with st.expander("IMPORTANTE: Formato del archivo Excel", expanded=True):
    st.markdown("""
    Tu archivo Excel **debe contener estas 6 columnas**. 
    * **Espacios en nombres:** 'Proyecto A ' se agrupará con 'Proyecto A'.
    * **Formatos de %:** Tanto **0.1** como **10** serán interpretados como **10%**. 1.0 será interpretado como **100%**.
    """)
    
    # Esta tabla muestra exactamente las columnas requeridas por el código
    data_ejemplo = {
        "Proyecto": ["Proyecto A", "Proyecto A ", "Proyecto B"],
        "Total Proyecto": [50000, 50000, 100000],
        "Hito": ["Diseño", "Desarrollo", "Entrega Final"],
        "% del Proyecto": [0.3, 70, 1.0],  # Mezcla de decimales y enteros
        "Fecha Inicio": ["2024-01-01", "2024-02-01", "2024-03-01"],
        "Fecha Fin": ["2024-01-31", "2024-04-30", "2024-05-31"]
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
            # 1. Limpieza de nombres de proyecto (Bypass de duplicados por espacios/mayúsculas)
            df['Proyecto'] = df['Proyecto'].astype(str).str.strip().str.title()

            # 2. Normalización de porcentajes (Detecta si es base 1 o base 100)
            def normalizar_porcentaje(valor):
                try:
                    val = float(valor)
                    return val / 100 if val > 1 else val
                except:
                    return 0.0

            df['Pct_Normalizado'] = df['% del Proyecto'].apply(normalizar_porcentaje)
            df['Fecha Inicio'] = pd.to_datetime(df['Fecha Inicio'])
            df['Fecha Fin'] = pd.to_datetime(df['Fecha Fin'])
            
            # --- PANEL DE AUDITORÍA ---
            st.subheader("🔍 Verificación de Proyectos (Suma de Hitos)")
            audit = df.groupby('Proyecto')['Pct_Normalizado'].sum().reset_index()
            
            cols_audit = st.columns(min(len(audit), 4))
            for i, (idx, row) in enumerate(audit.iterrows()):
                with cols_audit[i % 4]:
                    porcentaje_total = round(row['Pct_Normalizado'] * 100, 2)
                    if 99.0 <= porcentaje_total <= 101.0:
                        st.success(f"**{row['Proyecto']}**\n\n{porcentaje_total}% ✅")
                    else:
                        st.error(f"**{row['Proyecto']}**\n\n{porcentaje_total}% 🚨")

            # --- CÁLCULO DE DISTRIBUCIÓN ---
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
            
            # Totales Finales
            f_tot = {c: '' for c in df_final.columns}
            f_tot['Proyecto'] = 'TOTAL MENSUAL'
            for c in ['Monto Hito'] + meses: 
                f_tot[c] = df_final[c].sum()
            df_final = pd.concat([df_final, pd.DataFrame([f_tot])], ignore_index=True)

            # --- VISUALIZACIÓN ---
            st.subheader("📅 Proyección Mensual")
            st.dataframe(df_final.style.format(subset=['Monto Hito'] + meses, precision=2), use_container_width=True)

            # --- EXPORTACIÓN CON BYPASS PARA NOTION ---
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, index=False, sheet_name='Proyeccion')
                wb = writer.book
                fmt = wb.add_format({'num_format': '#,##0.00'})
                ws = writer.sheets['Proyeccion']
                ws.set_column(2, len(df_final.columns), 18, fmt)
            
            b64 = base64.b64encode(buffer.getvalue()).decode()
            filename = "reporte_proyeccion.xlsx"
            
            st.markdown(f"""
                <a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" 
                   download="{filename}" 
                   style="text-decoration: none;">
                    <div style="
                        background-color: #2e7d32;
                        color: white;
                        padding: 16px 24px;
                        border-radius: 10px;
                        text-align: center;
                        font-weight: bold;
                        font-size: 18px;
                        cursor: pointer;
                        border: 2px solid #1b5e20;
                        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
                        transition: 0.3s;">
                        📥 DESCARGAR EXCEL
                    </div>
                </a>

                <div style="
                    background-color: #fff4e5; 
                    border-left: 6px solid #ffa117;
                    padding: 15px;
                    margin-top: 20px;
                    border-radius: 6px;
                    font-family: sans-serif;">
                    <h4 style="margin: 0 0 8px 0; color: #663c00; font-size: 1rem;">
                        ¿Problemas con la descarga?
                    </h4>
                    <p style="margin: 0; color: #663c00; font-size: 0.9rem; line-height: 1.4;">
                        Debido a la seguridad de <b>Notion</b>, si al hacer clic no ocurre nada:
                        <br><br>
                        1. Haz <b>clic derecho</b> sobre el botón verde y selecciona <i>"Abrir en pestaña nueva"</i>.
                        <br>
                        2. O pulsa el icono de la <b>flecha ↗️</b> para abrir en ventana completa.
                    </p>
                </div>
            """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error procesando el archivo: {e}")
