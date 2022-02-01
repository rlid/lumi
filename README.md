# Notes
## Python
- `pip freeze > requirements.txt` to generate requirements.txt with version numbers
- `python -m unittest [test dir].[test file]` to run unit tests in a specific file

## Database
- `gcloud beta sql connect devins`
- `./cloud_sql_proxy -instances=lumiask:europe-west2:devins=tcp:9470`

## Google Cloud
- `gcloud app logs tail -s default`

## Git
- `git remote add [name] [url]` for each additional repo
- `git remote update`
- `git remote add all [url]` for the origin repo
- `git remote set-url --add --push all [url]` for each additional repo


# To-Do
## add transaction model to show account activities, e.g. income due to answers, referrals etc with timestamp
## Make template for "Get Started"
- I am looking for someone with a specific experience, e.g.
  - lives at / used to live at [a location]
  - in [a profession]
  - works at / used to work at [a company]
  - into a specific hobby
  - etc
- to
  - (open-ended) share their knowledge / experience / opinion / advice by answering a few questions
  - take a picture / record a video of a place / object of interest [under a specific condition]
  - to give how-to instructions / step-by-step walk-through
  - help to find specific information, e.g. a post on Reddit, a YouTube video, source of a meme etc
  - do online activities together, e.g. play a game
  - help to publicise something on social media
- NO legal / tax advice - keep it casual and make friends!

### Add verification protocol to guide
- take a picture / record a video with hand gesture "L" in frame
- possibly consider a few variations to the gesture chosen by the asker to prevent photoshopping

## incentive optimization
- prevent cheating with multiple account
- once a request is fullfilled, the answerer is presented with options to show appreciations by sharing the reward, to either the people who introduced the him to the request, or if the answerer is answering the asker directly, to the community (not just contributors of this request, to discourage people from making a node on every quest), 
- options:
  - if answered with introductions: 0 - 40%, 20% as default, shared equally in the referral chain
  - if answered without introduction: 0 - 20%, 10% as default, shared [equally among the [20% / 10, if the lowest ranked users are tied, randomly choose such that the total number = 20% * N or 10] users with the highest goodwill level / in proportion to goodwill level?]
- answerer's goodwill level
  - option 1: cumulative own reward shared, increases as the reward is shared [decreases as shared reward is received?]
  - option 2: exponentially weighted average of amount shared, to give new users a fair chance
- the more you share, the more will be shared with you

### referrals
- a node is created for the referrer, 

Maths

competence = Prob of success = p

credibility = Prob(Claim Fail | Fail) = 1 - q

q for answerer = q1

q for asker = q2

Proportion of claimed success

= p + (1-p)*q1 = p + q1 - p*q1 = p * (1 - q1) + q1 for answerer

= 1 - [(1-p) + p * q2] = p - p * q2 = p * (1 - q2) for asker

If q1 = q2, then the difference in proportion of claimed success = prob of lying, the larger the discrepancy, the larger the prob of lying
