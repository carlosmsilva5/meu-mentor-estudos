import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

# ---------------- CONFIG ----------------
st.set_page_config(layout="wide", page_title="Mentor Elite Pro", page_icon="🎯")

# ---------------- CSS PREMIUM ----------------
st.markdown("""
<style>
    .stApp { background-color: #2f3136; color: #e4e6eb; }
    section[data-testid="stSidebar"] { background-color: #000000; }
    .card { background: #3a3b3c; padding: 18px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #4f4f4f; text-align: center; }
    .title { font-size: 14px; color: #b0b3b8; font-weight: bold; text-transform: uppercase; }
    .value { font-size: 28px; font-weight: bold; color: #ffffff; }
    .ciclo-card { background: #3a3b3c; border: 1px solid #4f4f4f; padding: 15px; border-radius: 10px; text-align: center; border-top: 4px solid #3ec6a8; }
    .cronograma-table { width: 100%; border-collapse: collapse; background: #3a3b3c; border-radius: 8px; overflow: hidden; margin-top: 15px; }
    .cronograma-table td, .cronograma-table th { padding: 12px; border: 1px solid #4f4f4f; text-align: left; }
    .cronograma-table th { background: #202225; color: #3ec6a8; }
    .dia-num { background: #4e1d3d; color: white; font-weight: bold; text-align: center !important; width: 45px; }
    .giro-badge { background: #3ec6a8; color: #202225; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 18px; display: inline-block; margin-bottom: 15px;}
</style>
""", unsafe_allow_html=True)

# ---------------- FUNÇÕES ----------------
def save_data(sheet, df_new):
    try:
        # Carrega o que já existe na planilha
        df_atual = conn.read(worksheet=sheet).dropna(how='all')
        # Junta com o novo registro
        df_novo = pd.concat([df_atual, df_new], ignore_index=True)
        # Atualiza a planilha no Google Sheets
        conn.update(worksheet=sheet, data=df_novo)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"Erro ao salvar dados: {e}")

