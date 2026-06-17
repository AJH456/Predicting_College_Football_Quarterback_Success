# **Predicting College Quarterback Recruit Success**

Data Sources for this project: 

https://247sports.com/

https://www.sports-reference.com/cfb/ 

_This project seeks to answer the following:_

**To what extent can a quarterback's high school scouting stats such as star rating and scouting report sentiment, as well as their committed colleges team-level statisitics from the season prior to the players arrival, predict that players career success at that school?**

This Project will be accessed using Regression to predict a quarterbacks success at the school they committed to out of high school. A players success, given data availability, will be accessed as their overall touchdown to interception ratio. Most schools would not consider a quarterback a "success" if they were not on the team for more then 1 year. Therefore, this project will only attempt to analysis quarterbacks who stayed at their committed school for at least 2 years. Due to the core research of scouting report sentiment analysis involved with this project, only players with scouting reports from 247sports.com will be analyzed.

_This project combines the following datasets in order to achieve results (Datasets available under the Data section folder):_

# Data

### Data from 247 sports:

- scouting_reports_2019.json
- scouting_reports_2020.json
- scouting_reports_2021.json
- scouting_reports_2022.json
- scouting_reports_2023.json

These datasets were web scrapped from the 247 sports quarterback recruit rankings list from 2019 - 2023. 2019 was the earliest year scrapped because there were little to no scouting reports on 247 sports prior to that year. 2023 was the last year scrapped as we want our players to have been in college for a few years.

### Data from college football reference:

- Team_standings_2018_2025.xlsx
- Team_stats_2018_2025.xlsx
- player_stats_2018_2025.csv

These datasets provide team-level and player-level stats data for additional context and modeling purposes.

### Created datasets:
- cleaned_recruits_data.csv
- final_player_data.csv
- qb_trait_scores.csv


# Code: 

The order of code notebooks in sequential order of creation and what they accomplish:

1.) All web scrappers in the "Web Scrappers" folder 

    These notebooks all seperately scrape different years of Quarterback recruitment rankings information from 247sports.com and store them in the jsons listed above.


2.) Data_Cleaning_and_Feature_Engineering.ipynb

    This notebook imports all of the json files from web scraping, converts them to dataframes, cleans the data, adds new features (feature engineering) and exports them into one consolidated dataset called 'cleaned_recruits_data.csv'

3.) qb_sentiment_analysis.ipynb

    This notebook reads in the data from the prior notebook, 'cleaned_recruits_data.csv', and uses Natural Language Processing to create sentiment scores for each detectable category of a players characterisitics given their scouting report. For example, each players scouting report is read in and aspects such as 'arm strength' or 'accuracy' are created as new columns and assigned a sentiment score that can be in the range of (-1 to 1). This portion of the project is by far the most important as it is the most experimental part and is crucial to the research question. To better visualize these sentiment scores, various visualizations were created to display the differences among players in the data. These visualizations were saved as pngs and stored in the 'visualizations' folder. Lastly, the finalized recruitment dataset with the sentiment scores were exported/ saved as 'qb_trait_scores'.

4.) Scouting_Report_Cleaning_and_Merging.ipynb

    This notebook imports the college football reference datasets: 'Team_standings_2018_2025.xlsx', 'Team_stats_2018_2025.xlsx' and 'player_stats_2018_2025.csv'. It also imports the dataset from the previous notebook, 'qb_trait_scores', in order to merge all of these datsets together. This allows for the creation of the following dataset such that every row represents a given quarterback recruit with their recruitment stats/ characteristics, their average career stats at their committed school, and their teams stats and standings from the season prior to their enrollment at that school. Lastly, the data was filter so that players must have played at least 2 years at their committed school. This final dataset was exported as the 'final_player_data.csv'.

5.) modeling.ipynb

    This final notebook imports the 'final_player_data.csv' and attempts to use the wide pool of player stats, recruitment stats, and team level stats to predict that players career touchdown to interception ratio at their committed school. A wide variety of regression models were attempted, such as: Multiple linear regression, Ridge Regression, Lasso Regression, XGBoost Regression, Random Forest Regression and Gradient Boosting Regression. Although the results were quite mild and may not be statisitically distinguishable from 0, an XGBoost model produced noticably better results than the other models with the following variables: 'composite_rating', 'overall_losses_team_before_enrollment', 'ppg_offense_team_before_enrollment', 'ppg_defense_team_before_enrollment', 'srs_team_before_enrollment'. Specifially, here are my concluding notes within this notebook:

    Although the results from this project are quite disappointing, there are still some key takeaways.

    - XGBoost modeling seemed to provide slightly positive results (although not meeting homoscadesticity assumption)

    - More Scouting and college football recruit data needs to be made publically available. 

    - The Data is far too small to make a great model for this problem. This may be for a few reasons such as limited scouting data and the transfer portal, of which has caused recent recruits to transfer schools. This affects the model because every player used for this project must play for the team they committed to out of high school for at least 2 years. I did this because how can one consider a recruit a success for their program if they are not there for more then one season?

    - From the Results of the XGBoost, one could hypothesize that a high school recruits composite rating, a teams losses in the season prior to the recruits arrival, a teams points per game in the season prior to the recruits arrival, a teams points per game that their defense let's up in the season prior to the recruits arrival, and that teams srs in the season before a recruits arrival ALL could have an affect on that recruits career TD/ Interception ratio at their committed school.


