# using SendGrid's Python Library
# https://github.com/sendgrid/sendgrid-python
import os

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

body_text = ("Amazon SES Test (Python)\r\n"
             "This email was sent with Amazon SES using the "
             "AWS SDK for Python (Boto)."
             )

body_html = """<html>
<head></head>
<body>
  <h1>Amazon SES Test (SDK for Python)</h1>
  <p>This email was sent with
    <a href='https://aws.amazon.com/ses/'>Amazon SES</a> using the
    <a href='https://aws.amazon.com/sdk-for-python/'>
      AWS SDK for Python (Boto)</a>.</p>
</body>
</html>
            """
# send_email(
#     sender='sender@knowble.com',
#     recipient='recipient@knowble.com',
#     subject="Amazon SES Test (SDK for Python)",
#     body_text=body_text,
#     body_html=body_html
# )


message = Mail(
    from_email='sender@knowble.com',
    to_emails='recipient@knowble.com',
    subject='Sending with Twilio SendGrid is Fun',
    plain_text_content=body_text,
    html_content=body_html)
try:
    sg = SendGridAPIClient('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')
    response = sg.send(message)
    print(response.status_code)
    print(response.body)
    print(response.headers)
except Exception as e:
    print(e.message)
