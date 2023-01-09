import pyspark
import pandas as pd
import numpy as np

from pyspark.sql import SparkSession

import findspark
findspark.init()

spark = SparkSession.builder \
.master("local") \
.config("spark.driver.extraClassPath","C:/Users/AnshumaanChauhan/Documents/spark-3.3.0-bin-hadoop3/spark-3.3.0-bin-hadoop3/jars/mysql-connector-java-5.1.48.jar") \
.config("spark.driver.memory","15g") \
.appName("Scalability Check of Systems for ML applications") \
.getOrCreate()

from pyspark.sql.functions import col, count, isnan, when

dataset = spark.read.csv('C:\\Users\AnshumaanChauhan\\Documents\\Systems for DS Umass\\Project\\archive (5)\\DelayedFlights.csv',
                         header=True)


#Checking which column has null or nan values how many times 
dataset.select([count(when(isnan(c) | col(c).isNull(), c)).alias(c) for c in dataset.columns]).show(vertical=True)

dataset.select(col("ArrDelay")).where((col("ArrDelay").isNull() | isnan(col("ArrDelay"))) & (col('Diverted')==1)).count()
#For all the flights that are diverted their ActualElaspedTime, ArrDelay and AirTime is null, because they did not land at correct destination

dataset.select(*(col(c) for c in dataset.columns)).where((col("TaxiIn").isNull() | isnan(col("TaxiIn")))).count()
dataset.select(*(col(c) for c in dataset.columns)).where((col("TaxiIn").isNull() | isnan(col("TaxiIn"))) & (col("Diverted")==0)).count()
dataset.select(*(col(c) for c in dataset.columns)).where((col("TaxiIn").isNull() | isnan(col("TaxiIn"))) & (col("Diverted")==0) & (col("CancellationCode")=='N')).count()
#As we can infer above the TaxiIn are ArrTime are Null a few times. But it is the case when the flight is either cancelled or diverted. So it is fine if we not exclude the null values

dataset.select(*(col(c) for c in dataset.columns)).where((col("TaxiOut").isNull() | isnan(col("TaxiOut")))).show(vertical=True)
dataset.select(*(col(c) for c in dataset.columns)).where(((col("TaxiOut").isNull() | isnan(col("TaxiOut")))) & (col("CancellationCode")=='N')).show(vertical=True)
#We can infer from the above queries that TaxiOut is null only in the case of a cancelled flight. So it is fine if these are converted to 0s after type casting

dataset.select(*(col(c) for c in dataset.columns)).where((col("CRSElapsedTime").isNull() | isnan(col("CRSElapsedTime")))).show(vertical=True)
dataset.select(*(col(c) for c in dataset.columns)).where((col("CRSElapsedTime").isNull() | isnan(col("CRSElapsedTime"))) & (col("Diverted")==0)).count()
#We can infer from the above queries that CRSElapsedTime is null only in the case of a diverted flight. So it is fine if these are converted to 0s after type casting
# Last columns have null values if the flight is cancelled instead of getting delayed, we do not drop these columns. Instead when we type cast the column to numeric data type these will be converted to zero which makes sense

dataset.count()
dataset.select("_c0").distinct().count()
#Means that _c0 column is just for indexing the entreis, therefore we will use this column for joining the 2 datasets

#Have to do some pre processing here as otherwise everything will be sent as Text there 
list_of_columns=dataset.columns
Categorical_columns=['UniqueCarrier','TailNum','Origin','Dest','CancellationCode']
#Because rest everything in minutes or numerical, last columns that are delays for specific reasons are null if the flight is cancelled
#They will be converted to 0 when we do the conversion from string to numeric 

for col_name in Categorical_columns:
    list_of_columns.remove(col_name) 

#Null values will be converted to 0.0
#Adding _c0 for the join operation, so that we have the correct join, and no duplicates are created due to the change of null to 0.0
Categorical_columns.append("_c0")

numeric_dataset= dataset.select(*(col(c).cast('float') for c in list_of_columns))
updated_dataset= numeric_dataset.join(dataset.select(*(col(c) for c in Categorical_columns)),"_c0")

#As the null values are handled during the pre-processing step we do not need to treat them by replacing them with the mean value, or some other technique used for handling the null values. Can also use pyspark.ml.features.Imputer module if have dataset which contains null values. (Best case is drop those rows if not facing with the problem of data insufficiency)

