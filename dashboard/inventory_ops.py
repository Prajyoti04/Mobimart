"""
inventory_ops.py
-----------------
Operational in-session inventory layer for the MobiMart dashboard
("Inventory & Orders" tab): product lookup, fulfillment checking, manual
stock transfers, and stock receipts.

WHAT "PLANNING INVENTORY" MEANS HERE
--------------------------------------
The MobiMart project (Phases 1-5C) never produced a standalone "current
on-hand inventory by store" dataset:
  - Phase 1's sales_history.csv is 52 weeks of HISTORICAL SALES, not stock.
  - Phase 4B's `available_units` column is a COMPANY-WIDE supply pool per
    model (the same number repeats across all 25 stores for a given
    model_id) -- it is supply available to the allocator, not a per-store
    on-hand count.
  - Phase 4B's `allocated_units` column IS store-specific: it's how many
    units of each model the optimizer actually placed at each store. That
    is the most recent, most granular inventory-like number the project
    has already computed.

This module therefore INITIALIZES a per-store, per-model "PLANNING
INVENTORY" position from Phase 4B's `allocated_units`, and holds it only in
Streamlit's `st.session_state` for the rest of the session. Every label in
this UI deliberately says "planning inventory" -- never "current inventory",
"stock on hand", or "live inventory" -- because this is not a real-time
warehouse/ERP feed. No original CSV is ever written to; transfers and
receipts made here only ever mutate `st.session_state`.
"""

import streamlit as st
import pandas as pd

REQUIRED_ALLOC_COLS = {"store_id", "model_id", "allocated_units"}

PLANNING_INVENTORY_NOTE = (
    "Planning inventory is initialized from Phase 4B allocation decisions and maintained only "
    "for the current Streamlit session. It is not a live warehouse/ERP stock feed."
)


def init_inventory(alloc: pd.DataFrame):
    """One-time session-state inventory initialization from the Phase 4B
    allocation plan. Safe to call on every Streamlit rerun -- only acts the
    first time per session, so it can be called early (e.g. for KPIs) and
    again inside the tab without side effects."""
    if "inv_state" in st.session_state:
        return
    if alloc.empty or not REQUIRED_ALLOC_COLS.issubset(alloc.columns):
        st.session_state.inv_state = {}
        st.session_state.inv_source = (
            "⚠️ No Phase 4B allocation data found — planning inventory could not be initialized."
        )
        st.session_state.transfer_log = []
        st.session_state.receipt_log = []
        return
    inv = {}
    for row in alloc[["store_id", "model_id", "allocated_units"]].itertuples(index=False):
        inv[(row.store_id, row.model_id)] = int(row.allocated_units)
    st.session_state.inv_state = inv
    st.session_state.inv_source = (
        "Planning inventory initialized from data/phase4b_allocation.csv (allocated_units). "
        + PLANNING_INVENTORY_NOTE
    )
    st.session_state.transfer_log = []
    st.session_state.receipt_log = []


def get_units(store_id: str, model_id: str) -> int:
    return st.session_state.inv_state.get((store_id, model_id), 0)


def set_units(store_id: str, model_id: str, value: int):
    st.session_state.inv_state[(store_id, model_id)] = max(0, int(value))


def total_planning_inventory() -> int:
    """Chain-wide planning inventory total, for use in KPI rows elsewhere
    (e.g. the Executive Overview). Returns 0 if not yet initialized."""
    return int(sum(st.session_state.get("inv_state", {}).values()))


def inventory_frame_for_model(model_id: str, stores: pd.DataFrame) -> pd.DataFrame:
    """Per-store planning inventory for one model, joined with store names."""
    rows = [dict(store_id=sid, planning_inventory_units=get_units(sid, model_id)) for sid in stores["store_id"]]
    df = pd.DataFrame(rows)
    if not stores.empty and not df.empty:
        df = df.merge(stores[["store_id", "store_name", "city", "tier"]], on="store_id", how="left")
        df = df[["store_id", "store_name", "city", "tier", "planning_inventory_units"]]
    return df.sort_values("planning_inventory_units", ascending=False).reset_index(drop=True)


