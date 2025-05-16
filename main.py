import pandas as pd
import streamlit as st
import os
from supabase import create_client, Client
import dotenv
import math

dotenv.load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
password = os.getenv("PAINEL_PASSWORD")
supabase: Client = create_client(url, key)


# -------------------------------
# Autenticação por senha simples
# -------------------------------
st.title("Painel de Dados")

senha_correta = os.getenv("PAINEL_PASSWORD", password)
senha = st.text_input("Digite a senha para acessar o painel:", type="password")


if senha != senha_correta:
    st.warning("Acesso restrito. Digite a senha correta.")
    st.stop()  # Interrompe o script se a senha estiver errada

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False


# Get the total number of users in each comunidad.
def get_status_hoje():
    total_users = supabase.table("Users").select("*", count="exact").execute().count
    users_today = supabase.table("Users").select("*", count="exact").eq("created_at", pd.Timestamp.now().strftime('%Y-%m-%d')).execute().count
    total_communities = supabase.table("Communities").select("*", count="exact").execute().count
    communities_today = supabase.table("Communities").select("*", count="exact").eq("created_at", pd.Timestamp.now().strftime('%Y-%m-%d')).execute().count
    total_posts = supabase.table("Posts").select("*", count="exact").execute().count
    posts_today = supabase.table("Posts").select("*", count="exact").eq("created_at", pd.Timestamp.now().strftime('%Y-%m-%d')).execute().count

    result = {
        "Usuários pra Meta": 1000 - total_users,
        "Total Usuários": total_users,
        "Usuários Hoje": users_today,
        "Total Comunidades": total_communities,
        "Comunidades Hoje": communities_today,
        "Total Posts": total_posts,
        "Posts Hoje": posts_today
    }

    return result



# Retorna a quantidade de usuários cadastrados por dia no período definido.
def get_usuarios_por_dia(data_inicio="2025-05-01", data_fim="2025-06-01"):
    response = supabase.table("Users") \
        .select("created_at") \
        .gte("created_at", data_inicio) \
        .lte("created_at", data_fim) \
        .execute()

    if not response.data:
        return pd.DataFrame(columns=["Período", "Total Usuários"])

    df = pd.DataFrame(response.data)
    df["Período"] = pd.to_datetime(df["created_at"]).dt.date
    resultado = df.groupby("Período").size().reset_index(name="Total Usuários")
    resultado = resultado.sort_values("Período", ascending=False)

    return resultado



# Retorna a quantidade de posts por usuário no período definido.
def get_posts_por_usuarios_por_periodo(data_inicio="2025-05-01", data_fim="2025-06-01"):
    response = (
        supabase.table("Posts")
        .select("author_id, Users!Posts_author_id_fkey(name)")
        .gte("created_at", data_inicio)
        .lte("created_at", data_fim)
        .execute()
    )

    if not response.data:
        return pd.DataFrame(columns=["author_id", "name", "Total Posts"])

    df = pd.DataFrame(response.data)
    # Extrai o nome do usuário do join correto
    df["name"] = df["Users"].apply(lambda u: u["name"] if u else None)
    resultado = df.groupby(["author_id", "name"]).size().reset_index(name="Total Posts")
    resultado = resultado.sort_values("Total Posts", ascending=False)
    return resultado



# Retorna a quantidade de posts por dia no período definido.
def get_posts_por_periodo(start_date, end_date):
    
    response = (
        supabase.table("Posts")
        .select("created_at")
        .gte("created_at", start_date)
        .lte("created_at", end_date)
        .execute()
    )

    if not response.data:
        return pd.DataFrame(columns=["data_post", "total"])

    df = pd.DataFrame(response.data)
    df["data_post"] = pd.to_datetime(df["created_at"]).dt.date
    resultado = df.groupby("data_post").size().reset_index(name="total")
    resultado = resultado.sort_values("data_post", ascending=False)

    return resultado



# Retorna a quantidade de usuários por comunidade.
def get_total_usuarios_por_comunidade():

    response = supabase.table("UsersCommunitiesRoles") \
        .select("community_id, Communities(name)") \
        .execute()

    if not response.data:
        return pd.DataFrame(columns=["name", "total_usuarios"])

    df = pd.DataFrame(response.data)

    # Extrair nome da comunidade a partir do join
    df["name"] = df["Communities"].apply(lambda c: c["name"] if c else None)

    resultado = df.groupby("name").size().reset_index(name="total_usuarios")
    resultado = resultado.sort_values("total_usuarios", ascending=False)

    return resultado



metrics = get_status_hoje()
df_metrics = pd.DataFrame([
    {
        "Usuários pra Meta": metrics["Usuários pra Meta"],
        "Total Usuários": metrics["Total Usuários"],
        "Usuários Hoje": metrics["Usuários Hoje"],
        "Total Comunidades": metrics["Total Comunidades"],
        "Comunidades Hoje": metrics["Comunidades Hoje"],
        "Total Posts": metrics["Total Posts"],
        "Posts Hoje": metrics["Posts Hoje"]
    }
])
st.table(df_metrics)


# Filtro de data para selecionar o período
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Data inicial", pd.to_datetime("2025-05-01"))
with col2:
    end_date = st.date_input("Data final", pd.to_datetime("2025-06-01"))

# Converter para string no formato esperado
start_date_str = start_date.strftime('%Y-%m-%d')
end_date_str = end_date.strftime('%Y-%m-%d')


st.header("Usuários por período")
usuariosPorDia = get_usuarios_por_dia(start_date_str, end_date_str)
df_metrics = pd.DataFrame(usuariosPorDia)
st.table(df_metrics)


st.header("Posts por período")
postsPorDia = get_posts_por_periodo(start_date_str, end_date_str)
df_posts_por_dia = pd.DataFrame(postsPorDia)
st.table(df_posts_por_dia)


st.header("Posts por usuário")
posts_por_usuario = get_posts_por_usuarios_por_periodo(start_date_str, end_date_str)
df_posts_por_usuario = pd.DataFrame(posts_por_usuario)
st.table(df_posts_por_usuario)


st.header("Total de usuários por comunidade")
totalUsuariosComunidade = get_total_usuarios_por_comunidade()
df_usuarios_por_comunidade = pd.DataFrame(totalUsuariosComunidade)
st.table(df_usuarios_por_comunidade)

# Paginação
items_per_page = 20
total_items = len(posts_por_usuario)
total_pages = math.ceil(total_items / items_per_page)

page = st.number_input("Página", min_value=1, max_value=max(1, total_pages), value=1, step=1)

start_idx = (page - 1) * items_per_page
end_idx = start_idx + items_per_page

df_posts_por_usuario = pd.DataFrame(posts_por_usuario).iloc[start_idx:end_idx]
st.table(df_posts_por_usuario)
st.caption(f"Página {page} de {total_pages}")