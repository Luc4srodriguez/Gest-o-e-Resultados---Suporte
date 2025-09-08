# app.py
import streamlit as st
import pandas as pd
import io
import re
import plotly.express as px
import plotly.graph_objects as go
import time
import json
from datetime import datetime, date, time as dtime
import unicodedata
import difflib
import os
import tempfile
from typing import Dict, Tuple, List, Optional

# ============================ CONFIG DA PÁGINA ============================
st.set_page_config(
    page_title="Novetech • Sistema Integrado",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================== ESTADO INICIAL ============================
def ss_setdefault(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

ss_setdefault("page", "login")
ss_setdefault("logged_in", False)
ss_setdefault("kpi_alias_map", {})
ss_setdefault("theme_choice", "Novetech (glass)")

# CSV / dados
ss_setdefault("df_base", None)
ss_setdefault("df_periodo", None)
ss_setdefault("periodo_inicio", None)
ss_setdefault("periodo_fim", None)

# Pesos e defaults
ss_setdefault("pesos_ferramentas", {
    "AtendSaúde": 20,
    "AtendeEndemias": 5,
    "PEC": 20,
    "eSUS Feedback": 15,
    "Infra": 10,
    "Meeds": 10,
    "Sistema Hospital": 5,
    "VISA": 5,
    "AB Território": 10
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

# proficiências default
for k in st.session_state["pesos_ferramentas"].keys():
    ss_setdefault(f"prof_{k}", 70)

# competências default
for comp in [
    "comp_atendimento","comp_sup1","comp_sup2",
    "comp_infra1","comp_trein_tecnica","comp_capacitacoes"
]:
    ss_setdefault(comp, 8 if comp not in ("comp_sup2","comp_infra1") else 7)

# campos gerais de avaliação
ss_setdefault("periodo_ref", datetime.now().strftime("%B/%Y"))
ss_setdefault("aderencia_valores", "Alta")
ss_setdefault("definir_prox_rev", False)
ss_setdefault("proxima_revisao", date.today())
ss_setdefault("cursos", "")
ss_setdefault("pontos_fortes", "")
ss_setdefault("pontos_melhorar", "")
ss_setdefault("feedback_final", "")
ss_setdefault("pip_check", False)
ss_setdefault("destaque_check", False)

# visibilidade para o técnico
ss_setdefault("mostrar_metas_para_tecnico", True)
ss_setdefault("show_cursos_to_tech", True)
ss_setdefault("show_pontos_fortes_to_tech", True)
ss_setdefault("show_pontos_melhorar_to_tech", True)

# metas (até 3)
for i in range(1,4):
    ss_setdefault(f"meta_titulo_{i}", "")
    ss_setdefault(f"meta_desc_{i}", "")
    ss_setdefault(f"meta_ind_{i}", "")
    ss_setdefault(f"meta_resp_{i}", "")
    ss_setdefault(f"meta_prazo_{i}", date.today())
    ss_setdefault(f"meta_is_curso_{i}", False)
    ss_setdefault(f"meta_show_to_tech_{i}", True)

# =============================== TEMA / ESTILO ===============================
def apply_novetech_theme():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    :root{
      --primary-gradient: linear-gradient(135deg,#06b6d4 0%,#3b82f6 100%);
      --bg-gradient: radial-gradient(1200px 600px at 50% -20%, #1f3a8a55 0%, transparent 70%),
                     linear-gradient(135deg,#0f172a 0%,#1e3a8a 45%,#0f172a 100%);
      --card-bg: rgba(255,255,255,0.10);
      --card-border: rgba(255,255,255,0.20);
      --text-primary: #ffffff;
      --text-secondary:#cbd5e1;
      --text-muted:#94a3b8;
      --input-bg: rgba(255,255,255,0.12);
      --input-border: rgba(255,255,255,0.28);
    }
    html, body, .stApp{ background: var(--bg-gradient) !important; color: var(--text-primary) !important;
      font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Arial !important;}
    #MainMenu, footer, .stDeployButton{visibility:hidden;} .stAppHeader{display:none;}
    .main .block-container{max-width:1200px !important; padding:2rem 1rem !important;}
    .block-card{
      background: var(--card-bg) !important; border: 1px solid var(--card-border) !important;
      border-radius: 20px !important; padding: 1.6rem !important; margin-bottom: 1rem !important;
      backdrop-filter: blur(14px) !important; -webkit-backdrop-filter: blur(14px) !important;
      box-shadow: 0 25px 50px -16px rgba(0,0,0,.35) !important;
    }
    .login-card{ composes: block-card; max-width:460px !important; margin: 2rem auto !important; text-align:center; }
    .novetech-logo{ display:inline-flex; align-items:center; justify-content:center; width:64px; height:64px; border-radius:16px;
      background: var(--primary-gradient); color:#fff; font-weight:700; font-size:1.25rem; margin-bottom:1rem; }
    .novetech-title{ font-size:2.4rem; font-weight:800; background: var(--primary-gradient);
      -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin:.25rem 0 .5rem 0; }
    .novetech-subtitle{ color:var(--text-secondary); }

    .stTextInput input, .stPasswordInput input, .stTextArea textarea, .stDateInput input{
      background: var(--input-bg) !important; border: 1px solid var(--input-border) !important; border-radius: 12px !important; color: var(--text-primary) !important;
      padding: .75rem 1rem !important;
    }
    .stSelectbox [data-baseweb="select"] > div{ background: var(--input-bg) !important; border: 1px solid var(--input-border) !important; border-radius: 12px !important; min-height: 44px !important;}
    .stSelectbox [data-baseweb="select"] *{ color: var(--text-primary) !important; }
    [data-baseweb="menu"]{ background: var(--card-bg) !important; border: 1px solid var(--card-border) !important; }

    .stButton > button{
      background: var(--primary-gradient) !important; color:#fff !important; border-radius: 12px !important; border: none !important;
      padding: .65rem 1.2rem !important; font-weight:700 !important; box-shadow: 0 8px 20px rgba(6,182,212,.35) !important;
    }
    [data-testid="metric-container"]{ background: var(--card-bg) !important; border:1px solid var(--card-border) !important; border-radius:16px !important; padding:1rem !important; }
    .stTabs [data-baseweb="tab-list"]{ background: var(--card-bg) !important; border:1px solid var(--card-border) !important; border-radius:12px !important; padding:.35rem !important;}
    .stTabs [aria-selected="true"]{ background: var(--primary-gradient) !important; color:#fff !important; }
    </style>
    """, unsafe_allow_html=True)

apply_novetech_theme()

# ================================ HELPERS =================================
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
        with open('users.json','r',encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        default_users = [
            {"username": "admin", "password": "admin123", "role": "coordenador", "name": "Administrador"},
            {"username": "tecnico1", "password": "tecnico123", "role": "tecnico", "name": "João Silva"},
            {"username": "demo", "password": "demo", "role": "coordenador", "name": "Usuário Demo"}
        ]
        save_users(default_users)
        return default_users
    except json.JSONDecodeError:
        st.error("Falha ao ler 'users.json'.")
        return []

def save_users(data): _atomic_write('users.json', data)

def load_fichas():
    try:
        with open('fichas.json','r',encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_fichas(data): _atomic_write('fichas.json', data)

# ---------- CSV robusto e preparação ----------
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
            df = pd.read_csv(
                buf, sep=opts["sep"], engine=opts["engine"],
                encoding=opts["encoding"], on_bad_lines="skip"
            )
            df.attrs["_read_opts_"] = opts
            return df
        except Exception as e:
            last_exc = e
            continue
    raise last_exc if last_exc else ValueError("Falha ao ler CSV.")

def converter_para_segundos(valor):
    try:
        if pd.isna(valor) or not isinstance(valor, str) or ":" not in valor: return None
        h, m, s = map(int, valor.strip().split(":"))
        return h * 3600 + m * 60 + s
    except: return None

def converter_para_minutos(valor):
    try:
        if pd.isna(valor) or not isinstance(valor, str) or ":" not in valor: return None
        h, m, s = map(int, valor.strip().split(":"))
        return h * 60 + m + s / 60
    except: return None

def formatar_tempo_minutos(minutos_total):
    if minutos_total is None or pd.isna(minutos_total): return "00:00"
    minutos = int(minutos_total)
    seg = int(round((minutos_total - minutos) * 60))
    return f"{minutos:02}:{seg:02}"

def linha_valida_em_colunas(row, colunas):
    for c in colunas:
        cell = row.get(c, None)
        if isinstance(cell, str):
            if re.search(r'\w', cell): return True
        elif pd.notna(cell): return True
    return False

def definir_turno(data_hora_str):
    try:
        if pd.isna(data_hora_str): return "Outro"
        dt = pd.to_datetime(data_hora_str)
        hora = dt.hour
        if 7 <= hora <= 12: return "Manhã"
        elif 13 <= hora <= 17: return "Tarde"
        else: return "Outro"
    except: return "Outro"

def preprocess_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()
    df = df.dropna(how="all")
    colunas_necessarias = [
        "name", "group_attendants_name", "client_name",
        "services_catalog_name", "services_catalog_area_name",
        "services_catalog_item_name", "ticket_title", "duration",
        "waiting_time", "responsible", "rating", "created_at"
    ]
    df = df[df.apply(lambda row: linha_valida_em_colunas(row, colunas_necessarias), axis=1)]
    df = df[[c for c in colunas_necessarias if c in df.columns]]

    df["tempo_espera_segundos"] = df["waiting_time"].apply(converter_para_segundos)
    df["duracao_minutos"] = df["duration"].apply(converter_para_minutos)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df["turno"] = df["created_at"].apply(definir_turno)
    return df

def filtrar_periodo(df: pd.DataFrame, inicio: Optional[date], fim: Optional[date]) -> pd.DataFrame:
    if df is None or "created_at" not in df.columns:
        return pd.DataFrame()
    if not inicio and not fim:
        return df.copy()
    mask = pd.Series([True]*len(df))
    if inicio:
        mask &= (df["created_at"].dt.date >= inicio)
    if fim:
        mask &= (df["created_at"].dt.date <= fim)
    return df[mask].copy()

def kpis_periodo(df: pd.DataFrame) -> Dict[str, Optional[float]]:
    if df is None or df.empty:
        return {"qtd":0, "espera_media":None, "duracao_media":None, "rating_media":None}
    return {
        "qtd": int(len(df)),
        "espera_media": float(df["tempo_espera_segundos"].dropna().mean()) if "tempo_espera_segundos" in df else None,
        "duracao_media": float(df["duracao_minutos"].dropna().mean()) if "duracao_minutos" in df else None,
        "rating_media": float(df["rating"].dropna().mean()) if "rating" in df else None
    }

# Normalização e matching
def _norm(txt: str) -> str:
    if txt is None: return ""
    txt = str(txt).strip().lower()
    txt = unicodedata.normalize('NFKD', txt)
    txt = ''.join(c for c in txt if not unicodedata.combining(c))
    txt = re.sub(r'[^a-z0-9@._\s-]', '', txt)
    txt = re.sub(r'\s+', ' ', txt)
    return txt.strip()

def _kpi_lookup_for_tech(tecnico: dict, df_resp: pd.DataFrame) -> Tuple[Optional[str], Optional[pd.DataFrame]]:
    if tecnico is None or df_resp is None or df_resp.empty:
        return None, None
    alias_map = st.session_state.get("kpi_alias_map", {})
    manual_key = alias_map.get(tecnico.get("username","").lower())
    labels = sorted([str(x).strip() for x in df_resp["responsible"].dropna().unique()])
    norm_map = {_norm(lbl): lbl for lbl in labels}

    if manual_key and manual_key in norm_map:
        lbl = norm_map[manual_key]
        return lbl, df_resp[df_resp["responsible"] == lbl].copy()

    candidatos = {_norm(tecnico.get("name","")), _norm(tecnico.get("username",""))}
    user = tecnico.get("username","")
    if "@" in user: candidatos.add(_norm(user.split("@")[0]))

    for c in list(candidatos):
        if c in norm_map:
            lbl = norm_map[c]
            return lbl, df_resp[df_resp["responsible"] == lbl].copy()

    keys = list(norm_map.keys())
    for c in list(candidatos):
        m = difflib.get_close_matches(c, keys, n=1, cutoff=0.82)
        if m:
            lbl = norm_map[m[0]]
            return lbl, df_resp[df_resp["responsible"] == lbl].copy()
    return None, None

# Heurística: meta parece curso?
def _looks_like_course(meta: dict) -> bool:
    text = f"{meta.get('titulo','')} {meta.get('descricao','')}".lower()
    tokens = ["curso", "treinamento", "capacitação", "certificado"]
    return any(t in text for t in tokens)

# ================================ PÁGINAS =================================
def pagina_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-card block-card">', unsafe_allow_html=True)
        st.markdown('<div class="novetech-logo">🚀</div>', unsafe_allow_html=True)
        st.markdown('<h1 class="novetech-title">Novetech</h1>', unsafe_allow_html=True)
        st.markdown('<p class="novetech-subtitle">Sistema Integrado</p>', unsafe_allow_html=True)

        st.markdown("### Acesse sua conta")
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Usuário", key="login_user").lower()
            password = st.text_input("Senha", type="password", key="login_pass")
            c1, c2 = st.columns(2)
            with c1: entrar = st.form_submit_button("Entrar", use_container_width=True)
            with c2: limpar = st.form_submit_button("Limpar", use_container_width=True)

        if limpar:
            st.session_state["login_user"] = ""
            st.session_state["login_pass"] = ""
            st.rerun()

        if entrar:
            if not username or not password:
                st.error("Preencha todos os campos.")
            else:
                with st.spinner("Verificando..."):
                    time.sleep(0.6)
                    users = load_users()
                    user_found = next((u for u in users if u['username']==username and u['password']==password), None)
                if user_found:
                    st.session_state["logged_in"] = True
                    st.session_state["user_info"] = user_found
                    st.session_state["page"] = "menu"
                    st.success(f"Bem-vindo(a), {user_found['name']}!")
                    time.sleep(0.5); st.rerun()
                else:
                    st.error("Usuário ou senha inválidos.")
        st.markdown('</div>', unsafe_allow_html=True)

def pagina_menu_principal():
    st.markdown('<div class="block-card">', unsafe_allow_html=True)
    c1, c2 = st.columns([3,1])
    with c1:
        st.markdown("## 🏠 Menu Principal")
        st.markdown(f"**Olá, {st.session_state['user_info']['name']}!**  \nPerfil: `{st.session_state['user_info']['role']}`")
    with c2:
        if st.button("🚪 Sair", use_container_width=True):
            for key in ["logged_in", "user_info", "page"]:
                if key in st.session_state: del st.session_state[key]
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="block-card">', unsafe_allow_html=True)
    role = st.session_state['user_info']['role']
    if role == "coordenador":
        menu = {
            "avaliar_tecnicos": ("📝", "Avaliar Técnicos"),
            "dashboard": ("📊", "Análise de Dados"),
            "minhas_fichas": ("📋", "Minhas Fichas (visão técnico)")
        }
    else:
        menu = {
            "minhas_fichas": ("📋", "Minhas Fichas"),
            "dashboard": ("📊", "Análise de Dados")
        }
    cols = st.columns(min(3, len(menu)))
    for i,(key,(icon,label)) in enumerate(menu.items()):
        with cols[i % len(cols)]:
            st.markdown(f"""
            <div style="text-align:center;padding:1rem;border:1px solid var(--card-border);
                 border-radius:12px;background: var(--input-bg);margin-bottom:1rem;">
                <div style="font-size:2rem;margin-bottom:.5rem;">{icon}</div>
                <div style="font-weight:600;">{label}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Abrir", key=f"open_{key}", use_container_width=True):
                st.session_state.page = key
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def criar_botao_voltar():
    st.markdown('<div class="block-card">', unsafe_allow_html=True)
    st.markdown("### 🧭 Navegação")
    if st.button("⬅ Voltar ao Menu Principal", use_container_width=True):
        st.session_state.page = "menu"; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------ DASHBOARD ------------------
def pagina_dashboard():
    criar_botao_voltar()
    st.markdown('<div class="block-card">', unsafe_allow_html=True)
    st.markdown("## 📊 Dashboard de Análise de Acionamentos")

    uploaded = st.file_uploader("📎 Envie sua planilha CSV", type=["csv"])
    if uploaded:
        try:
            content = uploaded.read()
            df = ler_csv_robusto(content)
            df = preprocess_df(df)
            st.session_state["df_base"] = df
            min_dt = pd.to_datetime(df["created_at"]).dt.date.min()
            max_dt = pd.to_datetime(df["created_at"]).dt.date.max()
            st.session_state["periodo_inicio"] = min_dt
            st.session_state["periodo_fim"] = max_dt
            st.success("Arquivo carregado com sucesso.")
        except Exception as e:
            st.error(f"Erro ao processar CSV: {e}")

    df = st.session_state.get("df_base")
    if df is None:
        st.info("Envie um CSV para liberar as análises.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    ini_default = st.session_state.get("periodo_inicio") or df["created_at"].dt.date.min()
    fim_default = st.session_state.get("periodo_fim") or df["created_at"].dt.date.max()
    c1, c2, c3 = st.columns([1,1,1])
    with c1: ini = st.date_input("Data inicial", value=ini_default)
    with c2: fim = st.date_input("Data final", value=fim_default)
    with c3:
        st.caption("Aplicar período em todo o sistema")
        if st.button("Aplicar período", use_container_width=True):
            st.session_state["periodo_inicio"] = ini
            st.session_state["periodo_fim"] = fim
            st.session_state["df_periodo"] = filtrar_periodo(df, ini, fim)
            st.success(f"Período aplicado: {ini} → {fim}")
            st.rerun()

    dff = st.session_state.get("df_periodo")
    if dff is None:
        dff = filtrar_periodo(df, st.session_state.get("periodo_inicio"), st.session_state.get("periodo_fim"))
    st.session_state["df_periodo"] = dff

    st.markdown("---")
    st.markdown("### 📌 Resumo Geral de Performance")
    META_AVALIACAO, META_DURACAO_MINUTOS, META_ESPERA_SEGUNDOS = 4.8, 28.0, 20.0
    media_rating = dff["rating"].dropna().mean() if "rating" in dff else None
    media_duracao = dff["duracao_minutos"].dropna().mean() if "duracao_minutos" in dff else None
    media_espera = dff["tempo_espera_segundos"].dropna().mean() if "tempo_espera_segundos" in dff else None

    c1, c2, c3 = st.columns(3)
    with c1:
        delta = (media_rating - META_AVALIACAO) if pd.notna(media_rating) else None
        st.metric(f"⭐ Avaliação Média (Meta: {META_AVALIACAO})",
                  f"{media_rating:.2f}" if pd.notna(media_rating) else "N/A",
                  f"{delta:+.2f}" if delta is not None else None)
    with c2:
        delta = (media_duracao - META_DURACAO_MINUTOS) if pd.notna(media_duracao) else None
        st.metric(f"🕒 Duração Média (Meta: {int(META_DURACAO_MINUTOS)} min)",
                  formatar_tempo_minutos(media_duracao) if pd.notna(media_duracao) else "N/A",
                  f"{delta:+.1f} min" if delta is not None else None)
    with c3:
        delta = (media_espera - META_ESPERA_SEGUNDOS) if pd.notna(media_espera) else None
        st.metric(f"⏳ Espera Média (Meta: {int(META_ESPERA_SEGUNDOS)} s)",
                  formatar_tempo_minutos((media_espera or 0)/60) if pd.notna(media_espera) else "N/A",
                  f"{delta:+.1f} s" if delta is not None else None)

    st.markdown("#### 🔍 Análises Detalhadas")
    tab1, tab2, tab3 = st.tabs(["🏢 Visão Geral", "📦 Por Serviço", "🙋 Por Responsável"])
    with tab1:
        if "turno" in dff.columns:
            _mostrar_tabela_grafico(dff, "turno", "Distribuição por Turno", "⏰", "#63D471")
        st.markdown("---")
        _mostrar_tabela_grafico(dff, "client_name", "Clientes que Mais Acionaram", "👤", "#63D471")
    with tab2:
        _mostrar_tabela_grafico(dff, "services_catalog_name", "Catálogos de Serviços Mais Usados", "📦", "#FFD166")
        st.markdown("---")
        _mostrar_tabela_grafico(dff, "services_catalog_item_name", "Itens do Catálogo Mais Solicitados", "🔧", "#EF476F")
        st.markdown("---")
        _mostrar_tabela_grafico(dff, "ticket_title", "Títulos de Tickets Mais Frequentes", "📌", "#06D6A0")
    with tab3:
        _mostrar_tabela_grafico(dff, "responsible", "Responsáveis com Mais Atendimentos", "🙋", "#118AB2", mostrar_todos=True)

    st.markdown('</div>', unsafe_allow_html=True)

def _mostrar_tabela_grafico(df, col_name, title, emoji, cor, mostrar_todos=False):
    if col_name not in df.columns:
        return
    st.subheader(f"{emoji} {title}")
    top_vals = df[col_name].value_counts()
    total_validos = df[col_name].dropna().shape[0]
    if not mostrar_todos:
        top_vals = top_vals.head(5)
    top_vals_df = top_vals.reset_index()
    top_vals_df.columns = [col_name, "count"]
    top_vals_df['Percentual'] = (top_vals_df['count'] / total_validos * 100) if total_validos else 0
    col1, col2 = st.columns([0.4, 0.6])
    with col1:
        st.markdown(f"*Total de linhas válidas:* {total_validos}")
        st.dataframe(
            top_vals_df.set_index(col_name),
            column_config={
                "count": st.column_config.NumberColumn("Contagem"),
                "Percentual": st.column_config.ProgressColumn("Percentual", format="%.2f%%", min_value=0, max_value=100)
            },
            use_container_width=True
        )
    with col2:
        fig = px.bar(
            top_vals_df, x=col_name, y="count",
            labels={col_name: "", "count": "Quantidade"},
            text="count", title="", custom_data=["Percentual"]
        )
        fig.update_traces(
            textposition='outside',
            marker_color=cor,
            hovertemplate='<b>%{x}</b><br>Contagem: %{y}<br>Percentual: %{customdata[0]:.2f}%<extra></extra>'
        )
        fig.update_layout(
            xaxis_tickangle=-45, yaxis=dict(tickformat="d"),
            margin=dict(t=20, l=20, r=20, b=20),
            height=380, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

# ------------------ COORDENADOR ------------------
def pagina_avaliar_tecnicos():
    criar_botao_voltar()
    st.markdown('<div class="block-card">', unsafe_allow_html=True)
    st.markdown("## 📝 Painel do Coordenador")

    tabs = st.tabs(["📝 Avaliar Técnicos", "📂 Histórico de Fichas", "👥 Gerenciar Usuários", "⚖ Pesos"])

    # ===== Avaliar =====
    with tabs[0]:
        users = load_users()
        tecnicos = [u for u in users if u['role'] == 'tecnico']
        if not tecnicos:
            st.warning("Nenhum técnico cadastrado.")
            st.markdown('</div>', unsafe_allow_html=True)
            return

        df_base = st.session_state.get("df_base")

        st.markdown("### 🗓️ Período da avaliação")
        ini_default = st.session_state.get("periodo_inicio")
        fim_default = st.session_state.get("periodo_fim")
        if df_base is not None:
            ini_default = ini_default or df_base["created_at"].dt.date.min()
            fim_default = fim_default or df_base["created_at"].dt.date.max()
        c1, c2, c3 = st.columns([1,1,1])
        with c1: ini = st.date_input("Data inicial", value=ini_default)
        with c2: fim = st.date_input("Data final", value=fim_default)
        with c3:
            st.caption("Aplicar período nesta página")
            if st.button("Aplicar período", use_container_width=True, key="aplicar_periodo_avaliar"):
                st.session_state["periodo_inicio"] = ini
                st.session_state["periodo_fim"] = fim
                if df_base is not None:
                    st.session_state["df_periodo"] = filtrar_periodo(df_base, ini, fim)
                    st.success(f"Período aplicado: {ini} → {fim}")
                    st.rerun()

        dff = st.session_state.get("df_periodo")
        if dff is None or dff.empty:
            st.info("Carregue um CSV e aplique o período no Dashboard.")
        else:
            st.markdown("### 👤 Selecione um Técnico")
            tec_nome = st.selectbox("Técnico", [t['name'] for t in tecnicos], index=0)
            tecnico = next((t for t in tecnicos if t['name']==tec_nome), None)

            lbl, df_tec = _kpi_lookup_for_tech(tecnico, dff)
            labels_resp = sorted(dff["responsible"].dropna().astype(str).unique()) if "responsible" in dff else []

            if df_tec is None or df_tec.empty:
                st.info("Vincule manualmente o responsável do CSV ao técnico escolhido.")
                escolha = st.selectbox("Vincular ao responsável do CSV:", options=["-- selecione --"]+labels_resp, index=0, key="vinc_manual")
                if escolha and escolha != "-- selecione --":
                    st.session_state["kpi_alias_map"][tecnico.get("username","").lower()] = _norm(escolha)
                    lbl = escolha
                    df_tec = dff[dff["responsible"] == escolha].copy()
                    st.success(f"Vinculado a: **{escolha}**")
            else:
                st.success(f"Indicadores (período filtrado) encontrados para **{lbl}**.")

            st.markdown("### 📍 Indicadores do Técnico — Período aplicado")
            k = kpis_periodo(df_tec)
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("Total de Atendimentos", f"{k['qtd']}")
            with c2: st.metric("Média de Espera", formatar_tempo_minutos((k['espera_media'] or 0)/60) if k['espera_media'] is not None else "N/A")
            with c3: st.metric("Média de Duração", formatar_tempo_minutos(k['duracao_media']) if k['duracao_media'] is not None else "N/A")
            with c4: st.metric("Média de Avaliação", f"{k['rating_media']:.2f}" if k['rating_media'] is not None else "N/A")

            subt1, subt2, subt3, subt4 = st.tabs(["🧪 Proficiência (Ferramentas)", "🧠 Competências (0–10)", "📈 Resultado Consolidado", "🎯 Metas & Plano"])

            with subt1:
                st.caption("Arraste os sliders (0–100%).")
                total_pond = 0.0
                cols = st.columns(3)
                for i,(nome,peso) in enumerate(st.session_state["pesos_ferramentas"].items()):
                    with cols[i % 3]:
                        st.session_state[f"prof_{nome}"] = st.slider(f"{nome} ({peso}%)", 0, 100, st.session_state[f"prof_{nome}"])
                        total_pond += st.session_state[f"prof_{nome}"] * (peso/100.0)
                st.metric("Índice de Proficiência nas Ferramentas (%)", f"{total_pond:.1f}%")
                prof_pct = total_pond

            with subt2:
                c1,c2 = st.columns(2)
                with c1:
                    st.session_state["comp_atendimento"] = st.slider("Habilidade técnica em atendimento", 0, 10, st.session_state["comp_atendimento"])
                    st.session_state["comp_sup1"] = st.slider("Suporte nível 1", 0, 10, st.session_state["comp_sup1"])
                    st.session_state["comp_sup2"] = st.slider("Suporte nível 2", 0, 10, st.session_state["comp_sup2"])
                with c2:
                    st.session_state["comp_infra1"] = st.slider("Infra nível 1", 0, 10, st.session_state["comp_infra1"])
                    st.session_state["comp_trein_tecnica"] = st.slider("Habilidade técnica para treinamento", 0, 10, st.session_state["comp_trein_tecnica"])
                    st.session_state["comp_capacitacoes"] = st.slider("Consegue realizar capacitações das ferramentas", 0, 10, st.session_state["comp_capacitacoes"])

                notas = {
                    "Habilidade técnica em atendimento": st.session_state["comp_atendimento"],
                    "Suporte nível 1": st.session_state["comp_sup1"],
                    "Suporte nível 2": st.session_state["comp_sup2"],
                    "Infra nível 1": st.session_state["comp_infra1"],
                    "Habilidade técnica para treinamento": st.session_state["comp_trein_tecnica"],
                    "Consegue realizar capacitações das ferramentas": st.session_state["comp_capacitacoes"],
                }
                soma_pesos = sum(st.session_state["pesos_competencias"].values()) or 1
                comp_pond_0_10 = sum(notas[n]*st.session_state["pesos_competencias"][n] for n in notas)/soma_pesos
                st.metric("Nota de Competências (ponderada, 0–10)", f"{comp_pond_0_10:.2f}")
                comp_pct = comp_pond_0_10*10.0

            with subt3:
                pb = st.session_state["pesos_blocos"]
                w_f, w_c = pb.get("Ferramentas",50), pb.get("Competências",50)
                final_pct = (prof_pct * (w_f/100.0)) + (comp_pct * (w_c/100.0))
                final_0_10 = final_pct/10.0
                conceito, estrelas = _conceito_por_nota(final_0_10), _estrela_por_nota(final_0_10)
                c1,c2,c3 = st.columns(3)
                with c1: st.metric("Resultado Consolidado (%)", f"{final_pct:.1f}%")
                with c2: st.metric("Nota Final (0–10)", f"{final_0_10:.2f}")
                with c3: st.metric("Conceito / ★", f"{conceito}  /  {estrelas}")

            with subt4:
                with st.form(key="ficha_form", clear_on_submit=False):
                    colA, colB = st.columns(2)
                    with colA:
                        st.session_state["periodo_ref"] = st.text_input("Período de referência", value=st.session_state["periodo_ref"])
                        st.session_state["aderencia_valores"] = st.selectbox(
                            "Aderência a Cultura e Valores",
                            ["Baixa","Média","Alta","Excelente"],
                            index=["Baixa","Média","Alta","Excelente"].index(st.session_state["aderencia_valores"])
                        )
                    with colB:
                        val = ui_toggle("Definir próxima revisão?", key="definir_prox_rev", value=st.session_state["definir_prox_rev"])
                        if val:
                            prox = st.session_state.get("proxima_revisao") or date.today()
                            st.session_state["proxima_revisao"] = st.date_input("Próxima revisão (sugestão)", value=prox, format="DD/MM/YYYY")

                    st.markdown("---")
                    st.markdown("#### 🧭 Metas SMART (próximo ciclo)")
                    metas = []
                    for i in range(1,4):
                        with st.expander(f"Meta {i}", expanded=(i==1)):
                            st.session_state[f"meta_titulo_{i}"] = st.text_input(f"Título da Meta {i}", value=st.session_state[f"meta_titulo_{i}"])
                            st.session_state[f"meta_desc_{i}"] = st.text_area(f"Descrição (SMART) {i}", value=st.session_state[f"meta_desc_{i}"])
                            st.session_state[f"meta_ind_{i}"] = st.text_input(f"Indicador/Como medir {i}", value=st.session_state[f"meta_ind_{i}"])
                            st.session_state[f"meta_resp_{i}"] = st.text_input(f"Responsável primário {i}", value=(st.session_state[f"meta_resp_{i}"] or tecnico['name']))
                            st.session_state[f"meta_prazo_{i}"] = st.date_input(f"Prazo {i}", value=st.session_state[f"meta_prazo_{i}"], format="DD/MM/YYYY")
                            ui_toggle("É um curso?", key=f"meta_is_curso_{i}", value=st.session_state[f"meta_is_curso_{i}"])
                            ui_toggle("Mostrar esta meta ao técnico?", key=f"meta_show_to_tech_{i}", value=st.session_state[f"meta_show_to_tech_{i}"])

                            if st.session_state[f"meta_titulo_{i}"] and st.session_state[f"meta_desc_{i}"] and st.session_state[f"meta_ind_{i}"]:
                                metas.append({
                                    "titulo": st.session_state[f"meta_titulo_{i}"].strip(),
                                    "descricao": st.session_state[f"meta_desc_{i}"].strip(),
                                    "indicador": st.session_state[f"meta_ind_{i}"].strip(),
                                    "responsavel": st.session_state[f"meta_resp_{i}"].strip(),
                                    "prazo": st.session_state[f"meta_prazo_{i}"].strftime("%d/%m/%Y"),
                                    "is_curso": bool(st.session_state[f"meta_is_curso_{i}"]),
                                    "show_to_tech": bool(st.session_state[f"meta_show_to_tech_{i}"]),
                                    "curso_realizado": False,
                                    "curso_certificado": None
                                })

                    st.markdown("#### 🧭 Plano de Ação e Desenvolvimento")
                    colx, coly = st.columns(2)
                    with colx:
                        st.session_state["cursos"] = st.text_area("Cursos/Treinamentos sugeridos", value=st.session_state["cursos"])
                        st.session_state["pontos_fortes"] = st.text_area("Pontos Fortes (síntese)", value=st.session_state["pontos_fortes"])
                        st.session_state["pontos_melhorar"] = st.text_area("Pontos a Melhorar (síntese)", value=st.session_state["pontos_melhorar"])
                    with coly:
                        ui_toggle("Mostrar 'Cursos/Treinamentos' ao técnico?", key="show_cursos_to_tech", value=st.session_state["show_cursos_to_tech"])
                        ui_toggle("Mostrar 'Pontos Fortes' ao técnico?", key="show_pontos_fortes_to_tech", value=st.session_state["show_pontos_fortes_to_tech"])
                        ui_toggle("Mostrar 'Pontos a Melhorar' ao técnico?", key="show_pontos_melhorar_to_tech", value=st.session_state["show_pontos_melhorar_to_tech"])

                    st.session_state["feedback_final"] = st.text_area("Feedback Final do Coordenador", value=st.session_state["feedback_final"])
                    ui_toggle("Sugerir PIP (Plano Individual de Melhoria)", key="pip_check", value=st.session_state["pip_check"])
                    ui_toggle("Indicar para Reconhecimento/Destaque", key="destaque_check", value=st.session_state["destaque_check"])
                    ui_toggle("Exibir metas ao técnico na ficha?", key="mostrar_metas_para_tecnico", value=st.session_state["mostrar_metas_para_tecnico"])

                    st.markdown("---")
                    st.subheader("✅ Pré-visualização")
                    pb = st.session_state["pesos_blocos"]
                    w_f, w_c = pb.get("Ferramentas",50), pb.get("Competências",50)
                    final_pct = (prof_pct * (w_f/100.0)) + (comp_pct * (w_c/100.0))
                    final_0_10 = final_pct/10.0
                    conceito, estrelas = _conceito_por_nota(final_0_10), _estrela_por_nota(final_0_10)
                    c1,c2,c3 = st.columns(3)
                    with c1: st.metric("Nota Final (0–10)", f"{final_0_10:.2f}")
                    with c2: st.metric("Conceito", conceito)
                    with c3: st.metric("Avaliação Geral (★)", estrelas)
                    st.caption(f"*Proficiência:* {prof_pct:.1f}%  •  *Competências:* {comp_pond_0_10:.2f}/10")

                    erros = []
                    if not metas: erros.append("Defina pelo menos 1 meta SMART.")
                    if not st.session_state["feedback_final"].strip(): erros.append("Preencha o Feedback Final do Coordenador.")
                    if erros:
                        st.warning("⚠ Ajustes necessários:\n\n- " + "\n- ".join(erros))

                    salvar = st.form_submit_button("✔ Salvar Avaliação")
                    if salvar:
                        if erros:
                            st.error("Não foi possível salvar. Corrija os pontos acima.")
                            st.stop()
                        fichas = load_fichas()
                        nova_ficha = {
                            "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "periodo_referencia": st.session_state["periodo_ref"],
                            "avaliador": st.session_state['user_info']['name'],
                            "periodo_aplicado": {
                                "inicio": st.session_state["periodo_inicio"].strftime("%d/%m/%Y") if st.session_state["periodo_inicio"] else None,
                                "fim": st.session_state["periodo_fim"].strftime("%d/%m/%Y") if st.session_state["periodo_fim"] else None,
                                "indicadores": k
                            },
                            "competencias": {
                                "habilidade_tecnica_atendimento": {"nota": st.session_state["comp_atendimento"]},
                                "suporte_nivel_1": {"nota": st.session_state["comp_sup1"]},
                                "suporte_nivel_2": {"nota": st.session_state["comp_sup2"]},
                                "infra_nivel_1": {"nota": st.session_state["comp_infra1"]},
                                "habilidade_tecnica_treinamento": {"nota": st.session_state["comp_trein_tecnica"]},
                                "capacitacoes_ferramentas": {"nota": st.session_state["comp_capacitacoes"]},
                                "nota_final": round(final_0_10,2),
                                "conceito": conceito,
                                "estrelinhas": estrelas,
                                "nota_competencias_pond": round(comp_pond_0_10,2)
                            },
                            "desempenho_ferramentas": {
                                "pesos": st.session_state["pesos_ferramentas"],
                                "proficiencias": {fk: st.session_state[f"prof_{fk}"] for fk in st.session_state["pesos_ferramentas"].keys()},
                                "indice_ponderado_pct": round(prof_pct,1)
                            },
                            "blocos_pesos": st.session_state["pesos_blocos"],
                            "cultura_valores": st.session_state["aderencia_valores"],
                            "metas": metas,
                            "plano_desenvolvimento": {
                                "cursos": st.session_state["cursos"],
                                "pontos_fortes": st.session_state["pontos_fortes"],
                                "pontos_melhorar": st.session_state["pontos_melhorar"],
                                "show_cursos_to_tech": st.session_state["show_cursos_to_tech"],
                                "show_pontos_fortes_to_tech": st.session_state["show_pontos_fortes_to_tech"],
                                "show_pontos_melhorar_to_tech": st.session_state["show_pontos_melhorar_to_tech"]
                            },
                            "feedback_final": st.session_state["feedback_final"],
                            "sugerir_pip": bool(st.session_state["pip_check"]),
                            "sugerir_destaque": bool(st.session_state["destaque_check"]),
                            "proxima_revisao": st.session_state["proxima_revisao"].strftime("%d/%m/%Y") if st.session_state.get("definir_prox_rev") else None,
                            "exibir_metas_tecnico": bool(st.session_state["mostrar_metas_para_tecnico"])
                        }
                        if tecnico['username'] not in fichas:
                            fichas[tecnico['username']] = []
                        fichas[tecnico['username']].insert(0, nova_ficha)
                        save_fichas(fichas)
                        st.success(f"Ficha de {tecnico['name']} salva com sucesso!")
                        time.sleep(0.5); st.rerun()

    # ===== Histórico =====
    with tabs[1]:
        users, fichas = load_users(), load_fichas()
        tecnicos = [u for u in users if u['role'] == 'tecnico']
        if not tecnicos:
            st.info("Sem técnicos cadastrados.")
        else:
            tec_nome_hist = st.selectbox("Selecione um Técnico", [t['name'] for t in tecnicos], key="hist_sel")
            tecnico_hist = next((t for t in tecnicos if t['name']==tec_nome_hist), None)
            arr = fichas.get(tecnico_hist['username'], [])
            if not arr:
                st.info("Nenhuma ficha encontrada para este técnico.")
            else:
                for idx, ficha in enumerate(arr):
                    with st.expander(f"Avaliação de {ficha.get('data','N/I')} — por {ficha.get('avaliador','N/I')}"):
                        comp = ficha.get("competencias", {})
                        ind = ficha.get("periodo_aplicado", {}).get("indicadores", {})
                        c1,c2,c3 = st.columns(3)
                        with c1: st.metric("Nota Final", f"{comp.get('nota_final','N/I')}")
                        with c2: st.metric("Conceito", comp.get("conceito","N/I"))
                        with c3: st.metric("★", comp.get("estrelinhas","N/I"))
                        st.caption(f"Período aplicado: {ficha.get('periodo_aplicado',{}).get('inicio','?')} → {ficha.get('periodo_aplicado',{}).get('fim','?')}")
                        ci1,ci2,ci3,ci4 = st.columns(4)
                        with ci1: st.metric("Total de Atendimentos", f"{ind.get('qtd','N/I')}")
                        with ci2: st.metric("Média de Espera", formatar_tempo_minutos((ind.get('espera_media') or 0)/60) if ind.get('espera_media') is not None else "N/I")
                        with ci3: st.metric("Média de Duração", formatar_tempo_minutos(ind.get('duracao_media')) if ind.get('duracao_media') is not None else "N/I")
                        with ci4: st.metric("Média de Avaliação", f"{(ind.get('rating_media') or 0):.2f}" if ind.get('rating_media') is not None else "N/I")

                        if ficha.get("metas"):
                            st.markdown("**Metas deste ciclo:**")
                            for j, m in enumerate(ficha["metas"], start=1):
                                is_curso = bool(m.get("is_curso", False) or _looks_like_course(m))
                                realizado = bool(m.get("curso_realizado", False))
                                status_txt = "✅ Realizado" if realizado else "⏳ Pendente"
                                cert_path = m.get("curso_certificado")

                                st.write(f"**{j}. {m.get('titulo','(sem título)')}** — indicador: {m.get('indicador','N/I')} — prazo: {m.get('prazo','N/I')} — curso: {'Sim' if is_curso else 'Não'}")
                                st.caption(m.get("descricao",""))
                                if is_curso:
                                    st.write(f"**Status do curso:** {status_txt}")
                                    if cert_path and os.path.exists(cert_path):
                                        with open(cert_path, "rb") as f:
                                            st.download_button("⬇ Certificado", f, file_name=os.path.basename(cert_path), key=f"dl_coord_{idx}_{j}")
                                    elif cert_path:
                                        st.caption("Certificado não localizado.")
                                st.markdown("---")
                        st.markdown(f"> *Feedback Final:* {ficha.get('feedback_final','—')}")

    # ===== Gerenciar Usuários =====
    with tabs[2]:
        with st.form("create_technician_form", clear_on_submit=True):
            st.subheader("➕ Adicionar Novo Técnico")
            new_name = st.text_input("Nome Completo")
            new_username = st.text_input("Nome de Usuário (para login)")
            new_password = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Criar Técnico")
            if submitted:
                users = load_users()
                if not new_name or not new_username or not new_password:
                    st.warning("Por favor, preencha todos os campos.")
                elif any(u['username'] == new_username.lower() for u in users):
                    st.error(f"O nome de usuário '{new_username}' já existe.")
                else:
                    new_user = {"username": new_username.lower(), "password": new_password, "role": "tecnico", "name": new_name}
                    users.append(new_user)
                    save_users(users)
                    st.success(f"Técnico '{new_name}' criado com sucesso!")
                    time.sleep(0.4); st.rerun()

        st.markdown("---")
        st.subheader("📋 Técnicos Cadastrados")
        users = load_users()
        tecnicos = [u for u in users if u['role'] == 'tecnico']
        if not tecnicos:
            st.info("Nenhum técnico cadastrado.")
        else:
            for t in tecnicos:
                st.write(f"*Nome:* {t['name']}  |  *Login:* `{t['username']}`")

    # ===== Pesos =====
    with tabs[3]:
        st.markdown("### ⚖ Configurar Pesos")
        st.caption("Ajuste os pesos. Alterações têm efeito imediato.")

        st.markdown("#### Ferramentas (soma ~100)")
        soma_f = 0
        cols = st.columns(3)
        for i, nome in enumerate(list(st.session_state["pesos_ferramentas"].keys())):
            with cols[i % 3]:
                st.session_state["pesos_ferramentas"][nome] = st.number_input(
                    f"Peso — {nome} (%)", min_value=0, max_value=100,
                    value=int(st.session_state["pesos_ferramentas"][nome]), step=1, key=f"peso_f_{nome}")
                soma_f += st.session_state["pesos_ferramentas"][nome]
        st.caption(f"Soma atual: **{soma_f}%**")

        st.markdown("#### Competências (escala relativa)")
        soma_c = 0
        cols = st.columns(3)
        for i, nome in enumerate(list(st.session_state["pesos_competencias"].keys())):
            with cols[i % 3]:
                st.session_state["pesos_competencias"][nome] = st.number_input(
                    f"Peso — {nome}", min_value=0, max_value=100,
                    value=int(st.session_state["pesos_competencias"][nome]), step=1, key=f"peso_c_{nome}")
                soma_c += st.session_state["pesos_competencias"][nome]
        st.caption(f"Soma atual (referência): **{soma_c}**")

        st.markdown("#### Blocos (devem somar 100)")
        c1, c2 = st.columns(2)
        with c1:
            st.session_state["pesos_blocos"]["Ferramentas"] = st.slider("Bloco Ferramentas (%)", 0, 100, st.session_state["pesos_blocos"]["Ferramentas"])
        with c2:
            st.session_state["pesos_blocos"]["Competências"] = 100 - st.session_state["pesos_blocos"]["Ferramentas"]
            st.write(f"Bloco Competências (%): **{st.session_state['pesos_blocos']['Competências']}**")

    st.markdown('</div>', unsafe_allow_html=True)

# ------------------ VISÃO DO TÉCNICO ------------------
def pagina_minhas_fichas():
    criar_botao_voltar()
    st.markdown('<div class="block-card">', unsafe_allow_html=True)
    st.markdown(f"## 📋 Painel de Desempenho — {st.session_state['user_info']['name']}")

    fichas = load_fichas()
    username = st.session_state['user_info']['username']
    arr = fichas.get(username, [])

    if not arr:
        st.info("Nenhuma ficha encontrada.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    ficha = arr[0]  # mais recente
    st.subheader("⭐ Sua Avaliação Mais Recente")
    comp = ficha.get("competencias", {})
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("Nota Final", f"{comp.get('nota_final','N/I')}")
    with c2: st.metric("Conceito", comp.get("conceito","N/I"))
    with c3: st.metric("★", comp.get("estrelinhas","N/I"))

    ind = ficha.get("periodo_aplicado", {}).get("indicadores", {})
    ci1,ci2,ci3,ci4 = st.columns(4)
    with ci1: st.metric("Total de Atendimentos", f"{ind.get('qtd','N/I')}")
    with ci2: st.metric("Média de Espera", formatar_tempo_minutos((ind.get('espera_media') or 0)/60) if ind.get('espera_media') is not None else "N/I")
    with ci3: st.metric("Média de Duração", formatar_tempo_minutos(ind.get('duracao_media')) if ind.get('duracao_media') is not None else "N/I")
    with ci4: st.metric("Média de Avaliação", f"{(ind.get('rating_media') or 0):.2f}" if ind.get('rating_media') is not None else "N/I")

    # -------- metas (visão técnico) ------------
    if ficha.get("exibir_metas_tecnico") and ficha.get("metas"):
        st.markdown("### 🎯 Suas Metas")

        existing_certs = []  # para mostrar botões de download FORA do form
        with st.form("progresso_cursos", clear_on_submit=False):
            houve_curso = False
            done_updates, upload_updates, set_is_course_updates = [], [], []

            for i, m in enumerate(ficha["metas"]):
                if not m.get("show_to_tech", True):
                    continue

                st.write(f"**{i+1}. {m.get('titulo','(sem título)')}**  —  Prazo: {m.get('prazo','N/I')}")
                st.caption(m.get("descricao",""))

                # considerar curso se flag ou heurística
                is_curso_effective = bool(m.get("is_curso", False) or _looks_like_course(m))
                if is_curso_effective:
                    houve_curso = True
                    if not m.get("is_curso", False):
                        st.caption("ℹ️ Detectamos que esta meta parece ser um **curso** (título/descrição).")

                    status_txt = "✅ Realizado" if m.get("curso_realizado") else "⏳ Pendente"
                    st.write(f"**Status atual:** {status_txt}")

                    cert_path = m.get("curso_certificado")
                    if cert_path and os.path.exists(cert_path):
                        # NÃO podemos usar download_button dentro do form
                        existing_certs.append((i, cert_path, m.get("titulo","Certificado")))
                        st.caption(f"Certificado anexado: **{os.path.basename(cert_path)}** (botão de download abaixo)")

                    done_val = st.checkbox("Curso realizado?", value=bool(m.get("curso_realizado")), key=f"curso_done_{i}")
                    up_file = st.file_uploader("Anexar/Substituir certificado (PDF/Imagem)", type=["pdf","png","jpg","jpeg"], key=f"curso_cert_{i}")

                    done_updates.append((i, done_val))
                    upload_updates.append((i, up_file))
                    if not m.get("is_curso", False):
                        set_is_course_updates.append(i)

                st.markdown("---")

            sub = st.form_submit_button("Salvar atualizações")
            if sub:
                changed = False
                # marcar como curso se heurística ativou
                for idx_meta in set_is_course_updates:
                    if idx_meta < len(ficha["metas"]):
                        ficha["metas"][idx_meta]["is_curso"] = True
                        changed = True
                # aplicar "realizado"
                for idx_meta, done_val in done_updates:
                    if idx_meta < len(ficha["metas"]):
                        if ficha["metas"][idx_meta].get("curso_realizado") != bool(done_val):
                            ficha["metas"][idx_meta]["curso_realizado"] = bool(done_val)
                            changed = True
                # salvar uploads
                for idx_meta, up in upload_updates:
                    if up is not None and idx_meta < len(ficha["metas"]):
                        os.makedirs("certificados", exist_ok=True)
                        ext = os.path.splitext(up.name)[1]
                        fname = f"{username}_meta{idx_meta+1}_{int(time.time())}{ext}"
                        path = os.path.join("certificados", fname)
                        with open(path, "wb") as f:
                            f.write(up.getbuffer())
                        ficha["metas"][idx_meta]["curso_certificado"] = path
                        changed = True

                if changed:
                    fichas[username][0] = ficha
                    save_fichas(fichas)
                    st.success("Progresso atualizado!")
                else:
                    st.info("Nenhuma alteração para salvar.")
                time.sleep(0.4); st.rerun()

        # Fora do form: exibir botões de download
        if existing_certs:
            st.markdown("#### 📎 Certificados anexados")
            for i, cert_path, titulo in existing_certs:
                if os.path.exists(cert_path):
                    with open(cert_path, "rb") as f:
                        st.download_button(f"Baixar certificado — {titulo}", f, file_name=os.path.basename(cert_path), key=f"dl_tech_out_{i}")
                else:
                    st.caption(f"Certificado não localizado ({os.path.basename(cert_path)}).")
        else:
            st.caption("Nenhuma meta marcada como curso.")

    # -------- Plano de Desenvolvimento (visibilidade) ----------
    plano = ficha.get("plano_desenvolvimento", {})
    if plano.get("show_cursos_to_tech", True) and plano.get("cursos"):
        st.markdown("### 🧩 Cursos/Treinamentos sugeridos")
        st.write(plano.get("cursos"))
    if plano.get("show_pontos_fortes_to_tech", True) and plano.get("pontos_fortes"):
        st.markdown("### 💪 Pontos fortes")
        st.write(plano.get("pontos_fortes"))
    if plano.get("show_pontos_melhorar_to_tech", True) and plano.get("pontos_melhorar"):
        st.markdown("### 🔧 Pontos a melhorar")
        st.write(plano.get("pontos_melhorar"))

    st.markdown(f"> *Feedback Final do Coordenador:* {ficha.get('feedback_final','—')}")
    # histórico resumido
    if len(arr) > 1:
        st.markdown("---")
        st.subheader("📂 Histórico de Avaliações Anteriores")
        for f in arr[1:]:
            with st.expander(f"Avaliação de {f.get('data','N/I')}"):
                st.write(f"*Conceito:* {f.get('competencias',{}).get('conceito','N/I')}  —  *Nota:* {f.get('competencias',{}).get('nota_final','N/I')}")

    st.markdown('</div>', unsafe_allow_html=True)

# ============================== ROTEAMENTO ==============================
def main():
    if not st.session_state.logged_in:
        pagina_login()
    else:
        page = st.session_state.page
        if page == "menu":
            pagina_menu_principal()
        elif page == "dashboard":
            pagina_dashboard()
        elif page == "minhas_fichas":
            pagina_minhas_fichas()
        elif page == "avaliar_tecnicos":
            pagina_avaliar_tecnicos()
        else:
            st.session_state.page = "menu"; st.rerun()

# -------- utilidades de conceito/estrela --------
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

if __name__ == "__main__":
    main()