def greedy_fulfillment_plan(model_id: str, required_qty: int, stores: pd.DataFrame):
    """Greedily fills `required_qty` from the stores with the most planning
    inventory first (no inventory is invented -- only what's in session
    state is ever considered). Returns
    (plan_df, total_available, fulfilled_qty, shortage_qty). Does NOT modify
    any inventory -- this is a read-only check."""
    inv_df = inventory_frame_for_model(model_id, stores)
    plan_rows = []
    remaining = required_qty
    for _, r in inv_df.iterrows():
        if remaining <= 0:
            break
        take = min(int(r["planning_inventory_units"]), remaining)
        if take > 0:
            plan_rows.append(dict(store_id=r["store_id"], store_name=r.get("store_name", ""),
                                   units_supplied=int(take)))
            remaining -= take
    plan_df = pd.DataFrame(plan_rows)
    total_available = int(inv_df["planning_inventory_units"].sum()) if not inv_df.empty else 0
    fulfilled = required_qty - max(remaining, 0)
    shortage = max(remaining, 0)
    return plan_df, total_available, int(fulfilled), int(shortage)


def _product_options(products: pd.DataFrame) -> pd.DataFrame:
    """Builds a display label straight from products.csv -- no hardcoded names."""
    out = products.copy()
    out["label"] = out["model_id"] + " — " + out["model_name"].fillna("")
    return out.sort_values("label")


def _store_options(stores: pd.DataFrame) -> pd.DataFrame:
    out = stores[["store_id", "store_name"]].copy()
    out["display"] = out["store_id"] + " — " + out["store_name"]
    return out


