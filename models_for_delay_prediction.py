import time
import pandas as pd
import numpy as np
from pandas import get_dummies

from sklearn.model_selection import cross_val_score
from sklearn.naive_bayes import GaussianNB
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from pytorch_tabnet.tab_model import TabNetClassifier, TabNetRegressor

path = "./data/DelayedFlights.csv"  # Can be made configurable. 

def read_csv_file():
    return pd.read_csv(path)

def remove_cancelled_flights(data_frame):
    data_frame = data_frame[data_frame['Cancelled'] != 1]
    data_frame = data_frame[data_frame['Diverted'] != 1]
    return data_frame

def return_one_or_zero(row):
    if int(row.ArrDelay) <= 15:
        return 0 
    else:
        return 1

def truncate_data_frame(data_frame):
    where = data_frame["Month"].isin([10,11,12])
    data_frame = data_frame[where]
    return data_frame

def get_dtypes(data, features):
    output = {}
    for f in features:
        dtype = str(data[f].dtype)
        if dtype not in output.keys(): output[dtype] = [f]
        else: output[dtype] += [f]
    return output

def get_equi_distribution_data(data_frame, target_feature):
    delayed = data_frame[data_frame[target_feature] == 1]
    not_delayed = data_frame[data_frame[target_feature] == 0]
    #new_dataset = pd.concat([delayed, not_delayed.sample(n=len(delayed
    new_dataset = pd.concat([not_delayed, delayed.sample(n=len(not_delayed))],0)
    print(delayed.shape)
    print(not_delayed.shape)
    return new_dataset

def calculate_results_for_models(model_names, x_values, y_values):
    cv_scores_for_models = {} 
    for model_name in model_names :
        start_time = time.time()
        model_string_name = type(model_name).__name__
        compute = cross_val_score(model_name, x_values, y_values, cv=5)
        end_time = time.time()
        cv_scores_for_models[model_string_name] = (compute.mean(), end_time - start_time)
    return cv_scores_for_models

def do_classify_using_tabnet(X, Y):
    total_len = len(X)
    training_len = int(total_len * 0.8)
    X_train, Y_train = X[:training_len], Y[:training_len]
    X_valid, Y_valid = X[training_len:], Y[training_len:]
    clf = TabNetClassifier()  #TabNetRegressor()
    start_time = time.time()
    clf.fit(
        X_train.values, Y_train.classification_label,
        eval_set=[(X_valid.values, Y_valid.classification_label)]
    )
    end_time = time.time()
    print("The time taken in seconds. is : ", end_time-start_time)

if __name__ == "__main__":
    data_frame = read_csv_file()
    target_feature = "classification_label"
    # Arr delay column can be used. Arr delay more 15 min, then delayed.
    data_frame = remove_cancelled_flights(data_frame)
    data_frame['classification_label'] = data_frame.apply(lambda row: return_one_or_zero(row), axis=1)
    leaky_features = ["Year", "Diverted", "ArrTime", "ActualElapsedTime", "AirTime", "ArrDelay", "TaxiOut", "Cancelled","TaxiIn", "CarrierDelay", "WeatherDelay", "NASDelay", "SecurityDelay","LateAircraftDelay", "CancellationCode", "change_in_elapsed_time", "TailNum"]
    features = [x for x in data_frame.columns if (x != target_feature) & (x not in leaky_features) & (len(data_frame[x].unique().tolist()) > 1)]
    data_frame = data_frame[features +[target_feature]]
    # Random sampling preffered.
    #data_frame = truncate_data_frame(data_frame)
    dtypes = get_dtypes(data_frame, features)
    new_dataset = get_equi_distribution_data(data_frame, target_feature)
    categories = ["Month", "DayOfWeek", "DayofMonth"]
    categories += dtypes["object"]
    numerical_features_excluding_classification_label = []
    for feature in dtypes["int64"]:
        if feature not in categories:
            numerical_features_excluding_classification_label.append(feature)
    numerical_features_excluding_classification_label += dtypes['float64']
    numerical_features = numerical_features_excluding_classification_label + ["classification_label"]
    one_hot_encoded = get_dummies(new_dataset[categories].fillna("Unknown"))
    final_dataset = pd.concat([one_hot_encoded, new_dataset[numerical_features].fillna(0)],1)
    final_feature_list = list(final_dataset.columns)
    training_features = final_feature_list.remove("classification_label")
    training_features = final_feature_list
    target_label_feature = ["classification_label"]
    trainable_df = final_dataset.sample(n=300000)
    print(trainable_df.shape)
    print("Final dataset prepared..")

    X = trainable_df[training_features]
    Y = trainable_df[target_label_feature]

    models = [GaussianNB(), RandomForestClassifier(), AdaBoostClassifier(), GradientBoostingClassifier(), XGBClassifier()]
    # PPT can include the fastest and most accurate ones..

    print(calculate_results_for_models(models, X, Y.classification_label))
    print("Calculation done..")

    print("Now for the Neural network based approach where we use TabNet : ")

    do_classify_using_tabnet(X, Y)




