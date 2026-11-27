"""Vietnamese research workbench UI V2. Scientific computations stay in service.py."""
from __future__ import annotations
import html,json,sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
sys.path.insert(0,str(Path(__file__).resolve().parent))
import service as svc

st.set_page_config(page_title="DAO Risk Simulator · Phòng nghiên cứu",page_icon="◈",layout="wide")
UI_VERSION="2.0"
PAGES=["Tổng quan","Dữ liệu DAO","Cấu hình & thực thi","So sánh cơ chế","Độ nhạy","Tái lập & xuất"]
MECHANISMS={"TW":"Token-Weighted","QV":"QV căn bậc hai theo ví","CAP":"Capping theo ví","VE":"Vote-Escrow"}
STATE_LABELS={"ELIGIBLE":"Đủ điều kiện","INFEASIBLE":"Không khả thi","NOT_READY":"Chưa đủ đặc tả","DECLINED":"Tác tử từ chối","ATTEMPTED_SUCCESS":"Đổi kết quả thành công","ATTEMPTED_FAILURE":"Không đạt chỉ tiêu","OUTCOME_UNKNOWN":"Chưa xác định outcome","UNKNOWN_OUTCOME":"Chưa xác định outcome"}
OUTCOMES={"ACCEPTED":"Chấp nhận","REJECTED":"Từ chối","FINISHED":"Đã kết thúc"}
FAMILIES={"SPLIT":"Chia nguồn VP","SWITCH":"Đổi phiếu","BRIBE_E":"Hối lộ có điều kiện","MOBILIZE":"Huy động quyền","FLASH":"Vay chớp nhoáng","HELD_LOAN":"Khoản vay nắm giữ"}

def theme():
    st.markdown("""<style>
    :root{--ink:#173344;--teal:#087c70;--paper:#f4f5f1}
    .stApp{background:var(--paper);color:var(--ink)}
    [data-testid="stHeader"]{background:rgba(244,245,241,.97)}
    .block-container{padding-top:4.5rem;padding-bottom:3rem;max-width:1320px}
    h1,h2,h3{color:var(--ink);letter-spacing:-.025em}
    h1{font-size:2.15rem!important;font-weight:680!important;line-height:1.18!important}
    h2{font-size:1.4rem!important}h3{font-size:1.12rem!important}p{line-height:1.6}
    [data-testid="stSidebar"]{background:#102e3c;border-right:1px solid #264755}
    [data-testid="stSidebar"] p,[data-testid="stSidebar"] label,[data-testid="stSidebar"] h3{color:#ecf3f3!important}
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p{color:#b8cdd1!important}
    [data-testid="stSidebar"] [role="radiogroup"]{gap:.15rem}
    [data-testid="stSidebar"] [role="radiogroup"] label{padding:.45rem .6rem;border-radius:6px}
    [data-testid="stSidebar"] [role="radiogroup"] label:hover{background:#244653}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){background:#28505a;border-left:3px solid #7bd3c4}
    [data-testid="stSidebar"] [role="radiogroup"] label>div:first-child{display:none}
    .rail-brand{font-size:1.12rem;font-weight:700;color:#f2f8f7;margin:.3rem 0 .15rem}.rail-brand span{color:#83cfc1}
    .rail-kicker{font-size:.69rem;letter-spacing:.15em;color:#a7c7cb;margin-bottom:1.4rem}
    .rail-context{border-top:1px solid #34515c;padding-top:1rem;margin-top:1rem;font-size:.83rem;color:#d8e8e9;line-height:1.65}
    .eyebrow{font-size:.7rem;letter-spacing:.14em;text-transform:uppercase;font-weight:650;color:#47706f;margin-bottom:.55rem}
    .intro{font-size:1rem;color:#4c6370;max-width:850px;line-height:1.65;margin-bottom:1.2rem}
    .evidence{display:inline-block;font-size:.73rem;color:#805719;background:#f8eddb;border:1px solid #ead7b7;padding:.2rem .5rem;border-radius:4px;margin-bottom:.65rem}
    .context-strip{display:grid;grid-template-columns:1.5fr 1fr 1fr 1fr;background:#eaf0ec;border:1px solid #d6e2dc;border-radius:7px;margin:.4rem 0 1.3rem;overflow:hidden}
    .context-item{padding:.65rem .85rem;border-right:1px solid #d6e2dc;min-width:0}.context-item:last-child{border-right:0}
    .context-item small{display:block;color:#526f72;font-size:.7rem;margin-bottom:.15rem}
    .context-item strong{display:block;color:#193e47;font-size:.88rem;font-weight:600;overflow-wrap:anywhere}
    .step{color:#224c57;font-size:.85rem;font-weight:650;margin:.2rem 0 .8rem}.step span{display:inline-block;padding:.1rem .4rem;margin-right:.5rem;border:1px solid #b4cac5;border-radius:4px;color:#187063;background:#edf4ef}
    [data-testid="stVerticalBlockBorderWrapper"]>div{border-color:#dae3e2!important;border-radius:8px!important;background:white}
    [data-testid="stMetric"]{padding:.3rem 0 .6rem;border-bottom:1px solid #d9e4e0}
    [data-testid="stMetricLabel"] p{font-size:.8rem;color:#516a72}[data-testid="stMetricValue"]{font-size:1.55rem!important;color:#1e5260}
    .stButton>button,.stDownloadButton>button{border-radius:5px;min-height:2.65rem;font-weight:550}
    .stButton>button[kind="primary"]{background:#087c70;border-color:#087c70;color:white}
    button:focus-visible,input:focus-visible,textarea:focus-visible{outline:2px solid #25887f!important;outline-offset:3px}
    [data-testid="stExpander"]{background:#fff;border-radius:6px}[data-testid="stDataFrame"]{border:1px solid #e0e7e5;border-radius:5px}
    .scope-note{font-size:.79rem;color:#587079;border-top:1px solid #d6e1df;padding-top:.8rem;margin-top:1.2rem}
    @media(max-width:740px){.block-container{padding-top:4.1rem;padding-left:1rem;padding-right:1rem}h1{font-size:1.75rem!important}.context-strip{grid-template-columns:1fr 1fr}.context-item:nth-child(2){border-right:0}.context-item:nth-child(-n+2){border-bottom:1px solid #d6e2dc}}
    </style>""",unsafe_allow_html=True)

