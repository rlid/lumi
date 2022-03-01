# To-Do

## Implement private mode
- Purpose: guarantee referral reward is paid (answerer cannot cheat)
- Hide the post on the site and make the root node inaccessible, so the answerer is forced to share the reward
- Total referral reward is capped at [20%] of total reward
- Distribution method: favour short distance to asker, i.e. spreading the word is more important than finding the "right" answerer 
- 1st referer in the successful chain gets 0.5 of total referral reward
- 2nd gets 0.5 of the remaining referer reward, and so on
- the answerer gets total reward - total referral reward distributed
- no incentive for answerer to use another account to refer himself as he will get the same reward
- (slight) problem: some incentive for a referer to use multiple accounts to create a chain referrals to extract max value from the total referral reward
  - the inventive is typically too small to justify the effort (create accounts and get all accounts to above withdrawal threshold)
  - the pattern will be easier to detect (accounts with only referral activities, because user is incentivised to reach withdraw threshold as quickly as possible)
- Option for mode switching: a post will start in private mode for certain duration and then be accessible from main site when the referral reward will be discretionary (and will incentivise distance to answerer)
  - the time limit changes the distribution inventive that favours short distance to asker, in the sense that it is better to find an answerer before the mode change to guarantee a referral reward


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
- once a request is fullfilled, the answerer is presented with options to show appreciations by sharing the reward, to
  either the people who introduced the him to the request, or if the answerer is answering the asker directly, to the
  community (not just contributors of this request, to discourage people from making a node on every post),
- options:
    - if answered with introductions: 0 - 40%, 20% as default, shared equally in the referral chain
    - if answered without introduction: 0 - 20%, 10% as default, shared [equally among
      the [20% / 10, if the lowest ranked users are tied, randomly choose such that the total number = 20% * N or 10]
      users with the highest goodwill level / in proportion to goodwill level?]
- answerer's goodwill level
    - option 1: cumulative own reward shared, increases as the reward is
      shared [decreases as shared reward is received?]
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

If q1 = q2, then the difference in proportion of claimed success = prob of lying, the larger the discrepancy, the larger
the prob of lying
