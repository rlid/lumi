import os

import boto3
from botocore.exceptions import ClientError
from flask import current_app
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
        current_app.logger.exception(e)
    else:
        current_app.logger.info("Email sent! Message ID:"),
        current_app.logger.info(response['MessageId'])


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
        current_app.logger.info(response.status_code)
        current_app.logger.info(response.body)
        current_app.logger.info(response.headers)
    except Exception as e:
        current_app.logger.exception(e)


def send_email_dummy(sender, recipient, subject, body_text, body_html=None):
    current_app.logger.info('--------------------------------- BEGIN EMAIL ----------------------------------')
    current_app.logger.info(f'From: {sender}')
    current_app.logger.info(f'To: {recipient}')
    current_app.logger.info(f'Subject: {subject}')
    current_app.logger.info(f'Content (Plain Text):\n{body_text}')
    current_app.logger.info(f'Content (HTML):\n{body_html}')
    current_app.logger.info('---------------------------------- END EMAIL -----------------------------------')
