"""土木工地日常行政與材料進出貨管理系統（Streamlit + SQLite）。"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from database import get_connection, init_db

st.set_page_config(page_title="工地行政管理系統", page_icon="🏗️", layout="wide")

init_db()

CATEGORIES = ["水電", "泥作", "鋼構", "水泥", "砂石", "模板", "其他"]
MATERIALS = ["水泥", "鋼筋", "砂石", "模板"]
UNITS = ["噸", "公斤", "立方公尺", "片", "支", "批"]
EXPENSE_CATEGORIES = ["膳食費", "五金耗材", "交通費", "清潔費", "雜支", "其他"]
EQUIPMENT = ["夯實機", "發電機"]


def run_query(sql: str, params: tuple = ()) -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def execute_sql(sql: str, params: tuple = ()) -> None:
    with get_connection() as conn:
        conn.execute(sql, params)


def vendor_options() -> dict[str, int]:
    df = run_query("SELECT id, name FROM vendors ORDER BY id")
    return {f"{row.id}｜{row.name}": row.id for row in df.itertuples()}


@st.dialog("新增材料進出貨紀錄")
def add_material_dialog(vendors: dict[str, int]):
    with st.form("add_material"):
        record_date = st.date_input("紀錄日期")
        material_name = st.selectbox("材料名稱", MATERIALS)
        vendor_label = st.selectbox("進貨廠商", list(vendors))
        inbound_qty = st.number_input("進貨量", min_value=0.0, step=1.0)
        used_qty = st.number_input("領料量", min_value=0.0, step=1.0)
        stock = st.number_input("目前庫存", min_value=0.0, step=1.0)
        safety_stock = st.number_input("安全庫存", min_value=0.0, step=1.0)
        unit = st.selectbox("單位", UNITS)
        unit_price = st.number_input("單價（元）", min_value=0.0, step=1.0)
        invoice_no = st.text_input("進貨單號")
        paid = st.checkbox("已請款對帳")
        note = st.text_area("備註")
        if st.form_submit_button("儲存", width="stretch"):
            execute_sql(
                """INSERT INTO materials
                (record_date, material_name, vendor_id, inbound_qty, used_qty, current_stock,
                 safety_stock, unit, unit_price, invoice_no, paid, note)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(record_date), material_name, vendors[vendor_label], inbound_qty, used_qty,
                    stock, safety_stock, unit, unit_price, invoice_no, int(paid), note,
                ),
            )
            st.success("已新增材料紀錄")
            st.rerun()


@st.dialog("修改材料進出貨紀錄")
def edit_material_dialog(record: pd.Series, vendors: dict[str, int]):
    current_label = f"{record['vendor_id']}｜{record['vendor_name']}"
    options = list(vendors)
    if current_label not in options:
        options.insert(0, current_label)
    with st.form("edit_material"):
        record_date = st.date_input("紀錄日期", pd.to_datetime(record["record_date"]))
        material_name = st.selectbox("材料名稱", MATERIALS, index=MATERIALS.index(record["material_name"]) if record["material_name"] in MATERIALS else 0)
        vendor_label = st.selectbox("進貨廠商", options, index=options.index(current_label))
        inbound_qty = st.number_input("進貨量", value=float(record["inbound_qty"]), min_value=0.0, step=1.0)
        used_qty = st.number_input("領料量", value=float(record["used_qty"]), min_value=0.0, step=1.0)
        stock = st.number_input("目前庫存", value=float(record["current_stock"]), min_value=0.0, step=1.0)
        safety_stock = st.number_input("安全庫存", value=float(record["safety_stock"]), min_value=0.0, step=1.0)
        unit = st.selectbox("單位", UNITS, index=UNITS.index(record["unit"]) if record["unit"] in UNITS else 0)
        unit_price = st.number_input("單價（元）", value=float(record["unit_price"]), min_value=0.0, step=1.0)
        invoice_no = st.text_input("進貨單號", value=record["invoice_no"] or "")
        paid = st.checkbox("已請款對帳", value=bool(record["paid"]))
        note = st.text_area("備註", value=record["note"] or "")
        if st.form_submit_button("儲存變更", width="stretch"):
            execute_sql(
                """UPDATE materials SET record_date=?, material_name=?, vendor_id=?, inbound_qty=?,
                used_qty=?, current_stock=?, safety_stock=?, unit=?, unit_price=?, invoice_no=?,
                paid=?, note=? WHERE id=?""",
                (
                    str(record_date), material_name, vendors.get(vendor_label, record["vendor_id"]),
                    inbound_qty, used_qty, stock, safety_stock, unit, unit_price, invoice_no,
                    int(paid), note, int(record["id"]),
                ),
            )
            st.success("已更新材料紀錄")
            st.rerun()


