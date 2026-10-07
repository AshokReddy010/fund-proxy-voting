# Direction labels scored on the test split

The correct answer for each proposal is how ten specialist ESG fund houses voted on it.

|                                                               |   proposals | accuracy   | supports precision   | supports recall   | opposes precision   | opposes recall   | no clear answer   |
|:--------------------------------------------------------------|------------:|:-----------|:---------------------|:------------------|:--------------------|:-----------------|:------------------|
| Keyword rules                                                 |         578 | 76.6%      | 92.7%                | 79.7%             | 98.3%               | 68.9%            | 18.5%             |
| openai-gpt-oss-120b / v1_zero_shot                            |         578 | 69.2%      | 73.7%                | 93.5%             | 81.2%               | 7.9%             | 6.4%              |
| Rules, then v1_zero_shot where rules are unclear              |         578 | 88.1%      | 90.0%                | 95.7%             | 98.3%               | 68.9%            | 4.0%              |
| openai-gpt-oss-120b / v2_with_guidance                        |         578 | 76.5%      | 80.6%                | 92.5%             | 86.8%               | 36.0%            | 6.1%              |
| Rules, then v2_with_guidance where rules are unclear          |         578 | 88.4%      | 90.6%                | 95.7%             | 97.5%               | 70.1%            | 4.0%              |
| openai-gpt-oss-120b / v3_examples_and_reframing               |         578 | 84.9%      | 89.3%                | 92.8%             | 91.5%               | 65.2%            | 5.4%              |
| Rules, then v3_examples_and_reframing where rules are unclear |         578 | 91.0%      | 92.8%                | 96.9%             | 96.9%               | 76.2%            | 2.9%              |

## Keyword rules: what it said against the correct answer

| correct   |   opposes |   supports |   unclear |
|:----------|----------:|-----------:|----------:|
| opposes   |       113 |         26 |        25 |
| supports  |         2 |        330 |        82 |

## openai-gpt-oss-120b / v1_zero_shot: what it said against the correct answer

| correct   |   opposes |   supports |   unclear |
|:----------|----------:|-----------:|----------:|
| opposes   |        13 |        138 |        13 |
| supports  |         3 |        387 |        24 |

## Rules, then v1_zero_shot where rules are unclear: what it said against the correct answer

| correct   |   opposes |   supports |   unclear |
|:----------|----------:|-----------:|----------:|
| opposes   |       113 |         44 |         7 |
| supports  |         2 |        396 |        16 |

## openai-gpt-oss-120b / v2_with_guidance: what it said against the correct answer

| correct   |   opposes |   supports |   unclear |
|:----------|----------:|-----------:|----------:|
| opposes   |        59 |         92 |        13 |
| supports  |         9 |        383 |        22 |

## Rules, then v2_with_guidance where rules are unclear: what it said against the correct answer

| correct   |   opposes |   supports |   unclear |
|:----------|----------:|-----------:|----------:|
| opposes   |       115 |         41 |         8 |
| supports  |         3 |        396 |        15 |

## openai-gpt-oss-120b / v3_examples_and_reframing: what it said against the correct answer

| correct   |   opposes |   supports |   unclear |
|:----------|----------:|-----------:|----------:|
| opposes   |       107 |         46 |        11 |
| supports  |        10 |        384 |        20 |

## Rules, then v3_examples_and_reframing where rules are unclear: what it said against the correct answer

| correct   |   opposes |   supports |   unclear |
|:----------|----------:|-----------:|----------:|
| opposes   |       125 |         31 |         8 |
| supports  |         4 |        401 |         9 |
