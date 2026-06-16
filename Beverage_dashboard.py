import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    _pw = None
    try:
        _pw = st.secrets.get("DASHBOARD_PASSWORD", None)
    except Exception:
        _pw = None
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

_check_login()

# =========================
# CENTERED LOGO
# =========================
if os.path.exists("SCP PARTNERS LOGO.png"):
    st.image("SCP PARTNERS LOGO.png", width=400)
else:
    st.markdown("## Southern Crown Partners")

st.write("")

# =========================
# PLOTLY THEME
# =========================
COLORS = ["#f0c040", "#4da6ff", "#5cdb95", "#ff6b6b", "#c084fc",
          "#fb923c", "#34d399", "#f472b6", "#38bdf8", "#a3e635"]

NO_ZOOM = {"scrollZoom": False, "displayModeBar": False, "doubleClick": False,
           "staticPlot": False}

def style_fig(fig, height=380):
    fig.update_layout(
        height=height,
        dragmode=False,
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
CHAIN_URL_2026 = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTvVcRVB18SsRTP7BDsu_o2BS1F8KgfoOvQPZrx-2Xp3kJDrnFz1etD3LDV7jYDqaiTEOn41bGSxXeg/pub?output=csv"
PERF_URL  = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRob5VHm3OJmGQlsrnmuRAtOce6Q2d6b7t5gb_QLtQeITg0jFzsEh9kXZI094PPglwh3vpmjSRGb0_D/pub?gid=78966595&single=true&output=csv"
CHAIN_URL_2025 = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT48aBMTv3Gk4EpHx5vz6bRUeOGtlNrx8bNrIkVFJbrUgTIhOBMX6nVDbe88ipodAQHSx9RPKCWvycp/pub?output=csv"

@st.cache_data
def load_perf_data(url):
    try:
        df = pd.read_csv(url)
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
            "Movement period/Capacity":        "Capacity",
            "Division/Linear":                 "Linear",
            "Store State/Square":              "Square",
            "Build Team/Cubic":                "Cubic",
            "Wholesaler/Unit Movement":        "Movement",
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

        for c in ["Movement", "Capacity", "Linear", "Square", "Cubic",
                  "Facings", "Price", "Unit Cost"]:
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

perf_df = load_perf_data(CHAIN_URL_2026)
perf_df_2025 = load_perf_data(CHAIN_URL_2025)

# =========================
# SIDEBAR FILTERS
# =========================
st.sidebar.markdown("## 🔍 Filters")

# --- Chain filter ---
chain_opts = sorted(perf_df["Chain"].dropna().unique().tolist()) if not perf_df.empty and "Chain" in perf_df.columns else []
sel_chain = st.sidebar.multiselect("Chain", chain_opts)

# --- Store filter (cascades from Chain selection) ---
store_pool = perf_df.copy()
if sel_chain and "Chain" in store_pool.columns:
    store_pool = store_pool[store_pool["Chain"].isin(sel_chain)]
store_opts = sorted(store_pool["_StoreLabel"].dropna().unique().tolist()) if not store_pool.empty and "_StoreLabel" in store_pool.columns else []
sel_store = st.sidebar.multiselect("Store", store_opts)

# --- State filter (cascades from Chain) ---
state_pool = perf_df.copy()
if sel_chain and "Chain" in state_pool.columns:
    state_pool = state_pool[state_pool["Chain"].isin(sel_chain)]
state_opts = sorted(state_pool["State"].dropna().unique().tolist()) if not state_pool.empty and "State" in state_pool.columns else []
sel_state = st.sidebar.multiselect("State", state_opts)

# --- Warehouse filter (cascades from State) ---
whl_code_pool = perf_df.copy()
if sel_chain and "Chain" in whl_code_pool.columns:
    whl_code_pool = whl_code_pool[whl_code_pool["Chain"].isin(sel_chain)]
if sel_state and "State" in whl_code_pool.columns:
    whl_code_pool = whl_code_pool[whl_code_pool["State"].isin(sel_state)]
whl_code_opts = sorted(whl_code_pool["Wholesaler Code"].dropna().unique().tolist()) if "Wholesaler Code" in whl_code_pool.columns else []
sel_wholesaler_code = st.sidebar.multiselect("Warehouse", whl_code_opts)

# --- Segment filter ---
seg_opts = sorted(perf_df["Segment"].dropna().unique().tolist()) if not perf_df.empty and "Segment" in perf_df.columns else []
sel_segment = st.sidebar.multiselect("Segment", seg_opts)

def apply_filters(df):
    d = df.copy()
    if "PlanoID" in d.columns:
        d["_StoreLabel"] = d["PlanoID"].str.split("|").str[0].str.strip()
    if sel_chain and "Chain" in d.columns:
        d = d[d["Chain"].isin(sel_chain)]
    if sel_store and "_StoreLabel" in d.columns:
        d = d[d["_StoreLabel"].isin(sel_store)]
    if sel_state and "State" in d.columns:
        d = d[d["State"].isin(sel_state)]
    if sel_wholesaler_code and "Wholesaler Code" in d.columns:
        d = d[d["Wholesaler Code"].isin(sel_wholesaler_code)]
    if sel_segment and "Segment" in d.columns:
        d = d[d["Segment"].isin(sel_segment)]
    return d

fp = apply_filters(perf_df) if not perf_df.empty else pd.DataFrame()
fp_2025 = apply_filters(perf_df_2025) if not perf_df_2025.empty else pd.DataFrame()

# =========================
# TABS
# =========================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Comparison (2025 vs 2026)",
    "🚚 Distributor Space Report",
    "🍺 Brewer Space Report",
    "📍 POD Report",
    "🏪 Store Report",
])

