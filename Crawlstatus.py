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
                print('snowflake status is '+' '.join(snowflakestatus.split()))
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