def formatar_tempo(minutos):
    if pd.isna(minutos) or minutos < 0: return "0min"
    if minutos < 60: return f"{int(minutos)}min"
    h, m = int(minutos // 60), int(minutos % 60)
    return f"{h:02d}h {m:02d}min"

def decimal_para_horas(horas_decimais):
    return formatar_tempo(horas_decimais * 60)

def append_data(worksheet_name, data_dict):
    """Função para adicionar uma nova linha na planilha Google"""
    try:
        # Tenta ler os dados existentes
        df_existente = conn.read(worksheet=worksheet_name)
        # Cria um DataFrame com a nova linha
        df_novo = pd.DataFrame([data_dict])
        # Junta o antigo com o novo
        df_final = pd.concat([df_existente, df_novo], ignore_index=True)
        # Atualiza a planilha inteira
        conn.update(worksheet=worksheet_name, data=df_final)
    except Exception as e:
        st.error(f"Erro na função append_data: {e}")
        
def calcular_streak(df):
    if df.empty or 'data' not in df.columns: return 0
    df['data_fmt'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
    datas_estudadas = df['data_fmt'].dropna().dt.date.sort_values(ascending=False).unique()
    
    if len(datas_estudadas) == 0: return 0
    
    hoje = datetime.now().date()
    streak = 0
    if (hoje - datas_estudadas[0]).days > 1: return 0
        
    data_atual = datas_estudadas[0]
    for data in datas_estudadas:
        if (data_atual - data).days <= 1:
            streak += 1
            data_atual = data
        else: break
    return streak

def calcular_giro_atual(df):
    """Calcula em qual semana (Giro) o aluno está baseado no primeiro registro de estudo"""
    if df.empty or 'data' not in df.columns: return 1
    df['data_fmt'] = pd.to_datetime(df['data'], format='%d/%m/%Y', errors='coerce')
    primeiro_dia = df['data_fmt'].min()
    if pd.isna(primeiro_dia): return 1
    
    hoje = pd.Timestamp.today().normalize()
    dias_passados = (hoje - primeiro_dia).days
    giro = (dias_passados // 7) + 1
    return max(1, giro)

conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=2)
def load_data(sheet):
    try:
        df = conn.read(worksheet=sheet).dropna(how='all')
        df.columns = [str(c).strip().lower() for c in df.columns] 
        return df
    except: return pd.DataFrame()

def overwrite_data(sheet, df_full):
    conn.update(worksheet=sheet, data=df_full)
    st.cache_data.clear()

# ---------------- CARREGAMENTO ----------------
df_estudo = load_data("progresso")
df_erros = load_data("caderno_erros")
df_config = load_data("config")
df_cronograma = load_data("cronograma")

# Se o cronograma estiver vazio (primeiro acesso), cria uma estrutura padrão
if df_cronograma.empty:
    df_cronograma = pd.DataFrame({
        "dia": [1, 2, 3, 4, 5, 6, 7],
        "materia_1": ["Português", "Dir. Constitucional", "Dir. Administrativo", "Português", "Dir. Constitucional", "Revisão Geral", "Simulado"],
        "materia_2": ["Raciocínio Lógico", "Informática", "Redação", "Raciocínio Lógico", "Informática", "Discursiva", "-"],
        "materia_3": ["-", "-", "-", "-", "-", "-", "-"]
    })
    overwrite_data("cronograma", df_cronograma)

materias_list = str(df_config["materias"].iloc[0]).split(",") if not df_config.empty and "materias" in df_config.columns else ["Português", "Direito Constitucional", "Direito Administrativo"]

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.title("📘 Estudômetro")
    menu_map = {
        "🏠 Dashboard": "Home",
        "⏱️ Registrar": "Registrar Estudo",
        "❌ Caderno de Erros": "Caderno de Erros",
        "🎯 Ciclo de Estudos": "Ciclo de Estudos",
        "⚙️ Gestão de Dados": "Gestão de Dados"
    }
    selection = st.radio("", list(menu_map.keys()))
    page = menu_map[selection]

# ---------------- PÁGINAS ----------------
if page == "Home":
    st.title("Visão Geral")
    
    # 1. Cálculos de Topo
    if not df_estudo.empty:
        df_estudo['tempo_num'] = pd.to_numeric(df_estudo['tempo'], errors='coerce').fillna(0)
        df_estudo['acertos_num'] = pd.to_numeric(df_estudo['acertos'], errors='coerce').fillna(0)
        df_estudo['total_q_num'] = pd.to_numeric(df_estudo['total_q'], errors='coerce').fillna(0)
        # Garante que as novas colunas existam (blindagem)
        for col in ['paginas', 'humor', 'tipo_estudo']:
            if col not in df_estudo.columns:
                df_estudo[col] = 0 if col == 'paginas' else "N/A"
        df_estudo['paginas_num'] = pd.to_numeric(df_estudo['paginas'], errors='coerce').fillna(0)

    t_min = pd.to_numeric(df_estudo['tempo'], errors='coerce').sum() if not df_estudo.empty else 0
    q_tot = pd.to_numeric(df_estudo['total_q'], errors='coerce').sum() if not df_estudo.empty else 0
    q_acc = pd.to_numeric(df_estudo['acertos'], errors='coerce').sum() if not df_estudo.empty else 0
    aproveitamento = (q_acc / q_tot * 100) if q_tot > 0 else 0
    streak_atual = calcular_streak(df_estudo)

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="card"><div class="title">Tempo Total</div><div class="value">{formatar_tempo(t_min)}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card"><div class="title">Taxa de Acertos</div><div class="value">{aproveitamento:.1f}%</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="card"><div class="title">Ofensiva (Streak)</div><div class="value">🔥 {streak_atual} Dias</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="card"><div class="title">Questões Feitas</div><div class="value">{int(q_tot)}</div></div>', unsafe_allow_html=True)

    st.divider()

    # --- NOVO BLOCO: CRONOGRAMA DE ESTUDOS NO DASHBOARD ---
    st.subheader("🗓️ Cronograma Atual")
    
    html_tabela_home = """<table style="width:100%; border-collapse: collapse; background-color: #3a3b3c; color: white; border-radius: 10px; overflow: hidden; border: 1px solid #4f4f4f;"><thead><tr style="background-color: #202225; color: #3ec6a8; text-align: left;"><th style="padding: 12px; border: 1px solid #4f4f4f;">Dia do Ciclo</th><th style="padding: 12px; border: 1px solid #4f4f4f;">Matéria 01</th><th style="padding: 12px; border: 1px solid #4f4f4f; text-align: center;">🌀 Giro</th><th style="padding: 12px; border: 1px solid #4f4f4f;">Matéria 02</th><th style="padding: 12px; border: 1px solid #4f4f4f;">Matéria 03</th><th style="padding: 12px; border: 1px solid #4f4f4f; background-color: #2b2d2e; text-align: center;">Total Dia</th></tr></thead><tbody>"""
    
    for _, row in df_cronograma.iterrows():
        m1, m2, m3 = [str(row.get(f'disciplina 0{i}', '-')) for i in range(1, 4)]
        t1, t2, t3 = [f"{row.get(f'tempo d{i} (h)', 0):.2f}h" if x != '-' and x != 'nan' else "" for i, x in enumerate([m1, m2, m3], 1)]
        total_dia = f"{row.get('total dia (h)', 0):.2f}h"
        
        # Converte para float e depois para int (corta o .0)
        ordem_raw = row.get('ordem', '-')
        ordem_v = int(float(ordem_raw)) if pd.notna(ordem_raw) and str(ordem_raw).strip() != '-' else '-'

        html_tabela_home += f"""<tr style="border-bottom: 1px solid #4f4f4f;"><td style="padding: 10px; border: 1px solid #4f4f4f; font-weight: bold; background: #2b2d2e; text-align: center;">{ordem_v}</td><td style="padding: 10px; border: 1px solid #4f4f4f;">{m1 if m1 != 'nan' else '-'} <br><small style='color:#3ec6a8'>{t1}</small></td><td style="padding: 10px; border: 1px solid #4f4f4f; text-align: center;">{int(row.get('giros', 1)) if pd.notna(row.get('giros')) else 1}</td><td style="padding: 10px; border: 1px solid #4f4f4f;">{m2 if m2 != 'nan' else '-'} <br><small style='color:#3ec6a8'>{t2}</small></td><td style="padding: 10px; border: 1px solid #4f4f4f;">{m3 if m3 != 'nan' else '-'} <br><small style='color:#3ec6a8'>{t3}</small></td><td style="padding: 10px; border: 1px solid #4f4f4f; font-weight: bold; color: #3ec6a8; background: #2b2d2e; text-align: center;">{total_dia}</td></tr>"""
    st.markdown(html_tabela_home + "</tbody></table>", unsafe_allow_html=True)
    st.divider()
    # --- FIM DO NOVO BLOCO ---

    if not df_estudo.empty:
        col_grafico1, col_grafico2 = st.columns(2)
        
        with col_grafico1:
            st.subheader("Desempenho por Disciplina")
            
            # Agrupamento Principal
            painel_disc = df_estudo.groupby("materia").agg(
                tempo_total=("tempo_num", "sum"),
                q_total=("total_q_num", "sum"),
                q_acertos=("acertos_num", "sum"),
                total_pag=("paginas_num", "sum")
            ).reset_index()

            # Humor Predominante
            humor_map = df_estudo.groupby("materia")['humor'].agg(lambda x: x.mode()[0] if not x.mode().empty else "N/A").reset_index()
            painel_disc = pd.merge(painel_disc, humor_map, on="materia", how="left")
            
            # Divisão de Tempo por Tipo
            df_tipos = df_estudo.groupby(["materia", "tipo_estudo"])["tempo_num"].sum().unstack(fill_value=0).reset_index()
            for t in ["Teoria", "Revisão", "Questões"]:
                if t not in df_tipos.columns: df_tipos[t] = 0
            
            painel_completo = pd.merge(painel_disc, df_tipos, on="materia", how="left")
            
            # --- RECUPERAÇÃO DO GRÁFICO RADAR (ESTILO PREMIUM MANTIDO) ---
            import textwrap
            
            painel_completo["aproveitamento"] = (painel_completo["q_acertos"] / painel_completo["q_total"] * 100).fillna(0)
            
            # Cria um novo rótulo juntando o nome da matéria (quebrado se for longo) e o percentual acumulado
            painel_completo["materia_label"] = painel_completo.apply(
                lambda row: f"{'<br>'.join(textwrap.wrap(str(row['materia']), width=22))}<br>{row['aproveitamento']:.1f}%", axis=1
            )
            
            # 1. Definir a cor dinâmica baseada na média de aproveitamento
            media_aprov = painel_completo["aproveitamento"].mean()
            if media_aprov >= 90: cor_radar = "#2ecc71"    # Verde
            elif media_aprov >= 80: cor_radar = "#f1c40f"  # Amarelo
            elif media_aprov >= 70: cor_radar = "#e67e22"  # Laranja
            else: cor_radar = "#e74c3c"                    # Vermelho

            # 2. Criar o gráfico com a cor definida
            fig_radar = px.line_polar(
                painel_completo, 
                r='aproveitamento', 
                theta='materia_label',  # <--- AGORA USA O RÓTULO COM O PERCENTUAL 
                line_close=True,
                markers=True,
                color_discrete_sequence=[cor_radar]
            )
            
            # Preenche a área com a cor dinâmica e transparência (0.3)
            fig_radar.update_traces(fill='toself', fillcolor=cor_radar, opacity=0.3)

            fig_radar.update_layout(
                polar=dict(
                    bgcolor='rgba(0,0,0,0)', 
                    radialaxis=dict(
                        visible=True, 
                        range=[0, 100], 
                        color='white', 
                        gridcolor='#4f4f4f',
                        showticklabels=False  # <--- ISSO REMOVE OS NÚMEROS INTERNOS
                    ),
                    angularaxis=dict(
                        color='white', 
                        gridcolor='#4f4f4f',
                        dtick=1 # <--- Força exibir todos os nomes
                    )
                ),
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                font=dict(color='white'),
                margin=dict(l=70, r=70, t=50, b=50) # Margens ajustadas para não cortar os rótulos longos
            )
            st.plotly_chart(fig_radar, use_container_width=True, config={'staticPlot': True})
            # -------------------------------------------------------------
            
            # --- TABELA DE DETALHAMENTO ATUALIZADA ---
            st.markdown("#### Detalhamento das Matérias")
            tab_v = painel_completo.copy()
            
            # Formatação de Tempos
            tab_v["Total"] = tab_v["tempo_total"].apply(formatar_tempo)
            tab_v["Teoria"] = tab_v["Teoria"].apply(formatar_tempo)
            tab_v["Rev."] = tab_v["Revisão"].apply(formatar_tempo)
            tab_v["Ques. (Tempo)"] = tab_v["Questões"].apply(formatar_tempo)
            
            # Formatação de Performance
            tab_v["Aprov."] = tab_v["aproveitamento"].map("{:.1f}%".format)
            
            # Seleção das Colunas (Incluindo o número de questões 'q_total')
            cols_final = [
                "materia", "Total", "Teoria", "Rev.", 
                "Ques. (Tempo)", "q_total", "total_pag", "humor", "Aprov."
            ]
            
            # Renomeação para exibição limpa
            st.dataframe(
                tab_v[cols_final].rename(columns={
                    "materia": "Matéria", 
                    "q_total": "Nº Quest.", 
                    "total_pag": "Págs", 
                    "humor": "Humor"
                }), 
                use_container_width=True, 
                hide_index=True
            )

        with col_grafico2:
            # 1. Preparação dos Dados (7 dias)
            hoje = pd.Timestamp.today().normalize()
            df_dias = pd.DataFrame({'data': pd.date_range(end=hoje, periods=7)})
            df_estudo['data_fmt'] = pd.to_datetime(df_estudo['data'], format='%d/%m/%Y', errors='coerce')
            
            est_agrup = df_estudo.groupby('data_fmt').agg({
                "tempo_num": "sum",
                "acertos_num": "sum",
                "total_q_num": "sum"
            }).reset_index()
            
            evol = pd.merge(df_dias, est_agrup, left_on='data', right_on='data_fmt', how='left').fillna(0)
            evol['data_label'] = evol['data'].dt.strftime('%d/%m')
            
            # --- LÓGICA DE FORMATAÇÃO 00h00min ---
            def formatar_para_grafico(minutos):
                h = int(minutos // 60)
                m = int(minutos % 60)
                return f"{h:02d}h{m:02d}min"

            evol['tempo_formatado'] = evol['tempo_num'].apply(formatar_para_grafico)
            evol['horas_decimal'] = (evol['tempo_num'] / 60).round(2)
            evol['perc_acerto'] = (evol['acertos_num'] / evol['total_q_num'] * 100).fillna(0).round(1)
            
            # 2. Gráfico 1: Horas Estudadas (Texto Fixo Formatado)
            st.subheader("Evolução de Carga Horária (7 Dias)")
            fig_horas = px.line(evol, x='data_label', y='horas_decimal', markers=True, text='tempo_formatado', color_discrete_sequence=['#3ec6a8'])
            fig_horas.update_traces(textposition="top center")
            fig_horas.update_layout(
                yaxis=dict(rangemode='tozero', gridcolor='#4f4f4f', title="Tempo"), 
                xaxis=dict(gridcolor='#4f4f4f', title="Data"),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'),
                margin=dict(l=20, r=20, t=30, b=20)
            )
            st.plotly_chart(fig_horas, use_container_width=True, config={'staticPlot': True})

            # 3. Gráfico 2: Desempenho Geral (Texto Fixo %)
            st.subheader("Desempenho Geral (7 Dias)")
            fig_desempenho = px.line(evol, x='data_label', y='perc_acerto', markers=True, text='perc_acerto', color_discrete_sequence=['#3ec6a8'])
            fig_desempenho.update_traces(textposition="top center", texttemplate='%{text}%')
            fig_desempenho.add_hline(y=90, line_dash="dash", line_color="#4f4f4f", annotation_text="Meta 90%")
            fig_desempenho.update_layout(
                yaxis=dict(range=[0, 105], gridcolor='#4f4f4f', title="% Acerto"), 
                xaxis=dict(gridcolor='#4f4f4f', title="Data"),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'),
                margin=dict(l=20, r=20, t=30, b=20)
            )
            st.plotly_chart(fig_desempenho, use_container_width=True, config={'staticPlot': True})

elif page == "Registrar Estudo":
    st.title("🧮 Novo Registro")
    with st.form("form_registro", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            materia = st.selectbox("Matéria", materias_list)
            tipo = st.selectbox("Tipo", ["Questões", "Revisão", "Teoria"])
        with col2:
            tempo = st.number_input("Tempo total (min)", 0)
            humor = st.selectbox("Humor/Energia", ["Neutro 😐", "Focado ⚡", "Cansado 😴"])
        with col3:
            # NOVO CAMPO: Dia do Cronograma
            dia_crono = st.selectbox("Dia do Ciclo", [1, 2, 3, 4, 5, 6, 7], help="Indique qual dia do seu cronograma de 7 dias você está executando agora.")
            # NOVO CAMPO: Atualizar o Giro do Ciclo
            giro_informado = st.number_input("Giro Atual", min_value=1, step=1, value=1, help="Informe em qual giro você está para atualizar automaticamente a tabela do cronograma.")
        
        st.divider()
        st.markdown("📝 **Questões**")
        cq1, cq2 = st.columns(2)
        q_t = cq1.number_input("Qtd Questões", 0)
        q_a = cq2.number_input("Acertos", 0)
        
        st.divider()
        st.markdown("📖 **Leitura de Páginas**")
        p1, p2 = st.columns(2)
        p_inicio = p1.number_input("Página Inicial", 0)
        p_fim = p2.number_input("Página Final", 0)
        
        
        
        if st.form_submit_button("Salvar Registro"):
            total_paginas = (p_fim - p_inicio) + 1 if p_fim >= p_inicio and p_fim > 0 else 0
            
            # --- ATUALIZAÇÃO DO GIRO NO CRONOGRAMA ---
            if not df_cronograma.empty:
                pos = dia_crono - 1
                if pos < len(df_cronograma):
                    # Garante que a coluna existe
                    if 'giros' not in df_cronograma.columns:
                        df_cronograma['giros'] = 1
                    
                    # Pega o índice real da linha correspondente ao dia e atualiza o giro
                    real_idx = df_cronograma.index[pos]
                    df_cronograma.at[real_idx, 'giros'] = giro_informado
                    
                    overwrite_data("cronograma", df_cronograma)
            
            novo_dado = pd.DataFrame([{
                "data": datetime.now().strftime("%d/%m/%Y"), 
                "materia": materia, 
                "tipo_estudo": tipo, 
                "humor": humor,
                "tempo": tempo, 
                "paginas": total_paginas,
                "acertos": q_a, 
                "total_q": q_t,
                "dia_cronograma": dia_crono # <- Salvando o número do dia
            }])
            
            save_data("progresso", novo_dado)
            st.success(f"Estudo do Dia {dia_crono:02d} salvo e Giro {giro_informado} atualizado no painel! {total_paginas} páginas contabilizadas.")
            st.rerun()

elif page == "Caderno de Erros":
    st.title("❌ Caderno de Erros Estratégico")
    
    # Lista de motivos de erro de alta performance
    tipos_erro = ["Atenção / Bobeira", "Teoria não vista", "Erro de Interpretação", "Pegadinha", "Jurisprudência da Banca"]
    
    with st.form("form_erro", clear_on_submit=True):
        m_e = st.selectbox("Matéria", materias_list)
        tipo_e = st.selectbox("Motivo do Erro", tipos_erro) # NOVO CAMPO DE SELEÇÃO
        link_e = st.text_input("Link ou Referência da Questão")
        obs_e = st.text_area("Insight: O que você aprendeu com esse erro?")
        
        if st.form_submit_button("Registrar no Caderno"):
            # Agora a variável 'tipo' recebe a sua escolha (tipo_e) em vez de ser fixa
            novo_e = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "materia": m_e, "tipo": tipo_e, "link": link_e, "comentario": obs_e}])
            
            df_atual_e = conn.read(worksheet="caderno_erros").dropna(how='all')
            # Garante que as colunas existam
            if df_atual_e.empty:
                df_atual_e = pd.DataFrame(columns=["data", "materia", "tipo", "link", "comentario"])
                
            conn.update(worksheet="caderno_erros", data=pd.concat([df_atual_e, novo_e], ignore_index=True))
            st.cache_data.clear()
            st.success(f"Erro de '{tipo_e}' catalogado com sucesso!")
            st.rerun()

    st.divider()
    st.subheader("📚 Seus Erros Registrados")
    
    if not df_erros.empty:
        st.dataframe(
            df_erros, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "data": "Data",
                "materia": "Matéria",
                "tipo": st.column_config.TextColumn("Motivo"), # Mostrando o motivo na tabela
                "link": st.column_config.LinkColumn("Link da Questão"),
                "comentario": st.column_config.TextColumn("Insight / Aprendizado")
            }
        )
    else:
        st.info("Você ainda não registrou nenhum erro no caderno. Bom trabalho (ou vá fazer mais questões!) 😉")
    
   
