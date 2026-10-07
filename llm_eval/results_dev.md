# Direction labels scored on the dev split

The correct answer for each proposal is how ten specialist ESG fund houses voted on it.

|                                                               |   proposals | accuracy   | supports precision   | supports recall   | opposes precision   | opposes recall   | no clear answer   |
|:--------------------------------------------------------------|------------:|:-----------|:---------------------|:------------------|:--------------------|:-----------------|:------------------|
| Keyword rules                                                 |         237 | 78.5%      | 94.9%                | 78.8%             | 100.0%              | 77.8%            | 18.6%             |
| openai-gpt-oss-120b / v1_zero_shot                            |         237 | 67.5%      | 73.7%                | 93.3%             | 100.0%              | 8.3%             | 9.3%              |
| Rules, then v1_zero_shot where rules are unclear              |         237 | 92.0%      | 93.1%                | 97.6%             | 100.0%              | 79.2%            | 3.0%              |
| openai-gpt-oss-120b / v2_with_guidance                        |         237 | 73.4%      | 77.9%                | 92.1%             | 81.5%               | 30.6%            | 6.3%              |
| Rules, then v2_with_guidance where rules are unclear          |         237 | 92.4%      | 92.6%                | 98.2%             | 98.3%               | 79.2%            | 1.7%              |
| openai-gpt-oss-120b / v3_examples_and_reframing               |         237 | 88.6%      | 90.2%                | 94.5%             | 94.7%               | 75.0%            | 3.0%              |
| Rules, then v3_examples_and_reframing where rules are unclear |         237 | 93.7%      | 93.6%                | 97.6%             | 100.0%              | 84.7%            | 1.7%              |

## Keyword rules: what it said against the correct answer

| correct   |   opposes |   supports |   unclear |
|:----------|----------:|-----------:|----------:|
| opposes   |        56 |          7 |         9 |
| supports  |         0 |        130 |        35 |

## openai-gpt-oss-120b / v1_zero_shot: what it said against the correct answer

| correct   |   opposes |   supports |   unclear |
|:----------|----------:|-----------:|----------:|
| opposes   |         6 |         55 |        11 |
| supports  |         0 |        154 |        11 |

## Rules, then v1_zero_shot where rules are unclear: what it said against the correct answer

| correct   |   opposes |   supports |   unclear |
|:----------|----------:|-----------:|----------:|
| opposes   |        57 |         12 |         3 |
| supports  |         0 |        161 |         4 |

## openai-gpt-oss-120b / v2_with_guidance: what it said against the correct answer

| correct   |   opposes |   supports |   unclear |
|:----------|----------:|-----------:|----------:|
| opposes   |        22 |         43 |         7 |
| supports  |         5 |        152 |         8 |

## Rules, then v2_with_guidance where rules are unclear: what it said against the correct answer

| correct   |   opposes |   supports |   unclear |
|:----------|----------:|-----------:|----------:|
| opposes   |        57 |         13 |         2 |
| supports  |         1 |        162 |         2 |

## openai-gpt-oss-120b / v3_examples_and_reframing: what it said against the correct answer

| correct   |   opposes |   supports |   unclear |
|:----------|----------:|-----------:|----------:|
| opposes   |        54 |         17 |         1 |
| supports  |         3 |        156 |         6 |

## Rules, then v3_examples_and_reframing where rules are unclear: what it said against the correct answer

| correct   |   opposes |   supports |   unclear |
|:----------|----------:|-----------:|----------:|
| opposes   |        61 |         11 |         0 |
| supports  |         0 |        161 |         4 |