def materials_page():
    st.title("材料進出貨管理")
    st.caption("記錄水泥、鋼筋、砂石與模板的庫存狀態；庫存低於安全量時會自動亮紅燈。")

    df = run_query(
        """SELECT m.*, v.name AS vendor_name FROM materials m
        JOIN vendors v ON m.vendor_id = v.id
        ORDER BY m.record_date DESC, m.id DESC"""
    )
    df["庫存狀態"] = df.apply(
        lambda r: "🔴 庫存不足" if r["current_stock"] < r["safety_stock"] else "🟢 正常", axis=1
    )

    low = df[df["current_stock"] < df["safety_stock"]]
    c1, c2, c3 = st.columns(3)
    c1.metric("進貨紀錄數", len(df))
    c2.metric("目前庫存合計", f"{df['current_stock'].sum():,.0f}")
    c3.metric("庫存不足項目", len(low), delta="需補貨" if len(low) else None, delta_color="inverse")
    if len(low):
        st.error("庫存不足：" + "、".join(f"{r.material_name}（{r.current_stock:g}/{r.safety_stock:g} {r.unit}）" for r in low.itertuples()))

    st.subheader("材料紀錄")
    with st.expander("查詢與篩選"):
        fc1, fc2 = st.columns(2)
        keyword = fc1.text_input("材料名稱／單號關鍵字")
        only_low = fc2.checkbox("只顯示庫存不足")
    show = df.copy()
    if keyword:
        show = show[show["material_name"].str.contains(keyword, case=False) | show["invoice_no"].fillna("").str.contains(keyword, case=False)]
    if only_low:
        show = show[show["current_stock"] < show["safety_stock"]]

    display = show.rename(columns={
        "id": "編號", "record_date": "日期", "material_name": "材料", "vendor_name": "廠商",
        "inbound_qty": "進貨量", "used_qty": "領料量", "current_stock": "庫存",
        "safety_stock": "安全量", "unit": "單位", "unit_price": "單價",
        "invoice_no": "單號", "paid": "已請款", "note": "備註",
    })
    st.dataframe(
        display[["編號", "日期", "材料", "廠商", "進貨量", "領料量", "庫存", "安全量", "單位", "單價", "單號", "已請款", "庫存狀態", "備註"]],
        width="stretch", hide_index=True,
    )

    vendors = vendor_options()
    st.subheader("新增／修改／刪除")
    action = st.radio("選擇操作", ["新增", "修改", "刪除"], horizontal=True)
    if action == "新增":
        if st.button("新增材料紀錄", type="primary"):
            add_material_dialog(vendors)
    elif action == "修改":
        if df.empty:
            st.info("尚無資料可修改")
        else:
            selected = st.selectbox("選擇紀錄", df["id"].tolist(), format_func=lambda i: f"#{i}｜{df.iloc[df.index[df['id'] == i][0]]['material_name']}｜{df.iloc[df.index[df['id'] == i][0]]['record_date']}")
            if st.button("修改所選紀錄", type="primary"):
                edit_material_dialog(df[df["id"] == selected].iloc[0], vendors)
    else:
        if df.empty:
            st.info("尚無資料可刪除")
        else:
            selected = st.selectbox("選擇要刪除的紀錄", df["id"].tolist(), format_func=lambda i: f"#{i}｜{df.iloc[df.index[df['id'] == i][0]]['material_name']}")
            if st.button("刪除所選紀錄", type="primary"):
                execute_sql("DELETE FROM materials WHERE id=?", (int(selected),))
                st.success("已刪除材料紀錄")
                st.rerun()