def header(kicker,title,description,synthetic=False):
    st.markdown(f'<div class="eyebrow">{html.escape(kicker)}</div>',unsafe_allow_html=True)
    st.title(title)
    if synthetic:st.markdown('<span class="evidence">Mô phỏng Cấp A · Giả định tổng hợp</span>',unsafe_allow_html=True)
    st.markdown(f'<div class="intro">{html.escape(description)}</div>',unsafe_allow_html=True)

def step(n,title):st.markdown(f'<div class="step"><span>{n}</span>{html.escape(title)}</div>',unsafe_allow_html=True)
def current_request():return st.session_state.get("current_request")
def fmt_value(v):return "Không xác định" if v is None else ("Có" if v else "Không") if isinstance(v,bool) else str(v)

def context(request=None):
    q=request or current_request()
    if not q:return
    c=q["config"];src=q.get("source",{});b=st.session_state.get("last_bundle")
    state="Đã thực thi" if b and b.get("input_hash")==svc.request_hash(q) else "Đã chuẩn bị"
    fields=[("Kịch bản",FAMILIES.get(c["attack"]["family"],c["attack"]["family"])),("Seed / world",f'{src.get("master_seed","—")} / {src.get("replicate","—")}'),("Nguồn quyền","MANA / khóa riêng" if c.get("ve") else "VP · TW / QV / Capping"),("Phiên làm việc",state)]
    body="".join(f'<div class="context-item"><small>{html.escape(k)}</small><strong>{html.escape(str(v))}</strong></div>' for k,v in fields)
    st.markdown(f'<div class="context-strip">{body}</div>',unsafe_allow_html=True)

def clear_results():
    for k in ("last_bundle","comparison_bundle","sensitivity_bundle","comparison_signature","sensitivity_signature"):st.session_state.pop(k,None)

def reset_configuration():
    prefixes=("budget_","cap_","snapshot_time_","resource_utility_","risk_utility_","opportunity_utility_","capital_utility_","custom_schedule_","published_at_","decision_at_","allocation_at_")
    keys={"cfg_total","cfg_distribution","cfg_alias","cfg_information","cfg_allocation","cfg_grant","cfg_block","cfg_mana","cfg_lock_amount","cfg_lock_remaining","cfg_mechanism","current_request","current_hash","batch_source"}
    for key in list(st.session_state):
        if key in keys or any(str(key).startswith(p) for p in prefixes):st.session_state.pop(key,None)
    # Explicit assignments also reconcile mounted browser widgets. Deleting a
    # widget key alone can leave its old frontend value visible after rerun.
    template=st.session_state.get("cfg_template","SPLIT")
    base=svc.build_scenario(template,st.session_state.get("cfg_seed",4302027),st.session_state.get("cfg_replicate",9))
    cfg=base["config"];attack=cfg["attack"];ve=cfg.get("ve") is not None
    defaults={"cfg_total":"","cfg_distribution":"preserve","cfg_alias":4,"cfg_information":"INFORMED_PROPOSER","cfg_allocation":"TARGETED_PROPOSAL","cfg_grant":False,"cfg_block":False,"cfg_mana":"1","cfg_lock_amount":0.5,"cfg_lock_remaining":0.5,"cfg_mechanism":"VE" if ve else "TW",f"budget_{template}":str(cfg["principals"][cfg["attacker"]]["budget"]),f"snapshot_time_{template}":int(cfg["proposal"]["snapshot_time"]),f"custom_schedule_{template}":False}
    if not ve:defaults[f"cap_{template}"]=str(cfg["cap_vp"])
    for name in ("resource_utility","risk_utility","opportunity_utility","capital_utility"):defaults[f"{name}_{template}"]=str(attack.get(name,"0"))
    for name in ("published_at","decision_at","allocation_at"):
        if name in attack:defaults[f"{name}_{template}"]=int(attack[name])
    st.session_state.update(defaults)
    clear_results()

def navigate(page,template=None,replicate=None):
    if template is not None:
        st.session_state["cfg_template"]=template;st.session_state["cfg_seed"]=4302027;st.session_state["cfg_replicate"]=replicate if replicate is not None else 9;reset_configuration()
    st.session_state["page"]=page

def require_request():
    q=current_request()
    if q is None:
        with st.container(border=True):
            st.subheader("Bắt đầu từ một kịch bản")
            st.write("Tạo thế giới tổng hợp hoặc nhập JSON đã lưu để dùng chức năng này.")
            a,b=st.columns(2)
            a.button("Thiết lập kịch bản",on_click=navigate,args=(PAGES[2],),type="primary",key="empty_config")
            b.button("Nhập cấu hình JSON",on_click=navigate,args=(PAGES[5],),key="empty_import")
    return q

def remember_result(b):st.session_state["last_bundle"]=b
def show_error(exc):
    st.error(f"Chưa thể thực hiện: {exc}")
    st.caption("Kiểm tra trường vừa thay đổi. Không có kết quả thay thế được tạo khi cấu hình hoặc mô hình có lỗi.")

def figure_options(r):
    no,yes=r.get("no_attack") or {},r.get("with_attack") or {};a,b=no.get("options"),yes.get("options")
    if not isinstance(a,list) or not isinstance(b,list) or len(a)!=len(b):return
    try:
        fig=go.Figure();labels=[f"Lựa chọn {i+1}" for i in range(len(a))]
        fig.add_bar(name="Không can thiệp",x=labels,y=[float(x) for x in a],marker_color="#b5c8c7")
        fig.add_bar(name="Nhánh có hành động",x=labels,y=[float(x) for x in b],marker_color="#087c70")
        fig.update_layout(barmode="group",height=310,margin=dict(l=0,r=12,t=32,b=5),paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font_color="#214653",yaxis_title=yes.get("unit",no.get("unit","Điểm mô hình")),legend=dict(orientation="h",y=1.16,x=0),xaxis=dict(showgrid=False),yaxis=dict(gridcolor="#e5ece9"))
        st.plotly_chart(fig,width="stretch",key=f"chart_{r.get('world_id')}_{r.get('mechanism')}_{r.get('factor_value','single')}")
    except (ValueError,TypeError):st.caption("Giá trị chính xác vẫn được giữ trong dữ liệu xuất; biểu đồ không quyết định outcome.")

