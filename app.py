"""Phase 5: Streamlit chat UI for the ESG Data Assistant — teachable edition."""

import json
import time
import streamlit as st
import pandas as pd
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from config import MONGODB_URI, MONGODB_DATABASE, OPENAI_API_KEY, OPENAI_MODEL
from agent.agent import ESGQueryWorkflow

st.set_page_config(page_title="ESG Data Assistant", page_icon="🌍", layout="wide")

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Prevent column content from overflowing into adjacent columns. */
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        min-width: 0;
    }

    /* Keep chat text/code wrapped within the chat column. */
    [data-testid="stChatMessageContent"] {
        max-width: 100%;
        overflow-wrap: anywhere;
        word-break: break-word;
    }
    [data-testid="stChatMessageContent"] pre,
    [data-testid="stChatMessageContent"] code {
        white-space: pre-wrap;
        word-break: break-word;
    }

    .step-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
    .step-number {
        display: inline-flex; align-items: center; justify-content: center;
        width: 28px; height: 28px; border-radius: 50%; font-weight: 700;
        font-size: 14px; color: white; flex-shrink: 0;
    }
    .step-passed { background-color: #22c55e; }
    .step-failed { background-color: #ef4444; }
    .step-blocked { background-color: #f59e0b; }
    .step-title { font-weight: 600; font-size: 15px; }
    .step-status-badge {
        display: inline-block; padding: 2px 8px; border-radius: 4px;
        font-size: 12px; font-weight: 600; color: white; margin-left: auto;
    }
    .badge-passed { background-color: #22c55e; }
    .badge-failed { background-color: #ef4444; }
    .badge-blocked { background-color: #f59e0b; }
    .explain-box {
        background-color: #f0f4ff; border-left: 3px solid #6366f1;
        padding: 10px 14px; margin: 8px 0; border-radius: 0 6px 6px 0;
        font-size: 13px; color: #374151;
    }
    div[data-testid="stExpander"] { border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 6px; }
    .pipeline-overview {
        display: flex; gap: 6px; flex-wrap: wrap; align-items: center;
        padding: 10px 0; margin-bottom: 12px;
    }
    .pipe-dot {
        display: inline-flex; align-items: center; gap: 4px;
        padding: 4px 10px; border-radius: 20px; font-size: 12px;
        font-weight: 600; color: white;
    }
    .pipe-arrow { color: #9ca3af; font-size: 16px; }
    /* Right pipeline inspector panel */
    [data-testid="stColumn"]:last-child {
        border-left: 2px solid #e5e7eb;
        padding-left: 1rem !important;
    }
</style>
""", unsafe_allow_html=True)

EXAMPLE_QUERIES = [
    "How have Apple's emissions trended over 10 years?",
    "Which sector has the highest average carbon intensity?",
    "Compare Microsoft and Google Scope 1 emissions in 2023",
    "Top 5 companies by renewable energy percentage",
    "Which companies have SBTi-aligned targets?",
    "Show me the board diversity trend for tech companies",
    "Which companies had controversies in 2023?",
    "Average ESG score by sector",
]

GUARDRAIL_DEMO_QUERIES = [
    "Find all companies mentioning 'green' in their reports",
    "Show me everything in the database",
    "Show companies filtered by metadata.confidence_score > 0.9",
]

STATUS_ICONS = {"passed": "✅", "failed": "❌", "blocked": "⚠️"}
STATUS_COLORS = {"passed": "#22c55e", "failed": "#ef4444", "blocked": "#f59e0b"}

NODE_LABELS = {
    "enrich": "Schema Enrichment",
    "generate": "MQL Generation",
    "validate": "Guardrail Validation & Execution",
    "synthesize": "Response Synthesis",
}
STEP_DELAY = 0.6
NODE_DELAY = 0.3


def check_mongodb_connection():
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        client.close()
        return True
    except (ConnectionFailure, Exception):
        return False


def check_llm_connection():
    return bool(OPENAI_API_KEY and OPENAI_API_KEY != "your-api-key-here")


@st.cache_resource
def get_workflow():
    return ESGQueryWorkflow()


def flatten_for_dataframe(results):
    def flatten(d, parent_key="", sep="."):
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten(v, new_key, sep).items())
            elif isinstance(v, list):
                items.append((new_key, ", ".join(str(x) for x in v)))
            else:
                items.append((new_key, v))
        return dict(items)
    return [flatten(r) for r in results]


def build_guardrail_query_preview(generated_mql):
    """Build a compact, display-friendly query payload for blocked guardrail cases."""
    if not generated_mql:
        return None

    query_type = generated_mql.get("query_type", "find")
    preview = {
        "collection": generated_mql.get("collection"),
        "query_type": query_type,
    }

    if query_type == "aggregate":
        preview["pipeline"] = generated_mql.get("pipeline", [])
    else:
        preview["filter"] = generated_mql.get("filter", {})
        if generated_mql.get("projection") is not None:
            preview["projection"] = generated_mql.get("projection")
        if generated_mql.get("sort") is not None:
            preview["sort"] = generated_mql.get("sort")
        if generated_mql.get("limit") is not None:
            preview["limit"] = generated_mql.get("limit")

    return preview


def render_pipeline_overview(trace):
    """Render the compact pipeline status bar at the top."""
    if not trace:
        return
    dots = []
    for i, step in enumerate(trace):
        status = step.get("status", "passed")
        color = STATUS_COLORS.get(status, "#6b7280")
        icon = STATUS_ICONS.get(status, "⬜")
        label = step.get("step", f"Step {i+1}")
        short = label.split("(")[0].strip()
        dots.append(
            f'<span class="pipe-dot" style="background-color:{color}">'
            f'{icon} {short}</span>'
        )
    html = '<div class="pipeline-overview">' + \
           ' <span class="pipe-arrow">→</span> '.join(dots) + \
           '</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_trace_step(step, index):
    """Render a single expandable trace step with educational content."""
    status = step.get("status", "passed")
    icon = STATUS_ICONS.get(status, "⬜")
    color_class = f"step-{status}" if status in ("passed", "failed", "blocked") else "step-passed"
    badge_class = f"badge-{status}" if status in ("passed", "failed", "blocked") else "badge-passed"
    title = step.get("step", f"Step {index+1}")
    detail = step.get("detail", "")

    with st.expander(f"{icon}  Step {index+1}: {title}", expanded=(status != "passed")):
        # Status + detail
        st.markdown(f"**Status:** `{status.upper()}`")
        st.markdown(detail)

        # Educational explanation
        explanation = step.get("explanation", "")
        if explanation:
            st.markdown(
                f'<div class="explain-box">💡 <strong>How it works:</strong> {explanation}</div>',
                unsafe_allow_html=True,
            )

        # Step-specific deep-dive content
        _render_step_details(step, title)


def _render_step_details(step, title):
    """Render the detailed technical content for each specific step type."""

    if "Schema Enrichment" in title:
        if step.get("collections"):
            st.markdown(f"**Collections loaded:** `{'`, `'.join(step['collections'])}`")
        if step.get("context_length_chars"):
            st.markdown(f"**Context size:** {step['context_length_chars']:,} characters")
        if step.get("context_preview"):
            with st.popover("📄 View schema context sent to LLM"):
                st.code(step["context_preview"], language="yaml")

    elif "Prompt Construction" in title:
        if step.get("total_prompt_chars"):
            st.markdown(f"**Total prompt size:** {step['total_prompt_chars']:,} characters")
        if step.get("few_shot_count"):
            st.markdown(f"**Few-shot examples:** {step['few_shot_count']} question/answer pairs")
        if step.get("few_shot_questions"):
            with st.popover("📋 View few-shot example questions"):
                for i, q in enumerate(step["few_shot_questions"], 1):
                    st.markdown(f"{i}. {q}")
        if step.get("system_prompt_preview"):
            with st.popover("📝 View system prompt (preview)"):
                st.code(step["system_prompt_preview"], language="text")

    elif "MQL Generation" in title:
        if step.get("llm_response_time_ms"):
            st.markdown(f"**LLM response time:** {step['llm_response_time_ms']}ms")
        if step.get("target_collection"):
            st.markdown(f"**Target collection:** `{step['target_collection']}`")
        if step.get("query_type"):
            st.markdown(f"**Query type:** `{step['query_type']}`")
        if step.get("raw_llm_response"):
            with st.popover("🤖 View raw LLM response"):
                st.code(step["raw_llm_response"], language="json")
        if step.get("parsed_mql"):
            st.markdown("**Parsed MQL:**")
            st.code(json.dumps(step["parsed_mql"], indent=2, default=str), language="json")

    elif "Field Allowlist" in title:
        if step.get("fields_checked"):
            st.markdown(f"**Fields checked:** `{'`, `'.join(step['fields_checked'])}`")
        if step.get("allowlist_size"):
            st.markdown(f"**Allowlist size:** {step['allowlist_size']} approved fields")

    elif "Index Coverage" in title:
        if step.get("filter_fields"):
            st.markdown(f"**Filter fields:** `{'`, `'.join(step['filter_fields'])}`")
        if step.get("available_indexes"):
            st.markdown("**Available indexes:**")
            for idx_name in step["available_indexes"]:
                st.markdown(f"  - `{idx_name}`")

    elif "Safety Injection" in title:
        if step.get("actions"):
            st.markdown("**Actions applied:**")
            for action in step["actions"]:
                st.markdown(f"  - {action}")

    elif "Query Execution" in title:
        if step.get("execution_time_ms") is not None:
            st.markdown(f"**Execution time:** {step['execution_time_ms']}ms")
        if step.get("result_count") is not None:
            st.markdown(f"**Documents returned:** {step['result_count']}")

    elif "Response Synthesis" in title:
        pass


def render_trace(trace):
    """Render the full processing pipeline trace."""
    if not trace:
        return

    st.markdown("---")
    st.markdown("### 🔬 Processing Pipeline")
    st.caption(
        "Each step below shows exactly what happened under the hood — "
        "from loading the schema, to building the LLM prompt, generating MQL, "
        "validating through guardrails, and executing the query."
    )
    render_pipeline_overview(trace)

    for i, step in enumerate(trace):
        render_trace_step(step, i)


def render_chart(df):
    """Render a Plotly chart if the data is suitable."""
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if len(df) < 2 or not numeric_cols:
        return

    if "reporting_year" in df.columns:
        chart_cols = [c for c in numeric_cols if c != "reporting_year"]
        if chart_cols:
            import plotly.express as px
            chart_df = df[["reporting_year"] + chart_cols[:3]].melt(
                id_vars="reporting_year", var_name="Metric", value_name="Value"
            )
            fig = px.line(chart_df, x="reporting_year", y="Value", color="Metric",
                          title="Trend Over Time")
            st.plotly_chart(fig, use_container_width=True)
    elif "_id" in df.columns:
        import plotly.express as px
        val_col = numeric_cols[0]
        fig = px.bar(df, x="_id", y=val_col, title=f"{val_col} by Category")
        st.plotly_chart(fig, use_container_width=True)


def render_streaming_step(step):
    """Render a single pipeline step inside a st.status container during live streaming."""
    status = step.get("status", "passed")
    icon = STATUS_ICONS.get(status, "⬜")
    title = step.get("step", "Processing")
    detail = step.get("detail", "")

    st.markdown(f"**{icon} {title}**")
    if detail:
        st.caption(detail)

    explanation = step.get("explanation", "")
    if explanation:
        st.markdown(
            f'<div class="explain-box">💡 <strong>How it works:</strong> {explanation}</div>',
            unsafe_allow_html=True,
        )

    if step.get("collections"):
        st.markdown(f"**Collections:** `{'`, `'.join(step['collections'])}`")
        if step.get("context_length_chars"):
            st.markdown(f"**Context size:** {step['context_length_chars']:,} chars")

    if step.get("total_prompt_chars"):
        st.markdown(
            f"**Prompt:** {step['total_prompt_chars']:,} chars, "
            f"{step.get('few_shot_count', 0)} few-shot examples"
        )

    if step.get("parsed_mql"):
        st.code(json.dumps(step["parsed_mql"], indent=2, default=str), language="json")
    elif step.get("llm_response_time_ms") and not step.get("parsed_mql"):
        st.markdown(f"**LLM response time:** {step['llm_response_time_ms']}ms")

    if step.get("fields_checked"):
        st.markdown(
            f"**Fields checked:** `{'`, `'.join(step['fields_checked'])}` "
            f"({step.get('allowlist_size', '?')} allowed)"
        )

    if step.get("filter_fields"):
        st.markdown(f"**Filter fields:** `{'`, `'.join(step['filter_fields'])}`")

    if step.get("actions"):
        for action in step["actions"]:
            st.markdown(f"  • {action}")

    if step.get("execution_time_ms") is not None:
        st.markdown(
            f"**Execution:** {step['execution_time_ms']}ms → "
            f"{step.get('result_count', 0)} document(s)"
        )


def main():
    # ── Sidebar (left) ──────────────────────────────────────────────────────
    with st.sidebar:
        st.title("ESG Data Assistant")

        mongo_ok = check_mongodb_connection()
        llm_ok = check_llm_connection()

        st.markdown("### Connection Status")
        st.markdown(f"{'✅' if mongo_ok else '❌'} MongoDB")
        st.markdown(f"{'✅' if llm_ok else '❌'} LLM ({OPENAI_MODEL})")

        st.divider()
        st.markdown("### 💬 Example Queries")
        for q in EXAMPLE_QUERIES:
            if st.button(q, key=f"ex_{q[:30]}", use_container_width=True):
                st.session_state["pending_query"] = q

        st.divider()
        st.markdown("### 🛡️ Guardrail Demos (expected rejections)")
        for q in GUARDRAIL_DEMO_QUERIES:
            if st.button(q, key=f"guard_{q[:30]}", use_container_width=True):
                st.session_state["pending_query"] = q

        st.divider()
        st.markdown("### ⚙️ Settings")
        max_results = st.slider("Max results to display", 5, 50, 20)
        show_charts = st.checkbox("Show charts for trend data", value=True)
        show_pipeline = st.checkbox("Show pipeline inspector", value=True)

    # ── Session state ───────────────────────────────────────────────────────
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "pending_query" not in st.session_state:
        st.session_state.pending_query = None
    if "current_trace" not in st.session_state:
        st.session_state.current_trace = []

    # ── Two-column layout: Chat (left) + Pipeline Inspector (right) ─────────
    if show_pipeline:
        chat_col, pipeline_col = st.columns([7, 3])
    else:
        chat_col = st.container()
        pipeline_col = None

    with chat_col:
        st.title("🌍 ESG Data Assistant")
        st.caption(
            "Ask natural language questions about ESG data stored in MongoDB."
        )

    # Pipeline inspector panel (right)
    if pipeline_col is not None:
        with pipeline_col:
            st.markdown("### 🔬 Pipeline Inspector")
            st.caption("Steps appear here in real time as your query is processed.")
            pipeline_area = st.container()
    else:
        pipeline_area = None

    # ── Render chat history (left column only) ──────────────────────────────
    with chat_col:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

                if msg.get("guardrail_query") is not None:
                    st.markdown("**Generated query (blocked by guardrails):**")
                    st.code(
                        json.dumps(msg["guardrail_query"], indent=2, default=str),
                        language="json",
                    )

                if msg.get("dataframe") is not None:
                    df = pd.DataFrame(msg["dataframe"])
                    st.dataframe(df, use_container_width=True)
                    if show_charts:
                        render_chart(df)

    # ── Chat input (full width, pinned to bottom) ───────────────────────────
    # Always render chat_input so the bar stays persistent on every rerun.
    user_prompt = st.chat_input("Ask about ESG data...")
    pending_prompt = st.session_state.pop("pending_query", None)
    prompt = user_prompt or pending_prompt

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

        with chat_col:
            with st.chat_message("user"):
                st.markdown(prompt)

        if not mongo_ok:
            with chat_col:
                with st.chat_message("assistant"):
                    st.error(
                        "MongoDB is not connected. Please check your connection settings."
                    )
            return
        if not llm_ok:
            with chat_col:
                with st.chat_message("assistant"):
                    st.error(
                        "LLM API key is not configured. "
                        "Please set OPENAI_API_KEY in your .env file."
                    )
            return

        workflow = get_workflow()
        accumulated_trace = []
        final_result = {}

        if pipeline_area is not None:
            # ── Stream with progressive rendering in right panel ────────────
            try:
                for step_data in workflow.stream(prompt):
                    node = step_data["node"]
                    new_steps = step_data["new_trace_steps"]
                    final_result = step_data["state"]

                    if new_steps:
                        time.sleep(NODE_DELAY)
                        label = NODE_LABELS.get(
                            node, node.replace("_", " ").title()
                        )
                        with pipeline_area:
                            with st.status(
                                f"{label}...", expanded=True
                            ) as node_status:
                                for step in new_steps:
                                    time.sleep(STEP_DELAY)
                                    accumulated_trace.append(step)
                                    render_streaming_step(step)

                                all_passed = all(
                                    s.get("status") == "passed"
                                    for s in new_steps
                                )
                                has_failed = any(
                                    s.get("status") == "failed"
                                    for s in new_steps
                                )
                                if all_passed:
                                    node_status.update(
                                        label=f"✅ {label}",
                                        state="complete",
                                        expanded=False,
                                    )
                                elif has_failed:
                                    node_status.update(
                                        label=f"❌ {label}",
                                        state="error",
                                        expanded=True,
                                    )
                                else:
                                    node_status.update(
                                        label=f"⚠️ {label}",
                                        state="error",
                                        expanded=True,
                                    )
            except Exception as e:
                with chat_col:
                    with st.chat_message("assistant"):
                        st.error(f"Error: {str(e)}")
                return
        else:
            # ── Pipeline hidden — run synchronously ─────────────────────────
            try:
                result = workflow.run(prompt)
                final_result = result
                accumulated_trace = result.get("trace", [])
            except Exception as e:
                with chat_col:
                    with st.chat_message("assistant"):
                        st.error(f"Error: {str(e)}")
                return

        st.session_state.current_trace = accumulated_trace

        # ── Show response in chat column ────────────────────────────────────
        response_text = final_result.get("response", "")
        query_result = final_result.get("query_result", {})
        generated_mql = final_result.get("generated_mql", {})

        df_data = None
        guardrail_query_preview = None
        with chat_col:
            with st.chat_message("assistant"):
                st.markdown(response_text)

                if (
                    not query_result.get("success")
                    and query_result.get("guardrail")
                    and query_result.get("guardrail") != "execution"
                ):
                    guardrail_query_preview = build_guardrail_query_preview(generated_mql)
                    if guardrail_query_preview is not None:
                        st.markdown("**Generated query (blocked by guardrails):**")
                        st.code(
                            json.dumps(guardrail_query_preview, indent=2, default=str),
                            language="json",
                        )

                if query_result.get("success") and query_result.get("results"):
                    flat = flatten_for_dataframe(query_result["results"])
                    df = pd.DataFrame(flat)
                    df_display = df.head(min(max_results, len(df)))
                    st.dataframe(df_display, use_container_width=True)
                    df_data = df_display.to_dict("records")

                    if show_charts:
                        render_chart(df_display)

        st.session_state.messages.append({
            "role": "assistant",
            "content": response_text,
            "trace": accumulated_trace,
            "dataframe": df_data,
            "guardrail_query": guardrail_query_preview,
        })

    else:
        # ── No new query: show stored trace in right panel ──────────────────
        if pipeline_area is not None:
            trace = st.session_state.get("current_trace", [])
            if trace:
                with pipeline_area:
                    for i, step in enumerate(trace):
                        status = step.get("status", "passed")
                        icon = STATUS_ICONS.get(status, "⬜")
                        title = step.get("step", f"Step {i+1}")
                        with st.expander(
                            f"{icon} {title}", expanded=(status != "passed")
                        ):
                            st.caption(step.get("detail", ""))
                            explanation = step.get("explanation", "")
                            if explanation:
                                st.markdown(
                                    f'<div class="explain-box">'
                                    f"💡 <strong>How it works:</strong> "
                                    f"{explanation}</div>",
                                    unsafe_allow_html=True,
                                )
            else:
                with pipeline_area:
                    st.info(
                        "Run a query to see the processing pipeline here.",
                        icon="👈",
                    )


if __name__ == "__main__":
    main()