@st.dialog("新增協力廠商")
def add_vendor_dialog():
    with st.form("add_vendor"):
        name = st.text_input("廠商名稱")
        category = st.selectbox("工種分類", CATEGORIES)
        contact = st.text_input("聯絡人")
        phone = st.text_input("電話")
        tax_id = st.text_input("統一編號")
        rating = st.slider("配合評價（1–5）", 1, 5, 3)
        note = st.text_area("備註")
        if st.form_submit_button("儲存", width="stretch"):
            if not name.strip() or not tax_id.strip():
                st.error("請填寫廠商名稱與統編")
            else:
                execute_sql(
                    "INSERT INTO vendors (name, category, contact, phone, tax_id, rating, note) VALUES (?,?,?,?,?,?,?)",
                    (name.strip(), category, contact, phone, tax_id.strip(), rating, note),
                )
                st.success("已新增廠商")
                st.rerun()


@st.dialog("修改協力廠商")
def edit_vendor_dialog(r: pd.Series):
    with st.form("edit_vendor"):
        name = st.text_input("廠商名稱", value=r["name"])
        category = st.selectbox("工種分類", CATEGORIES, index=CATEGORIES.index(r["category"]) if r["category"] in CATEGORIES else 0)
        contact = st.text_input("聯絡人", value=r["contact"])
        phone = st.text_input("電話", value=r["phone"])
        tax_id = st.text_input("統一編號", value=r["tax_id"])
        rating = st.slider("配合評價（1–5）", 1, 5, int(r["rating"]))
        note = st.text_area("備註", value=r["note"] or "")
        if st.form_submit_button("儲存變更", width="stretch"):
            execute_sql(
                "UPDATE vendors SET name=?, category=?, contact=?, phone=?, tax_id=?, rating=?, note=? WHERE id=?",
                (name.strip(), category, contact, phone, tax_id.strip(), rating, note, int(r["id"])),
            )
            st.success("已更新廠商資料")
            st.rerun()


def vendors_page():
    st.title("協力廠商名錄")
    st.caption("管理工地配合廠商的基本資料與評價。")
    df = run_query("SELECT * FROM vendors ORDER BY id")
    st.metric("廠商數", len(df))
    keyword = st.text_input("搜尋廠商名稱／工種／聯絡人")
    show = df.copy()
    if keyword:
        mask = show.apply(lambda r: keyword.lower() in " ".join(str(v) for v in r).lower(), axis=1)
        show = show[mask]
    st.dataframe(
        show.rename(columns={"id": "編號", "name": "廠商名稱", "category": "工種分類", "contact": "聯絡人", "phone": "電話", "tax_id": "統編", "rating": "評價", "note": "備註"}),
        width="stretch", hide_index=True,
    )
    st.subheader("新增／修改／刪除")
    action = st.radio("操作", ["新增", "修改", "刪除"], horizontal=True, key="vendor_action")
    if action == "新增":
        if st.button("新增廠商", type="primary"):
            add_vendor_dialog()
    elif action == "修改":
        if df.empty:
            st.info("尚無資料")
        else:
            selected = st.selectbox("選擇廠商", df["id"].tolist(), format_func=lambda i: df.iloc[df.index[df['id'] == i][0]]["name"], key="vendor_edit_sel")
            if st.button("修改所選廠商", type="primary"):
                edit_vendor_dialog(df[df["id"] == selected].iloc[0])
    else:
        if df.empty:
            st.info("尚無資料")
        else:
            selected = st.selectbox("選擇要刪除的廠商", df["id"].tolist(), format_func=lambda i: df.iloc[df.index[df['id'] == i][0]]["name"], key="vendor_del_sel")
            try:
                if st.button("刪除所選廠商", type="primary"):
                    execute_sql("DELETE FROM vendors WHERE id=?", (int(selected),))
                    st.success("已刪除廠商")
                    st.rerun()
            except Exception as exc:
                st.error(f"無法刪除（可能已有進貨紀錄關聯）：{exc}")