elif page == "Ciclo de Estudos":
    st.title("🎯 Planejamento do Ciclo")
    
    # 1. Badge de Giro Global
    giro_global = calcular_giro_atual(df_estudo)
    st.markdown(f'<div class="giro-badge">🔄 Você está no Giro {giro_global} do Ciclo Global</div>', unsafe_allow_html=True)
    
    # 2. Carga Horária Semanal
    horas_semana = st.number_input("Horas totais pretendidas na semana:", 5, 100, 25)

    st.write("---")

    # --- 3. LÓGICA DE CÁLCULO ---
    materias_ativas = []
    fatores_ativos = []
    for m in materias_list:
        if st.session_state.get(f"check_{m}", True):
            p_val = st.session_state.get(f"p_ciclo_{m}", 3)
            n_val = st.session_state.get(f"n_ciclo_{m}", 3)
            materias_ativas.append(m)
            fatores_ativos.append(p_val / n_val)
    
    soma_fatores = sum(fatores_ativos) if fatores_ativos else 1

    # --- 4. RENDERIZAÇÃO DOS CARDS E CONTROLES ---
    cols = st.columns(3)
    metas_calculadas_horas = {} 

    for i, m in enumerate(materias_list):
        with cols[i % 3]:
            ativo = st.checkbox(f"Incluir {m}", value=True, key=f"check_{m}")
            p_atual = st.session_state.get(f"p_ciclo_{m}", 3)
            n_atual = st.session_state.get(f"n_ciclo_{m}", 3)
            
            # Cálculo do tempo sugerido
            horas_sug = ((p_atual / n_atual) / soma_fatores) * horas_semana if ativo else 0.0
            metas_calculadas_horas[m] = round(horas_sug, 2)

            st.markdown(f"""
                <div style="background:{'#3a3b3c' if ativo else '#202225'}; padding:15px; border-radius:10px; border-top:4px solid {'#3ec6a8' if ativo else '#4f4f4f'}; text-align:center; margin-bottom:10px; opacity:{'1' if ativo else '0.3'};">
                    <b style="color:#b0b3b8; font-size:12px; text-transform:uppercase;">{m}</b><br>
                    <span style="color:white; font-size:24px; font-weight:bold;">{decimal_para_horas(horas_sug)}</span><br>
                    <small style="color:{'#3ec6a8' if ativo else '#4f4f4f'};">{"Meta Semanal" if ativo else "Fora do Ciclo"}</small>
                </div>
            """, unsafe_allow_html=True)

            st.select_slider("Peso", [1,2,3,4,5], 3, key=f"p_ciclo_{m}", disabled=not ativo)
            st.select_slider("Nível", [1,2,3,4,5], 3, key=f"n_ciclo_{m}", disabled=not ativo)

    st.divider()

    # --- 5. CRONOGRAMA DE EXECUÇÃO (EDITOR) ---
    st.subheader("🗓️ Cronograma de Execução (Editor)")
    
    if st.button("🪄 Distribuir Horas Calculadas na Tabela", use_container_width=True):
        df_temp = df_cronograma.copy()
        
        # Mapear aparições para dividir o tempo corretamente
        aparicoes = {}
        for c in ["disciplina 01", "disciplina 02", "disciplina 03"]:
            if c in df_temp.columns:
                for mat in df_temp[c].dropna():
                    if mat != "-":
                        aparicoes[mat] = aparicoes.get(mat, 0) + 1

        # Aplicar os tempos sugeridos divididos pelas aparições
        for idx, row in df_temp.iterrows():
            dia_total = 0
            for i in range(1, 4):
                col_m = f"disciplina 0{i}"
                col_h = f"tempo d{i} (h)"
                m_nome = str(row.get(col_m, "-")).strip()
                
                if m_nome in metas_calculadas_horas:
                    v_vezes = aparicoes.get(m_nome, 1)
                    valor_h = metas_calculadas_horas[m_nome] / v_vezes
                    df_temp.at[idx, col_h] = round(valor_h, 2)
                    dia_total += valor_h
            df_temp.at[idx, "total dia (h)"] = round(dia_total, 2)
        
        overwrite_data("cronograma", df_temp)
        st.success("🪄 Horas distribuídas! Revise e clique em 'Salvar e Aplicar' abaixo.")
        st.rerun()

    # Configuração do Editor
    config_crono = {
        "ordem": st.column_config.TextColumn("Dia", disabled=True),
        "disciplina 01": st.column_config.SelectboxColumn("Materia 01", options=materias_list),
        "tempo d1 (h)": st.column_config.NumberColumn("H. D1", format="%.2f h"),
        "giros": st.column_config.NumberColumn("🌀 Giro"),
        "disciplina 02": st.column_config.SelectboxColumn("Materia 02", options=materias_list),
        "tempo d2 (h)": st.column_config.NumberColumn("H. D2", format="%.2f h"),
        "disciplina 03": st.column_config.SelectboxColumn("Materia 03", options=materias_list),
        "tempo d3 (h)": st.column_config.NumberColumn("H. D3", format="%.2f h"),
        "total dia (h)": st.column_config.NumberColumn("Total Dia", format="%.2f h", disabled=True)
    }

    ed_ciclo = st.data_editor(df_cronograma, num_rows="fixed", use_container_width=True, hide_index=True, column_config=config_crono, key="ed_ciclo_final_fix")

    if st.button("💾 Salvar e Aplicar Ciclo", type="primary", use_container_width=True):
        ed_ciclo["total dia (h)"] = ed_ciclo["tempo d1 (h)"].fillna(0) + ed_ciclo["tempo d2 (h)"].fillna(0) + ed_ciclo["tempo d3 (h)"].fillna(0)
        # Salva em minutos para compatibilidade com o Dashboard
        for i in range(1, 4):
            ed_ciclo[f"tempo d{i} (min)"] = (ed_ciclo[f"tempo d{i} (h)"] * 60).astype(int)
        overwrite_data("cronograma", ed_ciclo)
        st.success("✅ Ciclo atualizado e salvo!")
        st.rerun()

    # --- 6. FIGURA VISUAL DO CRONOGRAMA (RESUMO) ---
    st.write("---")
    st.subheader("🖼️ Visualização do Cronograma Salvo")
    
    html_tabela = """<table style="width:100%; border-collapse: collapse; background-color: #3a3b3c; color: white; border-radius: 10px; overflow: hidden; border: 1px solid #4f4f4f;"><thead><tr style="background-color: #202225; color: #3ec6a8; text-align: left;"><th style="padding: 12px; border: 1px solid #4f4f4f;">Dia do Ciclo</th><th style="padding: 12px; border: 1px solid #4f4f4f;">Matéria 01</th><th style="padding: 12px; border: 1px solid #4f4f4f; text-align: center;">🌀 Giro</th><th style="padding: 12px; border: 1px solid #4f4f4f;">Matéria 02</th><th style="padding: 12px; border: 1px solid #4f4f4f;">Matéria 03</th><th style="padding: 12px; border: 1px solid #4f4f4f; background-color: #2b2d2e; text-align: center;">Total Dia</th></tr></thead><tbody>"""
    
    for _, row in df_cronograma.iterrows():
        m1, m2, m3 = [str(row.get(f'disciplina 0{i}', '-')) for i in range(1, 4)]
        t1, t2, t3 = [f"{row.get(f'tempo d{i} (h)', 0):.2f}h" if x != '-' and x != 'nan' else "" for i, x in enumerate([m1, m2, m3], 1)]
        total_dia = f"{row.get('total dia (h)', 0):.2f}h"

        html_tabela += f"""<tr style="border-bottom: 1px solid #4f4f4f;"><td style="padding: 10px; border: 1px solid #4f4f4f; font-weight: bold; background: #2b2d2e; text-align: center;">{row['ordem']}</td><td style="padding: 10px; border: 1px solid #4f4f4f;">{m1 if m1 != 'nan' else '-'} <br><small style='color:#3ec6a8'>{t1}</small></td><td style="padding: 10px; border: 1px solid #4f4f4f; text-align: center;">{int(row.get('giros', 1))}</td><td style="padding: 10px; border: 1px solid #4f4f4f;">{m2 if m2 != 'nan' else '-'} <br><small style='color:#3ec6a8'>{t2}</small></td><td style="padding: 10px; border: 1px solid #4f4f4f;">{m3 if m3 != 'nan' else '-'} <br><small style='color:#3ec6a8'>{t3}</small></td><td style="padding: 10px; border: 1px solid #4f4f4f; font-weight: bold; color: #3ec6a8; background: #2b2d2e; text-align: center;">{total_dia}</td></tr>"""
    
    st.markdown(html_tabela + "</tbody></table>", unsafe_allow_html=True)