# ─────────────────────────────────────────────
# TAB 1 — DISTRIBUTOR SPACE REPORT
# ─────────────────────────────────────────────
with tab2:
    st.header("Distributor Space Report")

    if fp.empty:
        st.warning("Could not load data — make sure both CSV files are in the same folder as this script.")
    else:
        # Calculate avg Day of Supply = (Capacity / Movement) * Movement Period
        dos_df = fp.dropna(subset=["Movement", "Capacity"]).copy()
        dos_df["DOS"] = (dos_df["Capacity"] / dos_df["Movement"].replace(0, float("nan"))) * 7
        avg_dos = dos_df["DOS"].mean()

        k1, k2, k3, k4, k5, k6 = st.columns(6)
        k1.metric("Store Count",       f"{fp['_StoreLabel'].nunique():,}")
        k2.metric("Total SKUs",        f"{fp['Product Name'].nunique():,}")
        k3.metric("Total Movement",    f"{fp['Movement'].sum():,.0f}")
        k4.metric("Total Cubic",       f"{fp['Cubic'].sum():,.0f}")
        k5.metric("Total Linear (in)", f"{fp['Linear'].sum():,.0f}")
        k6.metric("Avg Day of Supply", f"{avg_dos:,.1f}")

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
            st.plotly_chart(style_fig(fig), use_container_width=True, config=NO_ZOOM)

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
            st.plotly_chart(style_fig(fig2), use_container_width=True, config=NO_ZOOM)

        col_lin, col_sales = st.columns(2)

        with col_lin:
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
            st.plotly_chart(style_fig(fig3, height=380), use_container_width=True, config=NO_ZOOM)

        with col_sales:
            st.subheader("Sales Share by Distributor")
            fp_s = fp.dropna(subset=["Wholesaler", "Price", "Movement"]).copy()
            fp_s["Sales"] = fp_s["Price"] * fp_s["Movement"]
            sd = (fp_s.groupby("Wholesaler")["Sales"].sum()
                      .reset_index().sort_values("Sales", ascending=False))
            tot_sd = sd["Sales"].sum()
            sd["Share %"] = (sd["Sales"] / tot_sd * 100).round(1) if tot_sd > 0 else 0
            fig_sd = px.bar(sd, x="Wholesaler", y="Share %",
                            color="Wholesaler", color_discrete_sequence=COLORS,
                            text="Share %")
            fig_sd.update_traces(texttemplate="%{text:.1f}%",
                                 textposition="outside", marker_line_width=0)
            st.plotly_chart(style_fig(fig_sd, height=380), use_container_width=True, config=NO_ZOOM)

        st.write("")
        st.subheader("Sales by Brand (Top 15)")
        fp_b = fp.dropna(subset=["Brand", "Price", "Movement"]).copy()
        fp_b["Sales"] = fp_b["Price"] * fp_b["Movement"]
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
        st.plotly_chart(fig_sb, use_container_width=True, config=NO_ZOOM)

        # If a specific store is selected show raw SKUs, otherwise aggregate
        if sel_store:
            st.subheader(f"SKU Detail — {sel_store}")
            tbl = fp.dropna(subset=["Brand"]).copy()
            tbl["Day of Supply"] = (tbl["Capacity"] / tbl["Movement"].replace(0, float("nan")) * 7).round(1)
            display_cols = [c for c in ["Brand", "Package", "Segment", "Wholesaler",
                                        "Movement", "Capacity", "Facings", "Linear", "Cubic", "Day of Supply"]
                            if c in tbl.columns]
            tbl = tbl[display_cols].sort_values("Movement", ascending=False).reset_index(drop=True)
        else:
            st.subheader("SKU Detail (Aggregated Across Stores)")
            group_by = [c for c in ["Brand", "Package", "Segment", "Wholesaler"] if c in fp.columns]
            agg_cols = {c: "sum" for c in ["Movement", "Capacity", "Facings", "Linear", "Cubic"] if c in fp.columns}
            tbl = (fp.dropna(subset=["Brand"])
                     .groupby(group_by, as_index=False)
                     .agg(agg_cols)
                     .sort_values("Movement", ascending=False)
                     .reset_index(drop=True))
            tbl["Day of Supply"] = (tbl["Capacity"] / tbl["Movement"].replace(0, float("nan")) * 7).round(1)
            for c in ["Movement", "Facings", "Linear", "Cubic"]:
                if c in tbl.columns:
                    tbl[c] = tbl[c].round(1)
            display_cols = [c for c in ["Brand", "Package", "Segment", "Wholesaler",
                                        "Movement", "Capacity", "Facings", "Linear", "Cubic", "Day of Supply"]
                            if c in tbl.columns]
            tbl = tbl[display_cols]
        st.dataframe(tbl, use_container_width=True, height=360, hide_index=True)
        st.download_button("⬇ Download CSV",
                           tbl.to_csv(index=False).encode(),
                           "distributor_space.csv", "text/csv")