def results(bundle,details=True):
    st.subheader("Kết quả từ mô hình")
    rs=bundle.get("results",[]);summary=pd.DataFrame(bundle.get("summary",[]))
    if not rs:return
    if len(rs)>1:
        a,b,c=st.columns(3);a.metric("World nguồn",len({r.get("world_id") for r in rs}));b.metric("Cơ chế được đánh giá",len({r.get("mechanism") for r in rs}));c.metric("Cấu hình tham số",len({str(r.get("factor_value","Một cấu hình")) for r in rs}))
    idx=0
    if details and len(rs)>1:idx=st.selectbox("Xem chi tiết lượt",list(range(len(rs))),format_func=lambda i:f"{rs[i].get('world_id')} · {MECHANISMS.get(rs[i].get('mechanism'),rs[i].get('mechanism'))}"+(f" · {rs[i]['factor_value']}" if "factor_value" in rs[i] else ""),key="result_detail")
    r=rs[idx];state=r.get("state");label=STATE_LABELS.get(state,state or "Chưa xác định")
    messages={"ATTEMPTED_SUCCESS":"Hành động đã đổi outcome sang mục tiêu trong world này.","ATTEMPTED_FAILURE":"Đã thực hiện nhưng không đạt chỉ tiêu đổi outcome sang mục tiêu.","DECLINED":"Kế hoạch đủ điều kiện, nhưng tác tử chọn không hành động theo utility khai báo.","INFEASIBLE":"Kế hoạch không đủ điều kiện theo quyền, thời gian hoặc nguồn lực mô hình.","NOT_READY":"Còn thiếu điều kiện được khai báo hoặc hành vi chưa được triển khai.","OUTCOME_UNKNOWN":"Đã thực hiện nhưng chưa xác định outcome; không thay bằng thất bại."}
    notify=st.success if state=="ATTEMPTED_SUCCESS" else st.warning if state in ("NOT_READY","INFEASIBLE","OUTCOME_UNKNOWN") else st.info
    notify(f"{r.get('mechanism','')} · {label}. {messages.get(state,'Đọc điều kiện và phản ứng trước khi diễn giải.')}")
    no,yes=r.get("no_attack") or {},r.get("with_attack") or {}
    a,b,c=st.columns(3);a.metric("Outcome không can thiệp",OUTCOMES.get(no.get("outcome"),fmt_value(no.get("outcome"))));b.metric("Outcome nhánh hành động",OUTCOMES.get(yes.get("outcome"),fmt_value(yes.get("outcome"))));c.metric("Tiền ròng (TEST_COIN)",fmt_value(r.get("net_cash_expense")))
    if details:figure_options(r)
    if not summary.empty:
        display=summary.copy()
        for name in ("rate_eligible","rate_attempted"):
            if name in display:display[name]=[svc.fmt_rate(None if pd.isna(v) else v) for v in display[name]]
        display=display.rename(columns={"mechanism":"Cơ chế","worlds":"Số world","eligible":"Đủ điều kiện","attempted":"Đã thực hiện","success":"Đổi kết quả thành công","unknown_attempted":"Chưa xác định","rate_eligible":"Thành công / đủ điều kiện","rate_attempted":"Thành công / đã thực hiện","factor_name":"Tham số","factor_value":"Giá trị"})
        st.dataframe(display,width="stretch",hide_index=True)
    st.caption("Tỷ lệ dùng đúng mẫu số từng cột. Một world là minh họa, không phải ước lượng rủi ro thực tế; cơ chế cùng world không là mẫu độc lập.")
    if bundle.get("paired_comparisons"):
        with st.expander("Chênh lệch ghép cặp giữa các cơ chế",expanded=True):
            pairs=pd.DataFrame(bundle["paired_comparisons"])
            if "difference_rate" in pairs:pairs["difference_rate"]=[f"{x*100:+.4f}" if pd.notna(x) else "Không xác định" for x in pairs["difference_rate"]]
            st.dataframe(pairs.rename(columns={"reference":"Đối chứng","comparison":"So sánh","paired_worlds":"Số cặp world","difference_rate":"Chênh lệch (điểm %)","comparison_only":"Chỉ cơ chế so sánh","reference_only":"Chỉ đối chứng"}),width="stretch",hide_index=True)
            st.caption("Chỉ dùng world cùng đủ điều kiện và có policy success xác định; dấu dương nghĩa nhiều ca thành công hơn đối chứng.")
    rows=[]
    for x in rs:
        no,yes=x.get("no_attack") or {},x.get("with_attack") or {}
        rows.append({"World":x.get("world_id"),"Cơ chế":x.get("mechanism"),"Trạng thái":STATE_LABELS.get(x.get("state"),x.get("state")),"Đủ điều kiện":x.get("eligible"),"Đã thực hiện":x.get("attempted"),"Đổi kết quả thành công":x.get("policy_success"),"Outcome nền":no.get("outcome"),"Outcome hành động":yes.get("outcome"),"Nguồn VP/MANA":no.get("source_vp"),"Đơn vị điểm":yes.get("unit"),"Gini ví":yes.get("wallet_gini"),"HHI ví":yes.get("wallet_hhi"),"Tiền ròng TEST_COIN":x.get("net_cash_expense"),"Cơ hội (utility)":x.get("opportunity_cost_utility"),"Vốn (utility)":x.get("capital_cost_utility"),"Hoàn tất (giây mô hình)":x.get("time_to_action_completion"),"Tham số":x.get("factor_value"),"Mã lý do":x.get("reason",x.get("status"))})
    with st.expander("Bảng từng lượt và chỉ số tập trung"):st.dataframe(pd.DataFrame([{k:fmt_value(v) for k,v in row.items()} for row in rows]),width="stretch",hide_index=True)
    with st.expander("Quyết định, phản ứng và nguồn lực chi tiết"):
        a,b=st.columns(2)
        with a:st.json({k:r.get(k) for k in ("state","status","reason","responses","views","information_authorization")})
        with b:st.json({k:r.get(k) for k in ("resources","net_cash_expense","opportunity_cost_utility","capital_cost_utility","time_to_decision","time_to_action_completion","time_to_final_evaluation")})
        st.caption("Utility cá nhân, tiền tổng hợp và quyền khác đơn vị. Không hành động không có success hoặc thời gian hoàn tất.")
    with st.expander("Nguồn kết quả, hash và manifest"):st.code(bundle.get("input_hash",""),language=None);st.json(bundle.get("manifest",{}))
    st.caption(f"Thực thi mới: {bundle.get('elapsed_seconds',0):.3f} giây đồng hồ; khác thời gian sự kiện mô hình.")


