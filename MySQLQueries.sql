#Query to count the number of flights cancelled along with the cancellation code
# A = carrier, B = weather, C = NAS, D = security, N=None
select sys.dataset.CancellationCode, count(sys.dataset.CancellationCode) as Number_of_Flights
from sys.dataset
group by sys.dataset.CancellationCode;

#Query to calculate number of flights diverted 
select sys.dataset.Diverted, count(sys.dataset.Diverted) as Number_of_Flights
from sys.dataset
group by sys.dataset.Diverted;

#Adding a label column to store the results - whether slightly delayed, highly delayed or other
Alter table sys.dataset add label int;

# If slightly delayed = 0, highly delayed =1, other =2
UPDATE  sys.dataset
SET     sys.dataset.label = IF((sys.dataset.CancellationCode='N' and sys.dataset.Diverted=0 and sys.dataset.ArrDelay<=15),0, IF((sys.dataset.CancellationCode='N' and sys.dataset.Diverted=0 and sys.dataset.ArrDelay>15),1,2));

# Checking the distribution of the label values
select sys.dataset.label, count(sys.dataset.label)
from sys.dataset
group by sys.dataset.label;

# Sub splitting the value 2 (other) into 2 values - Diverted=3, Cancelled=2
UPDATE  sys.dataset
SET     sys.dataset.label = IF((sys.dataset.CancellationCode!='N'),2, IF((sys.dataset.Diverted=1),3,sys.dataset.label));

#Checking the distribution of delayedness, diverted, and cancelled 
select sys.dataset.label, count(sys.dataset.label) as Flights_in_each_category
from sys.dataset
group by sys.dataset.label;

#Carriers along with the number of flights in highly delayed category 
select sys.dataset.UniqueCarrier, count(sys.dataset.label) as Count
from sys.dataset
where sys.dataset.label=1
group by sys.dataset.UniqueCarrier
order by Count desc;

#Carriers along with the number of flights in Cancelled category 
select sys.dataset.UniqueCarrier, count(sys.dataset.label) as Count
from sys.dataset
where sys.dataset.label=2
group by sys.dataset.UniqueCarrier
order by Count desc;

#Carriers along with the number of flights in Diverted category 
select sys.dataset.UniqueCarrier, count(sys.dataset.label) as Count
from sys.dataset
where sys.dataset.label=3
group by sys.dataset.UniqueCarrier
order by Count desc;

#Carriers and the average delay their flights seems to have
select sys.dataset.UniqueCarrier, avg(sys.dataset.ArrDelay) as Avg_Delay
from sys.dataset
where sys.dataset.ArrDelay>0 and sys.dataset.CancellationCode='N' and sys.dataset.Diverted=0
group by sys.dataset.UniqueCarrier
order by Avg_Delay desc;

#Average delay in flights based on the origin of flights
select sys.dataset.Origin, avg(sys.dataset.ArrDelay) as Avg_delay_per_flight
from sys.dataset
where sys.dataset.ArrDelay>0 and sys.dataset.CancellationCode='N' and sys.dataset.Diverted=0
group by sys.dataset.Origin
order by Avg_delay_per_flight desc;

#Average delay in flights based on the final destination of flights
select sys.dataset.Dest, avg(sys.dataset.ArrDelay) as Avg_delay_per_flight
from sys.dataset
where sys.dataset.ArrDelay>0 and sys.dataset.CancellationCode='N' and sys.dataset.Diverted=0
group by sys.dataset.Dest
order by Avg_delay_per_flight desc;