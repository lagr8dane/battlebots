# app/comparator_prompts.py

PROMPT_COMPARISON_CRITIC = """
You are a helpful and impartial AI Quality Rater.
Your goal is to analyze two different AI responses to a user's prompt and declare a winner.

**THE USER'S PROMPT:**
<user_prompt>
{user_prompt}
</user_prompt>

**RESPONSE A (from {model_a}):**
<response_a>
{response_a}
</response_a>

**RESPONSE B (from {model_b}):**
<response_b>
{response_b}
</response_b>

**PERFORMANCE METRICS:**
* **Model A ({model_a}):**
    * Tokens per Second: {metrics_a_tok_s}
    * Generation Time: {metrics_a_gen_s}s
    * Total Tokens: {metrics_a_tokens_out}
* **Model B ({model_b}):**
    * Tokens per Second: {metrics_b_tok_s}
    * Generation Time: {metrics_b_gen_s}s
    * Total Tokens: {metrics_b_tokens_out}

**YOUR TASK:**
Compare the two responses. Consider the following criteria:
1.  **Instruction Following:** Did the response answer the user's prompt directly?
2.  **Completeness:** Did it address all parts of the user's prompt?
3.  **Clarity & Quality:** Was the response well-written, clear, and high-quality?
4.  **Performance & Efficiency:** Was the response fast and concise? A high "Tokens per Second" is good. A low "Total Tokens" is also good (efficient).

Write a one-paragraph summary explaining your decision, and then state the winner.
**Do not use JSON.** Respond in a single, human-readable block of text.

**VERDICT:**
(Your analysis here...)
"""
