# --- RECUPERAÇÃO DO GRÁFICO RADAR (ESTILO PREMIUM MANTIDO) ---
            import textwrap
            
            painel_completo["aproveitamento"] = (painel_completo["q_acertos"] / painel_completo["q_total"] * 100).fillna(0)
            
            # Quebra textos muito longos a cada 20 caracteres para não vazar a tela e junta com o percentual
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
                theta='materia_label', 
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
                        dtick=1  # <--- FORÇA O PLOTLY A MOSTRAR TODOS OS RÓTULOS
                    )
                ),
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                font=dict(color='white'),
                # AUMENTO DAS MARGENS PARA IMPEDIR QUE TEXTOS LONGOS SEJAM CORTADOS
                margin=dict(l=70, r=70, t=50, b=50) 
            )
            st.plotly_chart(fig_radar, use_container_width=True, config={'staticPlot': True})
            # -------------------------------------------------------------
