import os
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
import streamlit as st
import pandas as pd
import json, boto3, io
from datetime import datetime

st.set_page_config(
    page_title="OSINT Intelligence Platform",
    page_icon="🛰",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background-color: #0d1117; color: #c9d1d9;
}
.main { background-color: #0d1117; }
[data-testid="stSidebar"] { background-color: #161b22; border-right:1px solid #21262d; }
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
h1,h2,h3 { font-family:'IBM Plex Mono',monospace; color:#e6edf3; }
.stMetric label { color:#8b949e !important; font-size:0.72rem !important;
                  letter-spacing:0.08em; text-transform:uppercase; }
.stMetric [data-testid="stMetricValue"] { color:#58a6ff !important;
    font-family:'IBM Plex Mono'; font-size:1.6rem; }
.badge-high   { background:#1a3a2a; color:#3fb950; border:1px solid #2ea043;
    padding:2px 8px; border-radius:3px; font-size:0.72rem; font-family:'IBM Plex Mono'; }
.badge-medium { background:#2d2a1a; color:#d29922; border:1px solid #9e6a03;
    padding:2px 8px; border-radius:3px; font-size:0.72rem; font-family:'IBM Plex Mono'; }
.badge-low    { background:#3a1a1a; color:#f85149; border:1px solid #da3633;
    padding:2px 8px; border-radius:3px; font-size:0.72rem; font-family:'IBM Plex Mono'; }
.badge-type   { background:#1a1f3a; color:#79c0ff; border:1px solid #388bfd;
    padding:2px 8px; border-radius:3px; font-size:0.72rem; font-family:'IBM Plex Mono'; }
.badge-verify { background:#3a1a2d; color:#f778ba; border:1px solid #db61a2;
    padding:2px 8px; border-radius:3px; font-size:0.72rem; font-family:'IBM Plex Mono'; }
.msg-card { background:#161b22; border:1px solid #21262d;
    border-left:3px solid #388bfd; border-radius:6px;
    padding:14px 16px; margin-bottom:10px; }
.msg-card-high   { border-left-color:#3fb950; }
.msg-card-medium { border-left-color:#d29922; }
.msg-card-low    { border-left-color:#f85149; }
.msg-meta { font-family:'IBM Plex Mono'; font-size:0.72rem; color:#8b949e; margin-bottom:6px; }
.msg-note { background:#0d1117; border:1px solid #21262d; border-radius:4px;
    padding:8px 10px; margin-top:8px; font-size:0.84rem; color:#e6edf3; line-height:1.6; }
.msg-text { font-size:0.83rem; color:#8b949e; margin-top:6px; line-height:1.5;
    border-top:1px solid #21262d; padding-top:8px; }
.score-bar { font-family:'IBM Plex Mono'; font-size:0.72rem; color:#58a6ff; margin-left:10px; }
.action-flag { background:#1a2a1a; border:1px solid #2ea043; border-radius:3px;
    padding:3px 8px; font-size:0.75rem; color:#3fb950; margin:2px; display:inline-block; }
.section-header { font-family:'IBM Plex Mono'; font-size:0.72rem; color:#8b949e;
    letter-spacing:0.12em; text-transform:uppercase;
    border-bottom:1px solid #21262d; padding-bottom:6px; margin-bottom:14px; }
/* Fix Streamlit default white backgrounds in selects/inputs */
.stSelectbox > div > div { background-color:#161b22 !important; color:#c9d1d9 !important; }
div[data-baseweb="select"] { background-color:#161b22 !important; }
</style>
""", unsafe_allow_html=True)

# ── S3 loader ─────────────────────────────────────────────────────────────────
def _s3():
    try:
        creds = st.secrets["aws"]
        return boto3.client("s3", region_name=creds["AWS_DEFAULT_REGION"],
                            aws_access_key_id=creds["AWS_ACCESS_KEY_ID"],
                            aws_secret_access_key=creds["AWS_SECRET_ACCESS_KEY"])
    except Exception:
        return boto3.client("s3", region_name="us-east-1")

def _bucket():
    try:
        return st.secrets["aws"]["S3_BUCKET"]
    except Exception:
        return "osint-monitor-data"

@st.cache_data(ttl=300)
def load_table(name):
    try:
        obj = _s3().get_object(Bucket=_bucket(), Key=f"tables/{name}.parquet")
        return pd.read_parquet(io.BytesIO(obj["Body"].read()))
    except Exception as e:
        if "NoSuchKey" not in str(e):
            st.warning(f"Could not load {name}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def load_manifest():
    try:
        obj = _s3().get_object(Bucket=_bucket(), Key="manifest.json")
        return json.loads(obj["Body"].read())
    except Exception:
        return {"last_sync": "unknown", "total_rows": 0}

@st.cache_data(ttl=300)
def load_all():
    return {
        "messages":        load_table("messages"),
        "classifications": load_table("classifications"),
        "entities":        load_table("entities"),
        "crypto":          load_table("crypto_addresses"),
        "channel_runs":    load_table("channel_runs"),
    }

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛰 OSINT Platform")
    st.markdown("---")
    page = st.radio("Navigation", [
        "📡 Intelligence Feed",
        "🕸 Network Graph",
        "🗺 Geographic Map",
        "📋 Briefing Generator"
    ], label_visibility="collapsed")
    st.markdown("---")
    manifest = load_manifest()
    last_sync = manifest.get("last_sync", "unknown")
    if last_sync != "unknown":
        last_sync = last_sync[:16].replace("T", " ")
    st.markdown("**Last sync**")
    st.code(f"{last_sync} UTC", language=None)
    st.markdown("**Total records**")
    st.code(f"{manifest.get('total_rows', 0):,}", language=None)
    st.markdown("---")
    if st.button("↻  Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

data = load_all()
msgs  = data["messages"]
clsf  = data["classifications"]
ents  = data["entities"]

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — INTELLIGENCE FEED
# ══════════════════════════════════════════════════════════════════════════════
if page == "📡 Intelligence Feed":
    st.markdown("<div class='section-header'>Intelligence Feed</div>", unsafe_allow_html=True)

    if msgs.empty:
        st.info("No messages loaded. Run Module 1 to collect data.")
        st.stop()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        profiles = ["All"] + sorted(msgs["profile"].dropna().unique().tolist())
        pf = st.selectbox("Profile", profiles)
    with col2:
        tf = st.selectbox("Credibility", ["All", "high", "medium", "low"])
    with col3:
        if not clsf.empty and "primary_typology" in clsf.columns:
            typs = ["All"] + sorted(clsf["primary_typology"].dropna().unique().tolist())
        else:
            typs = ["All"]
        tt = st.selectbox("Typology", typs)
    with col4:
        vf = st.selectbox("Show", ["Priority + AI flagged", "All messages", "Verification queue"])

    # Merge
    if not clsf.empty:
        merged = msgs.merge(
            clsf[["message_id","channel","primary_typology","secondary_typology",
                  "composite_credibility","credibility_tier","requires_verification",
                  "typology_rationale","actionable_flags",
                  "source_reliability","content_coherence","corroboration","manipulation_risk"]],
            on=["message_id","channel"], how="left"
        )
    else:
        merged = msgs.copy()
        for c in ["primary_typology","credibility_tier","composite_credibility",
                  "requires_verification","typology_rationale","actionable_flags"]:
            merged[c] = None

    if vf == "Priority + AI flagged":
        merged = merged[(merged.get("priority_flag", pd.Series(dtype=int)).fillna(0)==1) |
                        (merged.get("ai_flagged", pd.Series(dtype=int)).fillna(0)==1)]
    elif vf == "Verification queue":
        merged = merged[merged.get("requires_verification", pd.Series(dtype=int)).fillna(0)==1]

    if pf != "All": merged = merged[merged["profile"]==pf]
    if tf != "All" and "credibility_tier" in merged.columns:
        merged = merged[merged["credibility_tier"]==tf]
    if tt != "All" and "primary_typology" in merged.columns:
        merged = merged[merged["primary_typology"]==tt]

    if "composite_credibility" in merged.columns:
        merged = merged.sort_values(["composite_credibility","timestamp"],
                                    ascending=[False,False], na_position="last")
    else:
        merged = merged.sort_values("timestamp", ascending=False)

    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("Shown", len(merged))
    m2.metric("AI flagged", int(merged["ai_flagged"].fillna(0).sum()) if "ai_flagged" in merged.columns else 0)
    m3.metric("High credibility", int((merged["credibility_tier"]=="high").sum()) if "credibility_tier" in merged.columns else 0)
    m4.metric("Needs verification", int(merged.get("requires_verification", pd.Series(dtype=int)).fillna(0).sum()))
    m5.metric("Typologies", int(merged["primary_typology"].nunique()) if "primary_typology" in merged.columns else 0)

    st.markdown("---")

    for _, row in merged.head(50).iterrows():
        tier     = str(row.get("credibility_tier") or "unknown")
        score    = row.get("composite_credibility")
        typology = str(row.get("primary_typology") or "")
        sec_type = str(row.get("secondary_typology") or "")
        note     = str(row.get("ai_analyst_note") or "")
        rationale= str(row.get("typology_rationale") or "")
        flags_raw= str(row.get("actionable_flags") or "[]")
        preview  = str(row.get("translated_text") or "")[:280]
        timestamp= str(row.get("timestamp") or "")[:16]
        channel  = str(row.get("channel") or "")
        keyword  = str(row.get("priority_keyword") or "–")
        ai_flag  = row.get("ai_flagged", 0)
        verify   = row.get("requires_verification", 0)
        src  = row.get("source_reliability","–")
        coh  = row.get("content_coherence","–")
        corr = row.get("corroboration","–")
        man  = row.get("manipulation_risk","–")

        try:
            flags = json.loads(flags_raw) if flags_raw not in ("[]","nan","") else []
        except Exception:
            flags = []

        score_str = f"{float(score):.2f}" if score is not None and str(score) != "nan" else "–"
        card_cls = f"msg-card msg-card-{tier if tier in ('high','medium','low') else 'unknown'}"

        badges = ""
        if tier in ("high","medium","low"):
            badges += f"<span class='badge-{tier}'>{tier.upper()}</span> "
        if typology and typology != "nan":
            badges += f"<span class='badge-type'>{typology}</span> "
        if sec_type and sec_type not in ("nan","None",""):
            badges += f"<span class='badge-type'>{sec_type}</span> "
        if verify:
            badges += "<span class='badge-verify'>⚠ VERIFY</span> "
        if ai_flag:
            badges += "<span class='badge-high'>✓ AI FLAGGED</span> "

        html = f"""<div class='{card_cls}'>
<div class='msg-meta'>@{channel} &nbsp;·&nbsp; {timestamp} &nbsp;·&nbsp; keyword: {keyword} &nbsp;·&nbsp; score: {score_str}
<span class='score-bar'>src:{src} coh:{coh} corr:{corr} manip:{man}</span></div>
<div style='margin:4px 0'>{badges}</div>"""
        if note and note not in ("nan","None","") and not note.startswith("triage error"):
            html += f"<div class='msg-note'>🔍 {note[:300]}</div>"
        if rationale and rationale not in ("nan","None",""):
            html += f"<div class='msg-note' style='color:#8b949e'>📋 {rationale[:200]}</div>"
        if flags:
            flag_html = "".join(f"<span class='action-flag'>→ {f}</span>" for f in flags[:3])
            html += f"<div style='margin-top:6px'>{flag_html}</div>"
        if preview:
            html += f"<div class='msg-text'>{preview}...</div>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — NETWORK GRAPH
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🕸 Network Graph":
    from pyvis.network import Network
    import tempfile, os

    st.markdown("<div class='section-header'>Entity Network Graph</div>", unsafe_allow_html=True)

    if ents.empty:
        st.info("No entity data yet. Run Module 1 to extract entities.")
        st.stop()

    col1, col2, col3 = st.columns(3)
    with col1:
        profiles = ["All"] + sorted(ents["profile"].dropna().unique().tolist())
        pf = st.selectbox("Profile", profiles)
    with col2:
        etypes = ["All"] + sorted(ents["entity_type"].dropna().unique().tolist())
        ef = st.selectbox("Entity type", etypes)
    with col3:
        min_m = st.slider("Min mentions", 1, 10, 2)

    e = ents.copy()
    if pf != "All": e = e[e["profile"]==pf]
    if ef != "All": e = e[e["entity_type"]==ef]

    counts = e.groupby(["entity_text","entity_type"]).size().reset_index(name="mentions")
    counts = counts[counts["mentions"] >= min_m]

    if counts.empty:
        st.warning("No entities meet criteria. Lower the min mentions slider.")
        st.stop()

    msg_ents = e.merge(counts[["entity_text"]], on="entity_text").groupby(
        ["message_id","channel"])["entity_text"].apply(list).reset_index()

    edge_counts = {}
    for _, row in msg_ents.iterrows():
        el = row["entity_text"]
        for i in range(len(el)):
            for j in range(i+1, len(el)):
                if el[i] != el[j]:
                    key = tuple(sorted([el[i], el[j]]))
                    edge_counts[key] = edge_counts.get(key, 0) + 1

    ECOL = {"PERSON":"#f0883e","ORG":"#58a6ff","GPE":"#3fb950",
            "LOC":"#bc8cff","NORP":"#d29922","FAC":"#ff7b72","EVENT":"#f778ba"}

    net = Network(height="600px", width="100%", bgcolor="#0d1117",
                  font_color="#c9d1d9", directed=False)
    net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=120)

    count_map = dict(zip(counts["entity_text"], counts["mentions"]))
    type_map  = dict(zip(counts["entity_text"], counts["entity_type"]))

    for _, row in counts.iterrows():
        color = ECOL.get(row["entity_type"], "#8b949e")
        size  = min(8 + row["mentions"] * 3, 40)
        net.add_node(row["entity_text"], label=row["entity_text"],
                     title=f"{row['entity_type']}: {row['mentions']} mentions",
                     color=color, size=size,
                     font={"size": max(10,min(14, 8+row["mentions"])), "color":"#c9d1d9"})

    for (a,b), w in edge_counts.items():
        if a in count_map and b in count_map:
            net.add_edge(a, b, value=w, title=f"Co-occur: {w}x",
                         color={"color":"#30363d","highlight":"#58a6ff"})

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
        tmp = f.name
    net.save_graph(tmp)
    with open(tmp, "r") as f:
        html = f.read()
    os.unlink(tmp)
    html = html.replace("background-color: #ffffff","background-color: #0d1117")
    html = html.replace("background-color: white","background-color: #0d1117")
    st.components.v1.html(html, height=620)

    st.markdown("---")
    st.markdown("<div class='section-header'>Top entities</div>", unsafe_allow_html=True)
    st.dataframe(counts.sort_values("mentions", ascending=False).head(20).rename(
        columns={"entity_text":"Entity","entity_type":"Type","mentions":"Mentions"}),
        use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — GEOGRAPHIC MAP
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🗺 Geographic Map":
    import folium
    from streamlit_folium import st_folium

    st.markdown("<div class='section-header'>Geographic Intelligence Map</div>", unsafe_allow_html=True)

    COORDS = {
        "General Santos":(6.1164,125.1716),"Sarangani":(5.923,124.996),
        "Mindanao":(7.5,125.0),"Davao":(7.1907,125.4553),
        "Bunia":(1.5596,30.246),"Ituri":(1.8,30.0),"North Kivu":(-1.0,29.0),
        "Myawaddy":(16.683,98.5),"Mae Sot":(16.717,98.567),"Chiang Mai":(18.788,98.985),
        "Myanmar":(19.745,96.13),"Singapore":(1.352,103.819),
        "Thailand":(15.87,100.993),"Philippines":(12.88,121.774),
        "Israel":(31.046,34.852),"Gaza":(31.354,34.309),"Lebanon":(33.854,35.862),
        "Ukraine":(48.379,31.166),"Iran":(32.427,53.688),"Yemen":(15.552,48.516),
        "DRC":(-4.038,21.759),"Congo":(-4.038,21.759),"Uganda":(1.373,32.29),
        "China":(35.861,104.195),"India":(20.594,78.963),"Russia":(61.524,105.318),
        "Gaza Strip":(31.354,34.309),"Guizhou":(26.843,106.838),
        "Spain":(40.463,-3.749),"Valencia":(39.470,-0.376),
    }
    TCOL = {
        "Arms Dealing":"red","Sanctions Evasion":"orange",
        "Scam Compound Operations":"orange","Human Trafficking & Smuggling":"darkred",
        "Forced Labour":"darkred","Cyber-enabled Fraud":"cadetblue",
        "Money Laundering":"purple","Crypto Laundering":"purple",
        "Terrorist Financing":"darkpurple","State Actor / Military Activity":"darkblue",
        "Natural Disaster":"green","Humanitarian Event":"lightgreen",
        "Public Health Event":"blue","Corruption":"pink",
        "Disinformation":"gray","Other / Unclassified":"lightgray",
    }

    if ents.empty or clsf.empty:
        st.info("No location data yet. Run Modules 1 and 2 to populate.")
        st.stop()

    loc_ents = ents[ents["entity_type"].isin(["GPE","LOC"])].copy()

    classified_msgs = clsf.merge(
        msgs[["message_id","channel","timestamp","translated_text","ai_analyst_note"]],
        on=["message_id","channel"], how="left"
    )

    loc_data = loc_ents.merge(
        classified_msgs[["message_id","channel","primary_typology","credibility_tier",
                          "composite_credibility","requires_verification",
                          "timestamp","ai_analyst_note","translated_text"]],
        on=["message_id","channel"], how="inner"
    )

    col1, col2 = st.columns(2)
    with col1:
        typs = ["All"] + sorted(loc_data["primary_typology"].dropna().unique().tolist())
        tt = st.selectbox("Typology", typs)
    with col2:
        tf = st.selectbox("Credibility", ["All","high","medium","low"])

    if tt != "All": loc_data = loc_data[loc_data["primary_typology"]==tt]
    if tf != "All": loc_data = loc_data[loc_data["credibility_tier"]==tf]

    m = folium.Map(location=[20,90], zoom_start=3, tiles="CartoDB dark_matter")
    placed = set()
    count  = 0

    for _, row in loc_data.iterrows():
        name   = row["entity_text"]
        coords = COORDS.get(name)
        if not coords: continue
        typo   = str(row.get("primary_typology") or "Other / Unclassified")
        tier   = str(row.get("credibility_tier") or "low")
        score  = row.get("composite_credibility")
        note   = str(row.get("ai_analyst_note") or "")
        ts     = str(row.get("timestamp") or "")[:10]
        score_str = f"{float(score):.2f}" if score is not None and str(score) != "nan" else "–"

        key = (name, typo)
        if key in placed: continue
        placed.add(key)

        color = TCOL.get(typo, "gray")
        popup_html = (f"<div style='font-family:monospace;font-size:12px'>"
                      f"<b>{name}</b><br><span style='color:#f0883e'>{typo}</span><br>"
                      f"{ts} | score: {score_str}"
                      + (f"<br><i>{note[:150]}</i>" if note and note != "nan" else "")
                      + "</div>")

        folium.CircleMarker(
            location=coords,
            radius=9 if tier=="high" else 5,
            color=color, fill=True, fill_color=color,
            fill_opacity=0.85 if tier=="high" else 0.5,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{name} — {typo}"
        ).add_to(m)
        count += 1

    st.metric("Locations plotted", count)
    st_folium(m, width=1200, height=550, returned_objects=[])

    st.markdown("---")
    st.markdown("<div class='section-header'>Location summary</div>", unsafe_allow_html=True)
    loc_summary = (loc_data.groupby(["entity_text","primary_typology","credibility_tier"])
                   .size().reset_index(name="signals")
                   .sort_values("signals", ascending=False).head(20))
    st.dataframe(loc_summary.rename(columns={
        "entity_text":"Location","primary_typology":"Typology",
        "credibility_tier":"Credibility","signals":"Signals"}),
        use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — BRIEFING GENERATOR
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Briefing Generator":
    st.markdown("<div class='section-header'>Intelligence Briefing Generator</div>", unsafe_allow_html=True)

    if clsf.empty:
        st.info("No classified data yet. Run Module 2 first.")
        st.stop()

    col1, col2, col3 = st.columns(3)
    with col1:
        profiles = ["All"] + sorted(clsf["profile"].dropna().unique().tolist())
        pf = st.selectbox("Profile", profiles)
    with col2:
        typs = ["All"] + sorted(clsf["primary_typology"].dropna().unique().tolist())
        tt = st.selectbox("Typology", typs)
    with col3:
        tier_sel = st.selectbox("Min credibility", ["high only","high + medium","all"])

    # Merge classifications with message text
    merged = clsf.merge(
        msgs[["message_id","channel","translated_text","ai_analyst_note","timestamp"]],
        on=["message_id","channel"], how="left"
    )

    if pf  != "All": merged = merged[merged["profile"]==pf]
    if tt  != "All": merged = merged[merged["primary_typology"]==tt]
    if tier_sel == "high only":
        merged = merged[merged["credibility_tier"]=="high"]
    elif tier_sel == "high + medium":
        merged = merged[merged["credibility_tier"].isin(["high","medium"])]

    merged = merged.sort_values("composite_credibility", ascending=False)
    st.metric("Messages in scope", len(merged))

    if merged.empty:
        st.warning("No messages match these filters. Try lowering the credibility filter.")
        st.stop()

    st.markdown("**Messages included:**")
    for _, row in merged.head(8).iterrows():
        score = row.get("composite_credibility")
        tier  = str(row.get("credibility_tier") or "–")
        typo  = str(row.get("primary_typology") or "–")
        ts    = str(row.get("timestamp") or "")[:16]
        ch    = str(row.get("channel") or "")
        score_str = f"{float(score):.2f}" if score is not None and str(score) != "nan" else "–"
        badge_col = {"high":"#3fb950","medium":"#d29922","low":"#f85149"}.get(tier,"#8b949e")
        st.markdown(
            f"- `{ts}` **@{ch}** — {typo} "
            f"<span style='color:{badge_col};font-family:IBM Plex Mono;font-size:0.8rem'>[{tier}]</span> "
            f"score: {score_str}",
            unsafe_allow_html=True
        )

    st.markdown("---")

    if st.button("Generate Intelligence Brief", type="primary", use_container_width=True):
        with st.spinner("Synthesising brief..."):
            findings = []
            for _, row in merged.head(10).iterrows():
                text  = str(row.get("translated_text") or "")[:250]
                note  = str(row.get("ai_analyst_note") or "")
                typo  = str(row.get("primary_typology") or "")
                score = row.get("composite_credibility")
                flags_raw = str(row.get("actionable_flags") or "[]")
                score_str = f"{float(score):.2f}" if score is not None and str(score) != "nan" else "–"
                try:
                    flags = json.loads(flags_raw) if flags_raw not in ("[]","nan","") else []
                except Exception:
                    flags = []
                content = note if (note and note not in ("nan","None","")) else text
                findings.append(
                    f"- [{typo} | score:{score_str}] {content[:200]}"
                    + (f" | Actions: {'; '.join(flags[:2])}" if flags else "")
                )

            findings_text = "\n".join(findings)
            today = datetime.now().strftime("%d %B %Y")

            prompt = f"""You are a senior analyst at a UN transnational crime and humanitarian research hub.
Based on the following intelligence findings from open-source monitoring, produce a structured analytical briefing.

Date: {today}
Profile: {pf} | Typology: {tt} | Credibility: {tier_sel}

FINDINGS:
{findings_text}

Write the briefing with these exact sections:
1. EXECUTIVE SUMMARY (2-3 sentences, most critical finding first)
2. KEY FINDINGS (bullet points with entity, location, activity, confidence)
3. ENTITY ANALYSIS (named actors, organisations, locations of concern)
4. EMERGING PATTERNS (trends, connections between findings)
5. RECOMMENDED ACTIONS (specific investigative or policy follow-up steps)
6. VERIFICATION REQUIREMENTS (what needs independent confirmation before acting)

Write in clear professional analytical prose. Be specific with names, places, and amounts where available."""

            client = boto3.client("bedrock-runtime", region_name="us-east-1")
            body   = json.dumps({
                "messages": [{"role":"user","content":[{"text":prompt}]}],
                "inferenceConfig": {"maxTokens": 1500}
            })
            resp  = client.invoke_model(modelId="amazon.nova-lite-v1:0", body=body,
                                        contentType="application/json", accept="application/json")
            brief = json.loads(resp["body"].read())["output"]["message"]["content"][0]["text"]

        st.markdown("---")
        st.markdown("### Generated Intelligence Brief")
        st.markdown(
            f"<div style='background:#161b22;border:1px solid #21262d;"
            f"border-radius:6px;padding:20px;line-height:1.7'>{brief}</div>",
            unsafe_allow_html=True
        )
        st.download_button("⬇ Download brief", data=brief,
                           file_name=f"brief_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                           mime="text/plain", use_container_width=True)