# ─────────────────────────────────────────────
# TAB 2 — BREWER SPACE REPORT
# ─────────────────────────────────────────────
with tab3:
    st.header("Brewer Space Report")

    if fp.empty:
        st.warning("Could not load data — make sure both CSV files are in the same folder as this script.")
    else:
        # --- Global Top N slider at the top ---
        all_mfr_count = fp.dropna(subset=["Manufacturer","Movement"])["Manufacturer"].nunique() if not fp.empty else 15
        all_brands_count = fp.dropna(subset=["Brand","Movement"])["Brand"].nunique() if not fp.empty else 15
        top_n = st.slider("Number of Brewers / Brands to show", min_value=5, max_value=min(all_brands_count, 50), value=15, step=5)

        st.write("")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Store Count",       f"{fp['_StoreLabel'].nunique():,}")
        k2.metric("Brewers / Suppliers", f"{fp['Manufacturer'].nunique():,}" if "Manufacturer" in fp.columns else 0)
        k3.metric("Total Movement",    f"{fp['Movement'].sum():,.0f}")
        k4.metric("Total SKUs",        f"{fp['Product Name'].nunique():,}")

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
            st.plotly_chart(style_fig(fig), use_container_width=True, config=NO_ZOOM)

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
            st.plotly_chart(style_fig(fig2), use_container_width=True, config=NO_ZOOM)

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
        st.plotly_chart(fig3, use_container_width=True, config=NO_ZOOM)

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
            st.plotly_chart(style_fig(fig4, max(380, top_n * 25)), use_container_width=True, config=NO_ZOOM)

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
with tab4:
    st.header("POD Report")
    st.caption("POD = Points of Distribution — number of unique planograms each brand appears on")

    if fp.empty:
        st.warning("Could not load data — make sure both CSV files are in the same folder as this script.")
    else:
        # --- Product filters ---
        pf1, pf2, pf3 = st.columns(3)
        with pf1:
            mfr_opts = sorted(fp["Manufacturer"].dropna().unique().tolist())
            pod_mfr = st.multiselect("Filter by Manufacturer", mfr_opts, key="pod_mfr")
        with pf2:
            brand_pool = fp if not pod_mfr else fp[fp["Manufacturer"].isin(pod_mfr)]
            brand_opts = sorted(brand_pool["Brand"].dropna().unique().tolist())
            pod_brand = st.multiselect("Filter by Brand", brand_opts, key="pod_brand")
        with pf3:
            seg_pool = brand_pool if not pod_brand else brand_pool[brand_pool["Brand"].isin(pod_brand)]
            seg_opts2 = sorted(seg_pool["Segment"].dropna().unique().tolist())
            pod_seg_filter = st.multiselect("Filter by Segment", seg_opts2, key="pod_seg")

        pf4, pf5, pf6 = st.columns(3)
        with pf4:
            pkg_pool = seg_pool if not pod_seg_filter else seg_pool[seg_pool["Segment"].isin(pod_seg_filter)]
            pkg_opts = sorted(pkg_pool["Package"].dropna().unique().tolist())
            pod_package = st.multiselect("Filter by Package Size", pkg_opts, key="pod_package")
        with pf5:
            prod_pool = pkg_pool if not pod_package else pkg_pool[pkg_pool["Package"].isin(pod_package)]
            prod_opts = sorted(prod_pool["Product Name"].dropna().unique().tolist())
            pod_product = st.multiselect("Filter by Product Name", prod_opts, key="pod_product")
        with pf6:
            chain_opts = sorted(fp["Chain"].dropna().unique().tolist()) if "Chain" in fp.columns else []
            pod_chain = st.multiselect("Filter by Chain", chain_opts, key="pod_chain")

        # Apply product filters
        fp_pod = fp.copy()
        if pod_mfr:
            fp_pod = fp_pod[fp_pod["Manufacturer"].isin(pod_mfr)]
        if pod_brand:
            fp_pod = fp_pod[fp_pod["Brand"].isin(pod_brand)]
        if pod_seg_filter:
            fp_pod = fp_pod[fp_pod["Segment"].isin(pod_seg_filter)]
        if pod_package:
            fp_pod = fp_pod[fp_pod["Package"].isin(pod_package)]
        if pod_product:
            fp_pod = fp_pod[fp_pod["Product Name"].isin(pod_product)]
        if pod_chain:
            fp_pod = fp_pod[fp_pod["Chain"].isin(pod_chain)]

        pk1, pk2, pk3 = st.columns(3)
        pk1.metric("Store Count",    f"{fp_pod['_StoreLabel'].nunique():,}")
        pk2.metric("Total SKUs",     f"{fp_pod['Product Name'].nunique():,}")
        pk3.metric("Total Movement", f"{fp_pod['Movement'].sum():,.0f}")

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
            st.plotly_chart(fig, use_container_width=True, config=NO_ZOOM)

        with col2:
            st.subheader("POD Count by Warehouse")
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
            st.plotly_chart(fig2, use_container_width=True, config=NO_ZOOM)

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
            st.plotly_chart(style_fig(fig3, 320), use_container_width=True, config=NO_ZOOM)

        st.subheader("Full POD Detail Table")
        # One row per Store + Product combination
        detail_cols = [c for c in ["Chain", "_StoreLabel", "Wholesaler Code",
                                   "Manufacturer", "Brand", "Package", "Segment",
                                   "Product Name", "Movement", "Capacity", "Facings"]
                       if c in fp_pod.columns]
        pod_full = (fp_pod[detail_cols]
                    .dropna(subset=["Product Name"])
                    .sort_values(["Chain", "_StoreLabel", "Brand", "Product Name"])
                    .reset_index(drop=True))
        pod_full = pod_full.rename(columns={"_StoreLabel": "Store"})
        st.dataframe(pod_full, use_container_width=True, height=450, hide_index=True)
        st.download_button("⬇ Download CSV",
                           pod_full.to_csv(index=False).encode(),
                           "pod_report.csv", "text/csv")