@st.dialog("修改進貨對帳狀態")
def edit_payment_dialog(r: pd.Series):
    with st.form("edit_payment"):
        paid = st.checkbox("已請款對帳", value=bool(r["paid"]))
        invoice_no = st.text_input("進貨單號", value=r["invoice_no"] or "")
        note = st.text_area("備註", value=r["note"] or "")
        if st.form_submit_button("儲存", width="stretch"):
            execute_sql("UPDATE materials SET paid=?, invoice_no=?, note=? WHERE id=?", (int(paid), invoice_no, note, int(r["id"])))
            st.success("已更新對帳狀態")
            st.rerun()


def invoices_page():
    st.title("進貨單據與廠商對應查詢")
    st.caption("點選任一筆進貨紀錄，查看供貨廠商、單價與請款對帳狀態。")
    df = run_query(
        """SELECT m.id, m.record_date, m.material_name, m.inbound_qty, m.unit,
        m.unit_price, m.invoice_no, m.paid, m.note, v.name AS vendor_name,
        v.category, v.contact, v.phone, v.tax_id, v.rating
        FROM materials m JOIN vendors v ON m.vendor_id = v.id
        ORDER BY m.record_date DESC"""
    )
    df["對帳狀態"] = df["paid"].map({1: "✅ 已請款", 0: "⬜ 未請款"})
    keyword = st.text_input("搜尋單號／材料／廠商")
    show = df.copy()
    if keyword:
        mask = show.apply(lambda r: keyword.lower() in " ".join(str(v) for v in r).lower(), axis=1)
        show = show[mask]
    st.dataframe(
        show.rename(columns={
            "id": "編號", "record_date": "日期", "material_name": "材料", "inbound_qty": "進貨量",
            "unit": "單位", "unit_price": "單價", "invoice_no": "進貨單號", "vendor_name": "供貨廠商",
            "category": "工種", "contact": "聯絡人", "phone": "電話", "tax_id": "統編",
            "rating": "評價", "note": "備註",
        })[["編號", "日期", "進貨單號", "材料", "進貨量", "單位", "單價", "供貨廠商", "工種", "聯絡人", "電話", "對帳狀態", "備註"]],
        width="stretch", hide_index=True,
        selection_mode="single-row", on_select="rerun", key="invoice_table",
    )
    sel = st.session_state.get("invoice_table", {}).get("selection", {}).get("rows", [])
    if sel:
        r = df.iloc[sel[0]]
        st.subheader(f"進貨單 #{r['id']} 詳情")
        d1, d2, d3 = st.columns(3)
        d1.info(f"**供貨廠商**：{r['vendor_name']}\n\n**工種**：{r['category']}\n\n**統編**：{r['tax_id']}")
        d2.info(f"**進貨日期**：{r['record_date']}\n\n**材料**：{r['material_name']} {r['inbound_qty']:g} {r['unit']}\n\n**單價**：{r['unit_price']:,.0f} 元\n\n**金額**：{r['unit_price'] * r['inbound_qty']:,.0f} 元")
        d3.success(f"**單號**：{r['invoice_no'] or '—'}\n\n**對帳狀態**：{r['對帳狀態']}\n\n**聯絡人**：{r['contact']}／{r['phone']}")
        if st.button("修改對帳狀態"):
            edit_payment_dialog(r)


@st.dialog("新增雜支")
def add_expense_dialog():
    with st.form("add_expense"):
        expense_date = st.date_input("日期")
        category = st.selectbox("類別", EXPENSE_CATEGORIES)
        item = st.text_input("項目")
        amount = st.number_input("金額（元）", min_value=0.0, step=1.0)
        handler = st.text_input("經手人")
        note = st.text_area("備註")
        if st.form_submit_button("儲存", width="stretch"):
            if not item.strip():
                st.error("請填寫項目")
            else:
                execute_sql(
                    "INSERT INTO expenses (expense_date, category, item, amount, handler, note) VALUES (?,?,?,?,?,?)",
                    (str(expense_date), category, item.strip(), amount, handler, note),
                )
                st.success("已新增雜支紀錄")
                st.rerun()