elif page == "Gestão de Dados":
    st.title("⚙️ Painel de Controle")
    t1, t2, t3, t4 = st.tabs(["🗓️ Editar Cronograma", "📚 Matérias", "📝 Histórico", "❌ Erros"])
    
    with t1:
        st.markdown("### 🗓️ Personalize sua semana de estudos")
        st.info("As alterações feitas aqui aparecerão na aba 'Ciclo de Estudos'.")
        
        # Se o cronograma estiver vazio, cria um modelo inicial
        if df_cronograma.empty:
            df_cronograma = pd.DataFrame([
                {"Dia": "Segunda", "Materia 1": "-", "Tempo (min)": 60, "Materia 2": "-", "Tempo 2 (min)": 60},
                {"Dia": "Terça", "Materia 1": "-", "Tempo (min)": 60, "Materia 2": "-", "Tempo 2 (min)": 60}
            ])

        ed_crono = st.data_editor(df_cronograma, num_rows="dynamic", key="ed_crono", use_container_width=True, hide_index=True)
        
        if st.button("Salvar Cronograma", type="primary"):
            # O comando abaixo limpa o cache ANTES de salvar para garantir a atualização
            st.cache_data.clear()
            overwrite_data("cronograma", ed_crono)
            st.success("Cronograma vinculado com sucesso!")
            st.rerun()

    with t2:
        st.markdown("### 📚 Gerenciar Disciplinas")
        
        # --- ADICIONAR NOVA MATÉRIA ---
        with st.expander("➕ Adicionar Nova Disciplina", expanded=True):
            nova = st.text_input("Nome da Matéria")
            if st.button("Confirmar Adição"):
                if nova and nova not in materias_list:
                    nova_lista = ",".join(materias_list + [nova])
                    overwrite_data("config", pd.DataFrame([{"materias": nova_lista}]))
                    st.success(f"✅ {nova} adicionada com sucesso!")
                    st.rerun()
                elif nova in materias_list:
                    st.warning("Esta matéria já está cadastrada.")
                else:
                    st.error("Digite um nome válido.")

        st.divider()

        # --- EXCLUIR MATÉRIA EXISTENTE ---
        with st.expander("🗑️ Excluir Disciplina"):
            if materias_list:
                materia_para_excluir = st.selectbox("Selecione a matéria para remover:", materias_list)
                
                st.warning(f"Atenção: Excluir '{materia_para_excluir}' não apagará seu histórico de estudos, mas ela não aparecerá mais nos novos registros ou ciclos.")
                
                if st.button("🚨 Excluir Definitivamente", type="secondary"):
                    # Filtra a lista removendo a matéria selecionada
                    nova_lista_materias = [m for m in materias_list if m != materia_para_excluir]
                    nova_string = ",".join(nova_lista_materias)
                    
                    overwrite_data("config", pd.DataFrame([{"materias": nova_string}]))
                    st.success(f"❌ {materia_para_excluir} removida!")
                    st.rerun()
            else:
                st.info("Nenhuma matéria cadastrada para excluir.")
            
    with t3:
        st.markdown("### Editar Histórico de Sessões")
        if not df_estudo.empty:
            ed_est = st.data_editor(df_estudo, num_rows="dynamic", key="ed_est", use_container_width=True)
            if st.button("Salvar Histórico"):
                overwrite_data("progresso", ed_est)
                st.success("Histórico salvo!")
                st.rerun()
                
            st.divider()
            
            # Nova seção: Zona de Perigo para zerar o histórico
            with st.expander("⚠️ Zona de Perigo (Apagar Tudo)"):
                st.warning("Tem certeza? Esta ação apagará **TODO** o seu histórico de estudos e zerará os gráficos. Esta ação não pode ser desfeita no aplicativo.")
                if st.button("🚨 Sim, Quero Zerar Meu Histórico", type="primary"):
                    # Cria um DataFrame vazio apenas com as colunas originais para não quebrar a planilha
                    df_vazio = pd.DataFrame(columns=["data", "materia", "tipo_estudo", "tempo", "acertos", "total_q"])
                    overwrite_data("progresso", df_vazio)
                    st.success("Histórico completamente zerado! Recomeçando de forma limpa.")
                    st.rerun()
        else:
            st.info("Seu histórico de estudos já está completamente vazio! Faça alguns pomodoros para começar a gerar dados. 🚀")
                
    with t4:
        st.markdown("### Editar Caderno de Erros")
        if not df_erros.empty:
            ed_err = st.data_editor(df_erros, num_rows="dynamic", key="ed_err", use_container_width=True)
            if st.button("Salvar Alterações de Erros", type="primary"):
                overwrite_data("caderno_erros", ed_err)
                st.success("Erros atualizados!")
                st.rerun()
            
            st.divider()
            
            # Nova seção: Zona de Perigo para zerar o Caderno de Erros
            with st.expander("⚠️ Zona de Perigo (Limpar Caderno de Erros)"):
                st.warning("Atenção: Isso apagará todos os insights e links de questões registrados. Esta ação não pode ser desfeita.")
                if st.button("🚨 Sim, Quero Limpar Todo o Caderno de Erros", key="btn_zerar_erros"):
                    # Cria um DataFrame vazio com as colunas corretas da aba de erros
                    df_vazio_erros = pd.DataFrame(columns=["data", "materia", "tipo", "link", "comentario"])
                    overwrite_data("caderno_erros", df_vazio_erros)
                    st.success("Caderno de erros limpo com sucesso!")
                    st.rerun()
        else:
            st.warning("O seu caderno de erros está vazio no momento. Registre novos erros na aba 'Caderno de Erros'.")
