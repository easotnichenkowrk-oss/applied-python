import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import requests
import datetime
from datetime import date
from datetime import datetime
from joblib import Parallel, delayed
import time
import plotly.express as px


st.set_page_config(page_title='HOMEWORK', layout='wide')
st.title('Проект №1. Анализ температурных данных')

# Реальные средние температуры (примерные данные) для городов по сезонам
seasonal_temperatures = {
    'New York': {'winter': 0, 'spring': 10, 'summer': 25, 'autumn': 15},
    'London': {'winter': 5, 'spring': 11, 'summer': 18, 'autumn': 12},
    'Paris': {'winter': 4, 'spring': 12, 'summer': 20, 'autumn': 13},
    'Tokyo': {'winter': 6, 'spring': 15, 'summer': 27, 'autumn': 18},
    'Moscow': {'winter': -10, 'spring': 5, 'summer': 18, 'autumn': 8},
    'Sydney': {'winter': 12, 'spring': 18, 'summer': 25, 'autumn': 20},
    'Berlin': {'winter': 0, 'spring': 10, 'summer': 20, 'autumn': 11},
    'Beijing': {'winter': -2, 'spring': 13, 'summer': 27, 'autumn': 16},
    'Rio de Janeiro': {'winter': 20, 'spring': 25, 'summer': 30, 'autumn': 25},
    'Dubai': {'winter': 20, 'spring': 30, 'summer': 40, 'autumn': 30},
    'Los Angeles': {'winter': 15, 'spring': 18, 'summer': 25, 'autumn': 20},
    'Singapore': {'winter': 27, 'spring': 28, 'summer': 28, 'autumn': 27},
    'Mumbai': {'winter': 25, 'spring': 30, 'summer': 35, 'autumn': 30},
    'Cairo': {'winter': 15, 'spring': 25, 'summer': 35, 'autumn': 25},
    'Mexico City': {'winter': 12, 'spring': 18, 'summer': 20, 'autumn': 15},
}

month_to_season = {
    12: 'winter', 1: 'winter', 2: 'winter',
    3: 'spring', 4: 'spring', 5: 'spring',
    6: 'summer', 7: 'summer', 8: 'summer',
    9: 'autumn', 10: 'autumn', 11: 'autumn'
}

def generate_realistic_temperature_data(cities, num_years=10):
    dates = pd.date_range(start='2010-01-01', periods=365 * num_years, freq='D')
    data = []
    for city in cities:
        for date in dates:
            season = month_to_season[date.month]
            mean_temp = seasonal_temperatures[city][season]
            temperature = np.random.normal(loc=mean_temp, scale=5)
            data.append({'city': city, 'timestamp': date, 'temperature': temperature})
    df = pd.DataFrame(data)
    df['season'] = df['timestamp'].dt.month.map(lambda x: month_to_season[x])
    return df

st.header('Загружаем данные')
if not st.checkbox('Рандомная таблица'):
    data = st.file_uploader('Выбрать файл')
else:
    data = generate_realistic_temperature_data(list(seasonal_temperatures.keys()))

colors = ['#6579BE', '#AFAFDA', '#F54800', '#4A7766', '#8A6729', '#EE8E46', '#19485F',
          '#D9E0A4', '#285B23', '#F2CFF1', '#EBC8B3', '#AFAFDA', '#EAB099', '#312F2C', '#D8D262']

def graph1(data):
    st.header('Визуализации')
    cities = st.multiselect('Выберите города',options=sorted(data['city'].unique()), default=sorted(data['city'].unique()))

    min_date = data['timestamp'].min().date()
    max_date = data['timestamp'].max().date()
    start_date, end_date = st.slider('Выберите период',min_value=min_date,max_value=max_date,value=(min_date, max_date),format='YYYY-MM-DD')

    filtered = data[(data['city'].isin(cities)) &(data['timestamp'] >= pd.to_datetime(start_date)) &(data['timestamp'] <= pd.to_datetime(end_date))]

    fig = px.line(filtered,x='timestamp',y='temperature',color='city',color_discrete_sequence=colors[:len(cities)],labels={'timestamp': 'Дата', 'temperature': 'Температура, °C'},title=None)

    fig.update_layout(height=600,template='plotly_white',legend_title_text='Города',margin=dict(l=20, r=20, t=20, b=20),)

    fig.update_traces(line=dict(width=1))
    st.plotly_chart(fig, use_container_width=True)

def graph2(data):
    min_date = data['timestamp'].min().date()
    max_date = data['timestamp'].max().date()
    start_date, end_date = st.slider('Выберите период',min_value=min_date,max_value=max_date,value=(min_date, max_date),format='YYYY-MM-DD',key='g2_slider')

    filtered = data[(data['timestamp'] >= pd.to_datetime(start_date)) & (data['timestamp'] <= pd.to_datetime(end_date))]

    cities = sorted(filtered['city'].unique())
    n_colors = len(cities)

    fig = px.line(filtered,x='timestamp',y='temperature',facet_col='city',facet_col_wrap=3,color='city',color_discrete_sequence=colors[:n_colors],labels={'timestamp': 'Дата', 'temperature': 'Температура, °C'},title=None)

    fig.update_layout(height=1200,template='plotly_white',legend_title_text='Город',margin=dict(l=20, r=20, t=20, b=20))

    fig.for_each_annotation(lambda a: a.update(text=a.text.split('=')[-1]))
    
    fig.update_traces(line=dict(width=1))

    st.plotly_chart(fig, use_container_width=True)