def render_inventory_tab(products: pd.DataFrame, stores: pd.DataFrame,
                          trans: pd.DataFrame, alloc: pd.DataFrame):
    st.subheader("Inventory & Orders")

    if products.empty or stores.empty:
        st.warning("Product or store master data unavailable.")
        return

    init_inventory(alloc)

    # ---------------- System status / disclaimer ----------------
    with st.container(border=True):
        s1, s2, s3, s4, s5 = st.columns(5)
        s1.markdown("**Data mode**\n\nPlanning / simulation environment")
        s2.markdown("**Inventory**\n\nInitialized from Phase 4B allocation output")
        s3.markdown("**Persistence**\n\nSession-only")
        s4.markdown("**Historical sales**\n\nRead-only")
        s5.markdown("**Analytical outputs**\n\nRead-only")
    st.caption(PLANNING_INVENTORY_NOTE)

    with st.expander("ℹ️ How to use this system"):
        st.markdown(
            "1. **Search a product** below.\n"
            "2. **Check its planning inventory** across all stores.\n"
            "3. **Enter an order quantity** in the fulfillment check.\n"
            "4. **Check whether the order can be fulfilled** and which stores would supply it.\n"
            "5. **Transfer stock** between stores if one location is short and another has surplus.\n"
            "6. **Receive incoming stock** when new inventory arrives at a store.\n"
            "7. Use the **Allocation / EOL & Markdown / Transfers / Simulation** tabs for the "
            "underlying planning decisions this inventory position is based on."
        )

    st.divider()

    product_opts = _product_options(products)
    store_opts = _store_options(stores)

    # ==================== A. Product Search ====================
    st.markdown("#### A. Product Search")
    sel_label = st.selectbox("Search product", product_opts["label"].tolist(), key="lookup_product")
    sel_row = product_opts[product_opts["label"] == sel_label].iloc[0]
    model_id = sel_row["model_id"]

    lc1, lc2, lc3, lc4 = st.columns(4)
    lc1.metric("Product ID", model_id)
    lc2.metric("Category", sel_row["category"] if "category" in sel_row and pd.notna(sel_row["category"]) else "—")
    price_val = sel_row.get("price", None)
    lc3.metric("Price", f"₹{price_val:,.0f}" if pd.notna(price_val) else "—")
    lc4.metric("Lifecycle status",
               sel_row["lifecycle_stage"] if "lifecycle_stage" in sel_row and pd.notna(sel_row.get("lifecycle_stage")) else "—")

    # ==================== B. Inventory Position ====================
    st.markdown("#### B. Inventory Position")
    inv_df = inventory_frame_for_model(model_id, stores)
    total_units = int(inv_df["planning_inventory_units"].sum()) if not inv_df.empty else 0
    stores_holding = int((inv_df["planning_inventory_units"] > 0).sum()) if not inv_df.empty else 0

    bc1, bc2 = st.columns(2)
    bc1.metric("Total planning inventory", f"{total_units:,} units")
    bc2.metric("Stores holding stock", f"{stores_holding} of {len(stores)}")
    st.dataframe(inv_df, use_container_width=True, hide_index=True)

    st.divider()

    # ==================== C. Create Order / Fulfillment Check ====================
    st.markdown("#### C. Create Order / Fulfillment Check")
    oc1, oc2, oc3 = st.columns([1, 2, 1])
    order_id = oc1.text_input("Order ID (optional)", key="order_id")
    order_label = oc2.selectbox("Product", product_opts["label"].tolist(), key="order_product")
    order_model_id = product_opts[product_opts["label"] == order_label].iloc[0]["model_id"]
    required_qty = oc3.number_input("Quantity", min_value=1, value=1, step=1, key="order_qty")

    if st.button("Check Fulfillment", key="check_fulfillment"):
        # Read-only check: does NOT modify any inventory.
        plan_df, total_available, fulfilled, shortage = greedy_fulfillment_plan(
            order_model_id, int(required_qty), stores
        )
        label = f"Order {order_id}" if order_id else "This order"

        if shortage == 0:
            st.success(f"✅ Order can be fulfilled — {label}.")
        elif fulfilled > 0:
            st.warning(f"⚠️ Order cannot be fully fulfilled — {label} is partially fulfillable.")
        else:
            st.error(f"❌ Order cannot be fully fulfilled — {label} has no available planning inventory.")

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Requested", f"{int(required_qty)}")
        mc2.metric("Available", f"{total_available}")
        mc3.metric("Shortage", f"{shortage}")

        if not plan_df.empty:
            st.write("Suggested source stores (largest planning inventory first):")
            st.dataframe(plan_df, use_container_width=True, hide_index=True)

        # Existing Phase 5C recommendation touching this product, shown for
        # context only -- never automatically executed.
        if not trans.empty and {"predecessor_model_id", "successor_model_id"}.issubset(trans.columns):
            related = trans[
                (trans["predecessor_model_id"] == order_model_id) |
                (trans["successor_model_id"] == order_model_id)
            ]
            if "recommended_transfer_units" in related.columns:
                related = related[related["recommended_transfer_units"] > 0]
            if not related.empty:
                st.info("ℹ️ Existing Phase 5C planning recommendation(s) touch this product "
                        "(shown for context only — not automatically executed):")
                cols = [c for c in ["store_id", "predecessor_model_id", "successor_model_id",
                                     "transfer_priority", "recommended_transfer_units", "transfer_reason"]
                        if c in related.columns]
                st.dataframe(related[cols], use_container_width=True, hide_index=True)

    st.divider()

    # ==================== D. Inventory Actions ====================
    st.markdown("#### D. Inventory Actions")
    action_tab1, action_tab2 = st.tabs(["🔀 Transfer Stock", "📥 Receive Stock"])

    with action_tab1:
        tc1, tc2, tc3, tc4 = st.columns([2, 1, 1, 1])
        transfer_label = tc1.selectbox("Product", product_opts["label"].tolist(), key="transfer_product")
        transfer_model_id = product_opts[product_opts["label"] == transfer_label].iloc[0]["model_id"]
        from_display = tc2.selectbox("From store", store_opts["display"].tolist(), key="from_store")
        to_display = tc3.selectbox("To store", store_opts["display"].tolist(), key="to_store")
        transfer_qty = tc4.number_input("Quantity", min_value=1, value=1, step=1, key="transfer_qty")

        from_store_id = store_opts[store_opts["display"] == from_display].iloc[0]["store_id"]
        to_store_id = store_opts[store_opts["display"] == to_display].iloc[0]["store_id"]

        before_from = get_units(from_store_id, transfer_model_id)
        before_to = get_units(to_store_id, transfer_model_id)
        st.caption(f"Before transfer — {from_store_id}: **{before_from} units** • {to_store_id}: **{before_to} units**")

        if st.button("Confirm Transfer", key="confirm_transfer"):
            if from_store_id == to_store_id:
                st.error("❌ Source and destination stores must be different.")
            elif transfer_qty <= 0:
                st.error("❌ Quantity must be greater than zero.")
            elif transfer_qty > before_from:
                st.error(f"❌ Insufficient planning inventory at {from_store_id} — only {before_from} units "
                         f"available, cannot transfer {int(transfer_qty)}.")
            else:
                set_units(from_store_id, transfer_model_id, before_from - int(transfer_qty))
                set_units(to_store_id, transfer_model_id, before_to + int(transfer_qty))
                st.session_state.transfer_log.append(dict(
                    model_id=transfer_model_id, from_store=from_store_id, to_store=to_store_id,
                    quantity=int(transfer_qty)
                ))
                st.success("✅ Transfer completed for this session.")
                st.caption("This change is session-based only and is not written back to any historical CSV file.")
                ac1, ac2 = st.columns(2)
                ac1.metric(f"{from_store_id} (after)", f"{before_from - int(transfer_qty)} units",
                           delta=f"-{int(transfer_qty)}")
                ac2.metric(f"{to_store_id} (after)", f"{before_to + int(transfer_qty)} units",
                           delta=f"+{int(transfer_qty)}")
                st.write("Updated planning inventory for this product:")
                st.dataframe(inventory_frame_for_model(transfer_model_id, stores),
                             use_container_width=True, hide_index=True)

        if st.session_state.get("transfer_log"):
            with st.expander("Transfer history (this session)"):
                st.dataframe(pd.DataFrame(st.session_state.transfer_log), use_container_width=True, hide_index=True)

    with action_tab2:
        rc1, rc2, rc3 = st.columns([2, 1, 1])
        receive_label = rc1.selectbox("Product", product_opts["label"].tolist(), key="receive_product")
        receive_model_id = product_opts[product_opts["label"] == receive_label].iloc[0]["model_id"]
        receive_display = rc2.selectbox("Store", store_opts["display"].tolist(), key="receive_store")
        receive_qty = rc3.number_input("Quantity received", min_value=1, value=1, step=1, key="receive_qty")
        receive_store_id = store_opts[store_opts["display"] == receive_display].iloc[0]["store_id"]

        before_recv = get_units(receive_store_id, receive_model_id)
        st.caption(f"Before receipt — {receive_store_id}: **{before_recv} units**")

        if st.button("Confirm Receipt", key="confirm_receipt"):
            if receive_qty <= 0:
                st.error("❌ Quantity must be greater than zero.")
            else:
                set_units(receive_store_id, receive_model_id, before_recv + int(receive_qty))
                st.session_state.receipt_log.append(dict(
                    model_id=receive_model_id, store=receive_store_id, quantity=int(receive_qty)
                ))
                st.success("✅ Stock receipt recorded for this session.")
                st.caption("This change is session-based only and is not written back to any historical CSV file.")
                st.metric(f"{receive_store_id} (after)", f"{before_recv + int(receive_qty)} units",
                          delta=f"+{int(receive_qty)}")
                st.write("Updated planning inventory for this product:")
                st.dataframe(inventory_frame_for_model(receive_model_id, stores),
                             use_container_width=True, hide_index=True)

        if st.session_state.get("receipt_log"):
            with st.expander("Receipt history (this session)"):
                st.dataframe(pd.DataFrame(st.session_state.receipt_log), use_container_width=True, hide_index=True)
