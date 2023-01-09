This Repo consist of code and documentation needed for successfully running the project End to End.
Below are the steps needed to be installed before running this project : 

# 1) Install Spark / PySpark: (Assuming Mac OS)

### Install Homebrew
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

### Set brew to Path
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> /Users/admin/.zprofile
    eval "$(/opt/homebrew/bin/brew shellenv)"

### Install OpenJDK 11
    brew install openjdk@11

### Install Scala (optional)
    brew install scala

### Install Python
    brew install python 

### Install Apache Spark
    brew install apache-spark
    
# Install Spark/PySpark  (Download links/documentations for OS - Windows, Linux, etc.)    

### Install Spark
    https://spark.apache.org/downloads.html 

### Install Python/Anaconda
    https://docs.anaconda.com/anaconda/install/index.html

# 2) Install machine learning libraries (Assuming already configured anaconda installed)

### Install Pandas 
    conda install pandas

### Install Scikit-learn 
    pip install -U scikit-learn

### Install pytorch 
    Please refer website : https://pytorch.org/get-started/locally/

# 3) Installing of MySQL and the related connectors

### Install MySQL
    https://dev.mysql.com/downloads/installer/
    
### Install MySQL Connector
    https://jar-download.com/artifacts/mysql/mysql-connector-java/5.1.48/source-code

# 4) Dataset (Available at Kaggle)
    https://www.kaggle.com/datasets/giovamata/airlinedelaycauses

# 5) Required changes in the Python file:  
  
  ### Spark Session Inialization:
            .config("spark.driver.extraClassPath","C:/Users/AnshumaanChauhan/Documents/spark-3.3.0-bin-hadoop3/spark-3.3.0-bin-hadoop3/jars/mysql-connector-java-5.1.48.jar")
  
  Here we need to change specified in this config attribute path to the Path in the system 
  
  ### Dataset Load Statement:
        dataset = spark.read.csv('C:\\Users\AnshumaanChauhan\\Documents\\Systems for DS Umass\\Project\\archive (5)\\DelayedFlights.csv',
                         header=True)
  
  Change the path specified in the load instruction to the path where dataset is stored in the system 
  
  ### Loading dataset into and from MySQL 
    updated_dataset.select(*(col(c) for c in dataset.columns)).write.format("jdbc") \
    .option("url", "jdbc:mysql://localhost:3306/Sys") \
    .option("driver", "com.mysql.jdbc.Driver").option("dbtable", "dataset") \
    .option("user", "root").option("password", "MySQL").save()
    
    updated_dataset = spark.read.format("jdbc") \
    .option("url", "jdbc:mysql://localhost:3306/Sys") \
    .option("driver", "com.mysql.jdbc.Driver").option("dbtable", "dataset") \
    .option("user", "root").option("password", "MySQL").load()
    
  In these statements change the value of "user" and "password" to the values specified during initializing of MySQL on the system 

###  File Description and Content 
     - MySQLQueries.sql file constits of the MySQL Analysis
     - SparkSQL_Queries_and_Python.py contains the code for PySpark analysis and visualizations using Matplotlib
     - models_for_delay_prediction.py file has the Machine Learning component of the Project 

