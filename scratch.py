


# The email body for recipients with non-HTML email clients.
from utils.aws import send_email

body_text = ("Amazon SES Test (Python)\r\n"
             "This email was sent with Amazon SES using the "
             "AWS SDK for Python (Boto)."
             )

# The HTML body of the email.
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
send_email(
    sender='sender@lumiask.com',
    recipient='recipient@lumiask.com',
    subject="Amazon SES Test (SDK for Python)",
    body_text=body_text,
    body_html=body_html
)
