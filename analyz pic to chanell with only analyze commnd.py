import nest_asyncio
import asyncio
from telegram.ext import Application, CommandHandler, CallbackContext
from telegram import Update, Bot
import MetaTrader5 as mt5
import pandas as pd
import matplotlib.pyplot as plt
import io
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
import numpy as np

# فعال‌سازی nest_asyncio
nest_asyncio.apply()

# توکن بات تلگرام و آیدی کانال
TELEGRAM_API_TOKEN = '7179987083:AAFdCPbc1Z1GnK87ROwuVbL4Bga9KspL_Mg'
CHANNEL_ID = '@lordtest2'  # آیدی کانال تلگرام شما (برای ارسال به کانال)

# 1. اتصال به MetaTrader5
if not mt5.initialize():
    print("MetaTrader5 initialization failed")
    quit()

# تابع دریافت داده‌های تاریخی
def fetch_data(symbol, timeframe, start_date, end_date):
    rates = mt5.copy_rates_range(symbol, timeframe, start_date, end_date)
    if rates is None:
        print("Failed to get data for", symbol)
        return None

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    return df

# تابع پیش‌بینی قیمت آینده
def predict_future_price(dataframe, future_steps=1):
    X = np.arange(len(dataframe)).reshape(-1, 1)  # زمان به عنوان ویژگی
    y = dataframe['close'].values  # قیمت پایانی به عنوان هدف

    # آموزش مدل
    model = LinearRegression()
    model.fit(X, y)

    # پیش‌بینی قیمت آینده
    future_X = np.arange(len(dataframe), len(dataframe) + future_steps).reshape(-1, 1)
    predicted_prices = model.predict(future_X)
    return predicted_prices

# تابع محاسبه میانگین وزنی و تعادلی
def calculate_levels(dataframe):
    high_avg = np.average(dataframe['high'], weights=range(1, len(dataframe) + 1))
    low_avg = np.average(dataframe['low'], weights=range(1, len(dataframe) + 1))
    midpoint = (high_avg + low_avg) / 2
    return high_avg, low_avg, midpoint

# تابع مدیریت ریسک و پیشنهاد SL/TP
def calculate_risk(dataframe, entry_price, risk_percent=0.1):
    capital = 10000  # سرمایه فرضی
    risk_amount = capital * risk_percent
    stop_loss = entry_price - (risk_amount / 10)
    take_profit = entry_price + (risk_amount / 5)
    return stop_loss, take_profit

# رسم نمودار و ارسال به تلگرام
async def plot_and_send_to_telegram(symbol):
    # دریافت داده‌ها
    start_date = datetime.now() - timedelta(days=365)
    end_date = datetime.now()
    timeframe = mt5.TIMEFRAME_H6
    df = fetch_data(symbol, timeframe, start_date, end_date)

    if df is None:
        return

    # پیش‌بینی قیمت آینده
    predicted_prices = predict_future_price(df, future_steps=1)
    high_avg, low_avg, midpoint = calculate_levels(df)
    stop_loss, take_profit = calculate_risk(df, entry_price=df['close'].iloc[-1])

    prediction_text = (
        f"پیش‌بینی قیمت نماد {symbol} \n"
        f"قیمت تعادلی: {midpoint:.2f} USD\n"
        f"کف قیمت: {low_avg:.2f} USD\n"
        f"سقف قیمت: {high_avg:.2f} USD\n"
        f"محدوده SL: {stop_loss:.2f}, TP: {take_profit:.2f}\n"
        f"پیش‌بینی قیمت بعدی: {predicted_prices[0]:.2f} USD"
    )

    # رسم نمودار
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df['close'], label=f'{symbol} Price', color='blue')
    plt.axhline(midpoint, color='orange', linestyle='--', label='Midpoint')
    plt.title(f"{symbol} - 6-Hour Price Analysis (Last 365 Days)", fontsize=16)
    plt.xlabel("Time", fontsize=12)
    plt.ylabel("Price (USD)", fontsize=12)
    plt.legend()
    plt.grid()

    # ذخیره نمودار به صورت فایل PNG در حافظه
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)

    # ارسال نمودار و تحلیل به تلگرام
    bot = Bot(TELEGRAM_API_TOKEN)
    await bot.send_photo(chat_id=CHANNEL_ID, photo=buf, caption=prediction_text)

    # بسته شدن متاتریدر
    mt5.shutdown()

# دستورهای بات تلگرام
async def analyze(update: Update, context: CallbackContext):
    symbol = context.args[0] if context.args else "XAUUSD"
    await plot_and_send_to_telegram(symbol)

# تنظیمات بات تلگرام
async def main():
    application = Application.builder().token(TELEGRAM_API_TOKEN).build()
    application.add_handler(CommandHandler('analyze', analyze))

    # شروع بات تلگرام
    await application.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
