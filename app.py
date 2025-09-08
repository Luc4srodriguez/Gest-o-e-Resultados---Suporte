# app.py
import streamlit as st
import pandas as pd
import io
import re
import plotly.express as px
import plotly.graph_objects as go
import time
import json
from datetime import datetime, date, time as dtime, timedelta
import unicodedata
import difflib
import os
import tempfile
from typing import Dict, Tuple, List, Optional

# ============================ CONFIGURAÇÃO DA PÁGINA ============================
st.set_page_config(
    page_title="Novetech • Sistema Integrado",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =============================== ESTADO INICIAL ================================
def ss_setdefault(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

ss_setdefault("kpi_alias_map", {})
ss_setdefault("theme_choice", "Escuro (alto contraste)")

# =============================== TEMA / ESTILO ================================
THEME = {
    "BG": "#0B1220", "CARD": "#0F172A", "TEXT": "#E5E7EB",
    "ACCENT": "#06B6D4", "ACCENT_DARK": "#0891B2",
    "MUTED": "#94A3B8"
}

def apply_theme():
    choice = st.session_state.get("theme_choice", "Escuro (alto contraste)")
    if choice.startswith("Escuro"):
        theme_vals = dict(
            BG="#0B1220", CARD="#0F172A", TEXT="#E5E7EB",
            ACCENT="#06B6D4", ACCENT_DARK="#0891B2", MUTED="#94A3B8"
        )
    else:
        theme_vals = dict(
            BG="#F6F8FB", CARD="#FFFFFF", TEXT="#0F172A",
            ACCENT="#0EA5E9", ACCENT_DARK="#0284C7", MUTED="#64748B"
        )
    THEME.update(theme_vals)

    st.markdown(f"""
    <style>
    :root {{
      --bg: {THEME['BG']};
      --card: {THEME['CARD']};
      --text: {THEME['TEXT']};
      --accent: {THEME['ACCENT']};
      --accentDark: {THEME['ACCENT_DARK']};
      --muted: {THEME['MUTED']};
    }}
    html, body, .stApp {{
      background: var(--bg) !important;
      color: var(--text) !important;
      font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Arial;
    }}
    .block-card {{
      background: var(--card);
      border: 1px solid rgba(148,163,184,0.25);
      border-radius: 16px;
      padding: 18px 18px 8px 18px;
      box-shadow: 0 1px 2px rgba(2,6,23,0.08);
      margin-bottom: 14px;
    }}
    .block-help {{
      font-size: 0.9rem; color: var(--muted); margin-top: -6px; margin-bottom: 6px;
    }}
    .soft-divider {{
      border: none; border-top: 1px solid rgba(148,163,184,0.25); margin: 10px 0;
    }}
    .stButton>button {{
      background: linear-gradient(180deg, var(--accent), var(--accentDark));
      color: #fff !important;
      border: 0;
      border-radius: 10px;
      padding: 0.55rem 0.9rem;
      font-weight: 600;
    }}
    .stButton>button:hover {{ filter: brightness(0.96); }}
    .btn-secondary>button {{
      background: transparent !important;
      color: var(--accent) !important;
      border: 1px solid var(--accent) !important;
      border-radius: 10px !important;
    }}
    .pill {{
      display:inline-block; padding: 4px 10px; border-radius:999px;
      background: rgba(14,165,233,0.12); color: var(--accent); font-weight:600; font-size: 0.8rem;
      margin-left: 6px;
    }}
    .muted {{ color: var(--muted); }}
    .keyline {{ border-left: 4px solid var(--accent); padding-left: 10px; }}
    #MainMenu, footer {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

def apply_plot_theme(fig):
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=THEME["TEXT"])
    )

apply_theme()

# ========================= PESOS E DEFAULTS DE AVALIAÇÃO ======================
ss_setdefault("pesos_ferramentas", {
    "AtendSaúde": 20, "AtendeEndemias": 5, "PEC": 20,
    "eSUS Feedback": 15, "Infra": 10, "Meeds": 10,
    "Sistema Hospital": 5, "VISA": 5, "AB Território": 10
})
ss_setdefault("pesos_competencias", {
    "Habilidade técnica em atendimento": 1,
    "Suporte nível 1": 1,
    "Suporte nível 2": 1,
    "Infra nível 1": 1,
    "Habilidade técnica para treinamento": 1,
    "Consegue realizar capacitações das ferramentas": 1
})
ss_setdefault("pesos_blocos", {"Ferramentas": 50, "Competências": 50})

for k in st.session_state["pesos_ferramentas"].keys():
    ss_setdefault(f"prof_{k}", 70)
for comp in [
    "comp_atendimento","comp_sup1","comp_sup2","comp_infra1","comp_trein_tecnica","comp_capacitacoes"
]:
    ss_setdefault(comp, 8 if comp not in ("comp_sup2","comp_infra1") else 7)

ss_setdefault("periodo_ref", datetime.now().strftime("%B/%Y"))
ss_setdefault("aderencia_valores", "Alta")
ss_setdefault("definir_prox_rev", False)
ss_setdefault("proxima_revisao", date.today())
ss_setdefault("cursos", ""); ss_setdefault("pontos_fortes", ""); ss_setdefault("pontos_melhorar", "")
ss_setdefault("feedback_final", ""); ss_setdefault("pip_check", False); ss_setdefault("destaque_check", False)

ss_setdefault("mostrar_metas_para_tecnico", True)
for i in range(1,4):
    ss_setdefault(f"meta_titulo_{i}", ""); ss_setdefault(f"meta_desc_{i}", "")
    ss_setdefault(f"meta_ind_{i}", ""); ss_setdefault(f"meta_resp_{i}", "")
    ss_setdefault(f"meta_prazo_{i}", date.today()); ss_setdefault(f"meta_is_curso_{i}", False)

ss_setdefault("show_cursos_to_tech", True)
ss_setdefault("show_pontos_fortes_to_tech", True)
ss_setdefault("show_pontos_melhorar_to_tech", True)

# ================================ HELPERS ======================================
def safe_rerun():
    try:
        st.rerun()
    except Exception:
        pass

def ui_toggle(label, key, value=False, help=None):
    try:
        return st.toggle(label, value=value, key=key, help=help)
    except AttributeError:
        return st.checkbox(label, value=value, key=key, help=help)

def _atomic_write(path, data):
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=d)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(tmp, path)

def load_users():
    try:
        with open('users.json','r',encoding='utf-8') as f: return json.load(f)
    except FileNotFoundError:
        st.error("Arquivo 'users.json' não encontrado.")
        return []
    except json.JSONDecodeError:
        st.error("Falha ao ler 'users.json' (JSON inválido).")
        return []

def save_users(data): _atomic_write('users.json', data)

def load_fichas():
    try:
        with open('fichas.json','r',encoding='utf-8') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_fichas(data): _atomic_write('fichas.json', data)

def _safe_filename(name: str) -> str:
    base = unicodedata.normalize('NFKD', name).encode('ascii','ignore').decode()
    base = re.sub(r'[^A-Za-z0-9_.-]+', '_', base).strip('_')
    return base[:120] or "arquivo"

def save_certificado(username: str, meta_index: int, uploaded_file) -> str:
    os.makedirs(f'uploads/certificados/{username}', exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    fname = _safe_filename(uploaded_file.name)
    path = f'uploads/certificados/{username}/meta{meta_index+1}_{ts}_{fname}'
    with open(path,'wb') as f:
        f.write(uploaded_file.getbuffer())
    return path

def ler_csv_robusto(file_bytes: bytes) -> pd.DataFrame:
    tentativas = [
        {"sep": None, "engine": "python", "encoding": "utf-8"},
        {"sep": ";", "engine": "c", "encoding": "utf-8"},
        {"sep": ",", "engine": "c", "encoding": "utf-8"},
        {"sep": "\t", "engine": "c", "encoding": "utf-8"},
        {"sep": "|", "engine": "c", "encoding": "utf-8"},
        {"sep": None, "engine": "python", "encoding": "utf-8-sig"},
        {"sep": None, "engine": "python", "encoding": "latin1"},
    ]
    last_exc = None
    for opts in tentativas:
        try:
            buf = io.BytesIO(file_bytes)
            df = pd.read_csv(buf, sep=opts["sep"], engine=opts["engine"],
                             encoding=opts["encoding"], on_bad_lines="skip")
            df.attrs["_read_opts_"] = opts
            return df
        except Exception as e:
            last_exc = e
            continue
    raise last_exc if last_exc else ValueError("Falha ao ler CSV.")

def _parse_hms(val):
    if pd.isna(val): return None
    s = str(val).strip()
    if not s: return None
    parts = s.split(":")
    if not (1 <= len(parts) <= 3): return None
    try: parts = [int(p) for p in parts]
    except: return None
    if len(parts)==1: h,m,sec = 0,0,parts[0]
    elif len(parts)==2: h,m,sec = 0,parts[0],parts[1]
    else: h,m,sec = parts
    return h,m,sec

def converter_para_segundos(valor):
    try:
        h,m,s = _parse_hms(valor) or (None,None,None)
        if h is None: return None
        return h*3600 + m*60 + s
    except: return None

def converter_para_minutos(valor):
    try:
        h,m,s = _parse_hms(valor) or (None,None,None)
        if h is None: return None
        return h*60 + m + s/60
    except: return None

def formatar_tempo_minutos(minutos_total):
    if minutos_total is None or pd.isna(minutos_total): return "00:00"
    minutos = int(minutos_total)
    seg = int(round((minutos_total - minutos) * 60))
    return f"{minutos:02}:{seg:02}"

def linha_valida_em_colunas(row, colunas):
    for c in colunas:
        cell = row.get(c, None)
        if isinstance(cell, str) and re.search(r'\w', cell): return True
        elif pd.notna(cell): return True
    return False

def definir_turno(data_hora_str):
    try:
        if pd.isna(data_hora_str): return "Outro"
        dt = pd.to_datetime(data_hora_str)
        hora = dt.hour
        if   7 <= hora <= 12: return "Manhã"
        elif 13 <= hora <= 17: return "Tarde"
        elif 18 <= hora <= 22: return "Noite"
        else: return "Madrugada"
    except: return "Outro"

def _norm(txt: str) -> str:
    if txt is None: return ""
    txt = str(txt).strip().lower()
    txt = unicodedata.normalize('NFKD', txt)
    txt = ''.join(c for c in txt if not unicodedata.combining(c))
    txt = re.sub(r'[^a-z0-9@._\s-]', '', txt)
    txt = re.sub(r'\s+', ' ', txt)
    return txt.strip()

def _kpi_lookup_for_tech(tecnico: dict, kpis_norm: dict):
    if not tecnico: return (None, None)
    alias_map = st.session_state.get("kpi_alias_map", {})
    manual_key = alias_map.get(tecnico.get("username","").lower())
    if manual_key and manual_key in kpis_norm:
        return manual_key, kpis_norm[manual_key]
    candidatos = {_norm(tecnico.get("name","")), _norm(tecnico.get("username",""))}
    user = tecnico.get("username","")
    if "@" in user: candidatos.add(_norm(user.split("@")[0]))
    for c in list(candidatos):
        if c in kpis_norm: return c, kpis_norm[c]
    keys = list(kpis_norm.keys())
    for c in list(candidatos):
        m = difflib.get_close_matches(c, keys, n=1, cutoff=0.82)
        if m: return m[0], kpis_norm[m[0]]
    return (None, None)

def _conceito_por_nota(n):
    if n is None or pd.isna(n): return "N/A"
    if n >= 9.0: return "Excelente"
    if n >= 8.0: return "Muito Bom"
    if n >= 7.0: return "Bom"
    if n >= 6.0: return "Regular"
    return "A Melhorar"

def _estrela_por_nota(n):
    if n is None or pd.isna(n): return "⭐"
    if n >= 9.0: return "⭐⭐⭐⭐⭐"
    if n >= 8.0: return "⭐⭐⭐⭐"
    if n >= 7.0: return "⭐⭐⭐"
    if n >= 6.0: return "⭐⭐"
    return "⭐"

# ==================== PESOS: UTILITÁRIOS & PRESETS ============================
PREETS_FILE = "presets_pesos.json"  # filename

def load_presets() -> Dict:
    if os.path.exists(PREETS_FILE):
        try:
            with open(PREETS_FILE,'r',encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_presets(data: Dict):
    _atomic_write(PREETS_FILE, data)

def normalize_weights(d: Dict[str,int]) -> Dict[str,float]:
    s = sum(d.values()) or 1
    return {k: v/s for k,v in d.items()}

def ensure_sum_bar(values: List[int], label="Total"):
    total = sum(values)
    st.progress(min(total, 100)/100.0, text=f"{label}: {total} {'(OK)' if total==100 else '(ajuste necessário)'}")
    if total != 100:
        st.warning(f"O somatório precisa ser **100**. Atual: **{total}**.")

def donut_weights(weights: Dict[str,int], title: str):
    labels = list(weights.keys())
    vals = list(weights.values())
    fig = go.Figure(data=[go.Pie(labels=labels, values=vals, hole=.55)])
    fig.update_traces(textinfo='percent+label')
    fig.update_layout(title=title, margin=dict(t=30, b=10, l=10, r=10))
    apply_plot_theme(fig)
    st.plotly_chart(fig, use_container_width=True)

# ==================== FILTRO GLOBAL & KPIs (com período) ======================
def period_bounds(start_date: date, end_date: date) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """Converte datas em limites (início do dia e fim do dia)."""
    start_ts = pd.Timestamp.combine(start_date, dtime.min)
    end_ts = pd.Timestamp.combine(end_date, dtime.max)
    return start_ts, end_ts

def period_mask(series_dt: pd.Series, start_date: date, end_date: date) -> pd.Series:
    """Máscara robusta, inclusiva em ambos os lados, independente de timezone."""
    s = series_dt.copy()
    # normaliza timezone -> naive
    try:
        if pd.api.types.is_datetime64tz_dtype(s):
            s = s.dt.tz_convert(None)
    except Exception:
        try:
            s = s.dt.tz_localize(None)
        except Exception:
            pass
    start_ts, end_ts = period_bounds(start_date, end_date)
    return s.between(start_ts, end_ts, inclusive="both")

def compute_kpis_por_responsavel(df: pd.DataFrame):
    kpis_norm, labels_orig = {}, set()
    if "responsible" not in df.columns or df.empty: return kpis_norm, labels_orig
    df_res = df.copy()
    df_res["responsible"] = df_res["responsible"].astype(str).str.strip()
    df_res = df_res[df_res["responsible"].str.len() > 0]
    if df_res.empty: return kpis_norm, labels_orig
    grp = df_res.groupby("responsible", dropna=True)
    base = grp.size().rename("qtd").to_frame().reset_index()
    df_k = base
    if "rating" in df_res.columns:
        df_k = df_k.merge(grp["rating"].mean().rename("rating_media"), on="responsible", how="left")
    if "duracao_minutos" in df_res.columns:
        df_k = df_k.merge(grp["duracao_minutos"].mean().rename("duracao_media"), on="responsible", how="left")
    if "tempo_espera_segundos" in df_res.columns:
        df_k = df_k.merge(grp["tempo_espera_segundos"].mean().rename("espera_media"), on="responsible", how="left")
    for _, r in df_k.iterrows():
        resp = str(r["responsible"]).strip()
        labels_orig.add(resp)
        data = {
            "responsavel_label": resp,
            "qtd": int(r["qtd"]),
            "rating_media": float(r.get("rating_media")) if pd.notna(r.get("rating_media")) else None,
            "duracao_media": float(r.get("duracao_media")) if pd.notna(r.get("duracao_media")) else None,
            "espera_media": float(r.get("espera_media")) if pd.notna(r.get("espera_media")) else None,
        }
        keys_for_this = {_norm(resp)}
        if "@" in resp: keys_for_this.add(_norm(resp.split("@")[0]))
        m = re.search(r"\(([^)]+)\)", resp)
        if m: keys_for_this.add(_norm(m.group(1)))
        for k in keys_for_this:
            if k: kpis_norm[k] = data
    return kpis_norm, sorted(labels_orig)

def render_period_filter(df: pd.DataFrame, title="🗓️ Filtro Global de Período",
                         key_start="period_start", key_end="period_end") -> Tuple[Optional[date], Optional[date], bool]:
    if "created_dt" not in df.columns:
        st.warning("Coluna 'created_at' ausente — filtro indisponível.")
        return None, None, False
    valid_dt = df["created_dt"].dropna()
    if valid_dt.empty:
        st.warning("Datas inválidas no arquivo — filtro indisponível.")
        return None, None, False
    min_date = valid_dt.min().date(); max_date = valid_dt.max().date()
    st.markdown("<div class='block-card'>", unsafe_allow_html=True)
    st.markdown(f"#### {title} <span class='pill'>global</span>", unsafe_allow_html=True)
    st.markdown("<div class='block-help'>O intervalo aqui afeta o Dashboard e os indicadores usados na Avaliação.</div>", unsafe_allow_html=True)
    c1,c2,c3 = st.columns([0.33,0.33,0.34])
    with c1:
        start_date = st.date_input("Data inicial", min_value=min_date, max_value=max_date,
                                   value=st.session_state.get(key_start, min_date), key=key_start)
    with c2:
        end_date = st.date_input("Data final", min_value=min_date, max_value=max_date,
                                 value=st.session_state.get(key_end, max_date), key=key_end)
    with c3:
        if start_date > end_date:
            st.error("A data inicial não pode ser maior que a final.")
            total_sel = 0
        else:
            mask = period_mask(df["created_dt"], start_date, end_date)
            total_sel = int(mask.sum())
        st.metric("Registros no período", f"{total_sel}")
    st.caption(f"Período: **{start_date.strftime('%d/%m/%Y')}** → **{end_date.strftime('%d/%m/%Y')}**")
    st.markdown("</div>", unsafe_allow_html=True)
    return start_date, end_date, True

def filter_df_by_period(df: pd.DataFrame, start_date: date, end_date: date) -> pd.DataFrame:
    if "created_dt" not in df.columns or start_date is None or end_date is None:
        return df.copy()
    mask = period_mask(df["created_dt"], start_date, end_date)
    return df.loc[mask].copy()

# ================================ COMPONENTES UI ================================
def mostrar_tabela_grafico(df, col_name, title, emoji, cor, mostrar_todos=False):
    if col_name not in df.columns: return
    st.markdown(f"<div class='block-card'><div class='keyline'><h3>{emoji} {title}</h3></div>", unsafe_allow_html=True)
    top_vals = df[col_name].value_counts()
    total_validos = df[col_name].dropna().shape[0]
    if not mostrar_todos: top_vals = top_vals.head(5)
    top_vals_df = top_vals.reset_index()
    top_vals_df.columns = [col_name, "count"]
    top_vals_df['Percentual'] = (top_vals_df['count'] / total_validos * 100) if total_validos > 0 else 0
    col1,col2 = st.columns([0.46,0.54])
    with col1:
        st.caption(f"Total de linhas válidas: **{total_validos}**")
        st.dataframe(
            top_vals_df.set_index(col_name),
            column_config={
                "count": st.column_config.NumberColumn("Contagem"),
                "Percentual": st.column_config.ProgressColumn("Percentual", format="%.2f%%", min_value=0, max_value=100)
            },
            use_container_width=True
        )
    with col2:
        fig = px.bar(top_vals_df, x=col_name, y="count", labels={col_name:"", "count":"Quantidade"},
                     text="count", custom_data=["Percentual"])
        fig.update_traces(textposition='outside', marker_color=cor,
                          hovertemplate='<b>%{x}</b><br>Contagem: %{y}<br>Percentual: %{customdata[0]:.2f}%<extra></extra>')
        fig.update_layout(xaxis_tickangle=-15, margin=dict(t=25,l=10,r=10,b=20), height=360)
        apply_plot_theme(fig)
        st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ================================ PÁGINAS ======================================
def pagina_login():
    st.markdown("<div class='block-card'>", unsafe_allow_html=True)
    st.image("https://cdn-icons-png.flaticon.com/512/1827/1827978.png", width=90)
    st.markdown("## Sistema de Avaliação — Novetech")
    st.caption("Acesse com seu usuário e senha. Em caso de dúvidas, fale com o suporte interno.")
    with st.form("login_form"):
        username = st.text_input("Usuário", key="login_user", help="Seu login cadastrado").lower()
        password = st.text_input("Senha", type="password", key="login_pass", help="Use uma senha forte e não compartilhe.")
        cols = st.columns([1,1])
        with cols[0]:
            entrar = st.form_submit_button("Entrar")
        with cols[1]:
            st.markdown("<div class='btn-secondary'>", unsafe_allow_html=True)
            st.form_submit_button("Limpar", on_click=lambda: (st.session_state.__setitem__("login_user",""), st.session_state.__setitem__("login_pass","")))
            st.markdown("</div>", unsafe_allow_html=True)
        if entrar:
            users = load_users()
            user_found = next((u for u in users if u['username']==username and u['password']==password), None)
            if user_found:
                st.session_state["logged_in"] = True
                st.session_state["user_info"] = user_found
                st.session_state["page"] = "menu"
                st.success("Login realizado!")
                time.sleep(0.3); st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")
    st.markdown("</div>", unsafe_allow_html=True)

def pagina_menu_principal():
    st.markdown("<div class='block-card'>", unsafe_allow_html=True)
    st.markdown("### Menu principal")
    st.caption("Escolha uma área.")
    role = st.session_state['user_info']['role']
    menu_options = (
        {"avaliar_tecnicos":{"label":"Avaliação de Técnicos","icon":"📝"},
         "pesos":{"label":"Pesos","icon":"⚖️"},
         "dashboard":{"label":"Análise de Dados","icon":"📊"},
         "historico":{"label":"Histórico de Fichas","icon":"📂"},
         "usuarios":{"label":"Gerenciar Usuários","icon":"👥"}}
        if role=="coordenador"
        else {"minhas_fichas":{"label":"Minhas Fichas","icon":"📋"},
              "dashboard":{"label":"Análise de Dados","icon":"📊"}}
    )
    cols = st.columns(min(5, len(menu_options)))
    for i,(page_key, page_info) in enumerate(menu_options.items()):
        with cols[i % len(cols)]:
            st.markdown(f"**{page_info['icon']} {page_info['label']}**")
            if st.button("Abrir", key=f"open_{page_key}", use_container_width=True):
                # roteamento especial
                if page_key == "historico":
                    st.session_state.page = "avaliar_tecnicos"
                    st.session_state._subtab = "historico"
                elif page_key == "usuarios":
                    st.session_state.page = "avaliar_tecnicos"
                    st.session_state._subtab = "usuarios"
                elif page_key == "pesos":
                    st.session_state.page = "avaliar_tecnicos"
                    st.session_state._subtab = "pesos"
                else:
                    st.session_state.page = page_key
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def criar_botao_voltar():
    st.markdown("<div class='block-card'>", unsafe_allow_html=True)
    st.caption("Navegação")
    st.markdown("<div class='btn-secondary'>", unsafe_allow_html=True)
    if st.button("⬅ Voltar ao Menu Principal"):
        st.session_state.page = "menu"; st.rerun()
    st.markdown("</div></div>", unsafe_allow_html=True)

# -------------------------------- DASHBOARD ------------------------------------
def pagina_dashboard():
    criar_botao_voltar()
    st.markdown("<div class='block-card'>", unsafe_allow_html=True)
    st.markdown("## 📊 Dashboard de Análise de Acionamentos")
    st.caption("Carregue seu CSV. O filtro de período impacta todas as análises e a avaliação.")
    uploaded_file = st.file_uploader("📎 Envie sua planilha (CSV)", type=["csv"], label_visibility="visible",
                                     help="CSV com cabeçalhos. Delimitador detectado automaticamente.")
    clear_cols = st.columns([0.5,0.5])
    with clear_cols[0]:
        if st.button("Limpar dados carregados", use_container_width=True):
            if "df_raw" in st.session_state: del st.session_state["df_raw"]
            st.success("Dados removidos."); time.sleep(0.2); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    if not uploaded_file and "df_raw" not in st.session_state:
        st.info("Aguardando upload para iniciar a análise.")
        return

    try:
        if uploaded_file:
            content = uploaded_file.read()
            df = ler_csv_robusto(content)
            opts = df.attrs.get("_read_opts_", {})
            if opts:
                st.success(f"Lido como **{opts.get('encoding')}** • sep **{opts.get('sep') or 'auto'}** • engine **{opts.get('engine')}**")
            df.columns = df.columns.str.strip()
            df = df.dropna(how="all")
            colunas_necessarias = [
                "name","group_attendants_name","client_name",
                "services_catalog_name","services_catalog_area_name",
                "services_catalog_item_name","ticket_title","duration",
                "waiting_time","responsible","rating","created_at"
            ]
            df = df[df.apply(lambda row: linha_valida_em_colunas(row, colunas_necessarias), axis=1)]
            df = df[[c for c in colunas_necessarias if c in df.columns]]

            if "waiting_time" in df.columns:
                df["tempo_espera_segundos"] = df["waiting_time"].apply(converter_para_segundos)
            if "duration" in df.columns:
                df["duracao_minutos"] = df["duration"].apply(converter_para_minutos)
            if "rating" in df.columns:
                df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
            if "created_at" in df.columns:
                df["turno"] = df["created_at"].apply(definir_turno)
                df["created_dt"] = pd.to_datetime(df["created_at"], errors="coerce")
            else:
                df["created_dt"] = pd.NaT

            # normaliza timezone para garantir filtro correto
            try:
                if pd.api.types.is_datetime64tz_dtype(df["created_dt"]):
                    df["created_dt"] = df["created_dt"].dt.tz_convert(None)
            except Exception:
                try:
                    df["created_dt"] = df["created_dt"].dt.tz_localize(None)
                except Exception:
                    pass

            st.session_state["df_raw"] = df
        else:
            df = st.session_state["df_raw"]

        # Filtro global confiável
        if "created_dt" in df.columns and not df["created_dt"].dropna().empty:
            start_date, end_date, ok = render_period_filter(df, key_start="period_start", key_end="period_end")
            df_f = filter_df_by_period(df, start_date, end_date) if ok else df
        else:
            st.warning("Sem datas válidas para filtrar."); df_f = df

        st.session_state["df_filtered"] = df_f

        # botão para baixar CSV filtrado
        st.markdown("<div class='block-card'>", unsafe_allow_html=True)
        st.caption("Exportar dados do período:")
        csv_bytes = df_f.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Baixar CSV filtrado", data=csv_bytes, file_name=f"acionamentos_filtrado_{datetime.now().strftime('%Y%m%d')}.csv")
        st.markdown("</div>", unsafe_allow_html=True)

        # KPIs por responsável
        kpis_norm, labels_orig = compute_kpis_por_responsavel(df_f)
        st.session_state["kpis_por_responsavel"] = kpis_norm
        st.session_state["kpis_labels_orig"] = labels_orig

        # --------- Resumo + Percentuais ----------
        st.markdown("<div class='block-card'>", unsafe_allow_html=True)
        st.markdown("### 📌 Resumo Geral de Performance (período filtrado)")
        META_AVALIACAO, META_DURACAO_MINUTOS, META_ESPERA_SEGUNDOS = 4.8, 28.0, 20.0
        media_rating = df_f["rating"].dropna().mean() if "rating" in df_f.columns else float('nan')
        media_duracao = df_f["duracao_minutos"].dropna().mean() if "duracao_minutos" in df_f.columns else float('nan')
        media_espera_segundos = df_f["tempo_espera_segundos"].dropna().mean() if "tempo_espera_segundos" in df_f.columns else float('nan')
        show_pct = st.checkbox("Exibir percentuais de atingimento", value=True, key="show_pct_dash")
        c1,c2,c3 = st.columns(3)
        with c1:
            delta = media_rating - META_AVALIACAO if pd.notna(media_rating) else None
            st.metric(f"⭐ Avaliação Média (Meta: {META_AVALIACAO})",
                      f"{media_rating:.2f}" if pd.notna(media_rating) else "N/A",
                      f"{delta:.2f}" if delta is not None else None)
            if show_pct and pd.notna(media_rating):
                ating = media_rating / META_AVALIACAO if META_AVALIACAO>0 else 0
                st.caption(f"Atingimento: **{ating:.1%}**")
        with c2:
            delta = media_duracao - META_DURACAO_MINUTOS if pd.notna(media_duracao) else None
            st.metric(f"🕒 Duração Média (Meta: {int(META_DURACAO_MINUTOS)} min)",
                      formatar_tempo_minutos(media_duracao) if pd.notna(media_duracao) else "N/A",
                      f"{delta:+.1f} min" if delta is not None else None)
            if show_pct and pd.notna(media_duracao) and media_duracao>0:
                ating = META_DURACAO_MINUTOS / media_duracao
                st.caption(f"Atingimento: **{ating:.1%}**")
        with c3:
            delta = media_espera_segundos - META_ESPERA_SEGUNDOS if pd.notna(media_espera_segundos) else None
            st.metric(f"⏳ Espera Média (Meta: {int(META_ESPERA_SEGUNDOS)} s)",
                      formatar_tempo_minutos(media_espera_segundos/60) if pd.notna(media_espera_segundos) else "N/A",
                      f"{delta:+.1f} s" if delta is not None else None)
            if show_pct and pd.notna(media_espera_segundos) and media_espera_segundos>0:
                ating = META_ESPERA_SEGUNDOS / media_espera_segundos
                st.caption(f"Atingimento: **{ating:.1%}**")
        st.markdown("</div>", unsafe_allow_html=True)

        # --------- SLAs ----------
        st.markdown("<div class='block-card'>", unsafe_allow_html=True)
        st.markdown("### 🎯 Atingimento de Metas (SLA)")
        p1,p2,p3 = st.columns(3)
        with p1:
            st.caption("SLA de Avaliação")
            if pd.notna(media_rating):
                ating = (media_rating / META_AVALIACAO)
                st.progress(min(ating,1.0), text=f"{media_rating:.2f} / {META_AVALIACAO}")
            else: st.caption("N/A")
        with p2:
            st.caption("SLA de Duração")
            if pd.notna(media_duracao) and media_duracao>0:
                ating = META_DURACAO_MINUTOS / media_duracao
                st.progress(min(ating,1.0), text=f"{formatar_tempo_minutos(media_duracao)} / {int(META_DURACAO_MINUTOS)}:00")
            else: st.caption("N/A")
        with p3:
            st.caption("SLA de Tempo de Espera")
            if pd.notna(media_espera_segundos) and media_espera_segundos>0:
                ating = META_ESPERA_SEGUNDOS / media_espera_segundos
                st.progress(min(ating,1.0), text=f"{media_espera_segundos:.1f}s / {int(META_ESPERA_SEGUNDOS)}s")
            else: st.caption("N/A")
        st.markdown("</div>", unsafe_allow_html=True)

        # --------- Análises Detalhadas ----------
        st.markdown("#### 🔍 Análises Detalhadas (período filtrado)")
        tab1,tab2,tab3 = st.tabs(["🏢 Visão Geral","📦 Por Serviço","🙋 Por Responsável"])
        with tab1:
            if "turno" in df_f.columns:
                mostrar_tabela_grafico(df_f, "turno", "Distribuição por Turno", "⏰", "#22C55E")
            mostrar_tabela_grafico(df_f, "client_name", "Clientes que Mais Acionaram", "👤", "#3B82F6")
        with tab2:
            mostrar_tabela_grafico(df_f, "services_catalog_name", "Catálogos de Serviços Mais Usados", "📦", "#F59E0B")
            mostrar_tabela_grafico(df_f, "services_catalog_item_name", "Itens do Catálogo Mais Solicitados", "🔧", "#EF4444")
            mostrar_tabela_grafico(df_f, "ticket_title", "Títulos de Tickets Mais Frequentes", "📌", "#10B981")
        with tab3:
            mostrar_tabela_grafico(df_f, "responsible", "Responsáveis com Mais Atendimentos", "🙋", "#0EA5E9", mostrar_todos=True)

            if "tempo_espera_segundos" in df_f.columns:
                st.markdown("<div class='block-card'>", unsafe_allow_html=True)
                st.subheader("⏳ Média de Tempo de Espera por Responsável")
                m1 = df_f.groupby("responsible")["tempo_espera_segundos"].mean().dropna().reset_index()
                m1["Tempo Formatado"] = (m1["tempo_espera_segundos"]/60).apply(formatar_tempo_minutos)
                fig = px.bar(m1.sort_values("tempo_espera_segundos"),
                             x="responsible", y="tempo_espera_segundos", text="Tempo Formatado",
                             labels={"tempo_espera_segundos":"Tempo Médio (s)","responsible":"Responsável"})
                fig.update_traces(textposition="outside", marker_color="#8b99ae")
                apply_plot_theme(fig); st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            if "duracao_minutos" in df_f.columns:
                st.markdown("<div class='block-card'>", unsafe_allow_html=True)
                st.subheader("🕒 Média de Duração por Responsável")
                m2 = df_f.groupby("responsible")["duracao_minutos"].mean().dropna().reset_index()
                m2["Duração Formatada"] = m2["duracao_minutos"].apply(formatar_tempo_minutos)
                fig = px.bar(m2.sort_values("duracao_minutos"),
                             x="responsible", y="duracao_minutos", text="Duração Formatada",
                             labels={"duracao_minutos":"Duração Média (min)","responsible":"Responsável"})
                fig.update_traces(textposition="outside", marker_color="#60a5fa")
                apply_plot_theme(fig); st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            if "rating" in df_f.columns:
                st.markdown("<div class='block-card'>", unsafe_allow_html=True)
                st.subheader("🌟 Média de Avaliação por Responsável")
                m3 = df_f.groupby("responsible")["rating"].mean().dropna().reset_index()
                fig = px.bar(m3.sort_values("rating"),
                             x="responsible", y="rating",
                             text=m3["rating"].round(2),
                             labels={"responsible":"Responsável","rating":"Média de Avaliação"})
                fig.update_traces(textposition="outside", marker_color="#f59e0b")
                fig.update_layout(yaxis=dict(tickformat=".2f"))
                apply_plot_theme(fig); st.plotly_chart(fig, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo. Detalhe: {e}")

# ----------------------- AVALIAÇÃO / COORDENADOR -------------------------------
def pagina_coordenador():
    criar_botao_voltar()
    st.markdown("## 👑 Painel do Coordenador")

    # >>> Agora 4 abas principais: Avaliar, Pesos, Histórico, Usuários
    tab_avaliar, tab_pesos, tab_hist, tab_user = st.tabs(
        ["📝 Avaliar Técnicos", "⚖️ Pesos", "📂 Histórico de Fichas", "👥 Gerenciar Usuários"]
    )

    # Guarda subtab preferida quando vier do menu
    _pref = st.session_state.pop("_subtab", None)
    if _pref == "historico":
        with tab_hist: pass
    elif _pref == "usuarios":
        with tab_user: pass
    elif _pref == "pesos":
        with tab_pesos: pass

    # ====================== AVALIAR ======================
    with tab_avaliar:
        st.markdown("<div class='block-card'>", unsafe_allow_html=True)
        st.markdown("### Criar Nova Ficha de Avaliação")
        st.caption("Use o filtro de período global abaixo. Os indicadores do técnico respeitam esse intervalo.")
        st.markdown("</div>", unsafe_allow_html=True)

        df_base = st.session_state.get("df_raw")
        if isinstance(df_base, pd.DataFrame):
            start_date, end_date, ok = render_period_filter(df_base, title="🗓️ Filtro Global de Período (Avaliação)",
                                                            key_start="period_start", key_end="period_end")
            df_filtrado = filter_df_by_period(df_base, start_date, end_date) if ok else df_base
            kpis_norm, labels_orig = compute_kpis_por_responsavel(df_filtrado)
            st.session_state["kpis_por_responsavel"] = kpis_norm
            st.session_state["kpis_labels_orig"] = labels_orig
        else:
            st.info("Para KPIs do CSV na ficha, carregue um arquivo em **📊 Dashboard**.")
            kpis_norm, labels_orig = {}, []

        users, fichas = load_users(), load_fichas()
        tecnicos = [u for u in users if u['role']=="tecnico"]
        if not tecnicos:
            st.info("Nenhum técnico cadastrado. Adicione um na aba **Gerenciar Usuários**.")
            return

        st.markdown("<div class='block-card'>", unsafe_allow_html=True)
        tecnico_nome = st.selectbox("Selecione um Técnico", [t['name'] for t in tecnicos], key="select_tecnico_aval",
                                    help="Procure pelo nome para filtrar.")
        st.markdown("</div>", unsafe_allow_html=True)
        tecnico = next((t for t in tecnicos if t['name']==tecnico_nome), None)

        kpis_norm = st.session_state.get("kpis_por_responsavel", {}) or {}
        labels_orig = st.session_state.get("kpis_labels_orig", []) or []
        kpi_key, kpi = _kpi_lookup_for_tech(tecnico, kpis_norm)

        st.markdown("<div class='block-card'>", unsafe_allow_html=True)
        if not kpi:
            st.info("Nenhum KPI encontrado a partir do CSV/período.")
            if labels_orig:
                choose = st.selectbox("Vincular manualmente ao responsável do CSV",
                                      options=["-- selecione --"] + labels_orig, index=0)
                if choose and choose != "-- selecione --":
                    key_norm = _norm(choose)
                    if key_norm in kpis_norm:
                        st.session_state["kpi_alias_map"][tecnico.get("username","").lower()] = key_norm
                        kpi_key, kpi = key_norm, kpis_norm[key_norm]
                        st.success(f"Vinculado a: {choose}")
        else:
            st.success(f"Indicadores (período filtrado) encontrados para **{kpi.get('responsavel_label','')}**.")
        st.markdown("</div>", unsafe_allow_html=True)

        # Bloco único de Indicadores do Técnico — Período aplicado
        st.markdown("<div class='block-card'>", unsafe_allow_html=True)
        st.markdown("#### 📌 Indicadores do Técnico — Período aplicado")
        c1,c2,c3,c4 = st.columns(4)
        if kpi:
            with c1: st.metric("Total de Atendimentos", f"{int(kpi['qtd'])}")
            with c2:
                me = kpi["espera_media"]
                st.metric("Média de Espera", formatar_tempo_minutos((me or 0.0)/60) if me is not None else "N/A")
            with c3:
                md = kpi["duracao_media"]
                st.metric("Média de Duração", formatar_tempo_minutos(md) if md is not None else "N/A")
            with c4:
                ma = kpi["rating_media"]
                st.metric("Média de Avaliação", f"{ma:.2f}" if ma is not None else "N/A")
        else:
            with c1: st.metric("Total de Atendimentos","N/A")
            with c2: st.metric("Média de Espera","N/A")
            with c3: st.metric("Média de Duração","N/A")
            with c4: st.metric("Média de Avaliação","N/A")
        st.markdown("</div>", unsafe_allow_html=True)

        # Abas internas (sem “Indicadores CSV” e sem “Pesos”)
        aba_ferr, aba_comp, aba_res, aba_meta = st.tabs(
            ["🧩 Proficiência (Ferramentas)", "🎯 Competências (0–10)", "✅ Resultado Consolidado", "🧭 Metas & Plano"]
        )

        # Proficiência (Ferramentas)
        with aba_ferr:
            st.markdown("<div class='block-card'>", unsafe_allow_html=True)
            st.caption("Arraste os sliders (0–100%). A contribuição de cada ferramenta é definida pelos pesos.")
            pesos_ferramentas = st.session_state["pesos_ferramentas"].copy()
            cols = st.columns(3); entradas = {}
            for i, nome in enumerate(pesos_ferramentas.keys()):
                with cols[i % 3]:
                    prof_val = st.slider(f"{nome} ({pesos_ferramentas[nome]}%)", 0, 100, st.session_state[f"prof_{nome}"], key=f"prof_{nome}")
                    entradas[nome] = prof_val
            soma_w_f = sum(pesos_ferramentas.values())
            total_ponderado = 0.0 if soma_w_f<=0 else sum(entradas[n]*pesos_ferramentas[n] for n in entradas)/soma_w_f
            st.metric("Índice de Proficiência nas Ferramentas (%)", f"{total_ponderado:.1f}%")
            st.session_state["prof_entradas"] = entradas
            st.session_state["prof_indice_pct"] = round(total_ponderado, 1)
            st.markdown("</div>", unsafe_allow_html=True)

        # Competências
        with aba_comp:
            st.markdown("<div class='block-card'>", unsafe_allow_html=True)
            st.caption("Notas (0–10) ponderadas por pesos relativos.")
            pesos_comp = st.session_state["pesos_competencias"].copy()
            c1,c2 = st.columns(2)
            with c1:
                comp_atendimento = st.slider("Habilidade técnica em atendimento", 0,10, st.session_state["comp_atendimento"], key="comp_atendimento")
                evid_atendimento = st.text_area("Evidências — Habilidade técnica em atendimento", key="evid_atendimento")
                comp_sup1 = st.slider("Suporte nível 1", 0,10, st.session_state["comp_sup1"], key="comp_sup1")
                evid_sup1 = st.text_area("Evidências — Suporte nível 1", key="evid_sup1")
                comp_sup2 = st.slider("Suporte nível 2", 0,10, st.session_state["comp_sup2"], key="comp_sup2")
                evid_sup2 = st.text_area("Evidências — Suporte nível 2", key="evid_sup2")
            with c2:
                comp_infra1 = st.slider("Infra nível 1", 0,10, st.session_state["comp_infra1"], key="comp_infra1")
                evid_infra1 = st.text_area("Evidências — Infra nível 1", key="evid_infra1")
                comp_trein_tecnica = st.slider("Habilidade técnica para treinamento", 0,10, st.session_state["comp_trein_tecnica"], key="comp_trein_tecnica")
                evid_trein_tecnica = st.text_area("Evidências — Habilidade técnica para treinamento", key="evid_trein_tecnica")
                comp_capacitacoes = st.slider("Consegue realizar capacitações das ferramentas", 0,10, st.session_state["comp_capacitacoes"], key="comp_capacitacoes")
                evid_capacitacoes = st.text_area("Evidências — Capacitações das ferramentas", key="evid_capacitacoes")

            notas_dict = {
                "Habilidade técnica em atendimento": comp_atendimento,
                "Suporte nível 1": comp_sup1,
                "Suporte nível 2": comp_sup2,
                "Infra nível 1": comp_infra1,
                "Habilidade técnica para treinamento": comp_trein_tecnica,
                "Consegue realizar capacitações das ferramentas": comp_capacitacoes
            }
            soma_pesos = sum(pesos_comp.values())
            nota_comp_ponderada = 0.0 if soma_pesos<=0 else sum(notas_dict[k]*pesos_comp.get(k,0) for k in notas_dict)/soma_pesos
            st.metric("Nota de Competências (ponderada, 0–10)", f"{nota_comp_ponderada:.2f}")
            st.session_state["notas_dict"] = notas_dict
            st.session_state["nota_comp_ponderada"] = round(nota_comp_ponderada,2)
            st.session_state["evidencias_dict"] = {
                "habilidade_tecnica_atendimento": evid_atendimento,
                "suporte_nivel_1": evid_sup1,
                "suporte_nivel_2": evid_sup2,
                "infra_nivel_1": evid_infra1,
                "habilidade_tecnica_treinamento": evid_trein_tecnica,
                "capacitacoes_ferramentas": evid_capacitacoes,
            }
            st.markdown("</div>", unsafe_allow_html=True)

        # Resultado
        with aba_res:
            st.markdown("<div class='block-card'>", unsafe_allow_html=True)
            st.caption("Combinação das notas por blocos, com pesos 100% controláveis.")
            w_f = st.session_state["pesos_blocos"]["Ferramentas"]/100.0
            w_c = st.session_state["pesos_blocos"]["Competências"]/100.0
            prof_pct = st.session_state.get("prof_indice_pct", 0.0)
            nota_prof_em_10 = prof_pct/10.0
            nota_comp = st.session_state.get("nota_comp_ponderada", 0.0)
            nota_final = (nota_prof_em_10*w_f) + (nota_comp*w_c)
            conceito = _conceito_por_nota(nota_final); estrelas = _estrela_por_nota(nota_final)
            cm1,cm2,cm3,cm4 = st.columns(4)
            with cm1: st.metric("Proficiência (→ 0–10)", f"{nota_prof_em_10:.2f}")
            with cm2: st.metric("Competências (0–10)", f"{nota_comp:.2f}")
            with cm3: st.metric("Nota Final (0–10)", f"{nota_final:.2f}")
            with cm4: st.metric("Conceito", conceito)
            st.write(f"**Avaliação Geral:** {estrelas}")
            st.session_state["nota_final"] = round(nota_final,2)
            st.session_state["conceito_final"] = conceito
            st.session_state["estrelinhas_final"] = estrelas
            st.markdown("</div>", unsafe_allow_html=True)

        # Metas & Plano
        with aba_meta:
            st.markdown("<div class='block-card'>", unsafe_allow_html=True)
            colA,colB = st.columns(2)
            with colA:
                periodo_ref = st.text_input("Período de referência", value=st.session_state["periodo_ref"], key="periodo_ref")
                aderencia_valores = st.selectbox("Aderência à Cultura e Valores", ["Baixa","Média","Alta","Excelente"],
                                                 index=["Baixa","Média","Alta","Excelente"].index(st.session_state["aderencia_valores"]),
                                                 key="aderencia_valores")
            with colB:
                definir_prox_rev = ui_toggle("Definir próxima revisão?", key="definir_prox_rev",
                                             value=st.session_state["definir_prox_rev"])
                proxima_revisao = st.date_input("Próxima revisão (sugestão)", value=st.session_state["proxima_revisao"], key="proxima_revisao") if definir_prox_rev else None

            st.markdown("#### 🧭 Metas SMART (próximo ciclo)")
            metas = []
            for i in range(1,4):
                with st.expander(f"Meta {i}", expanded=(i==1)):
                    t = st.text_input(f"Título da Meta {i}", value=st.session_state[f"meta_titulo_{i}"], key=f"meta_titulo_{i}_in")
                    d = st.text_area(f"Descrição (SMART) {i}", value=st.session_state[f"meta_desc_{i}"], key=f"meta_desc_{i}_in")
                    ind = st.text_input(f"Indicador/Como medir {i}", value=st.session_state[f"meta_ind_{i}"], key=f"meta_ind_{i}_in")
                    default_resp = tecnico['name'] if not st.session_state[f"meta_resp_{i}"] else st.session_state[f"meta_resp_{i}"]
                    resp = st.text_input(f"Responsável primário {i}", value=default_resp, key=f"meta_resp_{i}_in")
                    prazo = st.date_input(f"Prazo {i}", value=st.session_state[f"meta_prazo_{i}"], key=f"meta_prazo_{i}_in")
                    is_curso = st.checkbox("É curso/treinamento?", value=st.session_state[f"meta_is_curso_{i}"], key=f"meta_is_curso_{i}_chk")
                    if t and d and ind and prazo:
                        item = {"titulo": t.strip(), "descricao": d.strip(), "indicador": ind.strip(),
                                "responsavel": resp.strip(), "prazo": prazo.strftime("%d/%m/%Y"),
                                "is_curso": bool(is_curso)}
                        if is_curso:
                            item["realizado"] = False; item["certificado_path"] = None
                        metas.append(item)

            st.markdown("---")
            mostrar_metas_para_tecnico = st.checkbox("Exibir as metas para o técnico no painel dele",
                                                     value=st.session_state["mostrar_metas_para_tecnico"],
                                                     key="mostrar_metas_para_tecnico")
            st.markdown("#### 🧭 Plano de Ação e Desenvolvimento")
            vis1,vis2,vis3 = st.columns(3)
            with vis1:
                show_cursos_to_tech = st.checkbox("Mostrar CURSOS ao técnico", value=st.session_state["show_cursos_to_tech"], key="show_cursos_to_tech")
            with vis2:
                show_pontos_fortes_to_tech = st.checkbox("Mostrar PONTOS FORTES ao técnico", value=st.session_state["show_pontos_fortes_to_tech"], key="show_pontos_fortes_to_tech")
            with vis3:
                show_pontos_melhorar_to_tech = st.checkbox("Mostrar PONTOS A MELHORAR ao técnico", value=st.session_state["show_pontos_melhorar_to_tech"], key="show_pontos_melhorar_to_tech")
            cursos = st.text_area("Cursos/Treinamentos sugeridos", value=st.session_state["cursos"], key="cursos")
            pontos_fortes = st.text_area("Pontos Fortes (síntese)", value=st.session_state["pontos_fortes"], key="pontos_fortes")
            pontos_melhorar = st.text_area("Pontos a Melhorar (síntese)", value=st.session_state["pontos_melhorar"], key="pontos_melhorar")
            feedback_final = st.text_area("Feedback Final do Coordenador", value=st.session_state["feedback_final"], key="feedback_final")

            pip_check = st.checkbox("Sugerir PIP (Plano Individual de Melhoria)", value=st.session_state["pip_check"], key="pip_check")
            destaque_check = st.checkbox("Indicar para Reconhecimento/Destaque", value=st.session_state["destaque_check"], key="destaque_check")

            st.markdown("<hr class='soft-divider'/>", unsafe_allow_html=True)
            st.subheader("✅ Pré-visualização")
            st.write(f"*Técnico:* {tecnico['name']}  |  *Período:* {periodo_ref or 'N/I'}")
            st.write(f"*Proficiência (%):* {st.session_state.get('prof_indice_pct',0.0):.1f}%  → *0–10:* {(st.session_state.get('prof_indice_pct',0.0)/10):.2f}")
            st.write(f"*Competências (0–10):* {st.session_state.get('nota_comp_ponderada',0.0):.2f}")
            st.write(f"*Pesos dos blocos:* Ferramentas {st.session_state['pesos_blocos']['Ferramentas']}% | Competências {st.session_state['pesos_blocos']['Competências']}%")
            st.write(f"*Nota Final (0–10):* {st.session_state.get('nota_final',0.0):.2f}  |  *Conceito:* {st.session_state.get('conceito_final','N/I')}  |  *Geral:* {st.session_state.get('estrelinhas_final','⭐')}")
            st.write(f"*Aderência a Valores:* {aderencia_valores}")
            if definir_prox_rev and proxima_revisao:
                st.write(f"*Próxima revisão (sugestão):* {proxima_revisao.strftime('%d/%m/%Y')}")
            st.write(f"*Metas visíveis ao técnico:* {'Sim' if mostrar_metas_para_tecnico else 'Não'}")
            st.write(f"*Plano visível:* Cursos [{ 'Sim' if show_cursos_to_tech else 'Não' }], Pontos Fortes [{ 'Sim' if show_pontos_fortes_to_tech else 'Não' }], Pontos a Melhorar [{ 'Sim' if show_pontos_melhorar_to_tech else 'Não' }]")

            erros = []
            if len(metas)==0: erros.append("Defina ao menos 1 meta SMART.")
            if not feedback_final.strip(): erros.append("Preencha o Feedback Final do Coordenador.")
            if erros: st.warning("⚠ Ajustes necessários:\n- " + "\n- ".join(erros))

            act1, act2 = st.columns([0.5,0.5])
            with act1:
                st.markdown("<div class='btn-secondary'>", unsafe_allow_html=True)
                salvar_click = st.button("✔ Salvar Avaliação", use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with act2:
                draft = {
                    "tecnico": tecnico['name'],
                    "periodo": periodo_ref,
                    "resultado": {
                        "prof_pct": st.session_state.get("prof_indice_pct",0.0),
                        "prof_0_10": st.session_state.get("prof_indice_pct",0.0)/10,
                        "comp_0_10": st.session_state.get("nota_comp_ponderada",0.0),
                        "nota_final": st.session_state.get("nota_final",0.0),
                        "conceito": st.session_state.get("conceito_final","N/I"),
                        "estrelinhas": st.session_state.get("estrelinhas_final","⭐"),
                    },
                    "metas": metas
                }
                draft_bytes = json.dumps(draft, ensure_ascii=False, indent=2).encode("utf-8")
                st.download_button("⬇️ Exportar rascunho (JSON)", data=draft_bytes,
                                   file_name=f"rascunho_ficha_{_safe_filename(tecnico['name'])}.json",
                                   use_container_width=True)

            if salvar_click:
                if erros:
                    st.error("Não foi possível salvar. Corrija os pontos acima.")
                else:
                    nova_ficha = {
                        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "periodo_referencia": periodo_ref,
                        "avaliador": st.session_state['user_info']['name'],
                        "competencias": {
                            "habilidade_tecnica_atendimento": {"nota": st.session_state["comp_atendimento"], "evidencias": st.session_state["evidencias_dict"]["habilidade_tecnica_atendimento"]},
                            "suporte_nivel_1": {"nota": st.session_state["comp_sup1"], "evidencias": st.session_state["evidencias_dict"]["suporte_nivel_1"]},
                            "suporte_nivel_2": {"nota": st.session_state["comp_sup2"], "evidencias": st.session_state["evidencias_dict"]["suporte_nivel_2"]},
                            "infra_nivel_1": {"nota": st.session_state["comp_infra1"], "evidencias": st.session_state["evidencias_dict"]["infra_nivel_1"]},
                            "habilidade_tecnica_treinamento": {"nota": st.session_state["comp_trein_tecnica"], "evidencias": st.session_state["evidencias_dict"]["habilidade_tecnica_treinamento"]},
                            "capacitacoes_ferramentas": {"nota": st.session_state["comp_capacitacoes"], "evidencias": st.session_state["evidencias_dict"]["capacitacoes_ferramentas"]},
                            "pesos_competencias": st.session_state["pesos_competencias"],
                            "nota_competencias_ponderada": st.session_state["nota_comp_ponderada"]
                        },
                        "desempenho_ferramentas": {
                            "pesos": st.session_state["pesos_ferramentas"],
                            "proficiencias": st.session_state.get("prof_entradas", {}),
                            "indice_ponderado_pct": st.session_state.get("prof_indice_pct", 0.0)
                        },
                        "cultura_valores": aderencia_valores,
                        "metas": metas,
                        "mostrar_metas_para_tecnico": bool(mostrar_metas_para_tecnico),
                        "plano_desenvolvimento": {
                            "cursos": cursos, "pontos_fortes": pontos_fortes, "pontos_melhorar": pontos_melhorar
                        },
                        "visibilidade_plano": {
                            "cursos": bool(show_cursos_to_tech),
                            "pontos_fortes": bool(show_pontos_fortes_to_tech),
                            "pontos_melhorar": bool(show_pontos_melhorar_to_tech)
                        },
                        "feedback_final": feedback_final,
                        "pesos_blocos": st.session_state["pesos_blocos"],
                        "nota_final": st.session_state["nota_final"],
                        "conceito": st.session_state["conceito_final"],
                        "estrelinhas": st.session_state["estrelinhas_final"],
                        "sugerir_pip": bool(pip_check),
                        "sugerir_destaque": bool(destaque_check),
                        "proxima_revisao": proxima_revisao.strftime("%d/%m/%Y") if (definir_prox_rev and proxima_revisao) else None
                    }
                    if kpi:
                        nova_ficha["indicadores_csv"] = {
                            "responsavel_vinculado": kpi.get("responsavel_label",""),
                            "total_atendimentos": int(kpi["qtd"]),
                            "media_espera_segundos": float(kpi["espera_media"]) if kpi["espera_media"] is not None else None,
                            "media_duracao_minutos": float(kpi["duracao_media"]) if kpi["duracao_media"] is not None else None,
                            "media_avaliacao": float(kpi["rating_media"]) if kpi["rating_media"] is not None else None
                        }
                    if tecnico['username'] not in fichas: fichas[tecnico['username']] = []
                    fichas[tecnico['username']].insert(0, nova_ficha)
                    save_fichas(fichas)
                    st.success(f"Ficha de {tecnico['name']} salva com sucesso!")
                    time.sleep(0.3); st.rerun()

    # ====================== PESOS (aba principal) ======================
    with tab_pesos:
        st.markdown("<div class='block-card'>", unsafe_allow_html=True)
        st.markdown("#### 🎛️ Presets de Pesos")
        presets = load_presets()
        preset_names = ["—"] + list(presets.keys())
        cpr1,cpr2,cpr3,cpr4 = st.columns([0.32,0.22,0.22,0.24])
        with cpr1:
            selected_preset = st.selectbox("Carregar preset", preset_names, index=0, key="preset_sel")
        with cpr2:
            if st.button("Aplicar preset", use_container_width=True):
                if selected_preset != "—":
                    data = presets[selected_preset]
                    st.session_state["pesos_ferramentas"] = data.get("pesos_ferramentas", st.session_state["pesos_ferramentas"])
                    st.session_state["pesos_competencias"] = data.get("pesos_competencias", st.session_state["pesos_competencias"])
                    st.session_state["pesos_blocos"] = data.get("pesos_blocos", st.session_state["pesos_blocos"])
                    st.success(f"Preset '{selected_preset}' aplicado.")
                    safe_rerun()
        with cpr3:
            new_name = st.text_input("Salvar como (nome do preset)", key="preset_new_name", placeholder="Ex.: Padrão trimestre")
        with cpr4:
            if st.button("💾 Salvar preset", use_container_width=True):
                if new_name.strip():
                    presets[new_name.strip()] = {
                        "pesos_ferramentas": st.session_state["pesos_ferramentas"],
                        "pesos_competencias": st.session_state["pesos_competencias"],
                        "pesos_blocos": st.session_state["pesos_blocos"]
                    }
                    save_presets(presets)
                    st.success("Preset salvo."); safe_rerun()
                else:
                    st.warning("Informe um nome para o preset.")
        if selected_preset != "—":
            if st.button("🗑️ Excluir preset selecionado"):
                presets.pop(selected_preset, None); save_presets(presets)
                st.success("Preset excluído."); safe_rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='block-card'>", unsafe_allow_html=True)
        st.markdown("#### 🧩 Pesos — Proficiência nas Ferramentas (%)")
        nova_pf = {}
        cfs = st.columns(3)
        for i, nome in enumerate(st.session_state["pesos_ferramentas"].keys()):
            with cfs[i % 3]:
                nova_pf[nome] = st.number_input(
                    nome, min_value=0, max_value=100,
                    value=st.session_state["pesos_ferramentas"][nome],
                    key=f"peso_ferr_{nome}",
                    help="Peso relativo desta ferramenta (%)"
                )
        st.session_state["pesos_ferramentas"] = nova_pf
        ensure_sum_bar(list(nova_pf.values()), "Somatório de Pesos (Ferramentas)")
        donut_weights(nova_pf, "Distribuição de Pesos — Ferramentas")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='block-card'>", unsafe_allow_html=True)
        st.markdown("#### 🎯 Pesos — Competências (valores relativos)")
        n_pc = {}
        cols_pc = st.columns(3)
        for i, nome in enumerate(st.session_state["pesos_competencias"].keys()):
            with cols_pc[i % 3]:
                n_pc[nome] = st.number_input(
                    nome, min_value=0, max_value=100,
                    value=st.session_state["pesos_competencias"][nome],
                    key=f"peso_comp_{nome}",
                    help="Peso relativo desta competência (normalizado automaticamente)"
                )
        st.session_state["pesos_competencias"] = n_pc
        donut_weights(n_pc, "Distribuição de Pesos — Competências (relativos)")
        st.caption("Os pesos de competências são normalizados na hora do cálculo.")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='block-card'>", unsafe_allow_html=True)
        st.markdown("#### ⚖️ Pesos — Blocos (devem somar 100)")
        colb1,colb2 = st.columns(2)
        with colb1:
            w_ferr = st.number_input("Ferramentas (%)", 0, 100, value=st.session_state["pesos_blocos"]["Ferramentas"], key="peso_blocos_ferr")
        with colb2:
            w_comp = st.number_input("Competências (%)", 0, 100, value=st.session_state["pesos_blocos"]["Competências"], key="peso_blocos_comp")
        ensure_sum_bar([w_ferr, w_comp], "Somatório de Pesos (Blocos)")
        if w_ferr + w_comp == 100:
            st.session_state["pesos_blocos"] = {"Ferramentas": int(w_ferr), "Competências": int(w_comp)}
            st.success("Pesos atualizados.")
        else:
            st.error("A soma deve ser 100.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ====================== HISTÓRICO ======================
    with tab_hist:
        st.markdown("### Consultar Histórico de Avaliações")
        users, fichas = load_users(), load_fichas()
        tecnicos = [u for u in users if u['role']=="tecnico"]
        if not tecnicos:
            st.info("Nenhum técnico cadastrado.")
        else:
            st.markdown("<div class='block-card'>", unsafe_allow_html=True)
            tecnico_nome_hist = st.selectbox("Selecione um Técnico", [t['name'] for t in tecnicos], key="select_tecnico_hist")
            st.markdown("</div>", unsafe_allow_html=True)
            tecnico_hist = next((t for t in tecnicos if t['name']==tecnico_nome_hist), None)
            if tecnico_hist:
                arr = fichas.get(tecnico_hist['username'], [])
                if arr:
                    for idx_ficha, ficha in enumerate(arr):
                        with st.expander(f" Avaliação de {ficha.get('data','N/I')} — {ficha.get('avaliador','N/I')}"):
                            raw = json.dumps(ficha, ensure_ascii=False, indent=2).encode("utf-8")
                            st.download_button("⬇️ Baixar ficha (JSON)", data=raw,
                                               file_name=f"ficha_{_safe_filename(tecnico_hist['name'])}_{idx_ficha+1}.json",
                                               key=f"down_json_{idx_ficha}")

                            st.markdown("<div class='block-card'>", unsafe_allow_html=True)
                            nf = ficha.get('nota_final'); conc = ficha.get('conceito',"N/I"); est = ficha.get('estrelinhas',"N/I")
                            st.metric("Avaliação Geral (★)", est)
                            c1,c2 = st.columns(2)
                            c1.metric("Nota Final", f"{nf:.2f}" if isinstance(nf,(int,float)) else "N/I")
                            c2.metric("Conceito", conc)
                            ind = ficha.get("indicadores_csv")
                            if ind:
                                st.markdown("**Indicadores do ciclo**")
                                ci1,ci2,ci3,ci4 = st.columns(4)
                                with ci1: st.metric("Total de Atendimentos", f"{ind.get('total_atendimentos','N/I')}")
                                with ci2:
                                    me = ind.get("media_espera_segundos")
                                    st.metric("Média de Espera", formatar_tempo_minutos((me or 0.0)/60) if me is not None else "N/I")
                                with ci3:
                                    md = ind.get("media_duracao_minutos")
                                    st.metric("Média de Duração", formatar_tempo_minutos(md) if md is not None else "N/I")
                                with ci4:
                                    ma = ind.get("media_avaliacao")
                                    st.metric("Média de Avaliação", f"{ma:.2f}" if isinstance(ma,(int,float)) else "N/I")
                            st.markdown("</div>", unsafe_allow_html=True)

                            ferr = ficha.get("desempenho_ferramentas")
                            if ferr:
                                st.markdown("<div class='block-card'>", unsafe_allow_html=True)
                                st.markdown("**Proficiência nas Ferramentas (ponderado)**")
                                st.metric("Índice (%)", f"{ferr.get('indice_ponderado_pct',0):.1f}%")
                                with st.expander("Detalhe por ferramenta"):
                                    for nome, peso in ferr.get("pesos", {}).items():
                                        val = ferr.get("proficiencias", {}).get(nome, "N/I")
                                        st.write(f"- {nome} ({peso}%): {val}%")
                                st.markdown("</div>", unsafe_allow_html=True)

                            comp = ficha.get("competencias")
                            if comp:
                                st.markdown("<div class='block-card'>", unsafe_allow_html=True)
                                def _safe_note(block, key): return block.get(key,{}).get('nota','—')
                                st.markdown("**Competências (0–10)**")
                                st.write(f"- Habilidade técnica em atendimento: {_safe_note(comp,'habilidade_tecnica_atendimento')}")
                                st.write(f"- Suporte nível 1: {_safe_note(comp,'suporte_nivel_1')}")
                                st.write(f"- Suporte nível 2: {_safe_note(comp,'suporte_nivel_2')}")
                                st.write(f"- Infra nível 1: {_safe_note(comp,'infra_nivel_1')}")
                                st.write(f"- Habilidade técnica para treinamento: {_safe_note(comp,'habilidade_tecnica_treinamento')}")
                                st.write(f"- Consegue realizar capacitações das ferramentas: {_safe_note(comp,'capacitacoes_ferramentas')}")
                                if 'nota_competencias_ponderada' in comp:
                                    st.info(f"**Nota de Competências (ponderada):** {comp['nota_competencias_ponderada']:.2f}")
                                st.markdown("</div>", unsafe_allow_html=True)

                            if ficha.get("metas"):
                                st.markdown("<div class='block-card'>", unsafe_allow_html=True)
                                st.markdown(f"**Metas SMART** — *Visível ao técnico:* {'Sim' if ficha.get('mostrar_metas_para_tecnico') else 'Não'}")
                                for j, m in enumerate(ficha["metas"], start=1):
                                    linha = f"- **{j}. {m['titulo']}** — indicador: {m['indicador']} — responsável: {m.get('responsavel','N/I')} — prazo: {m['prazo']}"
                                    if m.get("is_curso"): linha += " — **[Curso]**"
                                    st.write(linha)
                                    if m.get("is_curso"):
                                        realizado = m.get("realizado", False)
                                        st.write(f"  ↳ Realizado pelo técnico: **{'Sim' if realizado else 'Não'}**")
                                        cert = m.get("certificado_path")
                                        if cert and os.path.exists(cert):
                                            with open(cert,"rb") as fh:
                                                st.download_button("Baixar certificado", data=fh.read(),
                                                                   file_name=os.path.basename(cert),
                                                                   key=f"down_cert_coord_{idx_ficha}_{j}")
                                        else:
                                            st.caption("  ↳ Nenhum certificado anexado.")
                                st.markdown("</div>", unsafe_allow_html=True)

                            pdv = ficha.get("plano_desenvolvimento",{})
                            if any([pdv.get("cursos"), pdv.get("pontos_fortes"), pdv.get("pontos_melhorar")]):
                                st.markdown("<div class='block-card'>", unsafe_allow_html=True)
                                st.markdown("**Plano de Ação e Desenvolvimento (registro)**")
                                if pdv.get("cursos"): st.write(f"- Cursos/Treinamentos: {pdv.get('cursos')}")
                                if pdv.get("pontos_fortes"): st.write(f"- Pontos Fortes: {pdv.get('pontos_fortes')}")
                                if pdv.get("pontos_melhorar"): st.write(f"- Pontos a Melhorar: {pdv.get('pontos_melhorar')}")
                                st.markdown("</div>", unsafe_allow_html=True)

                            st.markdown(f"> *Feedback Final:* {ficha.get('feedback_final','—')}")
                else:
                    st.info("Nenhuma ficha encontrada para este técnico.")

    # ====================== GERENCIAR USUÁRIOS ======================
    with tab_user:
        st.markdown("### Gerenciamento de Usuários Técnicos")
        with st.form("create_technician_form", clear_on_submit=True):
            st.markdown("<div class='block-card'>", unsafe_allow_html=True)
            st.subheader("➕ Adicionar Novo Técnico")
            new_name = st.text_input("Nome Completo")
            new_username = st.text_input("Nome de Usuário (para login)")
            new_password = st.text_input("Senha", type="password")
            cols = st.columns([1,1])
            with cols[0]:
                submit = st.form_submit_button("Criar Técnico")
            with cols[1]:
                st.markdown("<div class='btn-secondary'>", unsafe_allow_html=True)
                st.form_submit_button("Limpar")
                st.markdown("</div>", unsafe_allow_html=True)
            if submit:
                users = load_users()
                if not new_name or not new_username or not new_password:
                    st.warning("Preencha todos os campos.")
                elif any(u['username']==new_username.lower() for u in users):
                    st.error(f"O nome de usuário '{new_username}' já existe.")
                else:
                    new_user = {"username": new_username.lower(), "password": new_password, "role":"tecnico", "name": new_name}
                    users.append(new_user); save_users(users)
                    st.success(f"Técnico '{new_name}' criado!")
                    st.balloons(); time.sleep(0.3); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='block-card'>", unsafe_allow_html=True)
        st.subheader("📋 Técnicos Cadastrados")
        users = load_users()
        tecnicos = [u for u in users if u['role']=="tecnico"]
        if not tecnicos:
            st.info("Nenhum técnico cadastrado.")
        else:
            for t in tecnicos:
                st.write(f"• **{t['name']}** — login: `{t['username']}`")
        st.markdown("</div>", unsafe_allow_html=True)

# ------------------------------ PAINEL TÉCNICO ---------------------------------
def pagina_tecnico():
    criar_botao_voltar()
    st.markdown(f"## 📋 Painel de Desempenho — {st.session_state['user_info']['name']}")
    fichas = load_fichas(); username = st.session_state['user_info']['username']
    if username in fichas and fichas[username]:
        ficha_recente = fichas[username][0]
        st.markdown("<div class='block-card'>", unsafe_allow_html=True)
        st.subheader("⭐ Sua Avaliação Mais Recente")
        st.caption(f"Data: {ficha_recente.get('data','N/I')} • Avaliador: {ficha_recente.get('avaliador','N/I')}")
        nf = ficha_recente.get('nota_final'); conc = ficha_recente.get('conceito','N/I'); est = ficha_recente.get('estrelinhas','N/I')
        c1,c2,c3 = st.columns(3)
        with c1: st.metric("Avaliação Geral (★)", est)
        with c2: st.metric("Nota Final", f"{nf:.2f}" if isinstance(nf,(int,float)) else "N/I")
        with c3: st.metric("Conceito", conc)
        st.markdown("</div>", unsafe_allow_html=True)

        ind = ficha_recente.get("indicadores_csv")
        if ind:
            st.markdown("<div class='block-card'>", unsafe_allow_html=True)
            st.markdown("### 📌 Seus Indicadores deste ciclo")
            ci1,ci2,ci3,ci4 = st.columns(4)
            with ci1: st.metric("Total de Atendimentos", f"{ind.get('total_atendimentos','N/I')}")
            with ci2:
                me = ind.get("media_espera_segundos")
                st.metric("Média de Espera", formatar_tempo_minutos((me or 0.0)/60) if me is not None else "N/I")
            with ci3:
                md = ind.get("media_duracao_minutos")
                st.metric("Média de Duração", formatar_tempo_minutos(md) if md is not None else "N/I")
            with ci4:
                ma = ind.get("media_avaliacao")
                st.metric("Média de Avaliação", f"{ma:.2f}" if isinstance(ma,(int,float)) else "N/I")
            st.markdown("</div>", unsafe_allow_html=True)

        ferr = ficha_recente.get("desempenho_ferramentas")
        if ferr:
            st.markdown("<div class='block-card'>", unsafe_allow_html=True)
            st.markdown("### 🧩 Seu índice de proficiência nas ferramentas")
            st.metric("Índice (%)", f"{ferr.get('indice_ponderado_pct',0):.1f}%")
            st.markdown("</div>", unsafe_allow_html=True)

        if ficha_recente.get("mostrar_metas_para_tecnico") and ficha_recente.get("metas"):
            st.markdown("<div class='block-card'>", unsafe_allow_html=True)
            st.markdown("### 🎯 Suas Metas")
            metas = ficha_recente["metas"]
            for i, m in enumerate(metas):
                with st.expander(f"Meta {i+1}: {m['titulo']}", expanded=False):
                    st.write(f"- **Descrição:** {m.get('descricao','')}")
                    st.write(f"- **Indicador:** {m.get('indicador','')}")
                    st.write(f"- **Responsável:** {m.get('responsavel','N/I')}")
                    st.write(f"- **Prazo:** {m.get('prazo','N/I')}")
                    if m.get("is_curso"):
                        st.info("Esta meta é um **curso/treinamento**.")
                        current_done = bool(m.get("realizado", False))
                        new_done = st.checkbox("Realizei este curso", value=current_done, key=f"tec_meta_{i}_realizado")
                        cert_file = st.file_uploader("Anexar certificado (PDF/Imagem)", type=["pdf","png","jpg","jpeg"], key=f"tec_meta_{i}_upload")
                        cert_path = m.get("certificado_path")
                        if cert_path and os.path.exists(cert_path):
                            with open(cert_path,"rb") as fh:
                                st.download_button("Baixar certificado existente", data=fh.read(),
                                                   file_name=os.path.basename(cert_path),
                                                   key=f"down_cert_{i}")
                        if st.button("Salvar atualização desta meta", key=f"btn_save_meta_{i}"):
                            fichas_local = load_fichas()
                            metas_local = fichas_local.get(username, [])[0].get("metas", [])
                            if i < len(metas_local):
                                metas_local[i]["realizado"] = bool(new_done)
                                if cert_file is not None:
                                    try:
                                        saved = save_certificado(username, i, cert_file)
                                        metas_local[i]["certificado_path"] = saved
                                        st.success("Status atualizado e certificado anexado.")
                                    except Exception as e:
                                        st.error(f"Falha ao salvar certificado: {e}")
                                else:
                                    st.success("Status atualizado.")
                                save_fichas(fichas_local); safe_rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        vis = ficha_recente.get("visibilidade_plano", {})
        pdv = ficha_recente.get("plano_desenvolvimento", {})
        bloco = []
        if vis.get("cursos", False) and pdv.get("cursos"): bloco.append(("📚 Cursos/Treinamentos sugeridos", pdv.get("cursos")))
        if vis.get("pontos_fortes", False) and pdv.get("pontos_fortes"): bloco.append(("💪 Pontos Fortes", pdv.get("pontos_fortes")))
        if vis.get("pontos_melhorar", False) and pdv.get("pontos_melhorar"): bloco.append(("🔧 Pontos a Melhorar", pdv.get("pontos_melhorar")))
        if bloco:
            st.markdown("<div class='block-card'>", unsafe_allow_html=True)
            st.markdown("### 🧭 Plano de Ação e Desenvolvimento")
            for titulo, texto in bloco:
                st.write(f"**{titulo}:** {texto}")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(f"> *Feedback Final:* {ficha_recente.get('feedback_final','—')}")

        if len(fichas[username]) > 1:
            st.markdown("### 📂 Histórico de Avaliações Anteriores")
            for ficha_antiga in fichas[username][1:]:
                with st.expander(f"Avaliação de {ficha_antiga.get('data','N/I')}"):
                    nf_a = ficha_antiga.get('nota_final')
                    st.metric("Nota Final", f"{nf_a:.2f}" if isinstance(nf_a,(int,float)) else "N/I")
                    if ficha_antiga.get("mostrar_metas_para_tecnico") and ficha_antiga.get("metas"):
                        st.markdown("**Metas deste ciclo (somente leitura):**")
                        for j, m in enumerate(ficha_antiga["metas"], start=1):
                            linha = f"- {j}. {m['titulo']} — prazo: {m['prazo']}"
                            if m.get("is_curso"):
                                linha += " — [Curso]"
                                if m.get("realizado"): linha += " — realizado"
                            st.write(linha)
                    vis_old = ficha_antiga.get("visibilidade_plano", {})
                    pdv_old = ficha_antiga.get("plano_desenvolvimento", {})
                    bloco_old = []
                    if vis_old.get("cursos", False) and pdv_old.get("cursos"): bloco_old.append(("📚 Cursos/Treinamentos sugeridos", pdv_old.get("cursos")))
                    if vis_old.get("pontos_fortes", False) and pdv_old.get("pontos_fortes"): bloco_old.append(("💪 Pontos Fortes", pdv_old.get("pontos_fortes")))
                    if vis_old.get("pontos_melhorar", False) and pdv_old.get("pontos_melhorar"): bloco_old.append(("🔧 Pontos a Melhorar", pdv_old.get("pontos_melhorar")))
                    if bloco_old:
                        st.markdown("**Plano (somente leitura):**")
                        for titulo, texto in bloco_old: st.write(f"- **{titulo}:** {texto}")
    else:
        st.info("Nenhuma ficha encontrada.")

# ============================ FLUXO PRINCIPAL ==================================
if not st.session_state.get("logged_in", False):
    top_c1, top_c2 = st.columns([0.7,0.3])
    with top_c2:
        theme_sel = st.selectbox("Tema", ["Escuro (alto contraste)", "Claro (limpo)"], key="theme_choice")
        apply_theme()
    pagina_login()
else:
    top1, top2, top3 = st.columns([0.6, 0.25, 0.15])
    with top1:
        st.markdown(f"### Olá, {st.session_state['user_info']['name']}!")
        st.caption("Bem-vindo(a) ao Sistema Integrado de Avaliação — Novetech.")
    with top2:
        theme_sel = st.selectbox("Tema", ["Escuro (alto contraste)", "Claro (limpo)"], key="theme_choice")
        apply_theme()
    with top3:
        st.markdown("<div class='btn-secondary'>", unsafe_allow_html=True)
        if st.button("Logout"):
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    page = st.session_state.get("page", "menu")
    if page == "menu":
        pagina_menu_principal()
    elif page == "avaliar_tecnicos":
        pagina_coordenador()
    elif page == "minhas_fichas":
        pagina_tecnico()
    elif page == "dashboard":
        pagina_dashboard()