def overview():
    header("DAO / LAB · Không gian nghiên cứu","Khám phá cơ chế. Kiểm tra giả định.","Thiết lập thế giới tổng hợp, chạy mô hình Python và đọc kết quả đối chứng có thể tái lập.")
    with st.container(border=True):
        left,right=st.columns([1.6,1])
        with left:
            st.subheader("Bắt đầu một phép mô phỏng")
            st.write("Chọn nguồn lực và điều kiện thông tin, kiểm tra cấu hình rồi chủ động bấm chạy.")
            a,b=st.columns(2)
            a.button("Thiết lập mô phỏng",key="quick_config",type="primary",on_click=navigate,args=(PAGES[2],),width="stretch")
            b.button("Khám phá dữ liệu",key="quick_history",on_click=navigate,args=(PAGES[1],),width="stretch")
            st.caption("01 Chọn giả định  →  02 Thực thi  →  03 So sánh & xuất")
        with right:
            st.markdown("**Thử một ví dụ đã kiểm tra**")
            examples={"SPLIT · chia VP qua nhiều ví":("SPLIT",9),"TW · quyền biểu quyết không đều":("SWITCH",95),"VE · MANA và thời gian khóa":("VE_MOBILIZE",22)}
            chosen=st.selectbox("Ví dụ hướng dẫn",list(examples),label_visibility="collapsed",key="quick_example")
            t,i=examples[chosen]
            st.button("Dùng ví dụ này",key="quick_demo",on_click=navigate,args=(PAGES[2],t,i),width="stretch")
            st.caption("Ví dụ chọn trước. Grant SPLIT vẫn cần cấp tường minh; chọn ví dụ chưa chạy mô hình.")
    st.subheader("Hai nguồn bằng chứng, hai cách đọc")
    a,b=st.columns([1.2,1])
    with a:
        st.markdown("**Lịch sử và kết quả tính lại**")
        st.write("Phiếu được lưu, Baseline và phản thực tế cơ học. Một ví không đồng nghĩa một người đã xác minh.")
        info=svc.history_summary()
        for col,key,label in zip(st.columns(3),["proposals","votes","wallets"],["Đề xuất binding","Phiếu đã lưu","Ví từng tham gia"]):col.metric(label,f"{info[key]:,}".replace(",","."))
    with b:
        st.markdown("**Thế giới tổng hợp Cấp A**")
        st.write("TW, QV theo ví và Capping đối chứng cùng world. VE dùng MANA/lịch khóa riêng. Không có risk score thực tế0–100.")
        st.button("Nạp cấu hình đã lưu",key="quick_import",on_click=navigate,args=(PAGES[5],))
    status=svc.verification_status()
    with st.expander("Phiên bản và phạm vi kiểm chứng"):
        st.write(f"Mô hình: {svc.VERSION} · Giao diện {UI_VERSION}")
        if status.get("verified"):st.success(f"Đã xác minh phiên bản hiện tại · {status.get('total_tests','—')} bài kiểm thử.")
        else:st.info("Giao diện đã đổi so với hồ sơ cũ. Chỉ kiểm thử gắn đúng fingerprint mới xác minh phiên bản hiện tại.")
        st.json(status);st.json(svc.module_manifest())
    st.markdown('<div class="scope-note">Chạy cục bộ, không gửi giao dịch blockchain. Tần suất mô phỏng không phải xác suất thao túng thực tế. Thiếu bằng chứng không được thay bằng0.</div>',unsafe_allow_html=True)

