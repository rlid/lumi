Rules

Reward for introduction:
 - last introducer: 20%
 - 2nd last: 10%
 - nth last: 20%/2^(n-1)
 - Solution provider takes the rest - 10% fee (from 90% if no introduction to 50% as number of introductions approaches infinity)

How to agree on job completion
 - deadline (seller ack + [1] hrs) + mutually agreed extension
 - min word count
 - buyer confirmation

reputation = sum(price_i * if(no dispute, 1, if(self_rep_t-1 > user_rep_i_t-1, 1, -1)) / sum(price_i)

Job pricing
 - referer/seller suggestion (buyer's discretion to accept/reject, no change to the job if rejected)


Platform fee = 20%
Referer fee = 0 (if no referer) or 20%-30%
Seller fee = 80% - referer fee (80% to 50%)


Platform insurance = Initial platform insurance + 10% of total profit
User insurance = User deposit
Sponsor insurance = Sponsor deposit

Max value of task a seller can guarantee = 20% * Platform insurance + 10% * Sponsor insurance - Total claim against the seller + Additional guarantee offered by the seller (<= user deposit)

Max value of task a buyer can guarantee = 20% * Platform insurance + 10% * Sponsor insurance - Total claim against the buyer + Additional guarantee offered by the buyer (<= user deposit)

---
Guarantee

Buyer guarantee: if any dispute, the seller gets at least {20% * Platform insurance + 10% * Sponsor insurance - Total claim against the buyer + Additional guarantee offered by the buyer}

Seller guarantee: if any dispute, the buyer gets back at least {20% * Platform insurance + 10% * Sponsor insurance - Total claim against the seller + Additional guarantee offered by the seller}

In case of dispute, the side with a higher credibility level will get the guaranteed amount from the other side, but both will get a new credibility assessment from each other.

---
Credibility score:
If voted up: new score = min(self current score * 2, 


---
Design criteria of credibility rating
1. Does not deter new users 
2. Reward good consistency, penalise bar consistency 
3. Information loses value with tiTim

Reputation score: good/unknown/bad based on percentile
Sum(Job value * Job rating * Consistency factor)

Consistency factor:
Option 1: # of consecutive +/-'so
Option 2: hit ratio since inception 
Option 3: hit ratio in last [n] jobs

While the status is unverified, the user's ratings has no effect, once his status is verified, his ratings will take effect on the persons he rated on.


Upon job failure:
 - Buyer gets money back
 - Seller loses 50% of seller deposit, 10% of Platform insurance, 5% of Sponsor insurance
 - Buyer loses 

Verification process:
 - obtains + rating in jobs from 3 different users, earning 50% of verified user fees
 - once verified, allocate initial platform insurance = fees earned
 - job value insured = 20% of total insurance value

Conditions for buyers to posting higher value questions:
 - question without money-back guarantee (carries double voting power)
 - job value insured = 20% of total insurance value

Jobs without a money-back guarantee
 - not available to unverified users
 - carries [2]x voting power


Dispute resolution
 - protect the more profitable user (= 50% of the profit from each task involved)
 - platform insured value = 10% of total profit - total claims from user
 - protect the source of fund (buyer)
 - the side with higher reputation decides
 - incentive based



Users gets titles/unlock achievements depending on various stats

