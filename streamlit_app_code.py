import streamlit as st
import pandas as pd
import mysql.connector
from datetime import datetime
import os

# Page configuration
st.set_page_config(
    page_title="SEGUROPAR Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to match HTML styling
st.markdown("""
<style>
    .main {
        background-color: #f3f4f6;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border-left: 4px solid;
        margin-bottom: 1rem;
    }
    .metric-card.red {
        border-left-color: #ef4444;
    }
    .metric-card.green {
        border-left-color: #10b981;
    }
    .metric-card.yellow {
        border-left-color: #f59e0b;
    }
    .metric-card.blue {
        border-left-color: #3b82f6;
    }
    .metric-card.indigo {
        border-left-color: #6366f1;
    }
    .metric-card.orange {
        border-left-color: #f97316;
    }
    .metric-title {
        font-size: 0.875rem;
        font-weight: 500;
        color: #6b7280;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #111827;
    }
    .metric-detail {
        font-size: 0.875rem;
        color: #6b7280;
        margin-top: 0.25rem;
    }
    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
        display: inline-block;
    }
    .status-open {
        background-color: #fef3c7;
        color: #92400e;
    }
    .status-investigation {
        background-color: #fee2e2;
        color: #991b1b;
        font-weight: 600;
    }
    .status-settled {
        background-color: #d1fae5;
        color: #065f46;
    }
    .status-denied {
        background-color: #f3f4f6;
        color: #374151;
    }
    .fraud-high {
        background-color: #fee2e2;
        color: #991b1b;
        font-weight: 600;
    }
    .fraud-medium {
        color: #ea580c;
    }
    .high-value-tag {
        background-color: #ede9fe;
        color: #6b21a8;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.125rem 0.5rem;
        border-radius: 0.25rem;
        display: inline-block;
        margin-top: 0.25rem;
    }
    .short-time-tag {
        background-color: #ddd6fe;
        color: #5b21b6;
        font-size: 0.75rem;
        font-weight: 500;
        padding: 0.125rem 0.5rem;
        border-radius: 9999px;
        display: inline-block;
    }
    div[data-testid="stDataFrame"] {
        background: white;
        border-radius: 0.75rem;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    h1 {
        color: #111827;
        font-weight: 800;
    }
    h2 {
        color: #1f2937;
        font-weight: 700;
        border-left: 4px solid;
        padding-left: 0.75rem;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    h2.financial {
        border-left-color: #10b981;
    }
    h2.fraud {
        border-left-color: #ef4444;
    }
    h2.risk {
        border-left-color: #f97316;
    }
</style>
""", unsafe_allow_html=True)

# Database connection function
@st.cache_resource
def get_db_connection():
    """Create database connection with caching"""
    try:
        # Try to use Streamlit secrets first (for deployment)
        if hasattr(st, 'secrets') and 'database' in st.secrets:
            connection = mysql.connector.connect(
                host=st.secrets["database"]["host"],
                port=st.secrets["database"]["port"],
                user=st.secrets["database"]["user"],
                password=st.secrets["database"]["password"],
                database=st.secrets["database"]["database"]
            )
        else:
            # Fallback to environment variables or hardcoded (for local dev)
            connection = mysql.connector.connect(
                host=os.getenv("DB_HOST", "db-mysql-itom-do-user-28250611-0.j.db.ondigitalocean.com"),
                port=int(os.getenv("DB_PORT", "25060")),
                user=os.getenv("DB_USER", "5037_car"),
                password=os.getenv("DB_PASSWORD", "Pass2025_5037"),
                database=os.getenv("DB_NAME", "5037_car")
            )
        return connection
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        return None

# Query functions
def fetch_fraud_analytics():
    """Fetch data from fraud analytics view"""
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()
    
    query = """
    SELECT 
        Claim_ID as id,
        Policyholder_Name as policyholder,
        Fraud_Probability as fraud_prob,
        Claim_Amount_Requested as amount_requested,
        Settlement_Status as status,
        DATEDIFF(Submission_Date, Policy.Start_Date) as days_to_claim,
        Credit_Score as credit_score,
        Vehicle.Make as make,
        Is_Fraudulent_Flag as is_fraudulent
    FROM V_FRAUD_ANALYTICS_DASHBOARD
    LEFT JOIN Policy ON V_FRAUD_ANALYTICS_DASHBOARD.Policy_ID = Policy.Policy_ID
    LEFT JOIN Vehicle ON Policy.VIN = Vehicle.VIN
    ORDER BY Fraud_Probability DESC
    """
    
    try:
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Query error: {e}")
        conn.close()
        return pd.DataFrame()

def fetch_validation_queue():
    """Fetch claims requiring manager validation"""
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame()
    
    query = """
    SELECT 
        c.Claim_ID as id,
        CONCAT(ph.First_Name, ' ', ph.Last_Name) as policyholder,
        c.Claim_Amount_Requested as amount_requested,
        c.Settlement_Status as status,
        CONCAT(a.First_Name, ' ', a.Last_Name) as last_event_agent,
        MAX(ce.Event_Date) as last_event_time
    FROM Claim c
    JOIN Policyholder ph ON c.Policyholder_ID = ph.Policyholder_ID
    LEFT JOIN Claim_Event ce ON c.Claim_ID = ce.Claim_ID
    LEFT JOIN Agent a ON ce.Agent_ID = a.Agent_ID
    WHERE c.Claim_Amount_Requested >= 20000 
       OR c.Settlement_Status IN ('Denied', 'Settled')
    GROUP BY c.Claim_ID, ph.First_Name, ph.Last_Name, c.Claim_Amount_Requested, c.Settlement_Status, a.First_Name, a.Last_Name
    ORDER BY c.Claim_Amount_Requested DESC
    LIMIT 20
    """
    
    try:
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Query error: {e}")
        conn.close()
        return pd.DataFrame()

def fetch_agent_workload():
    """Fetch agent performance data"""
    conn = get_db_connection()
    if conn is None:
        return {}
    
    query = """
    SELECT 
        CONCAT(a.First_Name, ' ', a.Last_Name, ' (ID ', a.Agent_ID, ')') as agent_name,
        COUNT(ce.Event_ID) as event_count,
        AVG(DATEDIFF(c.Settlement_Date, c.Submission_Date)) as avg_processing_days
    FROM Agent a
    LEFT JOIN Claim_Event ce ON a.Agent_ID = ce.Agent_ID
    LEFT JOIN Claim c ON ce.Claim_ID = c.Claim_ID
    GROUP BY a.Agent_ID, a.First_Name, a.Last_Name
    ORDER BY event_count DESC
    LIMIT 3
    """
    
    try:
        df = pd.read_sql(query, conn)
        
        # Get summary stats
        summary_query = """
        SELECT 
            COUNT(DISTINCT c.Claim_ID) as total_claims,
            COUNT(CASE WHEN c.Settlement_Status IN ('Open', 'In Investigation') THEN 1 END) as pending_validation,
            AVG(DATEDIFF(COALESCE(c.Settlement_Date, CURDATE()), c.Submission_Date)) as avg_processing_days
        FROM Claim c
        """
        summary = pd.read_sql(summary_query, conn)
        
        conn.close()
        
        return {
            'top_agents': df.to_dict('records'),
            'total_claims_managed': int(summary['total_claims'].iloc[0]) if not summary.empty else 0,
            'pending_validation': int(summary['pending_validation'].iloc[0]) if not summary.empty else 0,
            'avg_processing_days': round(float(summary['avg_processing_days'].iloc[0]), 1) if not summary.empty else 0
        }
    except Exception as e:
        st.error(f"Query error: {e}")
        conn.close()
        return {}

def fetch_executive_kpis():
    """Fetch executive dashboard KPIs"""
    conn = get_db_connection()
    if conn is None:
        return {}
    
    try:
        # Financial metrics
        financial_query = """
        SELECT 
            SUM(p.Premium_Amount) as total_premiums,
            SUM(CASE WHEN c.Settlement_Status = 'Settled' THEN c.Claim_Amount_Settled ELSE 0 END) as total_settlements
        FROM Policy p
        LEFT JOIN Claim c ON p.Policy_ID = c.Policy_ID
        WHERE YEAR(p.Start_Date) = YEAR(CURDATE())
        """
        financial = pd.read_sql(financial_query, conn)
        
        total_premiums = float(financial['total_premiums'].iloc[0] or 0)
        total_settlements = float(financial['total_settlements'].iloc[0] or 0)
        loss_ratio = (total_settlements / total_premiums * 100) if total_premiums > 0 else 0
        
        # Fraud metrics
        fraud_query = """
        SELECT 
            COUNT(*) as total_cases,
            SUM(CASE WHEN Is_Fraudulent_Flag = 1 THEN 1 ELSE 0 END) as confirmed_fraud,
            SUM(CASE WHEN Settlement_Status = 'Denied' THEN 1 ELSE 0 END) as denied_claims
        FROM V_FRAUD_ANALYTICS_DASHBOARD
        """
        fraud = pd.read_sql(fraud_query, conn)
        
        total_cases = int(fraud['total_cases'].iloc[0] or 0)
        confirmed_fraud = int(fraud['confirmed_fraud'].iloc[0] or 0)
        fraud_rate = (confirmed_fraud / total_cases * 100) if total_cases > 0 else 0
        
        # High-risk customers
        risk_query = """
        SELECT 
            CONCAT(ph.First_Name, ' ', ph.Last_Name) as customer_name,
            ph.Credit_Score as credit_score,
            COUNT(c.Claim_ID) as claim_count,
            SUM(c.Claim_Amount_Requested) as total_claim_value
        FROM Policyholder ph
        JOIN Claim c ON ph.Policyholder_ID = c.Policyholder_ID
        WHERE ph.Credit_Score < 650
        GROUP BY ph.Policyholder_ID, ph.First_Name, ph.Last_Name, ph.Credit_Score
        HAVING claim_count >= 2
        ORDER BY claim_count DESC, ph.Credit_Score ASC
        LIMIT 5
        """
        risk_customers = pd.read_sql(risk_query, conn)
        
        conn.close()
        
        return {
            'loss_ratio': round(loss_ratio, 1),
            'total_premiums': total_premiums,
            'total_settlements': total_settlements,
            'confirmed_fraud_rate': round(fraud_rate, 1),
            'total_cases_processed': total_cases,
            'successful_fraud_interventions': int(fraud['denied_claims'].iloc[0] or 0),
            'churn_rate': 12.5,  # Placeholder - would need churn calculation
            'clv_increase_ytd': 7.2,  # Placeholder - would need CLV calculation
            'top_risk_customers': risk_customers.to_dict('records')
        }
    except Exception as e:
        st.error(f"Query error: {e}")
        conn.close()
        return {}

# Metric card component
def metric_card(title, value, detail="", color="blue"):
    """Display a styled metric card"""
    st.markdown(f"""
    <div class="metric-card {color}">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-detail">{detail}</div>
    </div>
    """, unsafe_allow_html=True)

# Navigation
def main():
    # Sidebar navigation
    st.sidebar.title("🛡️ SEGUROPAR")
    st.sidebar.markdown("---")
    
    view = st.sidebar.radio(
        "Select a view:",
        ["⚠️ Fraud Analyst", "💼 Claims Manager", "💸 Executive KPIs"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info("**Database:** Connected to 5037_car")
    
    # Route to different dashboards
    if view == "⚠️ Fraud Analyst":
        fraud_analyst_dashboard()
    elif view == "💼 Claims Manager":
        claims_manager_dashboard()
    else:
        executive_kpi_dashboard()

# FRAUD ANALYST DASHBOARD
def fraud_analyst_dashboard():
    st.markdown("# ⚠️ SEGUROPAR Fraud Analyst Dashboard")
    st.markdown("Prioritized claims queue, driven by real-time predictive analytics from the database.")
    st.markdown("---")
    
    # Fetch data
    with st.spinner("Loading fraud detection data..."):
        df = fetch_fraud_analytics()
    
    if df.empty:
        st.warning("No data available. Please check database connection.")
        return
    
    # KPI Cards
    high_priority = len(df[df['fraud_prob'] >= 0.75])
    avg_fraud_prob = df['fraud_prob'].mean() * 100
    confirmed_fraud = df['is_fraudulent'].sum() if 'is_fraudulent' in df.columns else 0
    total_claims = len(df)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        metric_card("High-Priority Claims", str(high_priority), "", "red")
    with col2:
        metric_card("Average Fraud Probability", f"{avg_fraud_prob:.1f}%", "", "orange")
    with col3:
        metric_card("Confirmed Fraud (YTD)", str(int(confirmed_fraud)), "", "red")
    with col4:
        metric_card("Total Claims in System", str(total_claims), "", "indigo")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Filter
    credit_filter = st.selectbox(
        "🔍 Filter by Credit Score:",
        [999, 700, 600, 550],
        format_func=lambda x: "All High Priority Claims" if x == 999 else f"Credit Score Below {x}"
    )
    
    # Apply filters
    filtered_df = df[df['fraud_prob'] >= 0.75].copy()
    if credit_filter != 999:
        filtered_df = filtered_df[filtered_df['credit_score'] < credit_filter]
    
    # Display table
    st.markdown(f"### 🔴 Claims Requiring Immediate Investigation ({len(filtered_df)} records)")
    
    if not filtered_df.empty:
        # Format display
        display_df = filtered_df.copy()
        display_df['fraud_prob'] = (display_df['fraud_prob'] * 100).round(1).astype(str) + '%'
        display_df['amount_requested'] = '$' + display_df['amount_requested'].apply(lambda x: f"{x:,.0f}")
        display_df['policyholder_info'] = display_df['policyholder'] + ' (CS: ' + display_df['credit_score'].astype(str) + ')'
        
        # Highlight short policy-to-claim time
        display_df['days_flag'] = display_df['days_to_claim'].apply(
            lambda x: f"{x} days 🟣 Short P:C" if x <= 30 else f"{x} days"
        )
        
        st.dataframe(
            display_df[['id', 'policyholder_info', 'make', 'fraud_prob', 'amount_requested', 'days_flag', 'status']].rename(columns={
                'id': 'ID',
                'policyholder_info': 'Policyholder (Credit Score)',
                'make': 'Vehicle',
                'fraud_prob': 'Fraud Probability',
                'amount_requested': 'Amount Requested',
                'days_flag': 'Policy-to-Claim Time',
                'status': 'Status'
            }),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No high-priority claims match the current filter criteria.")

# CLAIMS MANAGER DASHBOARD
def claims_manager_dashboard():
    st.markdown("# 💼 Claims Manager Dashboard")
    st.markdown("Oversight and validation hub for active claims and agent performance.")
    st.markdown("---")
    
    # Fetch data
    with st.spinner("Loading claims manager data..."):
        workload_data = fetch_agent_workload()
        validation_queue = fetch_validation_queue()
    
    if not workload_data:
        st.warning("No data available. Please check database connection.")
        return
    
    # KPI Cards
    col1, col2, col3 = st.columns(3)
    
    with col1:
        metric_card("Claims Pending Validation", str(workload_data['pending_validation']), "", "yellow")
    with col2:
        metric_card("Avg. Processing Time", f"{workload_data['avg_processing_days']} Days", "", "indigo")
    with col3:
        metric_card("Total Claims Handled (YTD)", str(workload_data['total_claims_managed']), "", "green")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Agent Performance
    st.markdown("## 👥 Agent Performance Summary (Event Count)")
    
    if workload_data['top_agents']:
        cols = st.columns(3)
        for idx, agent in enumerate(workload_data['top_agents']):
            with cols[idx]:
                st.markdown(f"""
                <div style="background: #eef2ff; padding: 1rem; border-radius: 0.5rem; text-align: center;">
                    <div style="font-weight: 500; color: #312e81; margin-bottom: 0.5rem;">{agent['agent_name']}</div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #4338ca;">{int(agent['event_count'])} Events</div>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Validation Queue
    st.markdown("### 🟡 Claims Requiring Manager Validation")
    
    if not validation_queue.empty:
        display_df = validation_queue.copy()
        display_df['amount_requested'] = '$' + display_df['amount_requested'].apply(lambda x: f"{x:,.0f}")
        display_df['high_value'] = display_df['amount_requested'].str.replace('$', '').str.replace(',', '').astype(float) >= 20000
        display_df['policyholder_display'] = display_df.apply(
            lambda row: f"{row['policyholder']}\n🟣 High-Value Review" if row['high_value'] else row['policyholder'],
            axis=1
        )
        
        st.dataframe(
            display_df[['id', 'policyholder', 'amount_requested', 'last_event_agent', 'last_event_time', 'status']].rename(columns={
                'id': 'ID',
                'policyholder': 'Policyholder',
                'amount_requested': 'Amount Requested',
                'last_event_agent': 'Last Agent Event',
                'last_event_time': 'Last Event Time',
                'status': 'Status'
            }),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.success("No claims currently require manager validation. Great job!")

# EXECUTIVE KPI DASHBOARD
def executive_kpi_dashboard():
    st.markdown("# 💸 Executive Management Dashboard")
    st.markdown("Strategic Key Performance Indicators for Profitability, Fraud Prevention, and Customer Retention.")
    st.markdown("---")
    
    # Fetch data
    with st.spinner("Loading executive KPI data..."):
        kpi_data = fetch_executive_kpis()
    
    if not kpi_data:
        st.warning("No data available. Please check database connection.")
        return
    
    # Financial Health Section
    st.markdown('<h2 class="financial">Financial Health & Profitability</h2>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        color = "red" if kpi_data['loss_ratio'] > 50 else "green"
        metric_card("Claim Loss Ratio", f"{kpi_data['loss_ratio']:.1f}%", 
                   "Total settlements paid vs. premiums collected", color)
    with col2:
        metric_card("Premiums Collected (YTD)", f"${kpi_data['total_premiums']/1000000:.2f}M", 
                   "Total YTD revenue from policy premiums", "green")
    with col3:
        metric_card("Settlements Paid (YTD)", f"${kpi_data['total_settlements']/1000:.0f}K", 
                   "Total claims cost (Losses) incurred", "red")
    with col4:
        metric_card("CLV Increase (YTD)", f"+{kpi_data['clv_increase_ytd']}%", 
                   "Customer Lifetime Value growth", "blue")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Fraud & Risk Management Section
    st.markdown('<h2 class="fraud">Fraud & Risk Management Effectiveness</h2>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        metric_card("Confirmed Fraud Rate", f"{kpi_data['confirmed_fraud_rate']:.1f}%", 
                   "Percentage of claims confirmed as fraudulent", "red")
    with col2:
        metric_card("Total Cases Processed", str(kpi_data['total_cases_processed']), 
                   "Total finalized claim files YTD", "indigo")
    with col3:
        metric_card("Successful Interventions", str(kpi_data['successful_fraud_interventions']), 
                   "Total denied fraudulent claims", "green")
    with col4:
        color = "orange" if kpi_data['churn_rate'] > 10 else "green"
        metric_card("Annual Churn Rate", f"{kpi_data['churn_rate']:.1f}%", 
                   "Policies cancelled before term completion", color)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # High-Risk Customers Section
    st.markdown('<h2 class="risk">Top High-Risk Customers (For Review)</h2>', unsafe_allow_html=True)
    st.markdown("### Customers with Highest Claim Frequency & Lowest Credit Scores")
    
    if kpi_data['top_risk_customers']:
        risk_df = pd.DataFrame(kpi_data['top_risk_customers'])
        risk_df['total_claim_value'] = '$' + risk_df['total_claim_value'].apply(lambda x: f"{x:,.0f}")
        
        st.dataframe(
            risk_df.rename(columns={
                'customer_name': 'Customer Name',
                'credit_score': 'Credit Score',
                'claim_count': 'Total Claims Filed',
                'total_claim_value': 'Total Claim Value'
            }),
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No high-risk customers identified.")

if __name__ == "__main__":
    main()