def history():
    header("Bằng chứng quan sát","Dữ liệu Decentraland DAO","Lọc đề xuất và tách kết quả tính lại khỏi trạng thái quản trị được quan sát.")
    with st.spinner("Đọc dữ liệu cục bộ…"):info=svc.history_summary();df=svc.historical_data()
    for col,(label,key) in zip(st.columns(4),[("Đề xuất B binding","proposals"),("Phiếu đã lưu","votes"),("Ví từng tham gia","wallets"),("Đủ điều kiện đối chứng","comparable")]):col.metric(label,f"{info[key]:,}".replace(",","."))
    with st.container(border=True):
        a,b,c=st.columns([1.4,1,1])
        with a:search=st.text_input("Tìm đề xuất",placeholder="Tên đề xuất hoặc Snapshot ID")
        if search:
            mask=pd.Series(False,index=df.index)
            for field in ("title","snapshot_id"):
                if field in df:mask|=df[field].astype(str).str.contains(search,case=False,regex=False)
            df=df[mask]
        with b:
            field="baseline_official_status_observed"
            selected=st.multiselect("Trạng thái quản trị được quan sát",sorted(df[field].dropna().astype(str).unique())) if field in df else []
            if selected:df=df[df[field].astype(str).isin(selected)]
        with c:
            scope=st.selectbox("Phạm vi đối chứng",["Toàn bộ B binding","Đủ điều kiện QV/Capping","Chưa đủ điều kiện QV/Capping"])
            if scope=="Đủ điều kiện QV/Capping":df=df[df["qv_status"]=="ASSESSED"]
            elif scope=="Chưa đủ điều kiện QV/Capping":df=df[df["qv_status"]!="ASSESSED"]
    st.caption(f"{len(df):,} đề xuất phù hợp · Tập đối chứng chọn theo cấu trúc/quy tắc, không theo outcome.")
    names={"title":"Đề xuất","baseline_computed_votes":"Số phiếu","baseline_computed_total_vp":"Tổng VP tính lại","baseline_computed_governance_outcome":"Outcome tính lại","baseline_official_status_observed":"Trạng thái quan sát","qv_status":"Cơ sở đối chứng"}
    st.dataframe(df[[k for k in names if k in df]].rename(columns=names),width="stretch",hide_index=True)
    if df.empty:
        st.info("Không có đề xuất phù hợp. Rút gọn từ khóa hoặc bỏ bớt bộ lọc.")
        return
    titles=df.set_index("snapshot_id")["title"].to_dict()
    sid=st.selectbox("Chi tiết đề xuất",df["snapshot_id"].astype(str).tolist(),format_func=lambda x:f"{str(titles.get(x,''))[:90]} · {x[:12]}…")
    detail=svc.historical_detail(sid);raw=detail.get("proposal",{});base=detail.get("baseline",{})
    st.subheader(raw.get("title","Chi tiết đề xuất"));st.caption(f"Snapshot {sid} · {raw.get('created_utc','Chưa xác định thời điểm')}")
    observed,computed,counter=st.tabs(["Lịch sử & phiếu quan sát","Baseline tính lại","Phản thực tế QV / Capping"])
    with observed:
        a,b=st.columns(2);a.metric("Trạng thái được quan sát",fmt_value(raw.get("baseline_official_status_observed")));b.metric("Phiếu được giữ",fmt_value(base.get("baseline_computed_votes")))
        votes=detail.get("votes")
        if isinstance(votes,pd.DataFrame):
            names={"voter_normalized":"Địa chỉ ví","choice_label":"Lựa chọn","vp":"VP ghi nhận","created_utc":"Thời điểm phiếu"}
            st.dataframe(votes[[k for k in names if k in votes]].rename(columns=names),width="stretch",hide_index=True)
            with st.expander("Bản ghi phiếu và provenance đầy đủ"):st.dataframe(votes,width="stretch",hide_index=True)
        st.caption("Phiếu còn lưu không xác định toàn bộ eligible universe hoặc danh tính/vai trò tấn công của ví.")
    with computed:
        outcome=base.get("baseline_computed_governance_outcome")
        st.metric("Outcome theo Baseline",OUTCOMES.get(outcome,fmt_value(outcome)))
        try:
            scores=json.loads(base.get("baseline_computed_option_vp_json","[]"));labels=json.loads(raw.get("choices_json","[]"))
            if scores:
                if len(labels)!=len(scores):labels=[f"Lựa chọn {i+1}" for i in range(len(scores))]
                st.bar_chart(pd.DataFrame({"Lựa chọn":labels,"VP tính lại":[float(x) for x in scores]}).set_index("Lựa chọn"),color="#087c70")
        except (ValueError,TypeError):st.caption("Giá trị chính xác nằm trong dữ liệu Baseline.")
        st.caption("Quy tắc ứng viên không chứng minh deployment hoặc việc Governance đã thực thi.")
        with st.expander("Quy tắc, cờ thiếu bằng chứng và Baseline đầy đủ"):st.json(base)
    with counter:
        row=df[df["snapshot_id"]==sid].iloc[0]
        if row.get("qv_status")=="ASSESSED":
            st.dataframe(pd.DataFrame([{"Cơ chế":m,"Outcome giả định":row.get(k)} for m,k in [("TW chính sách chung","cap_tw_outcome"),("QV theo ví","qv_qv_outcome"),("Capping theo ví","cap_cap_outcome")]]),hide_index=True,width="stretch")
        else:st.info("Chưa đủ điều kiện đối chứng QV/Capping; không tự tạo outcome thay thế.")
        st.caption("Trọng số giả định trên phiếu quan sát, không phải lịch sử đã xảy ra. VE không tái dựng khi thiếu lịch khóa.")
        with st.expander("Dữ liệu phản thực tế và cờ chi tiết"):st.json({k:v for k,v in row.to_dict().items() if k.startswith(("qv_","cap_"))})
    with st.expander("Toàn bộ trường và cờ kiểm toán"):
        st.dataframe(df,width="stretch",hide_index=True);st.json({k:v for k,v in raw.items() if not k.startswith(("qv_","cap_","baseline_"))})

