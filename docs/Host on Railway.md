# Hosting on Railway.app

## Forking and modifying procfile
1. Fork the repository [(click me)](https://github.com/jsmsj/GdriveCloneBot/fork)
   ![](../images/railway%201.png)
2. Open `Procfile` and replace `worker: python main.py` by `web: python main.py`
   ![](../images/railway%202.png)
   ![](../images/railway%203.png)
   ![](../images/railway%204.png)

## Railway.app settings.

1. Go to [railway.app/new](https://railway.app/new)
2. Select `Deploy from Github repo`
   ![](../images/railway%205.png)

3. Select the bot's repository.
   ![](../images/railway%206.png)

4. Select `Add variables`.
   ![](../images/railway%207.png)

5. Click on `Raw Editor` or add the variables one by one
   ![](../images/railway%208.png)

   ![](../images/railway%209.png)

6. Let Railway deploy the bot.
   ![](../images/railway%2010.png)

7. Once the below screen is shown then your bot has been deployed
   ![](../images/railway%2011.png)

## Last step to automatically recieve updates in the bot.

1. Go to `Actions` in your repository which you have forked.
   ![](../images/railway%2012.png)

2. Enable workflows
   ![](../images/railway%2013.png)

3. Choose `Sync Upstream`
   ![](../images/railway%2014.png)

4. Enable the workflow.
   ![](../images/railway%2015.png)

5. Run the workflow
   ![](../images/railway%2016.png)

6. Now you are done. Enjoy Cloning :)
   ![](../images/railway%2017.png)
   
