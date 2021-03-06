# -*- coding: utf-8 -*-
"""중장기_수요예측_자동화.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1Eyob5q2GKhfxSgfMRj5fAcfDW5kcAtcE
"""
import pandas as pd
import numpy as np
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error, mean_squared_log_error
from sklearn.model_selection import GridSearchCV,KFold,train_test_split
from sklearn.preprocessing import MinMaxScaler
from lightgbm import LGBMRegressor
import datetime
import pymysql
import warnings
from dateutil.relativedelta import relativedelta
warnings.filterwarnings('ignore')
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

conn = pymysql.connect(host='34.64.224.44', user='root', password='A412GBVSDsawe%$we', db='smart_factory')
sql_state='SELECT * FROM `rawdata`'
df1=pd.read_sql_query(sql_state, conn)

conn = pymysql.connect(host='34.64.224.44', user='root', password='A412GBVSDsawe%$we', db='smart_factory')
sql_state='SELECT * FROM `weather_day`'
weather=pd.read_sql_query(sql_state, conn)

conn = pymysql.connect(host='34.64.224.44', user='root', password='A412GBVSDsawe%$we', db='smart_factory')
sql_state='SELECT * FROM `building_construction_temp`'
construction=pd.read_sql_query(sql_state, conn)

conn = pymysql.connect(host='34.64.224.44', user='root', password='A412GBVSDsawe%$we', db='smart_factory')
sql_state='SELECT * FROM `predicted_variables`'
predicted_variables=pd.read_sql_query(sql_state, conn)

origin=df1.copy()

now = datetime.datetime.now().strftime('%R')
print('Demand Forecast Update Start --',now)

weather=weather.groupby(['SOLDDATE']).mean().reset_index()

df1=df1[['SOLDDATE','PRODNAME','QUANT']]

df1['연도'] = df1['SOLDDATE'].dt.year 
df1['월'] = df1['SOLDDATE'].dt.month 

construction=construction[['연도','월','총계']]
construction.columns=['연도','월','착공총계']
construction.rename(columns={'착공총계':'construction'},inplace=True)

df1=pd.merge(df1,construction,how='inner',on=['연도','월'])

weather.columns=['SOLDDATE','TEMP', 'HUM', 'RAIN', 'SNOW']
df1=pd.merge(df1,weather,how='inner',on=['SOLDDATE'])

df1 = df1.drop(['SOLDDATE','연도','월'],axis=1)

MinMaxScaler = MinMaxScaler()
for col in ['construction','TEMP','HUM','RAIN','SNOW']:
 df1[[col]] = MinMaxScaler.fit_transform(df1[[col]])

X=df1[['PRODNAME',	'construction',	'TEMP',	'HUM',	'RAIN',	'SNOW']]
Y=df1[['QUANT']]
X=pd.get_dummies(X)

X_train,X_test,Y_train,Y_test = train_test_split(X,Y,train_size=0.8,random_state=156,shuffle=True)

start_date = predicted_variables['SOLDDATE'][0] - relativedelta(years=1)
stop_date = start_date + relativedelta(days=90) + relativedelta(years=1)
end_date = predicted_variables['SOLDDATE'][len(predicted_variables)-1] - relativedelta(years=1)

start_date=start_date.strftime('%Y-%m-%d')
stop_date=stop_date.strftime('%Y-%m-%d')
end_date=end_date.strftime('%Y-%m-%d')


predicted_variables['SOLDDATE'] = predicted_variables['SOLDDATE'].astype('datetime64')
origin = origin.loc[(origin['SOLDDATE']>=start_date) & (origin['SOLDDATE']<=end_date)]
origin=origin[['SOLDDATE','CUSTID','PRODNAME']]

for i in range(0,len(origin)):
  origin['SOLDDATE'].iloc[i] = origin['SOLDDATE'].iloc[i] + relativedelta(years=1)

predicted_variables=predicted_variables.groupby(['SOLDDATE']).mean().reset_index()
final = pd.merge(origin,predicted_variables,how='inner',on=['SOLDDATE'])
final = final[['PRODNAME','TEMP','HUM','RAIN','SNOW','CONSTRUCTION']]
final = pd.merge(origin,predicted_variables,how='inner',on=['SOLDDATE'])

final = final[['PRODNAME','TEMP','HUM','RAIN','SNOW','CONSTRUCTION']]

for col in ['TEMP','HUM','RAIN','SNOW','CONSTRUCTION']:
  final[[col]] = MinMaxScaler.fit_transform(final[[col]])

final = pd.get_dummies(final)

lgbm_reg = LGBMRegressor(random_state=156,colsample_bytree=1.0,learning_rate=0.05,n_estimators=1000)
lgbm_reg.fit(X_train,Y_train)
lgbm_pred = lgbm_reg.predict(final)

origin['QUANT']=lgbm_pred
origin['QUANT'] = np.ceil(origin['QUANT'] / 100) * 100

production_planning = origin[origin['SOLDDATE']<stop_date]
demandforecast = origin.copy()

db_connection_str = 'mysql+pymysql://root:A412GBVSDsawe%$we@34.64.224.44:3306/smart_factory'
db_connection = create_engine(db_connection_str)
conn = db_connection.connect()

production_planning.to_sql(name = 'production_planning',con = db_connection, index = False, if_exists = 'replace') 
demandforecast.to_sql(name = 'demandforecast',con = db_connection, index = False, if_exists = 'replace')

now = datetime.datetime.now().strftime('%R')
print('Demand Forecast Update End --',now)