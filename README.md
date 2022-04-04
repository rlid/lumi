# Notes

## Python

- `pip freeze > requirements.txt` to generate requirements.txt with version numbers
- `python -m unittest [test dir].[test file]` to run unit tests in a specific file

## Database

- `gcloud beta sql connect devins`
- `./cloud_sql_proxy -instances=lumiask:europe-west2:devins=tcp:9470`

## Google Cloud

- `gcloud app logs tail -s default`

## AWS
- CodeCommit
  - for ~/.ssh/config: https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up-ssh-unixes.html
  - general info: https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up.html?icmpid=docs_acc_console_connect_np#setting-up-compat
- Install EB CLI
    - https://github.com/aws/aws-elastic-beanstalk-cli-setup
    - install virtualenv (macOS: `brew search virtualenv`)
    - deactivate any venv, then run `python ./aws-elastic-beanstalk-cli-setup/scripts/ebcli_installer.py`
    - add `eb` to
      PATH: `echo 'export PATH="/Users/rli/.ebcli-virtual-env/executables:$PATH"' >> ~/.zshrc && source ~/.zshrc`
- Using the EB CLI with AWS CodeCommit: https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli-codecommit.html
    - activate venv (so `python` can be found)
    - run `eb init`
    - run `eb create [env name]`, note the security groups created
- Amazon RDS
    - Create new database
        - enable public access
        - create a password for "postgres"
        - create a database
        - use the "default" security group
        - add the group noted for the EB environment to the inbound rules of the default security group
- Cloudflare
    - point set CNAME to the AWS URL
- Elastic Beanstalk
    - set the environment variables
    - remember to set FORCE_HTTPS=true after Cloudflare is set up
    - remember to set SENDGRID_API_KEY, AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY which are not loaded through Flask
      config

## Git

- `git remote add [name] [url]` for each additional repo
- `git remote update`
- `git remote add all [url]` for the origin repo
- `git remote set-url --add --push all [url]` for each additional repo

## Jinja2

- Test for not none: `x is not none` (note the lowercaes "n" in "none")

## SqlAlchemy

- Test for not none in filter: `x != None`, or `x.is_not(None)`

## Colour codes

- Green / Success: after user did something successfully, and no more action required
- Yellow / Warning: user is recommended / advised to do something
- Red / Danger: after user's action failed, and user needs to try something else
- Info / Cyan: purely FYI, no action required and any suggested/possible action is optional