# ─────────────────────────────────────────────
# TAB 4 — STORE REPORT
# ─────────────────────────────────────────────
with tab5:
    st.header("Store Report")

    if fp.empty:
        st.warning("Could not load data — make sure both CSV files are in the same folder as this script.")
    else:
        store_sum = (fp.groupby("PlanoID")
                       .agg(SKUs     =("Product Name",    "nunique"),
                            Movement =("Movement", "sum"),
                            Linear   =("Linear",   "sum"),
                            Cubic    =("Cubic",    "sum"),
                            Facings  =("Facings",  "sum"),
                            Brands   =("Brand",    "nunique"),
                            Segments =("Segment",  "nunique"))
                       .reset_index()
                       .sort_values("Movement", ascending=False))
        store_sum["Store"] = store_sum["PlanoID"].str.split("|").str[0].str.strip()

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Store Count",      f"{fp['_StoreLabel'].nunique():,}")
        k2.metric("Total Movement",   f"{store_sum['Movement'].sum():,.0f}")
        k3.metric("Avg SKUs / Store", f"{store_sum['SKUs'].mean():.0f}")
        k4.metric("Total SKUs",       f"{fp['Product Name'].nunique():,}")

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
            st.plotly_chart(fig, use_container_width=True, config=NO_ZOOM)

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
            st.plotly_chart(fig2, use_container_width=True, config=NO_ZOOM)

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
            st.plotly_chart(fig3, use_container_width=True, config=NO_ZOOM)

        st.subheader("Store Summary Table")
        disp = [c for c in ["Store", "SKUs", "Brands", "Segments",
                            "Movement", "Facings", "Linear", "Cubic"]
                if c in store_sum.columns]
        st.dataframe(store_sum[disp].reset_index(drop=True),
                     use_container_width=True, height=400)
        st.download_button("⬇ Download CSV",
                           store_sum[disp].to_csv(index=False).encode(),
                           "store_report.csv", "text/csv")

