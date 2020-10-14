# crawl-snowflakestatus
Crawl Snowflake status page and send alerts. https://status.snowflake.com/

> I am using Scrapy to crawl Snowflake status page and sending alerts using AWS Lambda and SES.

1) Create a Python Lambda layer with requests and scrapy python modules.

- Create Zip file

``` bash

#Create a folder

mkdir -p snowcrawler/python

#Change Dir
cd snowcrawler/python

#Install Module, I am using Python3.7.

pip3.7 install requests -t .

pip3.7 install scrapy -t .

#Change Dir
cd ..

#Zip it

zip -r9 ../pysnowcrawler.zip .



```

- Create a Lambda layer.

    - Log into AWS account.
    - Click on AWS Lambda service.
    - Under layers tab, Click on Create Layer.
    - Enter Name, Description, Select "Upload a .zip file" and click on Upload and select the zip file pysnowcrawler.zip
    - Select Python version I am using Python3.7.
    - Click on Create, this will create a new layer.


2) Create a Python Lambda Function (Requires a Role with SES send_mail access) and attach the layer.

``` python

import json
from scrapy import Selector
import datetime as dt
from datetime import datetime
from botocore.exceptions import ClientError
import boto3
import base64
import requests

CHARSET = "UTF-8"
SENDER = "Enter Sender email address"
SNOWFLAKE_REGION = "Enter you snowflake AWS Region" #example 'AWS - US West (Oregon)'
ADMIN_EMAIL = "Enter admin email" #needs a list ['email.com']
TO_ADDRESS = "Enter RECIPIENTS email " #needs a list ['email.com']

html_body = """<html>
<head></head>
<body>
  <h1>{header}</h1>
  <p>
       <br>{errordetails}<br>
       
  </p>
</body>
</html>
"""

def sendmail(errormessage,subject,RECIPIENTS):
    try:
            client = boto3.client('ses',region_name="Enter Aws region")
            htmlHeader = "Snowflake Service Error"
            response = client.send_email(
            Destination={
                'ToAddresses': RECIPIENTS,
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': html_body.format(header=htmlHeader,errordetails=errormessage),
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': subject,
                },
            },
            Source=SENDER,
            
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email Sent! Message ID:")
        print(response['MessageId'])

def lambda_handler(event, context):
    # TODO implement
    try:
        
        statustext = requests.get('https://status.snowflake.com/') 
        if statustext.status_code in [400,404,500,505]:
            errormessage = 'Snoflake status page not reachable'
            sendmail(errormessage,'Unable to crawl snowflake service status',ADMIN_EMAIL)
            return
        scrapy_info = Selector(text=statustext.text) 
        alldivs=scrapy_info.xpath('//div[contains(@class,"components-section")]//div[contains(@class,"component-container border-color is-group")]/div').getall()
        snowflakestatus = None
        for div in alldivs:
            if SNOWFLAKE_REGION in div:
                snowflakestatus =  (Selector(text=div).xpath('//span[contains(@class,"component-status tool")]/text()').get())
                print('snowflake status is '+snowflakestatus)
        if snowflakestatus == None:
            print('Unable to check status')
            errormessage = 'Unable to crawl snowflake service status'
            sendmail(errormessage,'Unable to crawl snowflake service status',ADMIN_EMAIL)
            return
        elif ' '.join(snowflakestatus.split()) != 'Operational':
            print('Snowflake service in '+SNOWFLAKE_REGION+' is down, status is '+str(' '.join(snowflakestatus.split())))
            errormessage = 'Snowflake service in '+SNOWFLAKE_REGION+' is down, status is '+str(' '.join(snowflakestatus.split()))
            sendmail(errormessage,'Snowflake service is down.',TO_ADDRESS)
    except Exception as e:
        sendmail(e,'Snowflake service crawler error',ADMIN_EMAIL)
        
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }



```


3) Schedule this Lambda using AWS Cloudwatch Event rules(Every 5 mins). This will send an alert if there is any change in the status.
