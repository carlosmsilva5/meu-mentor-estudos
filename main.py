import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide", page_title="Mentor Elite Pro")

# ---------------- CSS PREMIUM (Correção de Visual e Links) ----------------
st.markdown("""
<style>
    .stApp { background-color: #2f3136; color: #e4e6eb; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #3ec6a8, #2bbf9b); }
    .card { background: #3a3b3c; padding: 18px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #4f4f4f; }
    .title { font-size: 12px; color: #b0b3b8; font-weight: bold; text-transform: uppercase; }
    .value { font-size: 24px; font-weight: bold; color: #ffffff; }
    
    /* Heatmap Style */
    .heatmap-grid { display: flex; flex-wrap: wrap; gap: 3px; padding: 10px; background: #202225; border-radius: 8px; }
    .day { width: 12px; height: 12px; border-radius: 2px; }
    .day-off { background-color: #2f3136; border: 1px solid #40444b; }
    .day-on { background-color: #39d353; box-shadow: 0 0 5px #26a641; }
    
    /* Erros Agrupados */
    .erro-group { border-left: 5px solid #ff6b6b; background: #3a3b3c; padding: 12px; border-radius: 0 8px 8px 0; margin-bottom: 15px; }
    .erro-item { padding: 8px 0; border-bottom: 1px dashed #4f4f4f; }
    .link-btn { background: #3ec6a8; color: #000 !important; padding: 4px 10px; border-radius: 5px; text-decoration: none; font-weight: bold; font-size: 11px; display: inline-block; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

# ---------------- FUNÇÃO DE FORMATAÇÃO DE TEMPO ----------------
def formatar_tempo(minutos):
    if minutos < 60:
        return f"{int(minutos)}m"
    h = int(minutos // 60)
    m = int(minutos % 60)
    return f"{h}h {m:02d}m"

# ---------------- CONEXÃO E LIMPEZA ----------------
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def load_data(sheet):
    try:
        df = conn.read(worksheet=sheet).dropna(how='all')
        df.columns = [c.strip().lower() for c in df.columns] # Padroniza colunas
        return df
    except: return pd.DataFrame()

def save_data(sheet, df_new):
    df_atual = conn.read(worksheet=sheet).dropna(how='all')
    df_novo = pd.concat([df_atual, df_new], ignore_index=True)
    conn.update(worksheet=sheet, data=df_novo)
    st.cache_data.clear()

# ---------------- CARREGAMENTO ----------------
df_estudo = load_data("progresso")
df_erros = load_data("caderno_erros")
df_config = load_data("config")

# Lista de matérias vinda da aba 'config'
materias_list = str(df_config["materias"].iloc[0]).split(",") if not df_config.empty else ["Português", "Direito"]

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("📘 Mentor Elite")
    page = st.radio("", ["Home", "Registrar Estudo", "Caderno de Erros"])

# ---------------- HOME (DASHBOARD + HEATMAP) ----------------
if page == "Home":
    st.title("Dashboard")

    # Métricas
    t_min = pd.to_numeric(df_estudo['tempo'], errors='coerce').sum() if not df_estudo.empty else 0
    q_tot = pd.to_numeric(df_estudo['total_q'], errors='coerce').sum() if not df_estudo.empty else 0
    q_acc = pd.to_numeric(df_estudo['acertos'], errors='coerce').sum() if not df_estudo.empty else 0
    aproveitamento = (q_acc / q_tot * 100) if q_tot > 0 else 0

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="card"><div class="title">Tempo Total</div><div class="value">{formatar_tempo(t_min)}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card"><div class="title">Desempenho</div><div class="value">{aproveitamento:.1f}%</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="card"><div class="title">Erros Totais</div><div class="value">{len(df_erros)}</div></div>', unsafe_allow_html=True)

    # Heatmap de Constância
    st.markdown("### Constância (Últimos 90 dias)")
    if not df_estudo.empty:
        df_estudo['data_dt'] = pd.to_datetime(df_estudo['data'], dayfirst=True, errors='coerce').dt.date
        datas_estudo = df_estudo['data_dt'].unique()
        hoje = datetime.now().date()
        
        grid_html = '<div class="heatmap-grid">'
        for i in range(89, -1, -1):
            dia = hoje - timedelta(days=i)
            status = "day-on" if dia in datas_estudo else "day-off"
            grid_html += f'<div class="day {status}" title="{dia.strftime("%d/%m")}"></div>'
        grid_html += '</div>'
        st.markdown(grid_html, unsafe_allow_html=True)

    # Tabela de Disciplinas
    st.subheader("Painel de Disciplinas")
    if not df_estudo.empty:
        # Garante que as colunas sejam numéricas antes do groupby
        df_estudo['tempo'] = pd.to_numeric(df_estudo['tempo'], errors='coerce').fillna(0)
        df_estudo['acertos'] = pd.to_numeric(df_estudo['acertos'], errors='coerce').fillna(0)
        df_estudo['total_q'] = pd.to_numeric(df_estudo['total_q'], errors='coerce').fillna(0)
        
        painel = df_estudo.groupby("materia").agg({"tempo":"sum", "acertos":"sum", "total_q":"sum"}).reset_index()
        
        # APLICAÇÃO DA CORREÇÃO: Transforma minutos em Horas formatadas
        painel["tempo"] = painel["tempo"].apply(formatar_tempo)
        
        painel["%"] = (painel["acertos"]/painel["total_q"]*100).fillna(0).map("{:.1f}%".format)
        st.dataframe(painel, use_container_width=True, hide_index=True)

# ---------------- REGISTRAR ESTUDO (CÁLCULO DE PÁGINAS) ----------------
elif page == "Registrar Estudo":
    st.title("Novo Registro")
    with st.form("form_registro", clear_on_submit=True):
        col_m, col_t = st.columns(2)
        materia = col_m.selectbox("Matéria", materias_list)
        tipo = col_t.selectbox("Tipo de Estudo", ["Teoria Novo", "Revisão", "Questões"])
        
        tempo = st.number_input("Tempo (minutos)", 0)
        
        st.write("---")
        st.markdown("**📖 Leitura (Páginas)**")
        cp1, cp2 = st.columns(2)
        p_ini = cp1.number_input("Página Inicial", 0)
        p_fim = cp2.number_input("Página Final", 0)
        
        st.write("---")
        cq1, cq2 = st.columns(2)
        q_t = cq1.number_input("Qtd Questões", 0)
        q_a = cq2.number_input("Acertos", 0)

        if st.form_submit_button("Salvar Estudo"):
            total_paginas = (p_fim - p_ini) + 1 if p_fim >= p_ini and p_fim > 0 else 0
            novo = pd.DataFrame([{
                "data": datetime.now().strftime("%d/%m/%Y"),
                "materia": materia,
                "tipo_estudo": tipo,
                "tempo": tempo,
                "paginas": total_paginas,
                "acertos": q_a,
                "total_q": q_t
            }])
            save_data("progresso", novo)
            st.success(f"Salvo! {total_paginas} páginas contabilizadas.")
            st.rerun()

# ---------------- CADERNO DE ERROS (AGRUPADO + LINKS) ----------------
elif page == "Caderno de Erros":
    st.title("Caderno de Erros")
    with st.form("form_erro", clear_on_submit=True):
        materia_e = st.selectbox("Matéria", materias_list)
        tipo_e = st.selectbox("Causa do Erro", ["Teoria", "Atenção", "Pegadinha", "Interpretação"])
        link_e = st.text_input("Link da Questão (URL Completa)")
        obs_e = st.text_area("Insight/Comentário")
        
        if st.form_submit_button("Registrar Erro"):
            save_data("caderno_erros", pd.DataFrame([{
                "data": datetime.now().strftime("%d/%m/%Y"),
                "materia": materia_e,
                "tipo": tipo_e,
                "link": link_e,
                "comentario": obs_e
            }]))
            st.rerun()

    st.write("---")
    if not df_erros.empty:
        # AGRUPAMENTO POR MATÉRIA
        for mat in df_erros["materia"].unique():
            with st.container():
                st.markdown(f"#### 📙 {mat.upper()}")
                erros_da_materia = df_erros[df_erros["materia"] == mat]
                
                # Container para agrupar erros da mesma matéria
                st.markdown('<div class="erro-group">', unsafe_allow_html=True)
                for _, r in erros_da_materia.iterrows():
                    link_raw = str(r.get('link', '')).strip()
                    btn_html = f'<a href="{link_raw}" target="_blank" class="link-btn">ABRIR QUESTÃO ↗️</a>' if link_raw.startswith('http') else ""
                    
                    st.markdown(f"""
                    <div class="erro-item">
                        <small>{r['data']} | <b>{r['tipo']}</b></small><br>
                        {r['comentario']}<br>
                        {btn_html}
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Nenhum erro cadastrado.")