def graph3(data, i, temp):
    plt.figure(figsize=(15, 10))
    plt.plot(data[data['city'] == i]['timestamp'], data[data['city'] == i]['temperature'], color=colors[0], linewidth=1)
    
    plt.hlines(y=temp, color=colors[14], linestyles='-', xmin=data['timestamp'].min(), xmax=data['timestamp'].max(), linewidth=4, label = 'Текущее значение')
    
    city_data = data[data['city'] == i]
    anomalies = city_data[city_data['is_anomaly']]
    plt.scatter(anomalies['timestamp'], anomalies['temperature'], color='#EE8E46', label='Аномалии', s=20, zorder=3)
    
    plt.xticks(rotation=45)
    plt.legend()
    st.pyplot(plt.gcf())

def compare_data(data, city, temp, dt):
    st.subheader('Оценим аномальность текущей температуры')
    st.success(f'Сейчас в {city}: {temp:.1f} °C')
    season = month_to_season[int(datetime.strftime(date.today(), '%m'))]
    show = data[(data['city'] == city) & (data['season'] == season)].reset_index()
    show['temperature_now'] = temp
    cols = ['season', 'temperature_now', 'seasonal_mean', 'std']

    if show['temperature_now'].iloc[0] > show['seasonal_mean'].iloc[0] + 2 * show['std'].iloc[0]:
        message = f'Сегодня в {city} аномально жарко, так как температура выше среднесезонной на более чем 2 сигмы.'
    elif show['temperature_now'].iloc[0] < show['seasonal_mean'].iloc[0] - 2 * show['std'].iloc[0]:
        message = f'Сегодня в {city} аномально холодно, так как температура ниже среднесезонной на более чем 2 сигмы.'
    else:
        message = f'Сегодня в {city} погода нормальная, так как температура отличается от среднесезонной на менее чем 2 сигмы.'

    st.dataframe(show[cols], hide_index=True)
    st.write(message)
    st.subheader('Визуализация температурного временного ряда')
    graph3(dt, city, temp)

if data is not None:
    st.dataframe(data.head(10))
    graph1(data)
    graph2(data)

    st.header('Анализ временных рядов')
    start = time.time()
    data['rolling'] = data.groupby('city')['temperature'].transform(
        lambda x: x.rolling(window=30, min_periods=1).mean()
    )
    t_seq = time.time() - start

    def rolling_parallel(city):
        s = data[data['city'] == city]['temperature']
        return s.rolling(window=30, min_periods=1).mean()

    start = time.time()
    _ = Parallel(n_jobs=-1)(
        delayed(rolling_parallel)(city) for city in set(data['city'])
    )
    t_par = time.time() - start


    st.write('Вычислить скользящее среднее температуры с окном в 30 дней для сглаживания краткосрочных колебаний.') 
    data['rolling'] = data.groupby('city')['temperature'].transform(lambda x: x.rolling(window=30, min_periods=1).mean()) 
    st.dataframe(data) 

    st.write('Рассчитать среднюю температуру и стандартное отклонение для каждого сезона в каждом городе.') 
    data['seasonal_mean'] = data.groupby(['city', 'season'])['temperature'].transform(lambda x: x.mean()) 
    data['std'] = data.groupby(['city', 'season'])['temperature'].transform(lambda x: x.std()) 
    seasonal_data = data.groupby(['city', 'season'])[['seasonal_mean', 'std']].first().reset_index() 
    st.dataframe(seasonal_data) 

    st.write('Выявить аномалии, где температура выходит за пределы среднее ±2 𝜎 .') 
    data['is_anomaly'] = ((data['temperature'] > data['seasonal_mean'] + 2 * data['std']) | (data['temperature'] < data['seasonal_mean'] - 2 * data['std'])) 
    st.dataframe(data[data['is_anomaly']])

    st.subheader('Скорость анализа')
    st.write(f'Без распараллеливания: {t_seq:.2f} сек')
    st.write(f'С распараллеливанием: {t_par:.2f} сек')

    st.header('Мониторинг температуры')
    api = st.text_input('Введите ключ')
    city = st.selectbox('Выберите город', set(data['city']))

    if st.button('Ввести'):
        st.write(f'')
        url = 'https://api.openweathermap.org/data/2.5/weather'
        params = {'q': city, 'appid': api, 'units': 'metric'}
        response = requests.get(url, params=params, timeout=10)
        api_data = response.json()

        if api_data.get('cod') == 401:
            st.error('Неверный API-ключ. Проверьте корректность ключа OpenWeatherMap.')
        else:
            temp = api_data['main']['temp']
            col = ['season', 'seasonal_mean','std']
            col2 = ['temperature', 'rolling', 'seasonal_mean', 'std']
            st.subheader('Статистика температур')
            st.dataframe(data[data['city'] == city][col2].describe())

            st.subheader('Сезонные профили')
            st.dataframe(seasonal_data[seasonal_data['city'] == city][col], hide_index=True)
            
            st.write(f'')
            compare_data(seasonal_data, city, temp, data)

        st.header('Синхронные и асинхронные запросы')
        st.write('В данном проекте синхронный метод является более простым и оправданным, потому что делается только один запрос. Отсутсвует необходимость в асинхронном подкоде.')