del(numeric_dataset)
del(dataset)
numeric_dataset.unpersist()
dataset.unpersist()

updated_dataset.printSchema()

#Loading dataset into MySQL 
updated_dataset.select(*(col(c) for c in dataset.columns)).write.format("jdbc") \
.option("url", "jdbc:mysql://localhost:3306/Sys") \
.option("driver", "com.mysql.jdbc.Driver").option("dbtable", "dataset") \
.option("user", "root").option("password", "MySQL").save()

#Loading dataset from MySQL (after doing simple anaysis in MySQL)
updated_dataset = spark.read.format("jdbc") \
.option("url", "jdbc:mysql://localhost:3306/Sys") \
.option("driver", "com.mysql.jdbc.Driver").option("dbtable", "dataset") \
.option("user", "root").option("password", "MySQL").load()

updated_dataset.printSchema()

#Query to get frequency of flights that were diverted each month
diverted_monthwise = updated_dataset.select("Month","Diverted").where(updated_dataset["Diverted"]==1).groupBy("Month").count()
diverted_monthwise.sort(diverted_monthwise['count'].desc()).show()

#Query to get frequency of flights that were cancelled each month
cancelled_monthwise = updated_dataset.select("Month","Cancelled").where(updated_dataset["Cancelled"]==1).groupBy("Month").count()
cancelled_monthwise.sort(cancelled_monthwise['count'].desc()).show()

#Query to get frequency of flights that were highly delayed each month
highly_delayed_monthwise = updated_dataset.select("Month","label").where(updated_dataset["label"]==1).groupBy("Month").count()
highly_delayed_monthwise.sort(highly_delayed_monthwise['count'].desc()).show()

#Query to preprocess the data to get whether the flight is delayed or not, the delay in min (if any), departure time and arrival time in 'hour of day' and the flight distance bucketed with bucket size of distInterval (250). 
updated_dataset.createOrReplaceTempView("df")
distInterval = 250
dfres = spark.sql(""+
    "select "+
        "Distance,"+
        "concat_ws('-', STRING(floor(Distance/{0})*{0}), STRING(floor((Distance/{0}) + 1)*{0})) as DistRange,".format(distInterval)+
        "CASE WHEN length(CRSDepTime) <= 4 THEN 0 ELSE substring(STRING(CRSDepTime), 1, length(CRSDepTime)-4) END as CRSDeptHr,"+
        "CASE WHEN length(CRSArrTime) <= 4 THEN 0 ELSE substring(STRING(CRSArrTime), 1, length(CRSArrTime)-4) END as CRSArrHr,"+
        "CASE WHEN ActualElapsedTime - CRSElapsedTime > 0 THEN 1 ELSE 0 END as Delayed, "+
        "CASE WHEN ActualElapsedTime - CRSElapsedTime <= 0 THEN 1 ELSE 0 END as OnTime, "+
        "CASE WHEN ActualElapsedTime - CRSElapsedTime > 0 THEN ActualElapsedTime - CRSElapsedTime ELSE 0 END as Delay "+
    "from df "+
    "where (Cancelled == 0) AND (Diverted == 0)".format(distInterval))
dfres.createOrReplaceTempView("dfres")
dfres.show(20, truncate=False)

#Query to get percentage of flights delayed distributed over the departure hour of day. 
hourRes = spark.sql("select CRSDeptHr, sum(Delayed) / (sum(Delayed) + sum(OnTime)) * 100 as DelayedPercentage from dfres group by CRSDeptHr order by DelayedPercentage DESC")
hourRes.show(24, truncate=False)

#Query to get percentage of flights delayed distributed over the distance buckets. 
distRes = spark.sql("select DistRange, sum(Delayed) / (sum(Delayed) + sum(OnTime)) * 100 as DelayedPercentage from dfres group by DistRange order by DelayedPercentage DESC")
distRes.show(truncate=False)

# Starting Data Visualization

df_pandas = updated_dataset.toPandas()
df_pandas = df_pandas.fillna(0)

import matplotlib.pyplot as plt
import seaborn as sns

# Histograms to represent distribution of each feature 
for col,num in zip(df_pandas.describe().columns, range(1, len(df_pandas.columns))):
    plt.hist(df_pandas[col], bins =20)
    plt.grid(False)
    plt.title(col.upper())
    plt.tight_layout()
    plt.show()

