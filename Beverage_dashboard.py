import streamlit as st
import pandas as pd
import plotly.express as px
import os

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Southern Crown Partners Planogram Analysis",
    layout="wide"
)

# =========================
# LOGIN GATE
# =========================
def _check_login():
    import os as _os_login
    _pw = st.secrets.get("DASHBOARD_PASSWORD", None) if hasattr(st, "secrets") else None
    if _pw is None:
        _pw = _os_login.environ.get("DASHBOARD_PASSWORD", "Sharpentheedge")

    if st.session_state.get("_authenticated"):
        return True

    st.markdown("""
    <style>
      .login-wrap {
        max-width: 420px; margin: 80px auto 0; padding: 40px 36px 32px;
        background: #13161e; border-radius: 12px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.40);
        border-top: 4px solid #f0c040;
      }
      .login-title { color:#f0c040; font-size:1.35rem; font-weight:700;
                     letter-spacing:.04em; text-transform:uppercase; margin-bottom:4px; }
      .login-sub   { color:#8892a4; font-size:0.85rem; margin-bottom:24px; }
    </style>
    <div class='login-wrap'>
      <p class='login-title'>📊 Planogram Dashboard</p>
      <p class='login-sub'>Southern Crown Partners · Sign in to continue</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        st.markdown("#### Sign In")
        entered = st.text_input("Password", type="password", placeholder="Enter password")
        submitted = st.form_submit_button("Sign In", use_container_width=True)

    if submitted:
        if entered == _pw:
            st.session_state["_authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")

    st.stop()
    return False

_check_login()

# =========================
# CENTERED LOGO
# =========================
left, center, right = st.columns([2, 4, 2])
with center:
    if os.path.exists("SCP PARTNERS LOGO.png"):
        st.image("SCP PARTNERS LOGO.png", use_container_width=True)
    else:
        st.markdown("## Southern Crown Partners")

st.write("")

# =========================
# PLOTLY THEME
# =========================
COLORS = ["#f0c040", "#4da6ff", "#5cdb95", "#ff6b6b", "#c084fc",
          "#fb923c", "#34d399", "#f472b6", "#38bdf8", "#a3e635"]

def style_fig(fig, height=380):
    fig.update_layout(
        height=height,
        paper_bgcolor="#13161e",
        plot_bgcolor="#0d0f14",
        font=dict(color="#c8ccd8", size=12),
        xaxis=dict(gridcolor="#1f2433", zeroline=False),
        yaxis=dict(gridcolor="#1f2433", zeroline=False),
        margin=dict(l=10, r=10, t=40, b=80),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    return fig

# =========================
# LOAD DATA
# =========================
CHAIN_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSvM__YlxRIkpx2tUaqGAb59imnj0AZ6yp0ei0EhusuHB2Q2ypWEQfSSUtagTKs04-nQBBv6aJn7lm2/pub?gid=1239265988&single=true&output=csv"
PERF_URL  = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRob5VHm3OJmGQlsrnmuRAtOce6Q2d6b7t5gb_QLtQeITg0jFzsEh9kXZI094PPglwh3vpmjSRGb0_D/pub?gid=78966595&single=true&output=csv"

@st.cache_data
def load_perf_data():
    try:
        df = pd.read_csv(CHAIN_URL)
        df.columns = df.columns.str.strip()

        # Plano rows: Division/Linear column holds the chain name
        plano = df[df["Plano/Perf"] == "Plano"].copy()
        if "PlanoID" in plano.columns and "Division/Linear" in plano.columns:
            chain_map = plano.set_index("PlanoID")["Division/Linear"].to_dict()
        else:
            chain_map = {}
        if "PlanoID" in plano.columns and "Store State/Square" in plano.columns:
            state_map = plano.set_index("PlanoID")["Store State/Square"].to_dict()
        else:
            state_map = {}
        if "PlanoID" in plano.columns and "Wholesaler/Unit Movement" in plano.columns:
            whl_code_map = plano.set_index("PlanoID")["Wholesaler/Unit Movement"].to_dict()
        else:
            whl_code_map = {}

        # Perf rows: product-level data
        perf = df[df["Plano/Perf"] == "Perf"].copy()

        perf = perf.rename(columns={
            "Retail Store Number/UPC":        "UPC",
            "Selling LocationType/Name":       "Product Name",
            "Temperature/Assortment Action":   "Wholesaler",
            "Movement period/Capacity":        "Movement",
            "Division/Linear":                 "Linear",
            "Store State/Square":              "Square",
            "Build Team/Cubic":                "Cubic",
            "Wholesaler/Unit Movement":        "Unit Movement",
            "Width/Price":                     "Price",
            "Traffic flow/Unit Cost":          "Unit Cost",
            "Number of Stores/Manufacturer":   "Manufacturer",
            "Number of Segments/Brand":        "Brand",
            "Number of Fixtures/Package":      "Package",
            "Chain POG Field 1/Facings":       "Facings",
            "Chain POG Field 2/Dimensions":    "Dimensions",
            "Chain POG Field 3/WAMP Segment":  "Segment",
            "Chain POG Field 4/Inner Pack":    "Inner Pack",
            "Chain POG Field 5/X":             "X",
            "Chain POG Field 6/Y":             "Y",
        })

        for c in ["Movement", "Linear", "Square", "Cubic",
                  "Facings", "Unit Movement", "Price", "Unit Cost"]:
            perf[c] = pd.to_numeric(perf[c], errors="coerce")

        # Attach Chain from Plano rows and build a clean store label
        if "PlanoID" in perf.columns:
            perf["Chain"] = perf["PlanoID"].map(chain_map)
            perf["State"] = perf["PlanoID"].map(state_map)
            perf["Wholesaler Code"] = perf["PlanoID"].map(whl_code_map)
            perf["_StoreLabel"] = perf["PlanoID"].str.split("|").str[0].str.strip()

        return perf

    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

perf_df = load_perf_data()

# =========================
# SIDEBAR FILTERS
# =========================
st.sidebar.markdown("## 🔍 Filters")

# --- Chain filter (from Division column in Plano rows) ---
chain_opts = ["All"]
if not perf_df.empty and "Chain" in perf_df.columns:
    chain_opts += sorted(perf_df["Chain"].dropna().unique().tolist())
sel_chain = st.sidebar.selectbox("Chain", chain_opts)

# --- Store filter (cascades from Chain selection) ---
store_opts = ["All"]
if not perf_df.empty and "_StoreLabel" in perf_df.columns:
    store_pool = perf_df.copy()
    if sel_chain != "All" and "Chain" in store_pool.columns:
        store_pool = store_pool[store_pool["Chain"] == sel_chain]
    store_opts += sorted(store_pool["_StoreLabel"].dropna().unique().tolist())
sel_store = st.sidebar.selectbox("Store", store_opts)

# --- State filter (cascades from Chain) ---
state_opts = ["All"]
if not perf_df.empty and "State" in perf_df.columns:
    state_pool = perf_df.copy()
    if sel_chain != "All" and "Chain" in state_pool.columns:
        state_pool = state_pool[state_pool["Chain"] == sel_chain]
    state_opts += sorted(state_pool["State"].dropna().unique().tolist())
sel_state = st.sidebar.selectbox("State", state_opts)

# --- Wholesaler filter ---
whl_opts = ["All"]
if not perf_df.empty and "Wholesaler" in perf_df.columns:
    whl_opts += sorted(perf_df["Wholesaler"].dropna().unique().tolist())
sel_wholesaler = st.sidebar.selectbox("Wholesaler", whl_opts)

# --- Segment filter ---
seg_opts = ["All"]
if not perf_df.empty and "Segment" in perf_df.columns:
    seg_opts += sorted(perf_df["Segment"].dropna().unique().tolist())
sel_segment = st.sidebar.selectbox("Segment", seg_opts)

def apply_filters(df):
    d = df.copy()
    if "PlanoID" in d.columns:
        d["_StoreLabel"] = d["PlanoID"].str.split("|").str[0].str.strip()
    if sel_chain != "All" and "Chain" in d.columns:
        d = d[d["Chain"] == sel_chain]
    if sel_store != "All" and "_StoreLabel" in d.columns:
        d = d[d["_StoreLabel"] == sel_store]
    if sel_state != "All" and "State" in d.columns:
        d = d[d["State"] == sel_state]
    if sel_wholesaler != "All" and "Wholesaler" in d.columns:
        d = d[d["Wholesaler"] == sel_wholesaler]
    if sel_segment != "All" and "Segment" in d.columns:
        d = d[d["Segment"] == sel_segment]
    return d

fp = apply_filters(perf_df) if not perf_df.empty else pd.DataFrame()

# =========================
# TABS
# =========================
tab1, tab2, tab3, tab4 = st.tabs([
    "🚚 Distributor Space Report",
    "🍺 Brewer Space Report",
    "📍 POD Report",
    "🏪 Store Report",
])

# ─────────────────────────────────────────────
# TAB 1 — DISTRIBUTOR SPACE REPORT
# ─────────────────────────────────────────────
with tab1:
    st.header("Distributor Space Report")

    if fp.empty:
        st.warning("Could not load data — make sure both CSV files are in the same folder as this script.")
    else:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total SKUs",        len(fp))
        k2.metric("Total Movement",    f"{fp['Movement'].sum():,.0f}")
        k3.metric("Total Linear (in)", f"{fp['Linear'].sum():,.1f}")
        k4.metric("Total Cubic",       f"{fp['Cubic'].sum():,.0f}")

        st.write("")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Cubic Share by Distributor")
            wh = (fp.dropna(subset=["Wholesaler", "Cubic"])
                    .groupby("Wholesaler")["Cubic"].sum()
                    .reset_index().sort_values("Cubic", ascending=False))
            tot = wh["Cubic"].sum()
            wh["Share %"] = (wh["Cubic"] / tot * 100).round(1) if tot > 0 else 0
            fig = px.bar(wh, x="Wholesaler", y="Share %",
                         color="Wholesaler", color_discrete_sequence=COLORS,
                         text="Share %")
            fig.update_traces(texttemplate="%{text:.1f}%",
                              textposition="outside", marker_line_width=0)
            st.plotly_chart(style_fig(fig), use_container_width=True)

        with col2:
            st.subheader("Movement Share by Distributor")
            mv = (fp.dropna(subset=["Wholesaler", "Movement"])
                    .groupby("Wholesaler")["Movement"].sum()
                    .reset_index().sort_values("Movement", ascending=False))
            tot_mv = mv["Movement"].sum()
            mv["Share %"] = (mv["Movement"] / tot_mv * 100).round(1) if tot_mv > 0 else 0
            fig2 = px.bar(mv, x="Wholesaler", y="Share %",
                          color="Wholesaler", color_discrete_sequence=COLORS,
                          text="Share %")
            fig2.update_traces(texttemplate="%{text:.1f}%",
                               textposition="outside", marker_line_width=0)
            st.plotly_chart(style_fig(fig2), use_container_width=True)

        st.subheader("Linear Share by Distributor")
        lin = (fp.dropna(subset=["Wholesaler", "Linear"])
                 .groupby("Wholesaler")["Linear"].sum()
                 .reset_index().sort_values("Linear", ascending=False))
        tot_lin = lin["Linear"].sum()
        lin["Share %"] = (lin["Linear"] / tot_lin * 100).round(1) if tot_lin > 0 else 0
        fig3 = px.bar(lin, x="Wholesaler", y="Share %",
                      color="Wholesaler", color_discrete_sequence=COLORS,
                      text="Share %")
        fig3.update_traces(texttemplate="%{text:.1f}%",
                           textposition="outside", marker_line_width=0)
        st.plotly_chart(style_fig(fig3, height=340), use_container_width=True)

        st.write("")
        st.subheader("Sales by Distributor & Brand")
        col_s1, col_s2 = st.columns(2)

        with col_s1:
            st.subheader("Sales Share by Distributor")
            fp_s = fp.dropna(subset=["Wholesaler", "Price", "Unit Movement"]).copy()
            fp_s["Sales"] = fp_s["Price"] * fp_s["Unit Movement"]
            sd = (fp_s.groupby("Wholesaler")["Sales"].sum()
                      .reset_index().sort_values("Sales", ascending=False))
            tot_sd = sd["Sales"].sum()
            sd["Share %"] = (sd["Sales"] / tot_sd * 100).round(1) if tot_sd > 0 else 0
            fig_sd = px.bar(sd, x="Wholesaler", y="Share %",
                            color="Wholesaler", color_discrete_sequence=COLORS,
                            text="Share %")
            fig_sd.update_traces(texttemplate="%{text:.1f}%",
                                 textposition="outside", marker_line_width=0)
            st.plotly_chart(style_fig(fig_sd), use_container_width=True)

        with col_s2:
            st.subheader("Sales by Brand (Top 15)")
            fp_b = fp.dropna(subset=["Brand", "Price", "Unit Movement"]).copy()
            fp_b["Sales"] = fp_b["Price"] * fp_b["Unit Movement"]
            sb = (fp_b.groupby("Brand")["Sales"].sum()
                      .reset_index().sort_values("Sales", ascending=False).head(15))
            fig_sb = px.bar(sb.sort_values("Sales"),
                            x="Sales", y="Brand", orientation="h",
                            color="Sales",
                            color_continuous_scale=[[0, "#1a2535"], [1, "#f0c040"]],
                            text="Sales")
            fig_sb.update_traces(texttemplate="$%{text:,.2f}",
                                 textposition="outside", marker_line_width=0)
            fig_sb.update_layout(height=460, paper_bgcolor="#13161e",
                                 plot_bgcolor="#0d0f14", font=dict(color="#c8ccd8"),
                                 coloraxis_showscale=False,
                                 margin=dict(l=10, r=10, t=40, b=10),
                                 xaxis=dict(gridcolor="#1f2433"),
                                 yaxis=dict(gridcolor="#1f2433"))
            st.plotly_chart(fig_sb, use_container_width=True)

        st.subheader("SKU Detail (Aggregated Across Stores)")
        group_by = [c for c in ["Brand", "Package", "Segment", "Wholesaler"] if c in fp.columns]
        agg_cols = {c: "sum" for c in ["Movement", "Facings", "Linear", "Cubic"] if c in fp.columns}
        tbl = (fp.dropna(subset=["Brand"])
                 .groupby(group_by, as_index=False)
                 .agg(agg_cols)
                 .sort_values("Movement", ascending=False)
                 .reset_index(drop=True))
        for c in ["Movement", "Facings", "Linear", "Cubic"]:
            if c in tbl.columns:
                tbl[c] = tbl[c].round(1)
        st.dataframe(tbl, use_container_width=True, height=360, hide_index=True)
        st.download_button("⬇ Download CSV",
                           tbl.to_csv(index=False).encode(),
                           "distributor_space.csv", "text/csv")

# ─────────────────────────────────────────────
# TAB 2 — BREWER SPACE REPORT
# ─────────────────────────────────────────────
with tab2:
    st.header("Brewer Space Report")

    if fp.empty:
        st.warning("Could not load data — make sure both CSV files are in the same folder as this script.")
    else:
        # --- Global Top N slider at the top ---
        all_mfr_count = fp.dropna(subset=["Manufacturer","Movement"])["Manufacturer"].nunique() if not fp.empty else 15
        all_brands_count = fp.dropna(subset=["Brand","Movement"])["Brand"].nunique() if not fp.empty else 15
        top_n = st.slider("Number of Brewers / Brands to show", min_value=5, max_value=min(all_brands_count, 50), value=15, step=5)

        st.write("")
        k1, k2, k3 = st.columns(3)
        k1.metric("Brewers / Suppliers",
                  fp["Manufacturer"].nunique() if "Manufacturer" in fp.columns else 0)
        k2.metric("Total Movement", f"{fp['Movement'].sum():,.0f}")
        k3.metric("Total SKUs", len(fp))

        st.write("")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader(f"Cubic Share by Brewer (Top {top_n})")
            mc = (fp.dropna(subset=["Manufacturer", "Cubic"])
                    .groupby("Manufacturer")["Cubic"].sum()
                    .reset_index().sort_values("Cubic", ascending=False).head(top_n))
            tot = mc["Cubic"].sum()
            mc["Share %"] = (mc["Cubic"] / tot * 100).round(1) if tot > 0 else 0
            fig = px.bar(mc, x="Manufacturer", y="Share %",
                         color="Manufacturer", color_discrete_sequence=COLORS,
                         text="Share %")
            fig.update_traces(texttemplate="%{text:.1f}%",
                              textposition="outside", marker_line_width=0)
            st.plotly_chart(style_fig(fig), use_container_width=True)

        with col2:
            st.subheader(f"Movement Share by Brewer (Top {top_n})")
            mm = (fp.dropna(subset=["Manufacturer", "Movement"])
                    .groupby("Manufacturer")["Movement"].sum()
                    .reset_index().sort_values("Movement", ascending=False).head(top_n))
            tot_mm = mm["Movement"].sum()
            mm["Share %"] = (mm["Movement"] / tot_mm * 100).round(1) if tot_mm > 0 else 0
            fig2 = px.bar(mm, x="Manufacturer", y="Share %",
                          color="Manufacturer", color_discrete_sequence=COLORS,
                          text="Share %")
            fig2.update_traces(texttemplate="%{text:.1f}%",
                               textposition="outside", marker_line_width=0)
            st.plotly_chart(style_fig(fig2), use_container_width=True)

        st.subheader(f"Top {top_n} Brands by Movement")
        bm = (fp.dropna(subset=["Brand", "Movement"])
                .groupby(["Brand", "Manufacturer"])["Movement"].sum()
                .reset_index().sort_values("Movement", ascending=False).head(top_n))
        fig3 = px.bar(bm.sort_values("Movement", ascending=True),
                      x="Movement", y="Brand", orientation="h",
                      color="Manufacturer", color_discrete_sequence=COLORS,
                      text="Movement")
        fig3.update_traces(texttemplate="%{text:,.0f}",
                           textposition="outside", marker_line_width=0)
        fig3.update_layout(height=max(400, top_n * 30),
                           paper_bgcolor="#13161e",
                           plot_bgcolor="#0d0f14", font=dict(color="#c8ccd8"),
                           margin=dict(l=10, r=160, t=40, b=10),
                           xaxis=dict(gridcolor="#1f2433"),
                           yaxis=dict(gridcolor="#1f2433", categoryorder="total ascending"),
                           legend=dict(bgcolor="rgba(0,0,0,0)"))
        st.plotly_chart(fig3, use_container_width=True)

        if "Segment" in fp.columns:
            st.subheader(f"Segment Mix — Top {top_n} Brewers")
            top_mfr = (fp.dropna(subset=["Manufacturer","Movement"])
                         .groupby("Manufacturer")["Movement"].sum()
                         .nlargest(top_n).index.tolist())
            sm = (fp[fp["Manufacturer"].isin(top_mfr)]
                    .dropna(subset=["Manufacturer", "Segment", "Movement"])
                    .groupby(["Manufacturer", "Segment"])["Movement"].sum()
                    .reset_index())
            # Calculate share % within each Manufacturer
            sm_total = sm.groupby("Manufacturer")["Movement"].transform("sum")
            sm["Share %"] = (sm["Movement"] / sm_total * 100).round(1)
            fig4 = px.bar(sm, x="Manufacturer", y="Share %",
                          color="Segment", color_discrete_sequence=COLORS,
                          barmode="stack", text="Share %")
            fig4.update_traces(texttemplate="%{text:.1f}%",
                               textposition="inside", marker_line_width=0)
            st.plotly_chart(style_fig(fig4, max(380, top_n * 25)), use_container_width=True)

        st.subheader("Brand Detail Table")
        cols2 = [c for c in ["Manufacturer", "Brand", "Package", "Segment",
                             "Movement", "Facings", "Linear", "Cubic"] if c in fp.columns]
        grp2 = [c for c in ["Manufacturer", "Brand", "Package", "Segment"] if c in fp.columns]
        agg2 = {c: "sum" for c in ["Movement", "Facings", "Linear", "Cubic"] if c in fp.columns}
        tbl2 = (fp.dropna(subset=["Brand"])
                  .groupby(grp2, as_index=False)
                  .agg(agg2)
                  .sort_values("Movement", ascending=False)
                  .reset_index(drop=True))
        st.dataframe(tbl2, use_container_width=True, height=360, hide_index=True)
        st.download_button("⬇ Download CSV",
                           tbl2.to_csv(index=False).encode(),
                           "brewer_space.csv", "text/csv")

# ─────────────────────────────────────────────
# TAB 3 — POD REPORT
# ─────────────────────────────────────────────
with tab3:
    st.header("POD Report")
    st.caption("POD = Points of Distribution — number of unique planograms each brand appears on")

    if fp.empty:
        st.warning("Could not load data — make sure both CSV files are in the same folder as this script.")
    else:
        # --- Product filters ---
        pf1, pf2, pf3, pf4 = st.columns(4)
        with pf1:
            mfr_opts = ["All"] + sorted(fp["Manufacturer"].dropna().unique().tolist())
            pod_mfr = st.selectbox("Filter by Manufacturer", mfr_opts, key="pod_mfr")
        with pf2:
            brand_pool = fp if pod_mfr == "All" else fp[fp["Manufacturer"] == pod_mfr]
            brand_opts = ["All"] + sorted(brand_pool["Brand"].dropna().unique().tolist())
            pod_brand = st.selectbox("Filter by Brand", brand_opts, key="pod_brand")
        with pf3:
            seg_pool = brand_pool if pod_brand == "All" else brand_pool[brand_pool["Brand"] == pod_brand]
            seg_opts2 = ["All"] + sorted(seg_pool["Segment"].dropna().unique().tolist())
            pod_seg_filter = st.selectbox("Filter by Segment", seg_opts2, key="pod_seg")
        with pf4:
            prod_pool = seg_pool if pod_seg_filter == "All" else seg_pool[seg_pool["Segment"] == pod_seg_filter]
            prod_opts = sorted(prod_pool["Product Name"].dropna().unique().tolist())
            pod_products = st.multiselect(
                "Filter by Product Name",
                options=prod_opts,
                placeholder="Type to search & select products...",
                key="pod_product"
            )

        # Apply product filters
        fp_pod = fp.copy()
        if pod_mfr != "All":
            fp_pod = fp_pod[fp_pod["Manufacturer"] == pod_mfr]
        if pod_brand != "All":
            fp_pod = fp_pod[fp_pod["Brand"] == pod_brand]
        if pod_seg_filter != "All":
            fp_pod = fp_pod[fp_pod["Segment"] == pod_seg_filter]
        if pod_products:
            fp_pod = fp_pod[fp_pod["Product Name"].isin(pod_products)]

        st.write("")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("POD % of Total Stores by Chain")
            # Total stores per chain across all products
            total_stores_by_chain = (fp.groupby("Chain")["PlanoID"].nunique()
                                       .reset_index(name="Total Stores"))
            pod = (fp_pod.groupby("Chain")["PlanoID"].nunique()
                     .reset_index(name="POD Count"))
            pod = pod.merge(total_stores_by_chain, on="Chain", how="left")
            pod["POD %"] = (pod["POD Count"] / pod["Total Stores"] * 100).round(1)
            pod = pod.sort_values("POD %", ascending=False)
            fig = px.bar(pod.sort_values("POD %"),
                         x="POD %", y="Chain", orientation="h",
                         color="POD %",
                         color_continuous_scale=[[0, "#1a2535"], [1, "#f0c040"]],
                         text="POD %",
                         hover_data={"POD Count": True, "Total Stores": True})
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside", marker_line_width=0)
            fig.update_layout(height=max(400, len(pod) * 35),
                              paper_bgcolor="#13161e",
                              plot_bgcolor="#0d0f14", font=dict(color="#c8ccd8"),
                              coloraxis_showscale=False,
                              margin=dict(l=10, r=10, t=40, b=10),
                              xaxis=dict(gridcolor="#1f2433", range=[0, 115]),
                              yaxis=dict(gridcolor="#1f2433", categoryorder="total ascending"))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("POD Count by Wholesaler")
            pod_m = (fp_pod.groupby("Wholesaler Code")["PlanoID"].nunique()
                       .reset_index(name="POD Count")
                       .sort_values("POD Count", ascending=False))
            fig2 = px.bar(pod_m.sort_values("POD Count"),
                          x="POD Count", y="Wholesaler Code", orientation="h",
                          color="POD Count",
                          color_continuous_scale=[[0,"#1a2535"],[1,"#4da6ff"]],
                          text="POD Count")
            fig2.update_traces(textposition="outside", marker_line_width=0)
            fig2.update_layout(height=max(400, len(pod_m) * 35),
                               paper_bgcolor="#13161e",
                               plot_bgcolor="#0d0f14", font=dict(color="#c8ccd8"),
                               coloraxis_showscale=False,
                               margin=dict(l=10, r=10, t=40, b=10),
                               xaxis=dict(gridcolor="#1f2433"),
                               yaxis=dict(gridcolor="#1f2433", categoryorder="total ascending"))
            st.plotly_chart(fig2, use_container_width=True)

        # Build store lists
        all_stores = fp[["Chain", "_StoreLabel"]].drop_duplicates()
        stores_with = fp_pod[["_StoreLabel"]].drop_duplicates()
        missing_stores = all_stores[~all_stores["_StoreLabel"].isin(stores_with["_StoreLabel"])]
        missing_stores = missing_stores.sort_values(["Chain", "_StoreLabel"]).reset_index(drop=True)
        missing_stores.columns = ["Chain", "Store"]
        carrying_stores = all_stores[all_stores["_StoreLabel"].isin(stores_with["_StoreLabel"])].copy()
        carrying_stores = carrying_stores.sort_values(["Chain", "_StoreLabel"]).reset_index(drop=True)
        carrying_stores.columns = ["Chain", "Store"]

        st.write("")
        ms_col, cs_col = st.columns(2)

        with ms_col:
            st.markdown("**Stores <span style='color:#ff6b6b'>NOT</span> carrying this product**", unsafe_allow_html=True)
            if missing_stores.empty:
                st.success("All stores carry this product!")
            else:
                missing_chain_opts = ["All"] + sorted(missing_stores["Chain"].dropna().unique().tolist())
                sel_missing_chain = st.selectbox("Filter by Chain", missing_chain_opts, key="missing_chain")
                ms_filtered = missing_stores[missing_stores["Chain"] == sel_missing_chain] if sel_missing_chain != "All" else missing_stores
                st.caption(f"{len(ms_filtered)} stores not carrying this product")
                st.dataframe(ms_filtered, use_container_width=True, height=400, hide_index=True)
                st.download_button("⬇ Download Missing Stores",
                                   ms_filtered.to_csv(index=False).encode(),
                                   "missing_stores.csv", "text/csv")

        with cs_col:
            st.markdown("**Stores <span style='color:#5cdb95'>CARRYING</span> this product**", unsafe_allow_html=True)
            if carrying_stores.empty:
                st.warning("No stores carry this product.")
            else:
                carrying_chain_opts = ["All"] + sorted(carrying_stores["Chain"].dropna().unique().tolist())
                sel_carrying_chain = st.selectbox("Filter by Chain", carrying_chain_opts, key="carrying_chain")
                cs_filtered = carrying_stores[carrying_stores["Chain"] == sel_carrying_chain] if sel_carrying_chain != "All" else carrying_stores
                st.caption(f"{len(cs_filtered)} stores carrying this product")
                st.dataframe(cs_filtered, use_container_width=True, height=400, hide_index=True)
                st.download_button("⬇ Download Carrying Stores",
                                   cs_filtered.to_csv(index=False).encode(),
                                   "carrying_stores.csv", "text/csv")

        if "Segment" in fp_pod.columns:
            st.subheader("POD Count by Segment")
            pod_s = (fp_pod.groupby("Segment")["PlanoID"].nunique()
                       .reset_index(name="POD Count")
                       .sort_values("POD Count", ascending=False))
            fig3 = px.bar(pod_s, x="Segment", y="POD Count",
                          color="Segment", color_discrete_sequence=COLORS,
                          text="POD Count")
            fig3.update_traces(textposition="outside", marker_line_width=0)
            st.plotly_chart(style_fig(fig3, 320), use_container_width=True)

        st.subheader("Full POD Detail Table")
        # Include store and chain so each row is store-specific
        group_cols = [c for c in ["Chain", "_StoreLabel", "Manufacturer", "Brand", "Package", "Segment"]
                      if c in fp_pod.columns]
        pod_full = (fp_pod.groupby(group_cols, dropna=False)
                      .agg(
                          POD_Count=("PlanoID", "nunique"),
                          Movement=("Movement", "sum"),
                          Facings=("Facings", "sum"),
                      )
                      .reset_index()
                      .sort_values(["Chain", "_StoreLabel", "POD_Count"], ascending=[True, True, False])
                      .reset_index(drop=True))
        # Rename for display
        pod_full = pod_full.rename(columns={"_StoreLabel": "Store", "POD_Count": "POD Count"})
        st.dataframe(pod_full, use_container_width=True, height=380)
        st.download_button("⬇ Download CSV",
                           pod_full.to_csv(index=False).encode(),
                           "pod_report.csv", "text/csv")

# ─────────────────────────────────────────────
# TAB 4 — STORE REPORT
# ─────────────────────────────────────────────
with tab4:
    st.header("Store Report")

    if fp.empty:
        st.warning("Could not load data — make sure both CSV files are in the same folder as this script.")
    else:
        store_sum = (fp.groupby("PlanoID")
                       .agg(SKUs     =("Brand",    "count"),
                            Movement =("Movement", "sum"),
                            Linear   =("Linear",   "sum"),
                            Cubic    =("Cubic",    "sum"),
                            Facings  =("Facings",  "sum"),
                            Brands   =("Brand",    "nunique"),
                            Segments =("Segment",  "nunique"))
                       .reset_index()
                       .sort_values("Movement", ascending=False))
        store_sum["Store"] = store_sum["PlanoID"].str.split("|").str[0].str.strip()

        k1, k2, k3 = st.columns(3)
        k1.metric("Total Stores",     len(store_sum))
        k2.metric("Total Movement",   f"{store_sum['Movement'].sum():,.0f}")
        k3.metric("Avg SKUs / Store", f"{store_sum['SKUs'].mean():.0f}")

        st.write("")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Top Stores by Movement")
            fig = px.bar(store_sum.head(15).sort_values("Movement"),
                         x="Movement", y="Store", orientation="h",
                         color="Movement",
                         color_continuous_scale=[[0, "#1a2535"], [1, "#f0c040"]],
                         text="Movement")
            fig.update_traces(texttemplate="%{text:,.0f}",
                              textposition="outside", marker_line_width=0)
            fig.update_layout(height=460, paper_bgcolor="#13161e",
                              plot_bgcolor="#0d0f14", font=dict(color="#c8ccd8"),
                              coloraxis_showscale=False,
                              margin=dict(l=10, r=10, t=40, b=10),
                              xaxis=dict(gridcolor="#1f2433"),
                              yaxis=dict(gridcolor="#1f2433"))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("SKU Count per Store (Top 15)")
            fig2 = px.bar(store_sum.nlargest(15, "SKUs").sort_values("SKUs"),
                          x="SKUs", y="Store", orientation="h",
                          color="SKUs",
                          color_continuous_scale=[[0, "#1a2535"], [1, "#4da6ff"]],
                          text="SKUs")
            fig2.update_traces(textposition="outside", marker_line_width=0)
            fig2.update_layout(height=460, paper_bgcolor="#13161e",
                               plot_bgcolor="#0d0f14", font=dict(color="#c8ccd8"),
                               coloraxis_showscale=False,
                               margin=dict(l=10, r=10, t=40, b=10),
                               xaxis=dict(gridcolor="#1f2433"),
                               yaxis=dict(gridcolor="#1f2433"))
            st.plotly_chart(fig2, use_container_width=True)

        st.write("")
        st.subheader("Segment Mix for a Specific Store")
        store_names = sorted(store_sum["Store"].unique().tolist())
        sel_store = st.selectbox("Select Store", store_names)

        store_perf = fp[fp["PlanoID"].str.startswith(sel_store, na=False)]
        if not store_perf.empty and "Segment" in store_perf.columns:
            seg_s = (store_perf.groupby("Segment")["Movement"].sum()
                               .reset_index().sort_values("Movement", ascending=False))
            fig3 = px.pie(seg_s, names="Segment", values="Movement",
                          hole=0.5, color_discrete_sequence=COLORS)
            fig3.update_layout(height=340, paper_bgcolor="#13161e",
                               font=dict(color="#c8ccd8"),
                               margin=dict(l=10, r=10, t=40, b=10),
                               legend=dict(bgcolor="rgba(0,0,0,0)"))
            st.plotly_chart(fig3, use_container_width=True)

        st.subheader("Store Summary Table")
        disp = [c for c in ["Store", "SKUs", "Brands", "Segments",
                            "Movement", "Facings", "Linear", "Cubic"]
                if c in store_sum.columns]
        st.dataframe(store_sum[disp].reset_index(drop=True),
                     use_container_width=True, height=400)
        st.download_button("⬇ Download CSV",
                           store_sum[disp].to_csv(index=False).encode(),
                           "store_report.csv", "text/csv")