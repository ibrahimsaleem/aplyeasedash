import re
from datetime import datetime

import dash
from dash import html, dcc, dash_table, Input, Output, State
import flask
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------
# Flask Server & Dash App Instance
# ---------------------------------
server = flask.Flask(__name__)
app = dash.Dash(__name__, server=server, suppress_callback_exceptions=True)
app.title = "Job Application Tracker"

# ---------------------------------
# Custom CSS & index_string (mobile friendly)
# ---------------------------------
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f9fafb;
                margin: 0;
                padding: 0;
            }
            .dashboard-container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            .card {
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                padding: 20px;
                margin-bottom: 20px;
            }
            .stats-card {
                text-align: center;
                padding: 15px;
                border-radius: 8px;
                color: white;
                font-weight: bold;
            }
            .header-bar {
                background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            .no-data-message {
                text-align: center;
                padding: 40px 20px;
                color: #6c757d;
                font-style: italic;
            }
            .empty-chart-container {
                height: 300px;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-direction: column;
            }
            .btn-primary {
                background-color: #4b6cb7;
                border: none;
                transition: all 0.3s ease;
            }
            .btn-primary:hover {
                background-color: #3a5a9b;
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            }
            /* Mobile Friendly Adjustments */
            @media (max-width: 768px) {
                .dashboard-container {
                    padding: 10px;
                    width: 95%;
                }
                .card, .header-bar {
                    padding: 15px;
                    margin-bottom: 15px;
                }
                .header-bar {
                    flex-direction: column;
                    text-align: center;
                }
                .header-bar > div {
                    margin-bottom: 10px;
                }
                .header-bar img {
                    height: 28px;
                    margin-right: 5px;
                }
                .btn-primary, button {
                    width: 100%;
                    font-size: 14px;
                }
                input[type="text"] {
                    width: 100% !important;
                }
                .stats-card {
                    font-size: 18px;
                    padding: 10px;
                }
                .header-bar h1 {
                    font-size: 20px;
                }
                .header-bar p {
                    font-size: 14px;
                }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# ---------------------------------
# Main Container Layout (Multi-Page Routing)
# ---------------------------------
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# ---------------------------------
# HOME PAGE LAYOUT (For Dashboard Creation)
# ---------------------------------
def home_layout():
    return html.Div([
        html.Div([
            html.H1("🚀 Personal Job Application Tracker", className="mb-4"),
            html.P("Create your personalized job application dashboard by entering your information below:",
                   className="lead mb-4"),
            html.Div([
                dcc.Input(
                    id='username',
                    type='text',
                    placeholder='Enter your username (e.g., ibrahim91)',
                    style={'width': '100%', 'padding': '12px', 'marginBottom': '15px',
                           'borderRadius': '5px', 'border': '1px solid #ddd'}
                ),
                dcc.Input(
                    id='sheet-url',
                    type='text',
                    placeholder='Paste your PUBLIC Google Sheet URL here',
                    style={'width': '100%', 'padding': '12px', 'marginBottom': '15px',
                           'borderRadius': '5px', 'border': '1px solid #ddd'}
                ),
                html.Button(
                    'Create Dashboard',
                    id='submit-btn',
                    n_clicks=0,
                    style={
                        'padding': '12px 24px',
                        'backgroundColor': '#4b6cb7',
                        'color': 'white',
                        'border': 'none',
                        'borderRadius': '5px',
                        'cursor': 'pointer',
                        'width': '100%',
                        'fontSize': '16px',
                        'fontWeight': 'bold'
                    }
                ),
            ], style={'width': '500px', 'margin': '0 auto'}),
        ], className="header-bar", style={'textAlign': 'center', 'marginBottom': '30px'}),
        html.Div([
            html.Div(id='dashboard-link', style={'textAlign': 'center', 'marginTop': '20px'}),
            html.Div([
                html.H4("Required Spreadsheet Format", style={'marginBottom': '15px'}),
                html.P("For best results, your Google Sheet should include these columns:"),
                html.Ul([
                    html.Li("Company - the name of the company you applied to"),
                    html.Li("Position - job title or position"),
                    html.Li("Status - application status (e.g., Applied, Shortlisted, Interview, Approved, Rejected)"),
                    html.Li("Date - date of application (in any standard date format)"),
                    html.Li("LINK - URL to the job posting or application (optional)")
                ]),
                html.P("The dashboard will adapt to your data and show what's available."),
            ], className="card", style={'marginTop': '30px', 'textAlign': 'left'})
        ])
    ], className="dashboard-container")

# ---------------------------------
# Callback: Create Dashboard (From Home Page)
# ---------------------------------
@app.callback(
    Output('dashboard-link', 'children'),
    Input('submit-btn', 'n_clicks'),
    State('username', 'value'),
    State('sheet-url', 'value')
)
def create_user_dashboard(n_clicks, username, sheet_url):
    if not username or not sheet_url:
        return html.Div("❗ Please enter both username and sheet URL.", style={'color': 'red'})
    try:
        # Fetch the current data from Google Sheets
        sheet_id = sheet_url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        df = pd.read_csv(csv_url)
        df.columns = [col.strip().lower() for col in df.columns]
        # (Optional) Save initial CSV and column mapping locally if desired.
        column_map = {col.lower(): col for col in df.columns}
        column_info = pd.DataFrame({'original': df.columns, 'lowercase': list(df.columns)})
        column_info.to_csv(f"dashboard_columns_{username}.csv", index=False)
        # Save the provided sheet URL for potential future use (not used in dashboard refresh below)
        with open(f"dashboard_sheeturl_{username}.txt", "w") as f:
            f.write(sheet_url)
        # (Optional) Save CSV locally for first load.
        keywords = ['link', 'job page', 'resume']
        for col in df.columns:
            if any(keyword in col.lower() for keyword in keywords):
                df[col] = df[col].apply(lambda x: f"[link]({x})" if pd.notna(x) and str(x).strip() != "" else "")
        df.to_csv(f"dashboard_data_{username}.csv", index=False)

        # Return a link that points to: main_url/<encoded_excel_sheet_url>
        # For simplicity, we use the provided sheet URL as the dynamic route parameter (note: it should be URL-encoded).
        return html.Div([
            html.Div([
                html.I(className="fas fa-check-circle", style={'fontSize': '48px', 'color': '#28a745'}),
                html.H3("Dashboard created successfully!", style={'color': '#28a745', 'marginTop': '10px'}),
                html.A(
                    html.Button("View Your Dashboard", style={
                        'backgroundColor': '#4b6cb7',
                        'color': 'white',
                        'padding': '12px 24px',
                        'border': 'none',
                        'borderRadius': '5px',
                        'cursor': 'pointer',
                        'fontSize': '16px',
                        'marginTop': '15px'
                    }),
                    # The user is redirected to /<encoded_sheet_url>
                    href=f"/{sheet_url}",
                    target="_blank"
                )
            ], className="card", style={'textAlign': 'center', 'padding': '30px'})
        ])
    except Exception as e:
        return html.Div([
            html.Div([
                html.I(className="fas fa-exclamation-triangle", style={'fontSize': '48px', 'color': '#dc3545'}),
                html.H3("Error Creating Dashboard", style={'color': '#dc3545', 'marginTop': '10px'}),
                html.P(f"Failed to load sheet: {str(e)}", style={'marginTop': '10px'})
            ], className="card", style={'textAlign': 'center', 'padding': '30px'})
        ])

# ---------------------------------
# Dashboard Helper Functions (unchanged)
# ---------------------------------
def get_column_if_exists(df, col_names, column_map=None):
    if column_map is None:
        column_map = {col.lower(): col for col in df.columns}
    for col in col_names:
        if col.lower() in column_map:
            return column_map[col.lower()]
    return None

def calculate_success_rate(df, column_map):
    status_col = get_column_if_exists(df, ['status', 'application status', 'job status'], column_map)
    if not status_col:
        return "N/A"
    total = len(df)
    if total == 0:
        return "0%"
    positive_outcomes = len(df[df[status_col].str.lower().str.contains('approved|shortlisted|interview|offer', na=False)])
    return f"{round((positive_outcomes/total)*100)}%"

def count_status(df, status_pattern, column_map):
    status_col = get_column_if_exists(df, ['status', 'application status', 'job status'], column_map)
    if not status_col:
        return 0
    return df[status_col].str.lower().str.contains(status_pattern, case=False, na=False).sum()

def get_recent_activity(df, column_map):
    date_col = get_column_if_exists(df, ['date', 'application date', 'applied on', 'apply date'], column_map)
    if not date_col:
        return "No date information"
    try:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        latest_date = df[date_col].max()
        if pd.isna(latest_date):
            return "Date format error"
        return latest_date.strftime('%b %d, %Y')
    except:
        return "Date format error"

def create_status_pie(df, column_map):
    status_col = get_column_if_exists(df, ['status', 'application status', 'job status'], column_map)
    if not status_col:
        return create_empty_figure("Status distribution not available - no status column found")
    status_counts = df[status_col].value_counts()
    if len(status_counts) == 0:
        return create_empty_figure("No status data available")
    colors = px.colors.qualitative.Safe
    fig = go.Figure(data=[go.Pie(
        labels=status_counts.index,
        values=status_counts.values,
        hole=0.4,
        textinfo='label+percent',
        marker_colors=colors
    )])
    fig.update_layout(
        title='Application Status Distribution',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def create_timeline_chart(df, column_map):
    date_col = get_column_if_exists(df, ['date', 'application date', 'applied on', 'apply date'], column_map)
    status_col = get_column_if_exists(df, ['status', 'application status', 'job status'], column_map)
    if not date_col or not status_col:
        missing = []
        if not date_col:
            missing.append("date")
        if not status_col:
            missing.append("status")
        return create_empty_figure(f"Timeline not available - missing {' and '.join(missing)} data")
    try:
        df_timeline = df.copy()
        df_timeline[date_col] = pd.to_datetime(df_timeline[date_col], errors='coerce')
        df_timeline = df_timeline.dropna(subset=[date_col])
        if len(df_timeline) == 0:
            return create_empty_figure("Timeline not available - no valid dates found")
        df_timeline = df_timeline.sort_values(date_col)
        timeline_data = []
        status_counts = {}
        for date, status in zip(df_timeline[date_col], df_timeline[status_col]):
            if pd.isna(status):
                continue
            if status not in status_counts:
                status_counts[status] = 0
            status_counts[status] += 1
            timeline_data.append({'Date': date, 'Status': status, 'Count': status_counts[status]})
        if not timeline_data:
            return create_empty_figure("Timeline not available - no valid status data")
        timeline_df = pd.DataFrame(timeline_data)
        fig = px.line(timeline_df, x='Date', y='Count', color='Status',
                      title='Application Status Timeline',
                      labels={'Count': 'Cumulative Count', 'Date': 'Application Date'})
        fig.update_layout(
            legend_title_text='Status',
            xaxis_title="Date",
            yaxis_title="Number of Applications",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        return fig
    except Exception as e:
        return create_empty_figure(f"Timeline error - {str(e)}")

def create_company_distribution(df, column_map):
    company_col = get_column_if_exists(df, ['company', 'organization', 'employer'], column_map)
    if not company_col:
        return create_empty_figure("Company distribution not available - no company column found")
    if df[company_col].isna().all() or len(df[company_col].dropna()) == 0:
        return create_empty_figure("Company distribution not available - no company data")
    company_counts = df[company_col].value_counts().head(10)
    colors = px.colors.qualitative.Plotly
    fig = go.Figure(data=[go.Bar(
        x=company_counts.index,
        y=company_counts.values,
        marker_color=colors
    )])
    fig.update_layout(
        title='Top Companies Applied To',
        xaxis_title="Company",
        yaxis_title="Number of Applications",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def create_empty_figure(message):
    fig = go.Figure()
    fig.update_layout(
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": message,
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"size": 16, "color": "#6c757d"}
            }
        ],
        plot_bgcolor='rgba(240,240,240,0.3)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=300
    )
    return fig

# ---------------------------------
# Functions to Build Dashboard Page Content
# ---------------------------------
def build_dashboard_header(sheet_url):
    return html.Div([
        html.Div([
            html.Div([
                html.Img(src="/assets/dashboard-logo.png", style={'height': '32px', 'marginRight': '10px'}),
            ], style={'display': 'inline-block', 'verticalAlign': 'middle'}),
            html.Div([
                html.H1("Your Job Application Dashboard", style={'margin': '0', 'display': 'inline-block'}),
                html.P(f"Dashboard for: {sheet_url}", style={'color': 'rgba(255,255,255,0.8)', 'fontSize': '14px'})
            ], style={'display': 'inline-block', 'verticalAlign': 'middle'})
        ]),
        html.Div([
            html.Button("⟳ Refresh Data", id="refresh-button", style={
                'backgroundColor': 'white',
                'color': '#4b6cb7',
                'border': 'none',
                'padding': '8px 15px',
                'borderRadius': '5px',
                'fontWeight': 'bold',
                'cursor': 'pointer'
            })
        ])
    ], className="header-bar", style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'})

def build_dashboard_content(sheet_url):
    try:
        # Use the provided sheet_url directly
        sheet_id = sheet_url.split("/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        df = pd.read_csv(csv_url)
        df.columns = [col.strip().lower() for col in df.columns]
        # Rebuild the column mapping (optionally, you can cache this if needed)
        column_map = {col.lower(): col for col in df.columns}
        keywords = ['link', 'job page', 'resume']
        for col in df.columns:
            if any(keyword in col.lower() for keyword in keywords):
                df[col] = df[col].apply(lambda x: f"[link]({x})" if pd.notna(x) and str(x).strip() != "" else "")
        total_applications = len(df)
        success_rate = calculate_success_rate(df, column_map)
        recent_activity = get_recent_activity(df, column_map)
        approved_count = count_status(df, 'approved|offer|accepted', column_map)
        interview_count = count_status(df, 'interview', column_map)
        rejected_count = count_status(df, 'rejected|declined', column_map)
        status_pie = create_status_pie(df, column_map)
        timeline_chart = create_timeline_chart(df, column_map)
        company_chart = create_company_distribution(df, column_map)
        status_col = get_column_if_exists(df, ['status', 'application status', 'job status'], column_map)
        status_options = []
        if status_col:
            statuses = df[status_col].dropna().unique()
            status_options = [{'label': status, 'value': status} for status in statuses]
        content = html.Div([
            html.Div(f"Last refreshed: {datetime.now().strftime('%b %d, %Y, %I:%M:%S %p')}",
                     style={'textAlign': 'center', 'margin': '10px 0', 'fontStyle': 'italic'}),
            html.Div([
                html.Div([
                    html.Div([
                        html.H2(total_applications, style={'margin': '0', 'fontSize': '36px'}),
                        html.P("Total Applications", style={'margin': '5px 0 0 0', 'color': '#FFFFFF'})
                    ], className="stats-card", style={'backgroundColor': '#4b6cb7'}),
                ], className="card", style={'width': '24%', 'margin': '0 0.5%', 'padding': '0'}),
                html.Div([
                    html.Div([
                        html.H2(interview_count, style={'margin': '0', 'fontSize': '36px'}),
                        html.P("Interviews", style={'margin': '5px 0 0 0', 'color': '#FFFFFF'})
                    ], className="stats-card", style={'backgroundColor': '#17a2b8'}),
                ], className="card", style={'width': '24%', 'margin': '0 0.5%', 'padding': '0'}),
                html.Div([
                    html.Div([
                        html.H2(approved_count, style={'margin': '0', 'fontSize': '36px'}),
                        html.P("Approved", style={'margin': '5px 0 0 0', 'color': '#FFFFFF'})
                    ], className="stats-card", style={'backgroundColor': '#28a745'}),
                ], className="card", style={'width': '24%', 'margin': '0 0.5%', 'padding': '0'}),
                html.Div([
                    html.Div([
                        html.H2(success_rate, style={'margin': '0', 'fontSize': '36px'}),
                        html.P("Success Rate", style={'margin': '5px 0 0 0', 'color': '#FFFFFF'})
                    ], className="stats-card", style={'backgroundColor': '#ffc107'}),
                ], className="card", style={'width': '24%', 'margin': '0 0.5%', 'padding': '0'}),
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '20px'}),
            html.Div([
                html.Div([
                    html.Div([dcc.Graph(figure=status_pie)], className="card", style={'width': '48%', 'margin': '0 1% 20px 0'}),
                    html.Div([dcc.Graph(figure=timeline_chart)], className="card", style={'width': '48%', 'margin': '0 0 20px 1%'})
                ], style={'display': 'flex', 'justifyContent': 'space-between'}),
                html.Div([
                    html.Div([dcc.Graph(figure=company_chart)], className="card", style={'width': '100%', 'margin': '0 0 20px 0'})
                ])
            ]),
            html.Div([
                html.H3("Application Details", style={'marginBottom': '15px'}),
                html.Div([
                    html.Div([
                        html.Label("Filter by Status:"),
                        dcc.Dropdown(
                            id='status-filter',
                            options=status_options,
                            multi=True,
                            placeholder="Select status..."
                        ) if status_options else html.P("Status filtering not available",
                                                        style={'color': '#6c757d', 'fontStyle': 'italic'})
                    ], style={'width': '25%', 'paddingRight': '15px'}),
                    html.Div([
                        html.Label("Search:"),
                        dcc.Input(
                            id='search-input',
                            type='text',
                            placeholder='Search applications...',
                            style={'width': '100%', 'padding': '8px', 'borderRadius': '5px', 'border': '1px solid #ddd'}
                        )
                    ], style={'width': '25%'})
                ], style={'display': 'flex', 'marginBottom': '15px'}),
                dash_table.DataTable(
                    id='application-table',
                    columns=[
                        {"name": col, "id": col, "presentation": "markdown"}
                        if "link" in col.lower()
                        else {"name": col, "id": col}
                        for col in df.columns
                    ],
                    data=df.to_dict('records'),
                    filter_action="native",
                    sort_action="native",
                    page_size=10,
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'minWidth': '120px', 'padding': '10px'},
                    style_header={
                        'fontWeight': 'bold',
                        'backgroundColor': '#f8f9fa',
                        'borderBottom': '2px solid #dee2e6'
                    },
                    style_data_conditional=[
                        {"if": {"filter_query": "{" + status_col + "} contains 'Approved'"},
                         "backgroundColor": "#d4edda", "color": "#155724"} if status_col else {},
                        {"if": {"filter_query": "{" + status_col + "} contains 'Shortlisted'"},
                         "backgroundColor": "#fff3cd", "color": "#856404"} if status_col else {},
                        {"if": {"filter_query": "{" + status_col + "} contains 'Interview'"},
                         "backgroundColor": "#d1ecf1", "color": "#0c5460"} if status_col else {},
                        {"if": {"filter_query": "{" + status_col + "} contains 'Applied'"},
                         "backgroundColor": "#e2e3e5", "color": "#383d41"} if status_col else {},
                        {"if": {"filter_query": "{" + status_col + "} contains 'Rejected'"},
                         "backgroundColor": "#f8d7da", "color": "#721c24"} if status_col else {},
                    ],
                    style_as_list_view=True,
                    css=[{'selector': '.dash-cell div.dash-cell-value',
                          'rule': 'display: inline; white-space: inherit; overflow: inherit; text-overflow: inherit;'}],
                )
            ], className="card"),
            # Instructions and Footer (Updated)
            html.Div([
                html.H4("About AplyEase", style={'marginBottom': '15px', 'textAlign': 'center'}),
                html.P(
                    "Hi, I'm Mohammad Ibrahim Saleem, the creator of AplyEase—a revolutionary tool designed to simplify your job and internship applications so you can focus on your strengths and growth.",
                    style={'lineHeight': '1.6', 'textAlign': 'center'}
                ),
                html.H5("Our Mission", style={'marginTop': '20px', 'marginBottom': '10px', 'textAlign': 'center'}),
                html.P(
                    "AplyEase is a reverse recruiting firm dedicated to managing your application process efficiently. We handle everything from ATS resume optimization to proactive recruiter outreach, allowing you to build an impressive digital portfolio and focus on what matters most—your career development.",
                    style={'lineHeight': '1.6', 'textAlign': 'center'}
                ),
                html.H5("What We Offer", style={'marginTop': '20px', 'marginBottom': '10px', 'textAlign': 'center'}),
                html.Ul([
                    html.Li("ATS Resume Optimization – Tailor your resume to successfully pass Applicant Tracking Systems."),
                    html.Li("AI-Powered Job Search – Discover opportunities that match your skills and career goals."),
                    html.Li("Digital Portfolio Creation – Showcase your projects and achievements online."),
                    html.Li("LinkedIn Profile Enhancement – Optimize your professional presence."),
                    html.Li("Application Tracking – Monitor your application status in real time."),
                    html.Li("Recruiter Outreach – Connect with hiring managers to increase your chances of landing interviews.")
                ], style={'lineHeight': '1.6'}),
                html.P(
                    "Join hundreds of successful job seekers who have transformed their application process with AplyEase.",
                    style={'marginTop': '15px', 'lineHeight': '1.6', 'textAlign': 'center'}
                )
            ], className="card", style={'marginTop': '20px'}),
            html.Footer([
                html.P("AplyEase © 2025. All Rights Reserved. Designed by Mohammad Ibrahim Saleem.", 
                       style={'textAlign': 'center', 'color': '#6c757d', 'marginTop': '30px'})
            ])
        ])
        return content
    except Exception as e:
        return html.Div(f"Error loading dashboard for {sheet_url}: {str(e)}",
                        style={'textAlign': 'center', 'marginTop': '20px', 'color': 'red'})

def dashboard_layout(sheet_url):
    return html.Div([
        dcc.Store(id="dashboard-sheet-url", data=sheet_url),
        dcc.Interval(id="auto-refresh", interval=30*1000, n_intervals=0),  # refresh every 30 seconds
        build_dashboard_header(sheet_url),
        html.Div(id="dashboard-content", children=build_dashboard_content(sheet_url))
    ], className="dashboard-container")

# ---------------------------------
# PAGE ROUTING CALLBACK
# ---------------------------------
@app.callback(Output('page-content', 'children'),
              Input('url', 'pathname'))
def display_page(pathname):
    # If the URL is just "/" show the home page.
    if not pathname or pathname == "/":
        return home_layout()
    # Otherwise, treat the full pathname (minus the leading '/') as the Google Sheet URL.
    # (It must be URL-encoded.)
    sheet_url = pathname[1:]
    return dashboard_layout(sheet_url)

# ---------------------------------
# CALLBACK TO REFRESH DASHBOARD CONTENT (AUTO & MANUAL)
# ---------------------------------
@app.callback(
    Output('dashboard-content', 'children'),
    [Input('refresh-button', 'n_clicks'),
     Input('auto-refresh', 'n_intervals')],
    State('dashboard-sheet-url', 'data')
)
def update_dashboard_content(n_clicks, n_intervals, sheet_url):
    print(f"Refresh triggered: n_clicks={n_clicks}, n_intervals={n_intervals}")
    return build_dashboard_content(sheet_url)

# ---------------------------------
# Assets Route
# ---------------------------------
@server.route('/assets/<path:path>')
def serve_assets(path):
    return flask.send_from_directory('assets', path)

# ---------------------------------
# Main
# ---------------------------------
if __name__ == '__main__':
    app.run(debug=True)