# Bar plot representing frequency of flights cancelled monthwise
df_pandas[["Cancelled","Month"]].where(df_pandas["Cancelled"]==1).groupby("Month").count().plot(kind='bar',legend=False, ylabel="Number of Cancelled flights")

# Bar plot representing frequency of flights diverted monthwise
df_pandas[["Diverted","Month"]].where(df_pandas["Diverted"]==1).groupby("Month").count().plot(kind='bar',legend=False, ylabel="Number of Diverted flights")

# Bar plot representing frequency of highly delayed flights monthwise
df_pandas[["label","Month"]].where(df_pandas["label"]==1).groupby("Month").count().plot(kind='bar',legend=False, ylabel="Number of highly delayed flights")

# Visualization of distribution of flights being cancelled or not 
df_pandas["Cancelled"].value_counts().plot(kind="bar", xlabel="0 -Not cancelled 1-Cancelled", ylabel="Frequency")

# If a flight is cancelled what is the distribution of the cancellation code that is the reason of cancellation
df_pandas[["CancellationCode", "Cancelled"]].where(df_pandas["Cancelled"]==1).groupby("CancellationCode").count().plot(kind="bar", legend=False, ylabel="Frequency")

# Distribution of diverted flights
df_pandas["Diverted"].value_counts().plot(kind="bar", xlabel="0 -Not diverted 1-diverted", ylabel="Frequency")

# Visualization of the assmebled label column 
df_pandas["label"].value_counts().plot(kind="bar", xlabel="0-Slightly delayed 1-highly delayed 2-cancelled 3-diverted", ylabel="Frequency")

# Bar plot to visualize how many flights were highly delayed for each carrier flight
df_pandas[["label","UniqueCarrier"]].where(df_pandas["label"]==1).groupby("UniqueCarrier").count().plot(kind='bar', legend=False, ylabel='Number of highly delyaed flights')

# Bar plot to visualize how many flights were cancelled for each carrier flight
df_pandas[["label","UniqueCarrier"]].where(df_pandas["label"]==2).groupby("UniqueCarrier").count().plot(kind='bar', legend=False, ylabel='Number of Cancelled flights')

# Bar plot to visualize how many flights were diverted for each carrier flight
df_pandas[["label","UniqueCarrier"]].where(df_pandas["label"]==3).groupby("UniqueCarrier").count().plot(kind='bar', legend=False, ylabel='Number of diverted flights')

# Avergae delay caused by each carrier flight
df_pandas[["ArrDelay","UniqueCarrier"]].where(df_pandas["label"]==1).groupby("UniqueCarrier").mean().plot(kind='bar', legend=False, ylabel='Average delay in highly delayed flights')

# Average delay caused by flights when grouped together based on the origin airport 
df_pandas[["ArrDelay","Origin"]].where(df_pandas["label"]==1).groupby("Origin").mean()[:10].plot(kind='bar', legend=False, ylabel='Average delay')

# Average delay caused by flights when grouped together based on the destination airport 
df_pandas[["ArrDelay","Dest"]].where(df_pandas["label"]==1).groupby("Dest").mean()[:10].plot(kind='bar', legend=False, ylabel='Average delay')

# Frequency of flights that were diverted with respect to day of the week
df_pandas[["DayOfWeek","Diverted"]].where(df_pandas["Diverted"]==1).groupby("DayOfWeek").count().plot(kind='bar', legend=False, ylabel='Number of flights diverted')

# Frequency of flights that were cancelled with respect to day of the week
df_pandas[["DayOfWeek","Cancelled"]].where(df_pandas["Cancelled"]==1).groupby("DayOfWeek").count().plot(kind='bar', legend=False, ylabel='Number of flights cancelled')

# Frequency of flights that were labelled as highly delayed with respect to day of the week
df_pandas[["DayOfWeek","label"]].where(df_pandas["label"]==1).groupby("DayOfWeek").count().plot(kind='bar', legend=False, ylabel='Number of highly delayed flights')

# Classification of flights based on the Original Departure Time
fig, ax = plt.subplots(figsize = (15,10))
ax.hist([df_pandas["CRSDepTime"], df_pandas["CRSDepTime"].where(df_pandas["label"]==1),df_pandas["CRSDepTime"].where(df_pandas["Cancelled"]==1), df_pandas["CRSDepTime"].where(df_pandas["Diverted"]==1)], bins = 10, label = ["all flights","highly delayed", "cancelled", "diverted"])
plt.legend()

