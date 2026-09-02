import streamlit as st
import pandas as pd
from pathlib import Path
from inventory_ops import render_inventory_tab, init_inventory, total_planning_inventory

st.set_page_config(page_title="MobiMart Optimizer", page_icon="📱", layout="wide")

DASHBOARD_DIR=Path(__file__).resolve().parent
PROJECT_ROOT=DASHBOARD_DIR.parent
DATA_DIR=PROJECT_ROOT/"data"

def load(name, search_dirs=None):
    """Robust CSV loader: tries each candidate directory in order and
    returns the first match. Paths are all resolved relative to this file
    (never hardcoded), so the dashboard works after the ZIP is extracted
    anywhere, on any machine. Returns an empty DataFrame (never fabricated
    data) if the file isn't found in any candidate directory."""
    for d in (search_dirs or (DATA_DIR, DASHBOARD_DIR)):
        p = d/name
        if p.exists():
            return pd.read_csv(p)
    return pd.DataFrame()

# --- Final-output filename mapping ------------------------------------------
# The project has multiple analytical iterations per stage (e.g. Phase 4A ->
# 4B, Phase 5A -> 5B/5C). Each constant below points at the FINAL file for
# that stage, chosen by cross-checking docs/PHASE_4B_README.md +
# docs/PHASE_4C_README.md (4B is the "MobiMart optimizer" that 4C benchmarks
# against the naive baseline), docs/PHASE_5B_README.md (full 60-product
# lifecycle+markdown detail, a superset of eol_candidates.csv), and
# docs/PHASE_5C_README.md (25 actionable transfer lines, matching its README).
ALLOCATION_FILE = "phase4b_allocation.csv"
EOL_MARKDOWN_FILE = "phase5b_transition_markdown.csv"
TRANSFER_FILE = "phase5c_transfer_recommendations.csv"

scenario=load("scenario_comparison.csv")          # already working; lives alongside app.py
eol=load(EOL_MARKDOWN_FILE)
trans=load(TRANSFER_FILE)
alloc=load(ALLOCATION_FILE)
profiles=load("store_profiles.csv")
forecast=load("demand_forecasts.csv")
products=load("products.csv")
stores=load("stores.csv")  # needed by the new Inventory & Orders tab

st.title("📱 MobiMart Inventory & Allocation Optimizer")
st.caption("Decision-support dashboard • Forecast → Allocation → EOL → Markdown → Transfer → Simulation")

# KPI row
c1,c2,c3,c4=st.columns(4)
if not scenario.empty:
    normal=scenario[scenario.scenario.eq("normal")].iloc[0]
    festive=scenario[scenario.scenario.eq("festive")].iloc[0]
    c1.metric("Normal service level",f"{normal.avg_service_level_pct:.2f}%")
    c2.metric("Festive service level",f"{festive.avg_service_level_pct:.2f}%")
    c3.metric("Normal revenue",f"₹{normal.avg_revenue/1e7:.2f} Cr")
    c4.metric("Optimizer vs baseline",f"{normal.optimizer_revenue_lift_pct:.2f}%")
else:
    c1.metric("Normal service level","—"); c2.metric("Festive service level","—")
    c3.metric("Normal revenue","—"); c4.metric("Optimizer vs baseline","—")

# Second KPI row: chain-wide planning/operational snapshot, built only from
# data the project already computed (no new/invented figures).
init_inventory(alloc)  # idempotent; also called inside the Inventory & Orders tab
d1,d2,d3,d4,d5,d6=st.columns(6)
d1.metric("Planning inventory",f"{total_planning_inventory():,} units")
d2.metric("Products",f"{len(products):,}" if not products.empty else "—")
d3.metric("Stores",f"{len(stores):,}" if not stores.empty else "—")
d4.metric("EOL recommendations",f"{int((eol.lifecycle_status=='EOL_RECOMMEND').sum()):,}" if not eol.empty else "—")
d5.metric("Actionable transfers",f"{len(trans[trans.recommended_transfer_units>0]):,}" if not trans.empty else "—")
d6.metric("Allocated units",f"{int(alloc.allocated_units.sum()):,}" if not alloc.empty else "—")

st.divider()

tab_inv,tab1,tab2,tab3,tab4=st.tabs(["🧾 Inventory & Orders","📊 Simulation","📦 Allocation","🔴 EOL & Markdown","🔄 Transfers"])

with tab_inv:
    render_inventory_tab(products, stores, trans, alloc)


with tab1:
    st.subheader("Scenario stress test")
    if not scenario.empty:
        show=st.selectbox("Metric",["avg_service_level_pct","avg_revenue","avg_stockout_units",
                                    "avg_ending_inventory_units"])
        chart=scenario.set_index("scenario")[[show]]
        st.bar_chart(chart)
        st.dataframe(scenario,use_container_width=True,hide_index=True)
        st.info("The simulation is a stress test, not a forecast of realized future sales. Low service levels indicate that the starting allocation is insufficient for the simulated demand horizon.")
    else: st.warning("Simulation data unavailable.")

with tab2:
    st.subheader("Optimized allocation")
    if not alloc.empty:
        if "allocated_units" in alloc:
            st.metric("Allocated units",f"{int(alloc.allocated_units.sum()):,}")
        if "store_id" in alloc:
            store=alloc.groupby("store_id",as_index=False).agg(
                allocated_units=("allocated_units","sum"),
                forecast_units=("forecast_units","sum") if "forecast_units" in alloc else ("allocated_units","sum"))
            st.bar_chart(store.set_index("store_id")["allocated_units"])
        st.dataframe(alloc,use_container_width=True,hide_index=True)
    else: st.warning("Allocation data unavailable.")

with tab3:
    st.subheader("Lifecycle decisions")
    if not eol.empty:
        a,b,c=st.columns(3)
        a.metric("EOL recommendations",int((eol.lifecycle_status=="EOL_RECOMMEND").sum()))
        b.metric("Watch",int((eol.lifecycle_status=="WATCH").sum()))
        c.metric("Active",int((eol.lifecycle_status=="ACTIVE").sum()))
        filt=st.multiselect("Lifecycle status",sorted(eol.lifecycle_status.unique()),
                            default=sorted(eol.lifecycle_status.unique()))
        st.dataframe(eol[eol.lifecycle_status.isin(filt)],use_container_width=True,hide_index=True)
    else: st.warning("EOL data unavailable.")

with tab4:
    st.subheader("Store-level transition recommendations")
    if not trans.empty:
        a,b=st.columns(2)
        a.metric("Actionable transfer lines",len(trans[trans.recommended_transfer_units>0]))
        b.metric("Recommended units",int(trans.recommended_transfer_units.sum()))
        st.dataframe(trans.sort_values("transfer_priority",ascending=False),
                     use_container_width=True,hide_index=True)
    else: st.warning("Transfer data unavailable.")

st.divider()
st.caption("MobiMart prototype • Recommendations are planning outputs; production execution requires actual on-hand inventory, supplier lead times, transfer costs and realized demand.")