@st.dialog("修改雜支")
def edit_expense_dialog(r: pd.Series):
    with st.form("edit_expense"):
        expense_date = st.date_input("日期", pd.to_datetime(r["expense_date"]))
        category = st.selectbox("類別", EXPENSE_CATEGORIES, index=EXPENSE_CATEGORIES.index(r["category"]) if r["category"] in EXPENSE_CATEGORIES else 0)
        item = st.text_input("項目", value=r["item"])
        amount = st.number_input("金額（元）", value=float(r["amount"]), min_value=0.0, step=1.0)
        handler = st.text_input("經手人", value=r["handler"])
        note = st.text_area("備註", value=r["note"] or "")
        if st.form_submit_button("儲存變更", width="stretch"):
            execute_sql("UPDATE expenses SET expense_date=?, category=?, item=?, amount=?, handler=?, note=? WHERE id=?",
                        (str(expense_date), category, item, amount, handler, note, int(r["id"])))
            st.success("已更新雜支紀錄")
            st.rerun()


@st.dialog("新增機具租借")
def add_rental_dialog():
    with st.form("add_rental"):
        equipment_name = st.selectbox("機具名稱", EQUIPMENT)
        borrower = st.text_input("借用人")
        borrow_date = st.date_input("借出日期")
        due_date = st.date_input("預計歸還日")
        status = st.selectbox("狀態", ["借出中", "已歸還"])
        return_date = st.date_input("實際歸還日（若已歸還）") if status == "已歸還" else None
        note = st.text_area("備註")
        if st.form_submit_button("儲存", width="stretch"):
            if not borrower.strip():
                st.error("請填寫借用人")
            else:
                execute_sql(
                    """INSERT INTO equipment_rentals
                    (equipment_name, borrower, borrow_date, due_date, return_date, status, note)
                    VALUES (?,?,?,?,?,?,?)""",
                    (equipment_name, borrower.strip(), str(borrow_date), str(due_date),
                     str(return_date) if return_date else None, status, note),
                )
                st.success("已新增機具租借紀錄")
                st.rerun()


@st.dialog("修改機具租借")
def edit_rental_dialog(r: pd.Series):
    with st.form("edit_rental"):
        equipment_name = st.selectbox("機具名稱", EQUIPMENT, index=EQUIPMENT.index(r["equipment_name"]) if r["equipment_name"] in EQUIPMENT else 0)
        borrower = st.text_input("借用人", value=r["borrower"])
        borrow_date = st.date_input("借出日期", pd.to_datetime(r["borrow_date"]))
        due_date = st.date_input("預計歸還日", pd.to_datetime(r["due_date"]))
        status = st.selectbox("狀態", ["借出中", "已歸還"], index=0 if r["status"] == "借出中" else 1)
        return_date = None
        if status == "已歸還":
            return_date = st.date_input("實際歸還日", pd.to_datetime(r["return_date"]) if r["return_date"] else pd.Timestamp.now())
        note = st.text_area("備註", value=r["note"] or "")
        if st.form_submit_button("儲存變更", width="stretch"):
            execute_sql(
                """UPDATE equipment_rentals SET equipment_name=?, borrower=?, borrow_date=?, due_date=?,
                return_date=?, status=?, note=? WHERE id=?""",
                (equipment_name, borrower, str(borrow_date), str(due_date),
                 str(return_date) if return_date else None, status, note, int(r["id"])),
            )
            st.success("已更新機具租借紀錄")
            st.rerun()


