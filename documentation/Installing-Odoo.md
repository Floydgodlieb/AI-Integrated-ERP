# Installing of odoo on local machine.
To start of I cloned the github repo of odoo. This can take up to 10 minutes because of the sheer size of the repo.

While my laptop is buys with cloning the repo I went and looked for the database. This is the most important part that we need for this project.

They use PostgresSQL, this is one that I haven't used yet, so enough too learn. I've used Mysql for the biggerst part with some experiense in Mssql and some nosql databases. The difference between Mysql and Prostgress are not significant. Postgress is know fore have some deeper queries.

After installing Postgress its time to find the sql files about how the database was set up.

I came across a error while running postgres using pgAdmin 4. There seems to be a problem during the installation, to fix it I'm going to install pgAdmin 4 from the original source instead of the Postgress installer. This didn't resolve the issue.

I found out that there was a function made to create the tables. There is a file called `sql.yp` and in this file there a a couple of function. One of them is called 'create_model_table'.

# Docker
After running in the issue mentioned above our teacher told us to try docker. This could solve the issue with postgress. After having a look at the documentation of Odoo we found a docker container. 

Installing it makes two containers, one for odoo and the other for the database. The odoo leads to a port 8069:8069. Accesable at the url `http://localhost:8069/web/database/selector`.

This opens up a registration form with a generated password of 'na77-3nm3-smsv'. After filling in all forms I pressed the button 'create database'.

I am now in a dashboard with all services odoo delivers.        

In the settings I found a API key listing where i should be able to add a API to the software.

# Documentation
While reading the documentation you noticed the topic Search and read, Create records, Update records and Delete records. This gives us the information we needed. It is possible to use crud (create, read, update and delete) functions with a API. 

All we need now it to create a AI that sends API updates.

# AI
I found a AI model that is local and can use api's 
Its called LocalAI (https://github.com/mudler/LocalAI) and it's open source with a docker container.
It uses cpu power only. That means your laptop can use it while having a slow gpu or onboard graphics.