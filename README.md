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

- Using the EB CLI with AWS CodeCommit: https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli-codecommit.html

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