def admin_page():
    st.title("日常行政零用金與機具租借")
    st.caption("管理工地雜支與夯實機、發電機的借出／歸還狀態。")

    tab1, tab2 = st.tabs(["零用金雜支", "機具租借"])
    with tab1:
        exp = run_query("SELECT * FROM expenses ORDER BY expense_date DESC, id DESC")
        c1, c2 = st.columns(2)
        c1.metric("雜支筆數", len(exp))
        c2.metric("零用金支出合計", f"{exp['amount'].sum():,.0f} 元")
        st.dataframe(exp.rename(columns={"id": "編號", "expense_date": "日期", "category": "類別", "item": "項目", "amount": "金額", "handler": "經手人", "note": "備註"}), width="stretch", hide_index=True)
        action = st.radio("雜支操作", ["新增", "修改", "刪除"], horizontal=True, key="exp_action")
        if action == "新增":
            if st.button("新增雜支", type="primary"):
                add_expense_dialog()
        elif action == "修改":
            selected = st.selectbox("選擇紀錄", exp["id"].tolist(), format_func=lambda i: f"#{i}｜{exp.iloc[exp.index[exp['id'] == i][0]]['item']}", key="exp_sel")
            if st.button("修改所選雜支", type="primary"):
                edit_expense_dialog(exp[exp["id"] == selected].iloc[0])
        else:
            selected = st.selectbox("選擇要刪除的紀錄", exp["id"].tolist(), key="exp_del")
            if st.button("刪除所選雜支", type="primary"):
                execute_sql("DELETE FROM expenses WHERE id=?", (int(selected),))
                st.success("已刪除雜支紀錄")
                st.rerun()

    with tab2:
        rentals = run_query("SELECT * FROM equipment_rentals ORDER BY borrow_date DESC, id DESC")
        active = rentals[rentals["status"] == "借出中"]
        c1, c2 = st.columns(2)
        c1.metric("租借紀錄", len(rentals))
        c2.metric("目前借出中", len(active), delta="歸還提醒" if len(active) else None, delta_color="inverse")
        st.dataframe(rentals.rename(columns={"id": "編號", "equipment_name": "機具", "borrower": "借用人", "borrow_date": "借出日", "due_date": "預計歸還", "return_date": "實際歸還", "status": "狀態", "note": "備註"}), width="stretch", hide_index=True)
        if not active.empty:
            st.warning("尚未歸還：" + "、".join(f"{r.equipment_name}（{r.borrower}）" for r in active.itertuples()))
        action = st.radio("機具操作", ["新增", "修改／歸還", "刪除"], horizontal=True, key="rent_action")
        if action == "新增":
            if st.button("新增租借紀錄", type="primary"):
                add_rental_dialog()
        elif action == "修改／歸還":
            selected = st.selectbox("選擇紀錄", rentals["id"].tolist(), format_func=lambda i: f"#{i}｜{rentals.iloc[rentals.index[rentals['id'] == i][0]]['equipment_name']}｜{rentals.iloc[rentals.index[rentals['id'] == i][0]]['borrower']}", key="rent_sel")
            if st.button("修改／歸還所選紀錄", type="primary"):
                edit_rental_dialog(rentals[rentals["id"] == selected].iloc[0])
        else:
            selected = st.selectbox("選擇要刪除的紀錄", rentals["id"].tolist(), key="rent_del")
            if st.button("刪除所選租借紀錄", type="primary"):
                execute_sql("DELETE FROM equipment_rentals WHERE id=?", (int(selected),))
                st.success("已刪除租借紀錄")
                st.rerun()


st.sidebar.title("🏗️ 工地管理系統")
page = st.sidebar.radio("功能分頁", ["材料進出貨管理", "協力廠商名錄", "進貨單據與廠商對應查詢", "日常行政零用金與機具租借"])
st.sidebar.divider()
st.sidebar.caption("資料庫：site.db")
st.sidebar.caption("模擬資料：每張表 5 筆")

if page == "材料進出貨管理":
    materials_page()
elif page == "協力廠商名錄":
    vendors_page()
elif page == "進貨單據與廠商對應查詢":
    invoices_page()
else:
    admin_page()