def configuration():
    header("Thiết lập & thực thi","Một thế giới, giả định rõ ràng","Thiết lập ba bước. Mô hình chỉ chạy khi bạn bấm thực thi.",True)
    with st.container(border=True):
        step("01","Chọn thế giới nguồn")
        opts=svc.templates();ids=[r["id"] for r in opts];labels={r["id"]:r["label"] for r in opts}
        a,b,c=st.columns([2,1,1])
        with a:template=st.selectbox("Mẫu kịch bản",ids,format_func=lambda x:labels[x],key="cfg_template")
        st.session_state.setdefault("cfg_seed",4302027);st.session_state.setdefault("cfg_replicate",9)
        with b:seed=int(st.number_input("Master seed",min_value=0,max_value=2147483647,value=None,step=1,key="cfg_seed"))
        with c:replicate=int(st.number_input("Chỉ số world",min_value=0,max_value=999,value=None,step=1,key="cfg_replicate",help="World 9 được chọn minh họa, không đại diện phân phối rủi ro."))
        st.caption("Nguồn tổng hợp theo hợp đồng. Cùng seed/cấu hình tái tạo cùng đầu ra khoa học.")
    base=svc.build_scenario(template,seed,replicate);cfg=base["config"];ve=cfg.get("ve") is not None;split=cfg["attack"]["family"]=="SPLIT";overrides={}
    with st.container(border=True):
        step("02","Nguồn lực và điều kiện thực hiện")
        l,r=st.columns(2)
        with l:
            st.markdown("**Nguồn lực mô hình**")
            if not ve:
                total=st.text_input("Tổng VP nguồn (VP)",value="",key="cfg_total",placeholder="Giữ tổng VP của world nguồn",help="Hữu hạn và lớn hơn0; không quy VP thành tiền.")
                if total:overrides["total_vp"]=total
                overrides["distribution"]=st.selectbox("Phân bố VP",["preserve","equal","concentrated"],key="cfg_distribution",format_func=lambda x:{"preserve":"Giữ tỷ trọng đã sinh","equal":"Chia đều nguồn","concentrated":"Tập trung theo giả định"}[x])
            overrides["budget"]=st.text_input("Ngân sách attacker giả định (TEST_COIN)",value=str(cfg["principals"][cfg["attacker"]]["budget"]),key=f"budget_{template}",help="Ngân sách chung của chủ thể, không cấp lại theo từng ví.")
            if not ve:overrides["cap_vp"]=st.text_input("Trần khi chạy Capping theo ví (VP)",value=str(cfg["cap_vp"]),key=f"cap_{template}",help="Lớn hơn0; chỉCAP dùng, không phải trần theo người.")
            if split:overrides["alias_count"]=st.selectbox("Số ví chia nguồn k",[1,2,4,8],index=2,key="cfg_alias",help="Chia cùng nguồn VP, không tạo tiền mới.")
        with r:
            if split:
                st.markdown("**Quyền thông tin SPLIT**")
                overrides["information_condition"]=st.selectbox("Điều kiện thông tin",["INFORMED_PROPOSER","UNINFORMED_VOTER","BLOCKED"],key="cfg_information",help="Informed cần grant; uninformed không biết trước kế hoạch; blocked cần quy tắc cấm.")
                overrides["allocation_strategy"]=st.selectbox("Chính sách phân bổ",["TARGETED_PROPOSAL","GENERAL_PREALLOCATION"],key="cfg_allocation",format_func=lambda x:"Nhắm proposal cụ thể" if x=="TARGETED_PROPOSAL" else "Phân bổ tổng quát · chưa triển khai")
                overrides["grant_enabled"]=st.checkbox("Cấp grant thông tin ngoại sinh cho kịch bản",value=False,key="cfg_grant",help="Quyền giả định có role/content/timeline; không chứng minh proposer thật biết trước.")
                overrides["block_enabled"]=st.checkbox("Khai báo quy tắc cấm SPLIT ngoại sinh",value=False,key="cfg_block",help="Chỉ áp dụng nhánh BLOCKED; có thể khai báo cho lướiTypeB, không cấm toàn cục mọi nhánh.")
                st.caption("Grant chỉ dùng nhánh informed; rule chỉ dùng BLOCKED. Phân bổ cần xong trước snapshot. Thiếu hoặc xung đột điều kiện sẽ được báo rõ.")
            elif ve:
                st.markdown("**MANA và trạng thái khóa**")
                overrides["mana_scale"]=st.text_input("Hệ số MANA đủ điều kiện (giả định)","1",key="cfg_mana")
                overrides["lock_amount_fraction"]=str(st.slider("Tỷ lệ MANA khóa",0.01,1.0,0.5,0.01,key="cfg_lock_amount"))
                overrides["lock_remaining_fraction"]=str(st.slider("Tỷ lệ thời gian còn lại khả thi tại snapshot",0.01,1.0,0.5,0.01,key="cfg_lock_remaining",help="Theo phần tối đa còn lại khả thi, không phải tuổi ví."))
                st.caption("VE dùng MANA và lịch khóa riêng, không xếp chung đối chứng VP.")
            else:
                st.markdown("**Điều kiện của mẫu**")
                st.write("Quyền và phản ứng lấy từ world đã sinh. Chi phí utility và lịch hành động có thể mở ở phần nâng cao.")
                st.caption("Không suy động cơ ví thật từ dữ liệu lịch sử.")
    with st.expander("Nâng cao · lịch sự kiện và chi phí hành vi"):
        overrides["snapshot_time"]=int(st.number_input("Snapshot",min_value=86401,value=int(cfg["proposal"]["snapshot_time"]),step=1,key=f"snapshot_time_{template}"))
        custom=st.checkbox("Tùy chỉnh mốc hành động tuyệt đối",value=False,key=f"custom_schedule_{template}")
        if custom:
            schedule=[("published_at","Công bố hành động"),("decision_at","Quyết định")]+([("allocation_at","Hoàn tất phân bổ")] if split else [])
            for col,(key,label) in zip(st.columns(len(schedule)),schedule):
                with col:overrides[key]=int(st.number_input(label,min_value=0,value=int(cfg["attack"][key]),step=1,key=f"{key}_{template}"))
            st.caption("Đổi snapshot cần chỉnh lịch tuyệt đối nhất quán; SPLIT cần thông tin trước quyết định và phân bổ trước snapshot.")
        else:st.caption("Đổi snapshot dịch cùng lịch tương đối, quyền và khóa qua service.")
        for col,key,label in zip(st.columns(4),["resource_utility","risk_utility","opportunity_utility","capital_utility"],["Nguồn lực utility","Rủi ro utility","Cơ hội utility","Vốn utility"]):
            with col:overrides[key]=st.text_input(label,str(cfg["attack"].get(key,"0")),key=f"{key}_{template}")
        st.caption("Utility cá nhân khác TEST_COIN. Giây theo lịch mô hình, không phải thời gian giao dịch thật.")
    try:
        request=svc.build_scenario(template,seed,replicate,overrides);h=svc.request_hash(request)
        if st.session_state.get("current_hash")!=h:clear_results()
        st.session_state["current_request"]=request;st.session_state["current_hash"]=h;st.session_state["batch_source"]=(template,seed,overrides)
        context(request)
        with st.container(border=True):
            step("03","Kiểm tra và thực thi")
            a,b=st.columns([1.2,1])
            with a:selected=st.selectbox("Cơ chế cho một lượt",["VE"] if ve else ["TW","QV","CAP"],format_func=lambda x:MECHANISMS[x],key="cfg_mechanism")
            with b:st.caption("Đầu vào hợp lệ về cấu trúc. Model kiểm khả thi và quyết định khi chạy.")
            a,b,c=st.columns(3)
            if a.button("Thực thi kịch bản",type="primary",key="run_single",width="stretch"):
                with st.spinner("Đang gọi mô hình Python…"):remember_result(svc.run_scenario(request,[selected]))
                st.session_state["single_mechanism"]=selected
            b.button("So sánh cơ chế",on_click=navigate,args=(PAGES[3],),key="config_compare",width="stretch")
        bundle=st.session_state.get("last_bundle")
        if bundle and bundle.get("input_hash")==h and st.session_state.get("single_mechanism")==selected and bundle.get("model_fingerprint")==svc.module_manifest()["model_fingerprint"]:results(bundle)
        with st.expander("Kiểm tra cấu hình JSON, grant và khóa snapshot"):
            st.code(h,language=None);st.json(request)
            if ve:
                snapshot=request["config"]["proposal"]["snapshot_time"]
                locks=[{"Ví":e["wallet"],"MANA khóa":e["amount"],"CREATE":e["time"],"Kết thúc":e["end"],"Còn lại tại snapshot (giây)":e["end"]-snapshot} for e in request["config"]["ve"]["events"] if e["kind"]=="CREATE"]
                st.dataframe(pd.DataFrame(locks),width="stretch",hide_index=True)
                st.caption("EXTEND tương lai không thay đổi snapshot cũ.")
    except (ValueError,TypeError,KeyError) as exc:
        st.session_state.pop("current_request",None);clear_results();show_error(exc)
    st.button("Khôi phục mẫu",on_click=reset_configuration,key="reset_template",help="Giữ mẫu, seed, world; đưa nguồn lực/quyền về mặc định, kể cả khi đầu vào không hợp lệ.")


