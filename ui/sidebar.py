from datetime import datetime

import streamlit as st
from config.settings import tavily_config
from database.session import session_mgr


def render_sidebar():
    with st.sidebar:
        st.header("⚙️ Settings")

        language = st.selectbox("Language", ["中文", "日本語", "English"])

        st.divider()
        st.header("🎯 Processing Options")

        enable_deep_thinking = st.checkbox(
            "🧠 Enable Deep Thinking",
            value=False,
            help="Enable self-reflection and iterative refinement",
        )

        enable_web_search = st.checkbox(
            "🌐 Enable Web Search",
            value=False,
            help="Search internet for current information (Tavily)",
        )

        st.info("""
**Processing Flow:**
- **Basic**: Understanding -> Analysis -> Answer
- **Deep Thinking**: + Self-Reflection
- **Web Search**: + Internet Search
- **Medical/Legal**: Auto-enabled Web Search
- **Arch/DEV**: Auto-enabled Code Generation
        """)

        st.divider()
        st.header("📁 Sessions")

        if st.button("➕ New Session", use_container_width=True):
            new_session_id = session_mgr.create_session(
                f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "general",
                language,
            )
            st.session_state.current_session = new_session_id
            st.session_state.messages = []
            st.rerun()

        sessions = session_mgr.list_sessions()

        if sessions:
            # 构建优化的会话显示（摘要在前，日期在后）
            session_options = {}
            session_data = {}  # 存储完整数据用于后续操作

            for s in sessions:
                session_id = s["session_id"]

                # 获取摘要
                summary = s.get("summary", "").strip()
                if not summary:
                    messages = session_mgr.get_messages(session_id, limit=1)
                    if messages and messages[0]["role"] == "user":
                        first_msg = messages[0]["content"]
                        summary = (
                            first_msg[:50] + "..." if len(first_msg) > 50 else first_msg
                        )
                    else:
                        summary = "(空会话)"

                # 格式化日期
                updated_time = datetime.fromtimestamp(s["updated_at"])

                # 判断是今天还是更早
                today = datetime.now().date()
                if updated_time.date() == today:
                    time_str = updated_time.strftime("%H:%M")
                else:
                    time_str = updated_time.strftime("%m-%d %H:%M")

                # 组合显示：摘要 | 日期
                display_text = (
                    f"💬 {summary}\n   📅 {time_str} | {s.get('domain', 'general')}"
                )

                session_options[session_id] = display_text
                session_data[session_id] = s

            selected = st.selectbox(
                "Select Session",
                options=list(session_options.keys()),
                format_func=lambda x: session_options.get(x, "Unknown"),
                key="session_selector",
            )

            # 会话操作按钮
            col1, col2 = st.columns(2)

            with col1:
                if st.button("🔄 Load", use_container_width=True, key="load_session"):
                    if selected and selected != st.session_state.get("current_session"):
                        st.session_state.current_session = selected
                        history = session_mgr.get_messages(selected)
                        st.session_state.messages = [
                            {"role": msg["role"], "content": msg["content"]}
                            for msg in history
                        ]
                        st.rerun()

            with col2:
                if st.button(
                    "🗑️ Delete", use_container_width=True, key="delete_session"
                ):
                    if selected:
                        # 两次确认机制
                        confirm_key = f"confirm_delete_{selected}"
                        if not st.session_state.get(confirm_key, False):
                            st.session_state[confirm_key] = True
                            st.warning("⚠️ 再次点击确认删除")
                        else:
                            # 执行逻辑删除
                            session_mgr.delete_session(selected)
                            st.session_state[confirm_key] = False

                            # 如果删除的是当前会话，创建新会话
                            if selected == st.session_state.get("current_session"):
                                new_session_id = session_mgr.create_session(
                                    f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                                    "general",
                                    language,
                                )
                                st.session_state.current_session = new_session_id
                                st.session_state.messages = []

                            st.success("✅ 会话已删除（数据已保留用于审计）")
                            st.rerun()

        # 显示已删除会话的选项（审计功能）
        with st.expander("🗂️ 已删除会话（审计）", expanded=False):
            deleted_sessions = session_mgr.list_sessions(status="deleted")
            if deleted_sessions:
                st.caption(f"共 {len(deleted_sessions)} 个已删除会话")
                for s in deleted_sessions[:10]:  # 显示最近10个
                    deleted_time = datetime.fromtimestamp(s["updated_at"]).strftime(
                        "%Y-%m-%d %H:%M"
                    )
                    summary = s.get("summary", "No summary")[:40]
                    st.text(f"🗑️ {summary}")
                    st.caption(
                        f"   删除时间: {deleted_time} | 域: {s.get('domain', 'N/A')}"
                    )
            else:
                st.caption("暂无已删除会话")

        if not tavily_config.is_configured:
            st.warning("⚠️ Tavily API not configured. Web search disabled.")

    return language, enable_deep_thinking, enable_web_search
