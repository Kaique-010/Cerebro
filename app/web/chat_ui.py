import streamlit as st

from app.services.chat_service import ChatService

st.set_page_config(page_title="Cérebro Chat", page_icon="🧠", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #020b1f 0%, #0d1b45 45%, #2b2f8f 100%);
        color: #e4e7eb;
    }
    .app-title {
        color: #c0c0c0;
        font-size: 2.5rem;
        margin-bottom: .25rem;
    }
    .app-subtitle {
        color: #d4af37;
        margin-bottom: 1.5rem;
    }
    .tool-card {
        border: 1px solid rgba(212,175,55,.35);
        border-radius: 12px;
        padding: 1rem;
        background: rgba(5, 10, 30, .55);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "chat_service" not in st.session_state:
    st.session_state.chat_service = ChatService()
if "messages" not in st.session_state:
    st.session_state.messages = []

chat_service: ChatService = st.session_state.chat_service

with st.sidebar:
    st.header("⚙️ Executor com Tools")
    response_mode = st.selectbox(
        "Modo de resposta",
        options=["codegen", "answer"],
        index=0,
        format_func=lambda item: "Opção 3 • Gerar código" if item == "codegen" else "Resposta textual",
    )
    selected_tool = st.selectbox("Tool", chat_service.available_tools())
    tool_payload = st.text_input("Payload da tool", placeholder="Texto opcional")

    if st.button("Executar tool", use_container_width=True):
        tool_result = chat_service.run_tool(selected_tool, tool_payload)
        st.success(f"{tool_result.name}: {tool_result.output}")

    st.divider()
    st.caption("Memória incremental ativa: decisões + interações.")

st.markdown("<div class='app-title'>Cérebro • Chat Interface</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='app-subtitle'>Estilo Claude com degrade azul escuro → anil e paleta prata/dourado.</div>",
    unsafe_allow_html=True,
)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Como posso ajudar você hoje?")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            result = chat_service.chat(prompt, mode=response_mode)

        st.markdown(result["answer"])

        if result["limitations"]:
            with st.expander("Limitações detectadas"):
                for limitation in result["limitations"]:
                    st.write(f"- {limitation}")

    st.session_state.messages.append({"role": "assistant", "content": result["answer"]})