# Classification of flights based on the scheduled month
fig, ax = plt.subplots(figsize = (15,10))
ax.hist([df_pandas["Month"], df_pandas["Month"].where(df_pandas["label"]==1),df_pandas["Month"].where(df_pandas["Cancelled"]==1), df_pandas["Month"].where(df_pandas["Diverted"]==1)], bins = 10, label = ["all flights","highly delayed", "cancelled", "diverted"])
plt.legend()

# Classification of flights based on the distance between origin and destination
fig, ax = plt.subplots(figsize = (15,10))
ax.hist([df_pandas["Distance"], df_pandas["Distance"].where(df_pandas["label"]==1),df_pandas["Distance"].where(df_pandas["Cancelled"]==1), df_pandas["Distance"].where(df_pandas["Diverted"]==1)], bins = 10, label = ["all flights","highly delayed", "cancelled", "diverted"])
plt.legend()

# How much Delay in minutes was caused by each factor 
df_pandas['total_delay'] = (df_pandas['CarrierDelay'] + df_pandas['WeatherDelay'] + df_pandas['NASDelay'] + df_pandas['SecurityDelay'] + df_pandas['LateAircraftDelay'])
carrier_group = df_pandas['CarrierDelay'].groupby(df_pandas['UniqueCarrier']).mean()
weather_group = df_pandas['WeatherDelay'].groupby(df_pandas['UniqueCarrier']).mean()
nas_group = df_pandas['NASDelay'].groupby(df_pandas['UniqueCarrier']).mean()
security_group = df_pandas['SecurityDelay'].groupby(df_pandas['UniqueCarrier']).mean()
late_group = df_pandas['LateAircraftDelay'].groupby(df_pandas['UniqueCarrier']).mean()
w_bottom = carrier_group.values
n_bottom = w_bottom + weather_group.values
s_bottom = n_bottom + nas_group.values
l_bottom = s_bottom + security_group.values
x = carrier_group.index.values
fig, ax = plt.subplots(figsize = (15,10))
ax.set_xticks(np.arange(len(x)))
ax.bar(np.arange(len(x)),carrier_group.values, label='Carrier Delay')
ax.bar(np.arange(len(x)),weather_group.values, bottom=w_bottom, label='Weather Delay')
ax.bar(np.arange(len(x)),nas_group.values, bottom=n_bottom, label='NAS Delay')
ax.bar(np.arange(len(x)),security_group.values, bottom=s_bottom, label='Security Delay')
ax.bar(np.arange(len(x)),late_group.values, bottom=l_bottom, label='Late Aircraft Delay')
ax.set_xlabel('Aircraft Carrier Code')
ax.set_ylabel('Departure Delay in minutes')
plt.legend()
plt.show()

# Frequency of flights cancelled due to different cancellation codes
cancelled_group = df_pandas[df_pandas["Cancelled"]==1].groupby(['UniqueCarrier','CancellationCode']).size().reindex(fill_value=0.0).unstack()
cg = cancelled_group.fillna(0)
b_bottom = cg.loc[:,'A'].values
c_bottom = b_bottom + cg.loc[:,'B'].values
d_bottom = c_bottom + cg.loc[:,'B'].values
x = cg.loc[:,'A'].index.values
fig, ax = plt.subplots(figsize = (15,10))
ax.set_xticks(np.arange(len(x)))
ax.bar(np.arange(len(x)),cg.loc[:,'A'].values, align='center', label='Carrier')
ax.bar(np.arange(len(x)),cg.loc[:,'B'].values, align='center', bottom=b_bottom, label='Weather')
ax.bar(np.arange(len(x)),cg.loc[:,'C'].values, align='center', bottom=c_bottom, label='NAS')
ax.set_xlabel('Aircraft Carrier Code')
ax.set_ylabel('Number of Cancellations')
plt.legend()
plt.show()

# Correlation heatmap for different numeric features 
import seaborn as sns
numeric_columns_for_heatmap = []
for col in df_pandas.columns:
    if df_pandas[col].dtype != "object":
        numeric_columns_for_heatmap.append(col)
fig, ax = plt.subplots(figsize=(20,20))     
sns.heatmap(df_pandas[numeric_columns_for_heatmap].corr(), cmap = 'coolwarm', linewidths = 0.5, linecolor = 'black', ax=ax)