def comparison():
    header("Đối chứng có ghép cặp","So sánh cơ chế trên cùng world","Giữ chung tác tử, nguồn lực, quyền, seed và lịch. Chỉ đổi cơ chế trọng số.",True)
    request=require_request()
    if request is None:return
    context(request);ve=request["config"].get("ve") is not None;mechs=["VE"] if ve else ["TW","QV","CAP"]
    if ve:st.info("World dùng MANA/khóa. Chỉ đánh giá VE trong nhóm tương thích, không xếp cùng đối chứng VP.")
    else:st.caption("QV căn bậc hai theo ví; Capping theo ví. Không đồng nhất QV cổ điển hoặc trần theo chủ thể.")
    with st.container(border=True):
        a,b=st.columns([2,1])
        with a:mode=st.radio("Phạm vi thực thi",["Một world hiện tại","Nhóm world mới"],horizontal=True)
        with b:count=st.number_input("Số world tổng hợp",1,30,5,1,disabled=mode=="Một world hiện tại")
        signature=(svc.request_hash(request),mode,int(count),svc.module_manifest()["model_fingerprint"])
        if st.button("Chạy đối chứng",type="primary"):
            try:
                if mode=="Một world hiện tại":
                    with st.spinner("Đánh giá các cơ chế…"):bundle=svc.run_scenario(request,mechs)
                else:
                    src=st.session_state.get("batch_source")
                    if src is None:raise ValueError("JSON nhập lại chỉ có một world. Thiết lập từ mẫu để sinh batch.")
                    bar=st.progress(0,text="Sinh và thực thi world…")
                    def progress(done,total):bar.progress(done/total,text=f"World {done}/{total}")
                    bundle=svc.run_batch(src[0],src[1],int(count),src[2],mechs,progress)
                st.session_state["comparison_bundle"]=bundle;st.session_state["comparison_signature"]=signature;remember_result(bundle)
            except (ValueError,TypeError,KeyError) as exc:show_error(exc)
        st.caption("Tối đa30world, phân phối giả định theo loại mẫu. Cơ chế cùng world được giữ ghép cặp.")
    bundle=st.session_state.get("comparison_bundle")
    if bundle:
        if st.session_state.get("comparison_signature")==signature:results(bundle)
        else:st.info("Cấu hình đã thay đổi. Bấm chạy đối chứng để cập nhật.")

def sensitivity():
    header("Khám phá độ nhạy","Hiểu sự phụ thuộc vào giả định","Tách tái trọng số kết quả đã có với thực sự chạy lại mô hình.",True)
    kind=st.radio("Phương pháp",["Type A · tái trọng số dữ liệu đã có","Type B · tái mô phỏng"],horizontal=True)
    if kind.startswith("Type A"):
        with st.container(border=True):
            p=st.slider("Tỷ trọng SPLIT trong cơ hội đủ điều kiện (%)",0.0,100.0,2.91,0.01)
            shown=pd.DataFrame(svc.type_a(p/100))
            for name in ("rate","lower_delta95","upper_delta95"):shown[name]*=100
            st.dataframe(shown[["mechanism","rate","lower_delta95","upper_delta95"]].rename(columns={"mechanism":"Cơ chế","rate":"Tỷ lệ mô phỏng (%)","lower_delta95":"Cận dưới Δ so TW (điểm %)","upper_delta95":"Cận trên Δ so TW (điểm %)"}),width="stretch",hide_index=True)
        st.caption("Không sinh world mới. Đây là hỗn hợp cơ hội mô phỏng, không phải tỷ lệ gian lận lịch sử.")
        st.info("Điểm giao QV–TW ước lượng2,9056%; chỉ75,65%bootstrap có nghiệm trong[0,1]. Không phải ngưỡng an toàn chắc chắn.")
        with st.expander("Cách đọc bất định và dữ liệu bootstrap"):
            st.write("24,35% nghiệm ngoài miền. Không dùng khoảng hẹp[1,8%;4,5%]. Khoảng chênh lệch là percentile pointwise95%, không phải dải đồng thời hoặc CI vô điều kiện của p*. CAP−TW giao tại biên p=0.")
            st.json(svc.crossover_info())
    else:
        request=require_request()
        if request is None:return
        context(request);ve=request["config"].get("ve") is not None
        params={"lock_remaining_fraction":"Thời gian khóa còn lại","lock_amount_fraction":"Tỷ lệ MANA khóa"} if ve else {"alias_count":"Số ví SPLIT","cap_vp":"Trần VP/ví","budget":"Ngân sách TEST_COIN","information_condition":"Điều kiện thông tin"}
        if not ve and request["config"]["attack"]["family"]!="SPLIT":params={k:v for k,v in params.items() if k not in ("alias_count","information_condition")}
        with st.container(border=True):
            a,b=st.columns([1,2])
            with a:param=st.selectbox("Tham số khảo sát",list(params),format_func=lambda x:params[x])
            defaults={"alias_count":"1,2,4,8","cap_vp":"25000,50000,100000,200000","budget":"0,10,100","information_condition":"INFORMED_PROPOSER,UNINFORMED_VOTER,BLOCKED","lock_remaining_fraction":"0.25,0.5,1","lock_amount_fraction":"0.5,1"}
            with b:raw=st.text_input("Các giá trị thực thi, cách nhau dấu phẩy",defaults[param],key=f"grid_{param}")
            signature=(svc.request_hash(request),param,raw,svc.module_manifest()["model_fingerprint"])
            if st.button("Chạy lưới Type B",type="primary"):
                try:
                    vals=[v.strip() for v in raw.split(",") if v.strip()]
                    if param=="alias_count":vals=[int(v) for v in vals]
                    with st.spinner("Thực thi từng cấu hình…"):bundle=svc.run_sensitivity(request,param,vals)
                    st.session_state["sensitivity_bundle"]=bundle;st.session_state["sensitivity_signature"]=signature;remember_result(bundle)
                except (ValueError,TypeError,KeyError) as exc:show_error(exc)
            st.caption("2–8 giá trị khác nhau, chỉ hiển thị điểm đã chạy. Grant và rule phải khai báo trong cấu hình nguồn.")
        bundle=st.session_state.get("sensitivity_bundle")
        if bundle and st.session_state.get("sensitivity_signature")==signature:results(bundle)
        elif bundle:st.info("Lưới đã thay đổi. Chạy lại để xem kết quả phù hợp.")

