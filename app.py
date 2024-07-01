import pandas as pd
import csv
import yfinance as yf
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
import requests_cache
import streamviz as sv
session = requests_cache.CachedSession('yfinance.cache')
session.headers['User-agent'] = 'anish/1.0'

companies = []
col1, col2, col3 = st.columns(3)
# Fill up menu with tickers
with open('tickers.csv') as file:
    for line in csv.reader(file, delimiter=','):
        if line[0] != 'Symbol':
            companies.append(line[0])

# Create buttons
with st.sidebar:
    with st.form(key='form_submit'):

        FCF_growth_rate = st.slider("Revenue Growth Rate", 1, 50, 15) / 100
        discount_rate = st.slider("Discount Rate", 6, 20, 10) / 100
        TGT_growth_rate = st.slider("Target Growth Rate", 1, 5, 3) / 100

        stock_code = st.radio("Select one stock", ["None", "GOOG", "AAPL", "MSFT", "AMZN"])
        select_stock_code = st.selectbox("Enter Stock below", pd.DataFrame(companies), index=None, placeholder='Select stock from list...')

        if stock_code == "None":
            stock_code = select_stock_code
        submit = st.form_submit_button("Submit")


if submit:
    ticker = yf.Ticker(stock_code, session=session)
    revenue = ticker.financials
    balance_sheet = ticker.balance_sheet
    cash_flow = ticker.cash_flow
    revenue.query("index == 'Gross Profit' or index == 'Total Revenue' or index == 'Net Income'", inplace=True)
    balance_sheet.query("index == 'Cash Cash Equivalents And Short Term Investments' or index == 'Total Debt'", inplace=True)
    cash_flow.query("index == 'Free Cash Flow'", inplace=True)
    st.subheader(f"Name: {ticker.info['longName']}")
    percent = []
    balance = []
    flow = []

    # Remove last column
    revenue.drop(revenue.columns[len(revenue.columns) - 1], axis=1, inplace=True)
    balance_sheet.drop(balance_sheet.columns[len(balance_sheet.columns) - 1], axis=1, inplace=True)
    cash_flow.drop(cash_flow.columns[len(cash_flow.columns) - 1], axis=1, inplace=True)

    # Create extra rows
    for i in revenue.to_dict().values():
        percent.append(round(i['Gross Profit'] / i['Total Revenue'] * 100, 2))
    revenue.loc["Percent Gain"] = percent
    cash_flow = cash_flow.iloc[::-1, ::-1]

    cash_eq = balance_sheet.iloc[0].iloc[0]
    debt = balance_sheet.iloc[1].iloc[0]

    prev_4years_cash_flow = cash_flow.to_dict()

    print("fill previous 4 years cash flow")
    year = 0
    free_cash_flow = 0
    cash_flow_for_8years = {}

    # Leave only year within column
    for _, yf_fcf_time in enumerate(prev_4years_cash_flow):
        year = str(datetime.strftime(yf_fcf_time.to_pydatetime(), '%Y'))
        free_cash_flow = round(prev_4years_cash_flow[yf_fcf_time]["Free Cash Flow"])
        cash_flow_for_8years[year] = free_cash_flow

    running_free_cash_flow_calc = free_cash_flow
    discount_rate_4_years_ahead = {}
    for i in range(4):
        running_free_cash_flow_calc += round(running_free_cash_flow_calc * FCF_growth_rate)
        year = int(year) + 1
        cash_flow_for_8years[year] = running_free_cash_flow_calc
        discount_rate_4_years_ahead[year] = round(running_free_cash_flow_calc / ((1 + discount_rate) ** (i + 1)))

    terminal_value = (cash_flow_for_8years[year] * (1 + TGT_growth_rate))/(discount_rate - TGT_growth_rate)

    today_terminal_value = round(terminal_value / ((1 + discount_rate) ** 5))
    sum_of_future_FCF = sum(discount_rate_4_years_ahead.values()) + today_terminal_value
    enterprise_value = sum_of_future_FCF + cash_eq - debt
    fair_value = enterprise_value/ticker.info["impliedSharesOutstanding"]

    st.table(pd.DataFrame({'Stock Values': {'Fair Value': round(fair_value),
                                            'Current Value': round(ticker.info['previousClose']),
                                            '52 Week High': round(ticker.info['fiftyTwoWeekHigh']),
                                            '52 Week Low': round(ticker.info['fiftyTwoWeekLow'])}}))

    # Creating bar chart
    st.subheader("Free Cash Flow for 8 years")
    print(cash_flow_for_8years)
    st.bar_chart(cash_flow_for_8years)

    with col1:
        fair_value = round(fair_value)
        current_price = round(ticker.info['previousClose'])
        yearly_low = round(ticker.info['fiftyTwoWeekLow'])
        yearly_high = round(ticker.info['fiftyTwoWeekHigh'])

        fig = go.Figure(go.Indicator(
            domain={'x': [0, 1], 'y': [0, 1]},
            value=current_price,
            mode="gauge+number",
            title="52 weeks stock price",
            delta={'reference': fair_value},
            gauge={
                'axis': {'range': [yearly_low, yearly_high], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "lightGreen"},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [yearly_low, current_price], 'color': 'white'}
                ]
            }))

        st.plotly_chart(fig)

    with col2:
        pass
    with col3:
        fair_value = round(fair_value)
        current_price = round(ticker.info['previousClose'])
        yearly_low = round(ticker.info['fiftyTwoWeekLow'])
        yearly_high = round(ticker.info['fiftyTwoWeekHigh'])

        if fair_value > yearly_high:
            top_range_value = fair_value * 1.2
        else:
            top_range_value = yearly_high * 1.2

        fig3 = go.Figure(go.Indicator(
            mode="number+gauge+delta",
            gauge={
                'shape': 'bullet',
                'axis': {'range': [None, top_range_value]},
                'threshold': {
                    'line': {'color': "red", 'width': 2},
                    'thickness': 0.75,
                    'value': current_price},
                'steps': [
                    {'range': [0, yearly_low], 'color': "lightgray"},
                    {'range': [yearly_low, yearly_high], 'color': "lightGreen"}]
            },
            delta={'reference': current_price},
            value=fair_value,
            domain={'x': [0.1, 1], 'y': [0.2, 0.9]},
        ))

        st.plotly_chart(fig3)
