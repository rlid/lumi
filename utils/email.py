import os

import boto3
from botocore.exceptions import ClientError
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def send_email_aws(sender, recipient, subject, body_text, body_html=None,
                   charset="UTF-8",
                   configuration_set="lumiask-general",
                   region_name="eu-west-2"):
    client = boto3.client('ses', region_name=region_name)
    # Try to send the email.
    try:
        # Provide the contents of the email.
        message = {
            'Body': {
                'Text': {
                    'Charset': charset,
                    'Data': body_text,
                },
            },
            'Subject': {
                'Charset': charset,
                'Data': subject,
            },
        }
        if body_html:
            message['Body']['Html'] = {
                'Charset': charset,
                'Data': body_html,
            }

        response = client.send_email(
            Destination={
                'ToAddresses': [
                    recipient,
                ],
            },
            Message=message,
            Source=sender,
            # If you are not using a configuration set, comment or delete the
            # following line
            ConfigurationSetName=configuration_set,
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])


def send_email_sg(sender, recipient, subject, body_text, body_html=None):
    message = Mail(
        from_email=sender,
        to_emails=recipient,
        subject=subject,
        plain_text_content=body_text,
        html_content=body_html)
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e.message)


send_email = send_email_sg