def exports():
    header("Tái lập & xuất","Lưu và tiếp tục một thí nghiệm","Nhập cấu hình đã lưu hoặc tải đầu ra lần thực thi gần nhất. Giữ seed, nguồn và giá trị chưa biết.")
    with st.container(border=True):
        st.subheader("Nhập cấu hình")
        a,b=st.columns(2)
        with a:uploaded=st.file_uploader("Nạp cấu hình kịch bản JSON",type=["json"])
        with b:text=st.text_area("Hoặc dán cấu hình JSON",height=120,placeholder='{"schema": …, "config": …}')
        if st.button("Kiểm tra & nạp cấu hình"):
            try:
                source=uploaded.getvalue().decode("utf-8-sig") if uploaded is not None else text
                q=svc.import_scenario(source);st.session_state["current_request"]=q;st.session_state["current_hash"]=svc.request_hash(q)
                clear_results();st.session_state.pop("batch_source",None)
                st.success("Đã nạp cấu hình hợp lệ. Bấm thực thi bên dưới; mặc định trang thiết lập không ghi đè JSON đang nạp.")
            except (ValueError,TypeError,KeyError,UnicodeError) as exc:show_error(exc)
        st.caption("Ưu tiên tệp nếu có cả tệp và văn bản. Chỉ nhận schema mô hình, không cần khóa ví hay seed phrase.")
    q=current_request()
    if q:
        context(q);a,b=st.columns(2)
        if a.button("Thực thi cấu hình đang nạp",type="primary",width="stretch"):
            try:
                with st.spinner("Đang thực thi cấu hình…"):remember_result(svc.run_scenario(q))
            except (ValueError,TypeError,KeyError) as exc:show_error(exc)
        b.download_button("Tải cấu hình hiện tại JSON",json.dumps(q,ensure_ascii=False,indent=2),file_name="scenario.json",mime="application/json",width="stretch")
        with st.expander("Xem cấu hình đang hoạt động"):st.json(q)
    bundle=st.session_state.get("last_bundle")
    if not bundle:st.info("Chưa có kết quả để xuất. Thực thi một kịch bản hoặc nhóm world trước.");return
    try:
        artifacts=svc.export_bundle(bundle);st.subheader("Tải bộ kết quả")
        labels={"scenario.json":"Cấu hình · JSON","world_results.csv":"Từng lượt · CSV","summary.csv":"Tổng hợp · CSV","manifest.json":"Nguồn & phiên bản · JSON","report.md":"Báo cáo ngắn · Markdown","chart.svg":"Biểu đồ · SVG"}
        with st.container(border=True):
            cols=st.columns(3)
            for i,(name,data) in enumerate(artifacts.items()):
                mime="application/json" if name.endswith(".json") else "text/csv" if name.endswith(".csv") else "image/svg+xml" if name.endswith(".svg") else "text/markdown"
                cols[i%3].download_button(labels.get(name,name),data,file_name=name,mime=mime,key=f"download_{name}",width="stretch")
            st.caption("CSV giữ ô rỗng cho chưa biết. Manifest chứa hash, phiên bản và request nhóm; timing không cần giống byte.")
        results(bundle)
    except (ValueError,TypeError,KeyError) as exc:show_error(exc)

def main():
    theme();fp=svc.module_manifest()["model_fingerprint"]
    for key in ("last_bundle","comparison_bundle","sensitivity_bundle"):
        b=st.session_state.get(key)
        if b and b.get("model_fingerprint")!=fp:st.session_state.pop(key,None)
    with st.sidebar:
        st.markdown('<div class="rail-brand"><span>◈</span> DAO / LAB</div><div class="rail-kicker">PHÒNG MÔ PHỎNG NGHIÊN CỨU</div>',unsafe_allow_html=True)
        page=st.radio("Không gian nghiên cứu",PAGES,label_visibility="collapsed",key="page")
        q=current_request()
        if q:
            c=q["config"];src=q.get("source",{})
            st.markdown(f'<div class="rail-context"><strong>THÍ NGHIỆM HIỆN TẠI</strong><br>{html.escape(FAMILIES.get(c["attack"]["family"],c["attack"]["family"]))}<br>Seed {html.escape(str(src.get("master_seed","—")))} · World {html.escape(str(src.get("replicate","—")))}<br>{"MANA / khóa riêng" if c.get("ve") else "Nguồn VP tổng hợp"}</div>',unsafe_allow_html=True)
        else:st.caption("Chưa có kịch bản. Bắt đầu từ thiết lập hoặc nhập JSON.")
        st.divider();st.caption("Giao diện 2.0 · Cục bộ · Offline");st.caption("Quan sát lịch sử ≠ giả định tổng hợp")
    routes={PAGES[0]:overview,PAGES[1]:history,PAGES[2]:configuration,PAGES[3]:comparison,PAGES[4]:sensitivity,PAGES[5]:exports}
    try:routes[page]()
    except Exception as exc:
        show_error(exc)
        with st.expander("Chi tiết lỗi để kiểm tra cục bộ"):st.exception(exc)

if __name__=="__main__":main()

