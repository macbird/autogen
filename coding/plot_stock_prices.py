# filename: plot_stock_prices.py
import yfinance as yf
import matplotlib.pyplot as plt

# Download historical data for META and TSLA
meta_data = yf.download('META', start='2023-01-01', end='2023-12-31')
tesla_data = yf.download('TSLA', start='2023-01-01', end='2023-12-31')

# Plot the adjusted closing prices
plt.figure(figsize=(14, 7))
plt.plot(meta_data.index, meta_data['Adj Close'], label='META')
plt.plot(tesla_data.index, tesla_data['Adj Close'], label='TESLA')

# Configure the plot
plt.title('META vs TESLA Stock Price Change (2023)')
plt.xlabel('Date')
plt.ylabel('Adjusted Closing Price (USD)')
plt.legend()
plt.grid(True)

# Show the plot
plt.show()