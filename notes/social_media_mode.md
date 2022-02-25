### Strategy 1: fixed referral budget
- OP sets a portion of the total reward aside for referral, answerer will get any remaining RR not claimed. TR = RR + AR + PF
  - Strategy 1: 1st referrer gets half of RR, 2nd referrer gets half of the remaining RR, etc...
    - smaller incentive to cheat
    - smaller incentive to refer
  - Strategy 2: 1st referrer gets [1/n] of RR, 2nd referrer gets [1/n], and so on until the nth referrer, at which point there is no incentive to refer
    - fairer for the later referrers 
  - Strategy 3: each referrer decides for themselves how much to take from the RR pot
    - most flexible as users doing more targeted referrals (more effort) will take more and users doing mass blasts (less effort) will probably be happy with less
    - good option if the referrer knows how likely he can find the answerer directly

### Strategy 2: flexible referral budget
- OP sets only 1 reward to be shared between answerer and referrers (if any), platform fee is added on top. TR = R + PF
- 1st referrer gets X, on his node R will become R-X for sellers (OP is asker) and R+X for buyers (OP is answerer)
- less control for OP
- can get unrealistic, especially for buyers (OP is answerer), bad for publicity even if no traction


### Decision
 - Start with something simple - fixed referral budget, strategy 2 with n=4 and RR=40% of TR
 - Power user mode later with more flexibilities