# ─────────────────────────────────────────────
# TAB 5 — COMPARISON (2025 vs 2026)
# ─────────────────────────────────────────────
with tab1:
    st.header("Comparison: 2025 vs 2026")

    if fp.empty or fp_2025.empty:
        st.warning("Could not load one or both years of data for comparison.")
    else:
        # --- Same-Store Matching ---
        same_store = st.toggle(
            "Same-store comparison only",
            value=True,
            help="When on, comparison is limited to stores present in BOTH 2025 and 2026 datasets for an apples-to-apples view.",
        )

        common_stores = set(fp_2025["_StoreLabel"].dropna().unique()) & set(fp["_StoreLabel"].dropna().unique())
        if same_store:
            cmp_2025 = fp_2025[fp_2025["_StoreLabel"].isin(common_stores)]
            cmp_2026 = fp[fp["_StoreLabel"].isin(common_stores)]
        else:
            cmp_2025 = fp_2025
            cmp_2026 = fp

        mv_2025 = cmp_2025["Movement"].sum()
        mv_2026 = cmp_2026["Movement"].sum()
        mv_pct = ((mv_2026 - mv_2025) / mv_2025 * 100) if mv_2025 > 0 else 0

        k1, k2, k3, k4, k5, k6 = st.columns(6)
        if same_store:
            k1.metric("Matched Store Count", f"{len(common_stores):,}")
        else:
            k1.metric("Stores (all)", f"{cmp_2025['_StoreLabel'].nunique() + cmp_2026['_StoreLabel'].nunique():,}")
        k2.metric("2025 Stores",         f"{cmp_2025['_StoreLabel'].nunique():,}")
        k3.metric("2026 Stores",         f"{cmp_2026['_StoreLabel'].nunique():,}")
        k4.metric("2025 Total Movement", f"{mv_2025:,.0f}")
        k5.metric("2026 Total Movement", f"{mv_2026:,.0f}")
        k6.metric("Movement % Change",   f"{mv_pct:+.1f}%")

        st.write("")

        def share_compare(container, df25, df26, group_col, value_col, title, top_n=None):
            container.subheader(title)
            d25 = df25.dropna(subset=[group_col, value_col]).copy()
            d26 = df26.dropna(subset=[group_col, value_col]).copy()
            d25[group_col] = d25[group_col].astype(str)
            d26[group_col] = d26[group_col].astype(str)
            s25 = (d25.groupby(group_col)[value_col].sum().reset_index())
            s26 = (d26.groupby(group_col)[value_col].sum().reset_index())
            t25, t26 = s25[value_col].sum(), s26[value_col].sum()
            s25["Share %"] = (s25[value_col] / t25 * 100).round(1) if t25 > 0 else 0
            s26["Share %"] = (s26[value_col] / t26 * 100).round(1) if t26 > 0 else 0

            merged = s25[[group_col, "Share %"]].merge(
                s26[[group_col, "Share %"]], on=group_col, how="outer",
                suffixes=(" 2025", " 2026")
            ).fillna(0)
            merged["Change (pp)"] = (merged["Share % 2026"] - merged["Share % 2025"]).round(1)
            merged = merged.sort_values("Share % 2026", ascending=False)

            view = container.radio(
                "View", ["Share % (2025 vs 2026)", "Change (pp)"],
                horizontal=True, label_visibility="collapsed",
                key=f"view_{title}",
            )

            # Limit chart to top N (by 2026 share); full data still available via download
            if top_n is not None and len(merged) > top_n:
                chart_src = merged.nlargest(top_n, "Share % 2026")
                container.caption(f"Showing top {top_n} by 2026 share. Full list in CSV download.")
            else:
                chart_src = merged

            if view == "Change (pp)":
                chg = chart_src.sort_values("Change (pp)", ascending=False)
                fig = px.bar(chg, x=group_col, y="Change (pp)",
                             color="Change (pp)",
                             color_continuous_scale=[[0, "#e2574c"], [0.5, "#8892a4"], [1, "#3fb950"]],
                             color_continuous_midpoint=0,
                             text="Change (pp)")
                fig.update_traces(texttemplate="%{text:+.1f}", textposition="outside", marker_line_width=0)
                fig.update_layout(coloraxis_showscale=False)
            else:
                plot_df = chart_src.melt(id_vars=group_col,
                                       value_vars=["Share % 2025", "Share % 2026"],
                                       var_name="Year", value_name="Share %")
                fig = px.bar(plot_df, x=group_col, y="Share %", color="Year",
                             barmode="group",
                             color_discrete_map={"Share % 2025": "#4da6ff", "Share % 2026": "#f0c040"},
                             text="Share %")
                fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside", marker_line_width=0)
                # Overlay pp-change line on a secondary axis
                fig.add_trace(go.Scatter(
                    x=chart_src[group_col], y=chart_src["Change (pp)"],
                    mode="lines+markers+text",
                    name="Change (pp)",
                    text=[f"{v:+.1f}" for v in chart_src["Change (pp)"]],
                    textposition="top center",
                    textfont=dict(color="#00e5cc", size=11),
                    line=dict(color="#00e5cc", width=2),
                    marker=dict(color="#00e5cc", size=7),
                    yaxis="y2",
                ))
                fig.update_layout(
                    yaxis2=dict(title="Change (pp)", overlaying="y", side="right",
                                showgrid=False, zeroline=True, zerolinecolor="#3a3f52",
                                tickfont=dict(color="#00e5cc"),
                                title_font=dict(color="#00e5cc")),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                )
            container.plotly_chart(style_fig(fig, height=380).update_xaxes(type="category"), use_container_width=True, config=NO_ZOOM)

            tbl = merged.rename(columns={group_col: title.split(" by ")[-1] if " by " in title else group_col})
            container.download_button(
                "⬇ Download table (CSV)",
                tbl.to_csv(index=False).encode(),
                f"{title.replace(' ', '_').lower()}.csv",
                "text/csv",
                key=f"dl_{title}",
            )

        # Precompute Sales (Price * Movement) for sales-share comparison
        sales_2025 = cmp_2025.copy()
        sales_2026 = cmp_2026.copy()
        for _df in (sales_2025, sales_2026):
            if "Price" in _df.columns and "Movement" in _df.columns:
                _df["Sales"] = _df["Price"] * _df["Movement"]

        col1, col2 = st.columns(2)
        share_compare(col1, cmp_2025, cmp_2026, "Wholesaler", "Cubic", "Cubic Share by Distributor")
        share_compare(col2, cmp_2025, cmp_2026, "Wholesaler", "Movement", "Movement Share by Distributor")

        col3, col4 = st.columns(2)
        share_compare(col3, cmp_2025, cmp_2026, "Wholesaler", "Linear", "Linear Share by Distributor")
        share_compare(col4, sales_2025, sales_2026, "Wholesaler", "Sales", "Sales Share by Distributor")

        col5, col6 = st.columns(2)
        share_compare(col5, cmp_2025, cmp_2026, "Manufacturer", "Movement", "Movement Share by Brewer", top_n=15)
        share_compare(col6, cmp_2025, cmp_2026, "Manufacturer", "Cubic", "Cubic Share by Brewer", top_n=15)

        st.divider()
        st.subheader("POD Change by Brand")

        # Distributor filter (applies to both POD charts below)
        dist_opts = sorted(
            set(cmp_2025["Wholesaler"].dropna().unique())
            | set(cmp_2026["Wholesaler"].dropna().unique())
        )
        sel_dist = st.multiselect(
            "Filter by Distributor", dist_opts, key="pod_brand_dist",
            help="Limits both the Top Gains and Top Losses charts to the selected distributor(s).",
        )

        pod_25 = cmp_2025
        pod_26 = cmp_2026
        if sel_dist:
            pod_25 = pod_25[pod_25["Wholesaler"].isin(sel_dist)]
            pod_26 = pod_26[pod_26["Wholesaler"].isin(sel_dist)]

        key_cols = [c for c in ["Brand", "Package"] if c in pod_26.columns]
        p25 = (pod_25.dropna(subset=key_cols + ["_StoreLabel"])
                     .groupby(key_cols)["_StoreLabel"].nunique()
                     .reset_index(name="POD 2025"))
        p26 = (pod_26.dropna(subset=key_cols + ["_StoreLabel"])
                     .groupby(key_cols)["_StoreLabel"].nunique()
                     .reset_index(name="POD 2026"))
        pod_chg = p25.merge(p26, on=key_cols, how="outer").fillna(0)
        pod_chg["POD 2025"] = pod_chg["POD 2025"].astype(int)
        pod_chg["POD 2026"] = pod_chg["POD 2026"].astype(int)
        pod_chg["Change"] = pod_chg["POD 2026"] - pod_chg["POD 2025"]
        if "Package" in pod_chg.columns:
            pod_chg["Item"] = pod_chg["Brand"].astype(str) + " — " + pod_chg["Package"].astype(str)
        else:
            pod_chg["Item"] = pod_chg["Brand"].astype(str)

        def pod_chart(container, df, title, ascending):
            container.markdown(f"**{title}**")
            if df.empty or (df["Change"] == 0).all():
                container.info("No changes to display.")
                return
            fig = px.bar(df, x="Change", y="Item", orientation="h",
                         color="Change",
                         color_continuous_scale=[[0, "#e2574c"], [0.5, "#8892a4"], [1, "#3fb950"]],
                         color_continuous_midpoint=0,
                         text="Change",
                         hover_data={"POD 2025": True, "POD 2026": True})
            fig.update_traces(texttemplate="%{text:+d}", textposition="outside", marker_line_width=0)
            fig.update_layout(coloraxis_showscale=False,
                              yaxis=dict(categoryorder="total ascending", title=None))
            container.plotly_chart(style_fig(fig, height=440), use_container_width=True, config=NO_ZOOM)

        gains = pod_chg[pod_chg["Change"] > 0].nlargest(15, "Change").sort_values("Change")
        losses = pod_chg[pod_chg["Change"] < 0].nsmallest(15, "Change").sort_values("Change")

        gcol, lcol = st.columns(2)
        pod_chart(gcol, gains, "Top Gains", ascending=True)
        pod_chart(lcol, losses, "Top Losses", ascending=False)

        st.download_button(
            "⬇ Download table (CSV)",
            pod_chg.sort_values("Change", ascending=False).to_csv(index=False).encode(),
            "pod_change_by_brand.csv", "text/csv",
            key="dl_pod_brand",
        )

        st.write("")
        st.subheader("All Items (Aggregated Across Stores)")
        items_26 = (pod_26.dropna(subset=key_cols + ["_StoreLabel"])
                          .groupby(key_cols)["_StoreLabel"].nunique()
                          .reset_index(name="POD Count"))
        items_25 = (pod_25.dropna(subset=key_cols + ["_StoreLabel"])
                          .groupby(key_cols)["_StoreLabel"].nunique()
                          .reset_index(name="POD 2025"))
        pod_items = items_26.merge(items_25, on=key_cols, how="outer").fillna(0)
        pod_items["POD Count"] = pod_items["POD Count"].astype(int)
        pod_items["POD 2025"] = pod_items["POD 2025"].astype(int)
        pod_items["POD Change"] = pod_items["POD Count"] - pod_items["POD 2025"]

        # Attach representative Segment / Wholesaler (most common per Brand+Package, 2026 preferred)
        def _mode(s):
            m = s.dropna().mode()
            return m.iloc[0] if not m.empty else None
        ref_src = pod_26 if not pod_26.empty else pod_25
        for col in ["Segment", "Wholesaler"]:
            if col in ref_src.columns:
                ref = (ref_src.dropna(subset=key_cols)
                              .groupby(key_cols)[col].agg(_mode).reset_index())
                pod_items = pod_items.merge(ref, on=key_cols, how="left")

        ordered = [c for c in ["Brand", "Package", "Segment", "Wholesaler", "POD Count", "POD Change"]
                   if c in pod_items.columns]
        pod_items = (pod_items[ordered]
                     .sort_values("POD Count", ascending=False)
                     .reset_index(drop=True))
        st.dataframe(pod_items, use_container_width=True, height=450, hide_index=True)
        st.download_button(
            "⬇ Download CSV",
            pod_items.to_csv(index=False).encode(),
            "pod_all_items.csv", "text/csv",
            key="dl_pod_items",
        )