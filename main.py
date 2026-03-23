
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
    st.title("📘 Mentor Elite")
    menu_map = {
        "🏠 Dashboard": "Home",
        "⏱️ Registrar Pomodoro": "Registrar Estudo",
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
            for t in ["Teoria Novo", "Revisão", "Questões"]:
                if t not in df_tipos.columns: df_tipos[t] = 0
            
            painel_completo = pd.merge(painel_disc, df_tipos, on="materia", how="left")
            
            # --- RECUPERAÇÃO DO GRÁFICO RADAR (ESTILO PREMIUM MANTIDO) ---
            painel_completo["aproveitamento"] = (painel_completo["q_acertos"] / painel_completo["q_total"] * 100).fillna(0)
            
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
                theta='materia', 
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
                    angularaxis=dict(color='white', gridcolor='#4f4f4f')
                ),
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                font=dict(color='white'),
                margin=dict(l=40, r=40, t=20, b=20)
            )
            st.plotly_chart(fig_radar, use_container_width=True, config={'staticPlot': True})
            # -------------------------------------------------------------
            
            # --- TABELA DE DETALHAMENTO ATUALIZADA ---
            st.markdown("#### Detalhamento das Matérias")
            tab_v = painel_completo.copy()
            
            # Formatação de Tempos
            tab_v["Total"] = tab_v["tempo_total"].apply(formatar_tempo)
            tab_v["Teoria"] = tab_v["Teoria Novo"].apply(formatar_tempo)
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
            fig_desempenho = px.line(evol, x='data_label', y='perc_acerto', markers=True, text='perc_acerto', color_discrete_sequence=['#ffffff'])
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
        col1, col2 = st.columns(2)
        with col1:
            materia = st.selectbox("Matéria", materias_list)
            tipo = st.selectbox("Tipo", ["Teoria Novo", "Revisão", "Questões"])
        with col2:
            humor = st.selectbox("Humor/Energia", ["Focado ⚡", "Neutro 😐", "Cansado 😴"])
            tempo = st.number_input("Tempo total (min)", 0)
        
        st.divider()
        st.markdown("📖 **Leitura de Páginas**")
        p1, p2 = st.columns(2)
        p_inicio = p1.number_input("Página Inicial", 0)
        p_fim = p2.number_input("Página Final", 0)
        
        st.divider()
        st.markdown("📝 **Questões**")
        cq1, cq2 = st.columns(2)
        q_t = cq1.number_input("Qtd Questões", 0)
        q_a = cq2.number_input("Acertos", 0)
        
        if st.form_submit_button("Salvar Registro"):
            # Cálculo automático das páginas
            total_paginas = (p_fim - p_inicio) + 1 if p_fim >= p_inicio and p_fim > 0 else 0
            
            novo_dado = pd.DataFrame([{
                "data": datetime.now().strftime("%d/%m/%Y"), 
                "materia": materia, 
                "tipo_estudo": tipo, 
                "humor": humor,
                "tempo": tempo, 
                "paginas": total_paginas,
                "acertos": q_a, 
                "total_q": q_t
            }])
            
            save_data("progresso", novo_dado)
            st.success(f"Estudo salvo! {total_paginas} páginas contabilizadas.")
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
    
    # 1. Badge de Giro Global e Inputs de Topo
    giro_global = calcular_giro_atual(df_estudo)
    st.markdown(f'<div class="giro-badge">🔄 Você está no Giro {giro_global} do Ciclo Global</div>', unsafe_allow_html=True)
    
    col_topo1, col_topo2 = st.columns([1, 1.5])
    
    with col_topo1:
        horas_semana = st.number_input("Horas totais no ciclo:", 5, 100, 25)
        st.caption("Ajuste os Pesos (importância) e Níveis (sua base) para equilibrar o ciclo.")

    # --- NOVO: Pré-cálculo necessário para o gráfico e para integrar nos cards ---
    # Precisamos calcular a soma dos fatores antes de desenhar os cards para saber a hora individual
    fatores_pre = []
    for m in materias_list:
        # Pega o valor atual da session state (ou padroniza como 3 se não existir)
        p_v = st.session_state.get(f"p_{m}", 3)
        n_v = st.session_state.get(f"n_{m}", 3)
        fatores_pre.append(p_v / n_v)
    soma_fatores_total = sum(fatores_pre) if fatores_pre else 1

    # 2. Captura de Dados Integrada com Resultado (Substituindo o loop antigo)
    dados_ciclo = []
    st.write("---")
    st.subheader("📚 Ajuste e Distribuição por Disciplina") # Título atualizado
    cols_ajuste = st.columns(3)
    
    for i, m in enumerate(materias_list):
        with cols_ajuste[i % 3]:
            # Container visual do card
            st.markdown(f'<div style="background:#3a3b3c; padding:8px; border-radius:10px; border-top:4px solid #3ec6a8; text-align:center; margin-bottom:5px;"><b style="color:#3ec6a8; font-size:13px;">{m}</b></div>', unsafe_allow_html=True)
            
            # Controles de Ajuste
            p = st.select_slider("Peso", [1,2,3,4,5], 3, key=f"p_{m}")
            n = st.select_slider("Nível", [1,2,3,4,5], 3, key=f"n_{m}")
            g = st.number_input("Meta Giros", 1, 14, 1, key=f"g_{m}")
            
            # Cálculo individual baseado na pré-soma
            fator_m = p / n
            horas_m = (fator_m / soma_fatores_total) * horas_semana
            
            dados_ciclo.append({"materia": m, "fator": fator_m, "peso": p, "nivel": n, "giros": g, "horas": horas_m})
            
            # --- NOVO: Exibição do Resultado INTEGRADA dentro do card ---
            st.markdown(f"""
                <div style="background:#2b2d2e; padding:10px; border-radius:8px; border-left:5px solid #3ec6a8; margin-top:5px; margin-bottom:15px; text-align:center;">
                    <div style="font-size:11px; color:#b0b3b8;">Tempo Sugerido:</div>
                    <div style="font-size:20px; font-weight:bold; color:#ffffff;">{decimal_para_horas(horas_m)}</div>
                </div>
            """, unsafe_allow_html=True)

    # 3. Processamento e Gráfico de Pizza Pastel (Inalterado)
    df_c = pd.DataFrame(dados_ciclo)
    if not df_c.empty:
        # Nota: df_c["horas"] já foi calculado dentro do loop acima, não precisamos recalcular
        
        with col_topo2:
            base_cores = ['#FFB7B2', '#FFDAC1', '#E2F0CB', '#B5EAD7', '#C7CEEA', '#F3D1F4', '#F9FFB2', '#B2E2F2', '#D1F2B2', '#F2B2B2']
            cores_expandidas = (base_cores * (len(df_c) // len(base_cores) + 1))[:len(df_c)]
            
            fig_p = px.pie(df_c, values='horas', names='materia', hole=0.4, color_discrete_sequence=cores_expandidas)
            fig_p.update_traces(textinfo='label+percent', textposition='inside', marker=dict(line=dict(color='#202225', width=2)))
            fig_p.update_layout(showlegend=False, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', font=dict(size=12, color="white"))
            st.plotly_chart(fig_p, use_container_width=True, config={'staticPlot': True})

        # --- SEÇÃO 4 ANTIGA REMOVIDA (foi integrada no item 2) ---

        st.divider()
        st.subheader("🗓️ Ordem do Ciclo (Editável)")
        st.markdown("Dê um clique duplo para editar a **Disciplina, o Nº do Giro ou o Tempo** antes de salvar!")

        # 5. Gerando a ordem sugerida dinamicamente (Inalterado)
        blocos = []
        ordem_idx = 1
        max_giros = int(df_c["giros"].max()) if not df_c.empty else 1
        
        for giro_num in range(1, max_giros + 1):
            df_g = df_c[df_c["giros"] >= giro_num].sort_values("horas", ascending=False)
            for _, r in df_g.iterrows():
                tempo_bloco = r["horas"] / r["giros"]
                blocos.append({
                    "Ordem": ordem_idx,
                    "Disciplina": r["materia"],
                    "Giro": giro_num,
                    "Tempo": decimal_para_horas(tempo_bloco)
                })
                ordem_idx += 1
        
        df_sugestao = pd.DataFrame(blocos)
        
        # 6. Tabela Editável e Botão Salvar (Inalterado)
        ed_crono = st.data_editor(
            df_sugestao,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Ordem": st.column_config.NumberColumn("Fila", disabled=True),
                "Disciplina": st.column_config.SelectboxColumn("Disciplina", options=materias_list),
                "Giro": st.column_config.NumberColumn("Nº do Giro", min_value=1, max_value=20),
                "Tempo": st.column_config.TextColumn("Tempo do Bloco")
            },
            key="ed_ordem_ciclo"
        )
        
        if st.button("Salvar Meu Ciclo", type="primary"):
            overwrite_data("cronograma", ed_crono)
            st.success("Ciclo salvo com sucesso!")
            st.rerun()

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
        nova = st.text_input("Nova Matéria")
        if st.button("Adicionar Disciplina"):
            nova_lista = ",".join(materias_list + [nova])
            overwrite_data("config", pd.DataFrame([{"materias": nova_lista}]))
            st.success(f"{nova} adicionada!")
            st.rerun()
            
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
