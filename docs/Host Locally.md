# Hosting Locally
> Note: The bot doesn't use a lot of resources. My testing shows it uses less than 100 MB of RAM and 0.1% of CPU

## Create MongoDB URI and Discord Bot Token

1. Follow this tutorial and keep the mongodb uri as well as bot token handy.
2. Video: [YouTube](https://youtu.be/OQeUGL26Zdk)
3. Ignore the HEROKU Variables
4. Also Keep your discord user id with you.

## Setting up bot locally

1. Download the latest version of this repository from [this link](https://github.com/jsmsj/GdriveCloneBot/archive/refs/heads/master.zip)
2. Extract it at a suitable location
![](../images/local%201.png)

3. Go to cogs folder and delete _config.py.
4. Open _config_sample.py and edit accordingly.
    >Make sure to retain the quotes and brackets.

    ![](../images/local%202.png)

## Installing requirements

1. Open Command Prompt in that folder.
   ![](../images/local%203.png)

2. <b>Optional Step</b> Run `pip install virtualenv`.
3. Then run `virtualenv venv` to create a virtual environment.
   ![](../images/local%204.png)
4. Run `cd venv/Scripts`
5. Activate the virtual environment by running `activate`
6. Go back to the bot directory where main.py file is located.

7. Run `pip install -r requirements.txt`
   ![](../images/local%205.png)

## Running the bot

1. Run `python main.py`
   ![](../images/local%206.png)

# The bot is ready. Now you can use the bot as you wish.

### Commands Examples are available in the following video : 

<p><a href="https://www.youtube.com/watch?v=MfnP1M0BW7Y"> <img src="https://img.shields.io/badge/See%20Video-black?style=for-the-badge&logo=YouTube" width="160""/></a></p>